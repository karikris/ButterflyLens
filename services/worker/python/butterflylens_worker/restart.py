"""Append-only committed-work idempotency and offline public projection."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Literal, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json


RESTART_JOURNAL_SCHEMA_VERSION = "butterflylens-committed-work:v1.0.0"
RESUME_PLAN_SCHEMA_VERSION = "butterflylens-resume-plan:v1.0.0"
PUBLIC_OFFLINE_SCHEMA_VERSION = "butterflylens-public-offline:v1.0.0"
WorkKind = Literal["api_call", "download", "embedding", "artifact_commit"]
WORK_KINDS = frozenset({"api_call", "download", "embedding", "artifact_commit"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RestartError(RuntimeError):
    """Raised when restart state could repeat work or hide committed evidence."""


@dataclass(frozen=True)
class WorkItem:
    kind: WorkKind
    input_fingerprint: str


class CommittedWorkJournal:
    """Private append-only journal reconstructed on every process start."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._records = self._load()

    def decision(self, item: WorkItem) -> dict[str, object]:
        work_id = _work_id(item)
        existing = self._records.get(work_id)
        return {
            "work_id": work_id,
            "kind": item.kind,
            "input_fingerprint": item.input_fingerprint,
            "action": "reuse_committed" if existing is not None else "execute",
            "committed_record": None if existing is None else deepcopy(existing),
        }

    def record_commit(
        self,
        item: WorkItem,
        *,
        output_fingerprint: str,
        committed_at: datetime,
        acknowledgement: Mapping[str, object],
    ) -> dict[str, object]:
        _validate_item(item)
        _require_sha(output_fingerprint, "output fingerprint")
        _require_utc(committed_at, "commit time")
        if (
            acknowledgement.get("storage_state") != "persisted"
            or acknowledgement.get("output_fingerprint") != output_fingerprint
        ):
            raise RestartError("durable work acknowledgement is incomplete")
        work_id = _work_id(item)
        existing = self._records.get(work_id)
        if existing is not None:
            if existing["output_fingerprint"] != output_fingerprint:
                raise RestartError("committed work identity has conflicting output")
            return deepcopy(existing)
        preimage = {
            "schema_version": RESTART_JOURNAL_SCHEMA_VERSION,
            "work_id": work_id,
            "kind": item.kind,
            "input_fingerprint": item.input_fingerprint,
            "output_fingerprint": output_fingerprint,
            "committed_at": _utc_text(committed_at),
        }
        record = {**preimage, "record_fingerprint": _digest(preimage)}
        persisted = self._append(record)
        self._records[work_id] = persisted
        return deepcopy(persisted)

    def _load(self) -> dict[str, dict[str, object]]:
        if not self.path.exists():
            return {}
        try:
            metadata = self.path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or self.path.is_symlink():
                raise RestartError("committed-work journal must be a regular file")
            if stat.S_IMODE(metadata.st_mode) & 0o077:
                raise RestartError("committed-work journal permissions are too broad")
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise RestartError("committed-work journal is unreadable") from error
        records: dict[str, dict[str, object]] = {}
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise RestartError("committed-work journal contains invalid JSON") from error
            _validate_record(record)
            work_id = str(record["work_id"])
            if work_id in records:
                raise RestartError("committed-work journal contains duplicate work")
            records[work_id] = record
        return records

    def _append(self, record: Mapping[str, object]) -> dict[str, object]:
        encoded = canonicalize_json(record) + b"\n"
        flags = os.O_APPEND | os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags, 0o600)
            with os.fdopen(descriptor, "a+b") as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
                    raise RestartError("committed-work journal is not private")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.seek(0)
                persisted = _decode_records(handle.read().decode("utf-8"))
                existing = persisted.get(str(record["work_id"]))
                if existing is not None:
                    if existing["output_fingerprint"] != record["output_fingerprint"]:
                        raise RestartError("committed work identity has conflicting output")
                    return existing
                handle.seek(0, os.SEEK_END)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                return dict(record)
        except UnicodeDecodeError as error:
            raise RestartError("committed-work journal is not UTF-8") from error
        except OSError as error:
            raise RestartError("committed-work journal append failed") from error


def build_resume_plan(
    items: list[WorkItem],
    *,
    lease_fingerprint: str,
    checkpoint_fingerprint: str,
    journal: CommittedWorkJournal,
) -> dict[str, object]:
    _require_sha(lease_fingerprint, "lease fingerprint")
    _require_sha(checkpoint_fingerprint, "checkpoint fingerprint")
    decisions = [journal.decision(item) for item in items]
    work_ids = [str(row["work_id"]) for row in decisions]
    if len(work_ids) != len(set(work_ids)):
        raise RestartError("resume inventory contains duplicate semantic work")
    preimage = {
        "schema_version": RESUME_PLAN_SCHEMA_VERSION,
        "lease_fingerprint": lease_fingerprint,
        "checkpoint_fingerprint": checkpoint_fingerprint,
        "decisions": decisions,
    }
    return {
        **preimage,
        "execute_count": sum(row["action"] == "execute" for row in decisions),
        "reuse_count": sum(row["action"] == "reuse_committed" for row in decisions),
        "resume_fingerprint": _digest(preimage),
    }


