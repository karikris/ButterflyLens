from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402
from butterflylens_worker import (  # noqa: E402
    HeartbeatError,
    LeaseSnapshot,
    WorkerCapabilities,
    WorkerHeartbeatEmitter,
    build_worker_identity,
    load_or_create_registration,
    probe_machine_profile,
)


NOW = datetime(2026, 7, 18, 6, 30, tzinfo=timezone.utc)


def schemas() -> tuple[dict[str, dict[str, object]], Registry[object]]:
    loaded: dict[str, dict[str, object]] = {}
    registry: Registry[object] = Registry()
    for path in sorted((ROOT / "packages/contracts/schemas").glob("*.schema.json")):
        schema = json.loads(path.read_text(encoding="utf-8"))
        schema_id = schema["$id"]
        loaded[schema_id] = schema
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return loaded, registry


def validate(schema_id: str, record: dict[str, object]) -> None:
    loaded, registry = schemas()
    Draft202012Validator(
        loaded[schema_id], registry=registry, format_checker=FormatChecker()
    ).validate(record)


def machine_profile() -> dict[str, object]:
    return {
        "platform": "macos",
        "architecture": "arm64",
        "os_version": "macOS 27.0 synthetic fixture",
        "chip_label": "Apple M5 Pro synthetic fixture",
        "cpu_core_count": 14,
        "unified_memory_bytes": 64 * 1024**3,
        "mps_available": True,
        "mps_runtime": "torch=synthetic;mps_built=True",
    }


def capabilities() -> WorkerCapabilities:
    return WorkerCapabilities(
        supported_stage_ids=(
            "metadata",
            "download",
            "media_validation",
            "deduplication",
            "artifact_commit",
            "cache_cleanup",
        ),
        max_queue_records=512,
        max_queue_bytes=2 * 1024**3,
        rolling_prefetch_batches=2,
    )


def identity(registration_path: Path) -> dict[str, object]:
    registration = load_or_create_registration(
        registration_path,
        now=NOW,
        random_hex=lambda _: "01" * 12,
    )
    return build_worker_identity(
        registration,
        machine_profile=machine_profile(),
        capabilities=capabilities(),
        configured_models=(),
    )


def resources(_: Path) -> dict[str, int | None]:
    return {
        "process_rss_bytes": 128 * 1024**2,
        "mps_allocated_bytes": 0,
        "mps_reserved_bytes": 0,
        "free_disk_bytes": 500 * 1024**3,
    }


class MemorySink:
    def __init__(self, *, corrupt: bool = False) -> None:
        self.records: list[dict[str, object]] = []
        self.corrupt = corrupt

    def append_heartbeat(self, heartbeat: object) -> dict[str, object]:
        assert isinstance(heartbeat, dict)
        self.records.append(deepcopy(heartbeat))
        return {
            "storage_state": "persisted",
            "heartbeat_id": heartbeat["heartbeat_id"],
            "heartbeat_fingerprint": (
                "f" * 64 if self.corrupt else heartbeat["heartbeat_fingerprint"]
            ),
        }


