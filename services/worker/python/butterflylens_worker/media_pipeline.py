"""Bounded, model-free media admission and durable checkpoint pipeline."""

from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping, Protocol

import pyarrow as pa
import pyarrow.parquet as pq

from butterflylens.contracts.fingerprint import canonicalize_json


MEDIA_PIPELINE_SCHEMA_VERSION = "butterflylens-bounded-media-pipeline:v1.0.0"
UNFINISHED_MODEL_STAGES = {
    "yoloe": "unfinished_not_run",
    "full_frame": "unfinished_not_run",
    "bioclip": "unfinished_not_run",
    "scoring": "unfinished_not_run",
}
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class MediaPipelineError(RuntimeError):
    """Raised before bounds, durability, or source preservation can weaken."""


class DurableArtifactStore(Protocol):
    def commit_file(
        self, *, artifact_kind: str, path: Path, content_sha256: str
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class MediaInput:
    media_record_id: str
    source_record_fingerprint: str
    local_path: Path
    content_sha256: str
    media_type: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class MediaPipelinePolicy:
    max_queue_records: int = 512
    max_queue_bytes: int = 2 * 1024**3
    rolling_prefetch_batches: int = 0
    parquet_batch_records: int = 500

    def validate(self) -> None:
        if self.max_queue_records < 1 or self.max_queue_bytes < 1:
            raise MediaPipelineError("queue bounds must be positive")
        if not 0 <= self.rolling_prefetch_batches <= 4:
            raise MediaPipelineError("rolling prefetch must be zero to four")
        if self.rolling_prefetch_batches != 0:
            raise MediaPipelineError("rolling prefetch is disabled until measured useful")
        if not 1 <= self.parquet_batch_records <= self.max_queue_records:
            raise MediaPipelineError("Parquet batch size exceeds record capacity")


class BoundedStageQueue:
    """Deterministic queue whose record and byte limits are both hard."""

    def __init__(self, *, name: str, max_records: int, max_bytes: int) -> None:
        self.name = name
        self.max_records = max_records
        self.max_bytes = max_bytes
        self._items: deque[tuple[object, int]] = deque()
        self.byte_count = 0
        self.high_water_records = 0
        self.high_water_bytes = 0

    def put(self, item: object, *, byte_count: int) -> None:
        if byte_count < 0:
            raise MediaPipelineError("queue byte count cannot be negative")
        if len(self._items) + 1 > self.max_records:
            raise MediaPipelineError(f"{self.name} record capacity exceeded")
        if self.byte_count + byte_count > self.max_bytes:
            raise MediaPipelineError(f"{self.name} byte capacity exceeded")
        self._items.append((item, byte_count))
        self.byte_count += byte_count
        self.high_water_records = max(self.high_water_records, len(self._items))
        self.high_water_bytes = max(self.high_water_bytes, self.byte_count)

    def get(self) -> object:
        if not self._items:
            raise MediaPipelineError(f"{self.name} queue is empty")
        item, byte_count = self._items.popleft()
        self.byte_count -= byte_count
        return item

    def __bool__(self) -> bool:
        return bool(self._items)


def run_bounded_media_pipeline(
    inputs: list[MediaInput],
    *,
    work_dir: Path,
    store: DurableArtifactStore,
    policy: MediaPipelinePolicy | None = None,
) -> dict[str, object]:
    """Validate local media, deduplicate, checkpoint, commit, then clean cache."""

    selected = policy or MediaPipelinePolicy()
    selected.validate()
    if not inputs:
        raise MediaPipelineError("media pipeline requires at least one input")
    work_dir = Path(work_dir)
    work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    queues = {
        name: BoundedStageQueue(
            name=name,
            max_records=selected.max_queue_records,
            max_bytes=selected.max_queue_bytes,
        )
        for name in (
            "metadata",
            "download",
            "media_validation",
            "deduplication",
            "artifact_commit",
            "cache_cleanup",
        )
    }
    seen_record_ids: set[str] = set()
    canonical_by_digest: dict[str, str] = {}
    rows: list[dict[str, object]] = []
    parquet_parts: list[dict[str, object]] = []
    unique_inputs: list[MediaInput] = []
    for item in inputs:
        size = _validate_input(item, seen_record_ids)
        queues["metadata"].put(item, byte_count=len(canonicalize_json(item.metadata)))
        metadata_item = queues["metadata"].get()
        queues["download"].put(metadata_item, byte_count=size)
        downloaded = queues["download"].get()
        queues["media_validation"].put(downloaded, byte_count=size)
        validated = queues["media_validation"].get()
        queues["deduplication"].put(validated, byte_count=size)
        admitted = queues["deduplication"].get()
        assert isinstance(admitted, MediaInput)
        canonical_id = canonical_by_digest.setdefault(
            admitted.content_sha256, admitted.media_record_id
        )
        duplicate = canonical_id != admitted.media_record_id
        if not duplicate:
            unique_inputs.append(admitted)
        rows.append(
            {
                "media_record_id": admitted.media_record_id,
                "source_record_fingerprint": admitted.source_record_fingerprint,
                "content_sha256": admitted.content_sha256,
                "media_type": admitted.media_type,
                "byte_count": size,
                "canonical_media_record_id": canonical_id,
                "is_content_duplicate": duplicate,
                "metadata_json": canonicalize_json(admitted.metadata).decode(),
                "evidence_state": "media_validated_unreviewed",
            }
        )
        if len(rows) == selected.parquet_batch_records:
            _flush_parquet_part(work_dir, rows, parquet_parts)
    if rows:
        _flush_parquet_part(work_dir, rows, parquet_parts)
    committed: list[dict[str, object]] = []
    for item in unique_inputs:
        queues["artifact_commit"].put(item, byte_count=item.local_path.stat().st_size)
        queued = queues["artifact_commit"].get()
        assert isinstance(queued, MediaInput)
        committed.append(
            _commit_exact(
                store,
                artifact_kind="source_media",
                path=queued.local_path,
                content_sha256=queued.content_sha256,
            )
        )
    for part in parquet_parts:
        committed.append(
            _commit_exact(
                store,
                artifact_kind="parquet_checkpoint",
                path=Path(str(part["path"])),
                content_sha256=str(part["content_sha256"]),
            )
        )
    checkpoint_preimage = {
        "schema_version": MEDIA_PIPELINE_SCHEMA_VERSION,
        "policy": asdict(selected),
        "input_count": len(inputs),
        "unique_content_count": len(unique_inputs),
        "duplicate_content_count": len(inputs) - len(unique_inputs),
        "parquet_parts": parquet_parts,
        "media_sha256": sorted(item.content_sha256 for item in unique_inputs),
        "input_acquisition": "caller_supplied_local_no_network",
        "model_stage_status": UNFINISHED_MODEL_STAGES,
    }
    checkpoint_fingerprint = _digest(checkpoint_preimage)
    checkpoint = {
        **checkpoint_preimage,
        "checkpoint_fingerprint": checkpoint_fingerprint,
        "scientific_claim_allowed": False,
    }
    checkpoint_path = work_dir / "checkpoints" / "media-admission.checkpoint.json"
    _write_bytes_atomic(checkpoint_path, canonicalize_json(checkpoint) + b"\n")
    checkpoint_sha256 = _file_sha256(checkpoint_path)
    committed.append(
        _commit_exact(
            store,
            artifact_kind="checkpoint_manifest",
            path=checkpoint_path,
            content_sha256=checkpoint_sha256,
        )
    )
    deleted = 0
    cleanup_items = {item.local_path: item for item in inputs}
    for item in cleanup_items.values():
        queues["cache_cleanup"].put(item, byte_count=item.local_path.stat().st_size)
        cleanup = queues["cache_cleanup"].get()
        assert isinstance(cleanup, MediaInput)
        cleanup.local_path.unlink()
        deleted += 1
    return {
        **checkpoint,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha256,
        "durable_commit_receipts": tuple(committed),
        "cache_paths_deleted": deleted,
        "queue_high_water": {
            name: {
                "records": queue.high_water_records,
                "bytes": queue.high_water_bytes,
            }
            for name, queue in queues.items()
        },
        "execution_state": "durably_checkpointed",
    }


def _validate_input(item: MediaInput, record_ids: set[str]) -> int:
    if _STABLE_ID.fullmatch(item.media_record_id) is None or item.media_record_id in record_ids:
        raise MediaPipelineError("media record ID is invalid or duplicated")
    record_ids.add(item.media_record_id)
    if _SHA256.fullmatch(item.source_record_fingerprint) is None:
        raise MediaPipelineError("source record fingerprint is invalid")
    if _SHA256.fullmatch(item.content_sha256) is None:
        raise MediaPipelineError("media content fingerprint is invalid")
    if item.media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise MediaPipelineError("media type is not admitted")
    if not item.local_path.is_file() or item.local_path.is_symlink():
        raise MediaPipelineError("local media must be a regular file")
    if _file_sha256(item.local_path) != item.content_sha256:
        raise MediaPipelineError("local media checksum mismatch")
    _validate_media_signature(item.local_path, item.media_type)
    size = item.local_path.stat().st_size
    if size < 1:
        raise MediaPipelineError("local media is empty")
    if not isinstance(item.metadata, Mapping):
        raise MediaPipelineError("media metadata is invalid")
    canonicalize_json(item.metadata)
    return size


def _validate_media_signature(path: Path, media_type: str) -> None:
    with path.open("rb") as handle:
        prefix = handle.read(16)
    valid = (
        (media_type == "image/jpeg" and prefix.startswith(b"\xff\xd8\xff"))
        or (media_type == "image/png" and prefix.startswith(b"\x89PNG\r\n\x1a\n"))
        or (
            media_type == "image/webp"
            and prefix.startswith(b"RIFF")
            and prefix[8:12] == b"WEBP"
        )
    )
    if not valid:
        raise MediaPipelineError("media bytes do not match the declared type")


def _commit_exact(
    store: DurableArtifactStore,
    *,
    artifact_kind: str,
    path: Path,
    content_sha256: str,
) -> dict[str, object]:
    acknowledgement = dict(
        store.commit_file(
            artifact_kind=artifact_kind,
            path=path,
            content_sha256=content_sha256,
        )
    )
    if (
        acknowledgement.get("storage_state") != "persisted"
        or acknowledgement.get("artifact_kind") != artifact_kind
        or acknowledgement.get("content_sha256") != content_sha256
    ):
        raise MediaPipelineError("durable artifact acknowledgement is incomplete")
    return deepcopy(acknowledgement)


def _write_parquet_atomic(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".parquet-", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        table = pa.Table.from_pylist(rows)
        pq.write_table(table, temporary, compression="zstd")
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".checkpoint-", dir=path.parent)
    temporary = Path(name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _flush_parquet_part(
    work_dir: Path,
    rows: list[dict[str, object]],
    parts: list[dict[str, object]],
) -> None:
    part_path = (
        work_dir
        / "checkpoints"
        / f"media-admission-{len(parts):05d}.parquet"
    )
    row_count = len(rows)
    _write_parquet_atomic(part_path, rows)
    parts.append(
        {
            "path": str(part_path),
            "content_sha256": _file_sha256(part_path),
            "row_count": row_count,
        }
    )
    rows.clear()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