def build_public_offline_projection(
    *,
    submitted_snapshot: Mapping[str, object],
    committed_live_snapshot: Mapping[str, object] | None,
    heartbeat_observed_at: datetime | None,
    as_of: datetime,
    stale_after: timedelta,
) -> dict[str, object]:
    """Keep immutable/committed data available independently of worker liveness."""

    _require_utc(as_of, "projection time")
    if stale_after <= timedelta(0):
        raise RestartError("stale horizon must be positive")
    submitted = _validate_snapshot(submitted_snapshot, expected_mode="submitted")
    live = (
        None
        if committed_live_snapshot is None
        else _validate_snapshot(committed_live_snapshot, expected_mode="live")
    )
    if heartbeat_observed_at is not None:
        _require_utc(heartbeat_observed_at, "heartbeat time")
        if heartbeat_observed_at > as_of:
            raise RestartError("heartbeat cannot be in the future")
    online = (
        heartbeat_observed_at is not None
        and as_of - heartbeat_observed_at <= stale_after
    )
    current = live or submitted
    preimage = {
        "schema_version": PUBLIC_OFFLINE_SCHEMA_VERSION,
        "as_of": _utc_text(as_of),
        "worker_status": "online" if online else "offline",
        "current_snapshot": current,
        "submitted_snapshot": submitted,
        "committed_live_snapshot": live,
        "site_available": True,
        "committed_data_queryable": True,
        "live_is_stale": live is not None and not online,
    }
    return {**preimage, "projection_fingerprint": _digest(preimage)}


def _validate_snapshot(
    snapshot: Mapping[str, object], *, expected_mode: str
) -> dict[str, object]:
    record = deepcopy(dict(snapshot))
    if set(record) != {"snapshot_id", "mode", "artifact_fingerprint", "query_uri"}:
        raise RestartError("public snapshot fields are not exact")
    if record["mode"] != expected_mode:
        raise RestartError("public snapshot mode is invalid")
    _require_sha(record["artifact_fingerprint"], "snapshot artifact fingerprint")
    if not isinstance(record["snapshot_id"], str) or not record["snapshot_id"]:
        raise RestartError("public snapshot identity is invalid")
    if not isinstance(record["query_uri"], str) or not record["query_uri"].startswith("/"):
        raise RestartError("public snapshot query URI is invalid")
    return record


def _work_id(item: WorkItem) -> str:
    _validate_item(item)
    return f"blwk:v1:{_digest({'kind': item.kind, 'input_fingerprint': item.input_fingerprint})[:24]}"


def _validate_item(item: WorkItem) -> None:
    if item.kind not in WORK_KINDS:
        raise RestartError("work kind is invalid")
    _require_sha(item.input_fingerprint, "work input fingerprint")


def _validate_record(record: object) -> None:
    if not isinstance(record, dict) or set(record) != {
        "schema_version", "work_id", "kind", "input_fingerprint",
        "output_fingerprint", "committed_at", "record_fingerprint",
    }:
        raise RestartError("committed-work record fields are not exact")
    if record["schema_version"] != RESTART_JOURNAL_SCHEMA_VERSION:
        raise RestartError("committed-work record version is unsupported")
    item = WorkItem(str(record["kind"]), str(record["input_fingerprint"]))  # type: ignore[arg-type]
    if record["work_id"] != _work_id(item):
        raise RestartError("committed-work ID is invalid")
    _require_sha(record["output_fingerprint"], "output fingerprint")
    _parse_utc_text(record["committed_at"], "commit time")
    preimage = {key: value for key, value in record.items() if key != "record_fingerprint"}
    if record["record_fingerprint"] != _digest(preimage):
        raise RestartError("committed-work record fingerprint mismatch")


def _decode_records(value: str) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    for line in value.splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RestartError("committed-work journal contains invalid JSON") from error
        _validate_record(record)
        work_id = str(record["work_id"])
        if work_id in records:
            raise RestartError("committed-work journal contains duplicate work")
        records[work_id] = record
    return records


def _require_sha(value: object, field: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RestartError(f"{field} must be lowercase SHA-256")


def _require_utc(value: datetime, field: str) -> None:
    if value.tzinfo != timezone.utc:
        raise RestartError(f"{field} must use UTC")


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc_text(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RestartError(f"{field} must use canonical UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise RestartError(f"{field} is invalid") from error
    _require_utc(parsed, field)
    if _utc_text(parsed) != value:
        raise RestartError(f"{field} must use canonical UTC")
    return parsed


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