class WorkerIdentityHeartbeatTests(unittest.TestCase):
    def test_registration_is_private_atomic_and_stable_across_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "private" / "registration.json"
            first = load_or_create_registration(
                path, now=NOW, random_hex=lambda _: "01" * 12
            )
            second = load_or_create_registration(
                path,
                now=NOW + timedelta(days=1),
                random_hex=lambda _: self.fail("restart must not generate a new ID"),
            )
            self.assertEqual(first, second)
            self.assertEqual(first.worker_id, "blw:v1:" + "01" * 12)
            self.assertEqual(first.registered_at, NOW)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_identity_is_schema_valid_fingerprinted_and_model_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            worker_identity = identity(Path(temporary) / "registration.json")
        validate("urn:butterflylens:schema:worker-identity:v1.0.0", worker_identity)
        preimage = {
            key: value
            for key, value in worker_identity.items()
            if key != "identity_fingerprint"
        }
        self.assertEqual(
            worker_identity["identity_fingerprint"],
            hashlib.sha256(canonicalize_json(preimage)).hexdigest(),
        )
        self.assertEqual(worker_identity["configured_models"], [])
        self.assertFalse(worker_identity["scientific_claim_allowed"])
        self.assertNotIn("yoloe", worker_identity["capabilities"]["supported_stage_ids"])
        self.assertNotIn("bioclip", worker_identity["capabilities"]["supported_stage_ids"])

    def test_machine_probe_uses_observation_and_does_not_infer_mps(self) -> None:
        observed = probe_machine_profile(mps_probe=lambda: (False, None))
        self.assertIn(observed["platform"], {"macos", "linux"})
        self.assertIn(observed["architecture"], {"arm64", "x86_64"})
        self.assertGreater(observed["unified_memory_bytes"], 0)
        self.assertFalse(observed["mps_available"])
        self.assertIsNone(observed["mps_runtime"])

    def test_monotonic_heartbeats_bind_lease_resources_and_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            worker_identity = identity(path / "registration.json")
            sink = MemorySink()
            emitter = WorkerHeartbeatEmitter(
                worker_identity,
                free_disk_path=path,
                sink=sink,
                resource_probe=resources,
            )
            emitter.mark_idle()
            first = emitter.emit(observed_at=NOW)
            lease = LeaseSnapshot(
                lease_id="lease:m5:1",
                project_id="project:butterflylens",
                run_id="run:pilot",
                stage_id="download",
                worker_id=str(worker_identity["worker_id"]),
                revision=3,
                expires_at=NOW + timedelta(minutes=5),
            )
            emitter.attach_lease(lease)
            emitter.mark_running("download")
            second = emitter.emit(observed_at=NOW + timedelta(seconds=30))

        for heartbeat in (first, second):
            validate("urn:butterflylens:schema:worker-heartbeat:v1.0.0", heartbeat)
            preimage = {
                key: value
                for key, value in heartbeat.items()
                if key not in {"heartbeat_id", "heartbeat_fingerprint"}
            }
            self.assertEqual(
                heartbeat["heartbeat_fingerprint"],
                hashlib.sha256(canonicalize_json(preimage)).hexdigest(),
            )
            self.assertEqual(heartbeat["models"], [])
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))
        self.assertEqual(first["state"], "idle")
        self.assertEqual(second["state"], "running")
        self.assertEqual(second["lease_revision"], 3)
        self.assertEqual(len(sink.records), 2)

    def test_expired_lease_degrades_and_forbids_unfenced_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            worker_identity = identity(path / "registration.json")
            emitter = WorkerHeartbeatEmitter(
                worker_identity,
                free_disk_path=path,
                resource_probe=resources,
            )
            emitter.attach_lease(
                LeaseSnapshot(
                    lease_id="lease:expired",
                    project_id="project:butterflylens",
                    run_id="run:pilot",
                    stage_id="download",
                    worker_id=str(worker_identity["worker_id"]),
                    revision=1,
                    expires_at=NOW + timedelta(seconds=5),
                )
            )
            with self.assertRaisesRegex(HeartbeatError, "not protected"):
                emitter.mark_running("artifact_commit")
            heartbeat = emitter.emit(observed_at=NOW + timedelta(seconds=5))
        self.assertEqual(heartbeat["state"], "degraded")
        self.assertEqual(heartbeat["health_checks"][-1]["status"], "fail")

    def test_graceful_shutdown_drains_releases_and_emits_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            worker_identity = identity(path / "registration.json")
            sink = MemorySink()
            emitter = WorkerHeartbeatEmitter(
                worker_identity,
                free_disk_path=path,
                sink=sink,
                resource_probe=resources,
            )
            emitter.attach_lease(
                LeaseSnapshot(
                    lease_id="lease:shutdown",
                    project_id="project:butterflylens",
                    run_id="run:pilot",
                    stage_id="download",
                    worker_id=str(worker_identity["worker_id"]),
                    revision=2,
                    expires_at=NOW + timedelta(minutes=5),
                )
            )
            emitter.request_graceful_shutdown()
            with self.assertRaisesRegex(HeartbeatError, "cannot acquire"):
                emitter.attach_lease(
                    LeaseSnapshot(
                        "lease:other",
                        "project:butterflylens",
                        "run:other",
                        "download",
                        str(worker_identity["worker_id"]),
                        1,
                        NOW + timedelta(minutes=5),
                    )
                )
            with self.assertRaisesRegex(HeartbeatError, "lease remains"):
                emitter.complete_graceful_shutdown(observed_at=NOW)
            with self.assertRaisesRegex(HeartbeatError, "acknowledgement"):
                emitter.release_lease(
                    checkpoint_fingerprint="a" * 64,
                    acknowledgement={"storage_state": "persisted"},
                )
            emitter.release_lease(
                checkpoint_fingerprint="a" * 64,
                acknowledgement={
                    "storage_state": "persisted",
                    "lease_id": "lease:shutdown",
                    "lease_revision": 2,
                    "status": "released",
                    "checkpoint_fingerprint": "a" * 64,
                },
            )
            final = emitter.complete_graceful_shutdown(observed_at=NOW)
            with self.assertRaisesRegex(HeartbeatError, "closed"):
                emitter.emit(observed_at=NOW + timedelta(seconds=1))
        self.assertEqual(final["state"], "draining")
        self.assertIsNone(final["lease_id"])
        self.assertEqual(final["health_checks"][-1]["status"], "pass")
        self.assertEqual(len(sink.records), 1)

    def test_incomplete_sink_acknowledgement_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            emitter = WorkerHeartbeatEmitter(
                identity(path / "registration.json"),
                free_disk_path=path,
                sink=MemorySink(corrupt=True),
                resource_probe=resources,
            )
            with self.assertRaisesRegex(HeartbeatError, "acknowledgement"):
                emitter.emit(observed_at=NOW)

    def test_heartbeat_rejects_time_regression_and_invalid_nested_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            emitter = WorkerHeartbeatEmitter(
                identity(path / "registration.json"),
                free_disk_path=path,
                resource_probe=resources,
            )
            emitter.emit(observed_at=NOW)
            with self.assertRaisesRegex(HeartbeatError, "increase with sequence"):
                emitter.emit(observed_at=NOW)
            with self.assertRaisesRegex(HeartbeatError, "queue record_count"):
                emitter.emit(
                    observed_at=NOW + timedelta(seconds=1),
                    queues=(
                        {
                            "stage_id": "download",
                            "record_count": -1,
                            "byte_count": 0,
                            "capacity_records": 1,
                            "capacity_bytes": 1,
                        },
                    ),
                )

    def test_worker_runtime_has_no_network_or_model_execution_boundary(self) -> None:
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(
                (ROOT / "services/worker/python/butterflylens_worker").glob("*.py")
            )
        )
        for forbidden in (
            "import requests",
            "import httpx",
            "import aiohttp",
            "flickr.photos",
            "from_pretrained",
            ".load_state_dict(",
        ):
            self.assertNotIn(forbidden, sources)


if __name__ == "__main__":
    unittest.main()
