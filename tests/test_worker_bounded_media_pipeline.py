from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens_worker import (  # noqa: E402
    BoundedStageQueue,
    MediaInput,
    MediaPipelineError,
    MediaPipelinePolicy,
    UNFINISHED_MODEL_STAGES,
    run_bounded_media_pipeline,
)


JPEG_A = b"\xff\xd8\xff\xe0" + b"a" * 28
JPEG_B = b"\xff\xd8\xff\xe1" + b"b" * 36


class MemoryStore:
    def __init__(self, *, corrupt_kind: str | None = None) -> None:
        self.records: list[dict[str, object]] = []
        self.corrupt_kind = corrupt_kind

    def commit_file(
        self, *, artifact_kind: str, path: Path, content_sha256: str
    ) -> dict[str, object]:
        self.assert_file(path, content_sha256)
        record = {
            "storage_state": "persisted",
            "artifact_kind": artifact_kind,
            "content_sha256": (
                "f" * 64 if artifact_kind == self.corrupt_kind else content_sha256
            ),
            "storage_version": f"memory:{len(self.records) + 1}",
        }
        self.records.append(deepcopy(record))
        return record

    @staticmethod
    def assert_file(path: Path, expected: str) -> None:
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


def media(path: Path, record_id: str, payload: bytes) -> MediaInput:
    path.write_bytes(payload)
    return MediaInput(
        media_record_id=record_id,
        source_record_fingerprint=hashlib.sha256(record_id.encode()).hexdigest(),
        local_path=path,
        content_sha256=hashlib.sha256(payload).hexdigest(),
        media_type="image/jpeg",
        metadata={"provider": "fixture", "record_id": record_id},
    )


class WorkerBoundedMediaPipelineTests(unittest.TestCase):
    def test_queue_enforces_record_and_byte_capacity(self) -> None:
        queue = BoundedStageQueue(name="fixture", max_records=2, max_bytes=5)
        queue.put("a", byte_count=2)
        queue.put("b", byte_count=3)
        with self.assertRaisesRegex(MediaPipelineError, "record capacity"):
            queue.put("c", byte_count=0)
        self.assertEqual(queue.get(), "a")
        with self.assertRaisesRegex(MediaPipelineError, "byte capacity"):
            queue.put("c", byte_count=3)
        self.assertEqual(queue.high_water_records, 2)
        self.assertEqual(queue.high_water_bytes, 5)

    def test_pipeline_deduplicates_commits_parquet_then_cleans_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = media(root / "first.jpg", "media:1", JPEG_A)
            duplicate = media(root / "duplicate.jpg", "media:2", JPEG_A)
            second = media(root / "second.jpg", "media:3", JPEG_B)
            store = MemoryStore()
            result = run_bounded_media_pipeline(
                [first, duplicate, second],
                work_dir=root / "work",
                store=store,
                policy=MediaPipelinePolicy(
                    max_queue_records=4,
                    max_queue_bytes=1024,
                    rolling_prefetch_batches=0,
                    parquet_batch_records=4,
                ),
            )
            parts = sorted((root / "work/checkpoints").glob("*.parquet"))
            table = pq.read_table(parts)
            checkpoint = json.loads(
                (root / "work/checkpoints/media-admission.checkpoint.json").read_text()
            )
            remaining = [path.exists() for path in (first.local_path, duplicate.local_path, second.local_path)]

        self.assertEqual(table.num_rows, 3)
        self.assertEqual(table.column("is_content_duplicate").to_pylist(), [False, True, False])
        self.assertEqual(result["unique_content_count"], 2)
        self.assertEqual(result["duplicate_content_count"], 1)
        self.assertEqual(result["cache_paths_deleted"], 3)
        self.assertEqual(remaining, [False, False, False])
        self.assertEqual([row["artifact_kind"] for row in store.records], [
            "source_media",
            "source_media",
            "parquet_checkpoint",
            "checkpoint_manifest",
        ])
        self.assertEqual(result["model_stage_status"], UNFINISHED_MODEL_STAGES)
        self.assertEqual(checkpoint["model_stage_status"], UNFINISHED_MODEL_STAGES)
        self.assertEqual(result["input_acquisition"], "caller_supplied_local_no_network")
        self.assertEqual(len(result["parquet_parts"]), 1)
        self.assertFalse(result["scientific_claim_allowed"])

    def test_incomplete_durable_acknowledgement_preserves_every_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = media(root / "first.jpg", "media:1", JPEG_A)
            second = media(root / "second.jpg", "media:2", JPEG_B)
            with self.assertRaisesRegex(MediaPipelineError, "acknowledgement"):
                run_bounded_media_pipeline(
                    [first, second],
                    work_dir=root / "work",
                    store=MemoryStore(corrupt_kind="parquet_checkpoint"),
                    policy=MediaPipelinePolicy(max_queue_records=4, max_queue_bytes=1024, parquet_batch_records=4),
                )
            self.assertTrue(first.local_path.exists())
            self.assertTrue(second.local_path.exists())

    def test_oversized_checksum_mismatch_and_type_mismatch_fail_before_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = media(root / "valid.jpg", "media:1", JPEG_A)
            with self.assertRaisesRegex(MediaPipelineError, "byte capacity"):
                run_bounded_media_pipeline(
                    [valid],
                    work_dir=root / "oversized",
                    store=MemoryStore(),
                    policy=MediaPipelinePolicy(max_queue_records=1, max_queue_bytes=8, parquet_batch_records=1),
                )
            self.assertTrue(valid.local_path.exists())

            wrong_hash = MediaInput(**{**valid.__dict__, "content_sha256": "0" * 64})
            with self.assertRaisesRegex(MediaPipelineError, "checksum mismatch"):
                run_bounded_media_pipeline([wrong_hash], work_dir=root / "hash", store=MemoryStore())
            wrong_type = MediaInput(**{**valid.__dict__, "media_type": "image/png"})
            with self.assertRaisesRegex(MediaPipelineError, "declared type"):
                run_bounded_media_pipeline([wrong_type], work_dir=root / "type", store=MemoryStore())

    def test_parquet_rows_flush_in_bounded_parts_and_prefetch_requires_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = [
                media(root / f"{index}.jpg", f"media:{index}", JPEG_A + bytes([index]))
                for index in range(3)
            ]
            result = run_bounded_media_pipeline(
                inputs,
                work_dir=root / "work",
                store=MemoryStore(),
                policy=MediaPipelinePolicy(
                    max_queue_records=2,
                    max_queue_bytes=1024,
                    parquet_batch_records=2,
                ),
            )
            self.assertEqual(
                [part["row_count"] for part in result["parquet_parts"]], [2, 1]
            )
        with self.assertRaisesRegex(MediaPipelineError, "until measured useful"):
            MediaPipelinePolicy(rolling_prefetch_batches=4).validate()

    def test_pipeline_source_has_no_transport_or_model_execution(self) -> None:
        source = (
            ROOT / "services/worker/python/butterflylens_worker/media_pipeline.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import httpx",
            "import aiohttp",
            "urllib",
            "from_pretrained",
            "load_state_dict",
            "torch",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"yoloe": "unfinished_not_run"', source)
        self.assertIn('"bioclip": "unfinished_not_run"', source)


if __name__ == "__main__":
    unittest.main()
