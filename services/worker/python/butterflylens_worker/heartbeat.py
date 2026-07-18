"""Lease-aware append-only worker heartbeats and graceful shutdown state."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib
from pathlib import Path
import re
import resource
import shutil
from typing import Callable, Mapping, Protocol, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json
from butterflylens.contracts.live_worker import WORKER_HEARTBEAT_SCHEMA_VERSION


_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STATES = frozenset({"starting", "idle", "leased", "running", "paused", "draining", "degraded"})


class HeartbeatError(ValueError):
    """Raised when worker state cannot be reported without weakening fencing."""


class HeartbeatSink(Protocol):
    def append_heartbeat(self, heartbeat: Mapping[str, object]) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class LeaseSnapshot:
    lease_id: str
    project_id: str
    run_id: str
    stage_id: str
    worker_id: str
    revision: int
    expires_at: datetime


class WorkerHeartbeatEmitter:
    """Create monotonic heartbeats and close only after lease release."""

    def __init__(
        self,
        identity: Mapping[str, object],
        *,
        free_disk_path: Path,
        sink: HeartbeatSink | None = None,
        resource_probe: Callable[[Path], Mapping[str, int | None]] | None = None,
    ) -> None:
        self._identity = deepcopy(dict(identity))
        self._worker_id = str(identity.get("worker_id", ""))
        if _STABLE_ID.fullmatch(self._worker_id) is None:
            raise HeartbeatError("worker identity is invalid")
        fingerprint = identity.get("identity_fingerprint")
        if not isinstance(fingerprint, str) or _SHA256.fullmatch(fingerprint) is None:
            raise HeartbeatError("worker identity fingerprint is invalid")
        self._free_disk_path = Path(free_disk_path)
        self._sink = sink
        self._resource_probe = resource_probe or collect_resources
        self._sequence = 0
        self._state = "starting"
        self._lease: LeaseSnapshot | None = None
        self._stage_id: str | None = None
        self._shutdown_requested = False
        self._closed = False
        self._last_observed_at: datetime | None = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def shutdown_requested(self) -> bool:
        return self._shutdown_requested

    def mark_idle(self) -> None:
        self._require_open()
        if self._shutdown_requested:
            raise HeartbeatError("shutdown is already draining")
        if self._lease is not None:
            raise HeartbeatError("cannot become idle while a lease is attached")
        self._state = "idle"
        self._stage_id = None

    def attach_lease(self, lease: LeaseSnapshot) -> None:
        self._require_open()
        if self._shutdown_requested:
            raise HeartbeatError("draining worker cannot acquire a lease")
        _validate_lease(lease, self._worker_id)
        if self._lease is not None:
            raise HeartbeatError("worker already has an attached lease")
        self._lease = lease
        self._stage_id = lease.stage_id
        self._state = "leased"

    def mark_running(self, stage_id: str) -> None:
        self._require_open()
        if self._shutdown_requested:
            raise HeartbeatError("draining worker cannot start a stage")
        if self._lease is None or stage_id != self._lease.stage_id:
            raise HeartbeatError("running stage is not protected by the attached lease")
        self._stage_id = stage_id
        self._state = "running"

    def release_lease(
        self,
        *,
        checkpoint_fingerprint: str | None,
        acknowledgement: Mapping[str, object],
    ) -> None:
        self._require_open()
        if self._lease is None:
            raise HeartbeatError("worker has no lease to release")
        if checkpoint_fingerprint is not None and _SHA256.fullmatch(checkpoint_fingerprint) is None:
            raise HeartbeatError("release checkpoint fingerprint is invalid")
        if (
            acknowledgement.get("storage_state") != "persisted"
            or acknowledgement.get("lease_id") != self._lease.lease_id
            or acknowledgement.get("lease_revision") != self._lease.revision
            or acknowledgement.get("status") != "released"
            or acknowledgement.get("checkpoint_fingerprint")
            != checkpoint_fingerprint
        ):
            raise HeartbeatError("lease release acknowledgement is incomplete")
        self._lease = None
        self._stage_id = None
        self._state = "draining" if self._shutdown_requested else "idle"

    def request_graceful_shutdown(self) -> None:
        self._require_open()
        self._shutdown_requested = True
        self._state = "draining"

    def emit(
        self,
        *,
        observed_at: datetime,
        queues: Sequence[Mapping[str, int | str]] = (),
        models: Sequence[Mapping[str, object]] = (),
        cache: Mapping[str, int] | None = None,
        last_committed_artifact_fingerprint: str | None = None,
        last_committed_at: datetime | None = None,
        extra_health_checks: Sequence[Mapping[str, str]] = (),
    ) -> dict[str, object]:
        self._require_open()
        _require_utc(observed_at, "heartbeat time")
        if self._last_observed_at is not None and observed_at <= self._last_observed_at:
            raise HeartbeatError("heartbeat time must increase with sequence")
        if last_committed_artifact_fingerprint is not None and _SHA256.fullmatch(last_committed_artifact_fingerprint) is None:
            raise HeartbeatError("artifact fingerprint is invalid")
        if (last_committed_artifact_fingerprint is None) != (last_committed_at is None):
            raise HeartbeatError("artifact fingerprint and commit time must appear together")
        if last_committed_at is not None:
            _require_utc(last_committed_at, "artifact commit time")
            if last_committed_at > observed_at or last_committed_artifact_fingerprint is None:
                raise HeartbeatError("artifact commit lineage is invalid")
        lease = self._lease
        state = self._state
        health_checks = [dict(check) for check in extra_health_checks]
        if lease is not None and observed_at >= lease.expires_at:
            state = "degraded"
            health_checks.append(
                {
                    "check_id": "lease-expiry",
                    "status": "fail",
                    "message": "attached lease has expired; fenced work must stop",
                }
            )
        elif lease is not None:
            health_checks.append(
                {
                    "check_id": "lease-expiry",
                    "status": "pass",
                    "message": "attached lease remains within its observed expiry",
                }
            )
        if self._shutdown_requested:
            health_checks.append(
                {
                    "check_id": "graceful-shutdown",
                    "status": "pass" if lease is None else "warn",
                    "message": (
                        "shutdown drain is complete and no lease remains"
                        if lease is None
                        else "shutdown requested; attached lease must checkpoint and release"
                    ),
                }
            )
        self._sequence += 1
        preimage = {
            "schema_version": WORKER_HEARTBEAT_SCHEMA_VERSION,
            "worker_id": self._worker_id,
            "sequence": self._sequence,
            "observed_at": _utc_text(observed_at),
            "state": state,
            "project_id": None if lease is None else lease.project_id,
            "run_id": None if lease is None else lease.run_id,
            "lease_id": None if lease is None else lease.lease_id,
            "lease_revision": None if lease is None else lease.revision,
            "lease_expires_at": None if lease is None else _utc_text(lease.expires_at),
            "current_stage_id": self._stage_id,
            "resources": dict(self._resource_probe(self._free_disk_path)),
            "queues": [dict(queue) for queue in queues],
            "models": [dict(model) for model in models],
            "cache": dict(cache or {"entry_count": 0, "byte_count": 0, "hit_count": 0, "miss_count": 0}),
            "last_committed_artifact_fingerprint": last_committed_artifact_fingerprint,
            "last_committed_at": None if last_committed_at is None else _utc_text(last_committed_at),
            "health_checks": health_checks,
            "scientific_claim_allowed": False,
        }
        fingerprint = _digest(preimage)
        heartbeat = {
            **preimage,
            "heartbeat_id": f"blwh:v1:{fingerprint[:24]}",
            "heartbeat_fingerprint": fingerprint,
        }
        _validate_heartbeat_shape(heartbeat)
        self._last_observed_at = observed_at
        if self._sink is not None:
            acknowledgement = self._sink.append_heartbeat(deepcopy(heartbeat))
            if (
                acknowledgement.get("heartbeat_id") != heartbeat["heartbeat_id"]
                or acknowledgement.get("heartbeat_fingerprint") != fingerprint
                or acknowledgement.get("storage_state") != "persisted"
            ):
                raise HeartbeatError("heartbeat sink acknowledgement is incomplete")
        return heartbeat

    def complete_graceful_shutdown(self, *, observed_at: datetime) -> dict[str, object]:
        self._require_open()
        if not self._shutdown_requested:
            raise HeartbeatError("graceful shutdown was not requested")
        if self._lease is not None:
            raise HeartbeatError("cannot complete shutdown while a lease remains attached")
        heartbeat = self.emit(observed_at=observed_at)
        self._closed = True
        return heartbeat

    def _require_open(self) -> None:
        if self._closed:
            raise HeartbeatError("worker heartbeat emitter is closed")


def collect_resources(free_disk_path: Path) -> dict[str, int | None]:
    """Observe process, optional MPS, and disk counters without loading a model."""

    process_rss = _process_rss_bytes()
    allocated: int | None = None
    reserved: int | None = None
    try:
        torch = importlib.import_module("torch")
        if bool(torch.backends.mps.is_available()):
            allocated = int(torch.mps.current_allocated_memory())
            driver_memory = getattr(torch.mps, "driver_allocated_memory", None)
            reserved = int(driver_memory()) if callable(driver_memory) else None
    except (ImportError, AttributeError, RuntimeError):
        pass
    return {
        "process_rss_bytes": max(process_rss, 0),
        "mps_allocated_bytes": allocated,
        "mps_reserved_bytes": reserved,
        "free_disk_bytes": shutil.disk_usage(free_disk_path).free,
    }


def platform_is_macos() -> bool:
    import sys

    return sys.platform == "darwin"


def _process_rss_bytes() -> int:
    if not platform_is_macos():
        try:
            resident_pages = int(Path("/proc/self/statm").read_text().split()[1])
            import os

            return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))
        except (FileNotFoundError, IndexError, OSError, ValueError):
            pass
    maximum_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(maximum_rss if platform_is_macos() else maximum_rss * 1024)


def _validate_lease(lease: LeaseSnapshot, worker_id: str) -> None:
    for value in (lease.lease_id, lease.project_id, lease.run_id, lease.stage_id, lease.worker_id):
        if _STABLE_ID.fullmatch(value) is None:
            raise HeartbeatError("lease identity is invalid")
    if lease.worker_id != worker_id:
        raise HeartbeatError("lease belongs to another worker")
    if not isinstance(lease.revision, int) or isinstance(lease.revision, bool) or lease.revision < 1:
        raise HeartbeatError("lease revision is invalid")
    _require_utc(lease.expires_at, "lease expiry")


def _validate_heartbeat_shape(heartbeat: Mapping[str, object]) -> None:
    resources = heartbeat["resources"]
    if not isinstance(resources, dict) or set(resources) != {
        "process_rss_bytes",
        "mps_allocated_bytes",
        "mps_reserved_bytes",
        "free_disk_bytes",
    }:
        raise HeartbeatError("resource probe fields are not exact")
    for field in ("process_rss_bytes", "free_disk_bytes"):
        value = resources[field]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise HeartbeatError("resource probe value is invalid")
    for field in ("mps_allocated_bytes", "mps_reserved_bytes"):
        value = resources[field]
        if value is not None and (
            not isinstance(value, int) or isinstance(value, bool) or value < 0
        ):
            raise HeartbeatError("MPS resource value is invalid")
    if heartbeat["state"] not in _STATES:
        raise HeartbeatError("heartbeat state is invalid")
    queues = heartbeat["queues"]
    if not isinstance(queues, list):
        raise HeartbeatError("heartbeat queues are invalid")
    for queue in queues:
        if not isinstance(queue, dict) or set(queue) != {
            "stage_id",
            "record_count",
            "byte_count",
            "capacity_records",
            "capacity_bytes",
        }:
            raise HeartbeatError("heartbeat queue fields are not exact")
        if not isinstance(queue["stage_id"], str) or _STABLE_ID.fullmatch(queue["stage_id"]) is None:
            raise HeartbeatError("heartbeat queue stage is invalid")
        for field in ("record_count", "byte_count"):
            _require_nonnegative_integer(queue[field], f"queue {field}")
        for field in ("capacity_records", "capacity_bytes"):
            _require_positive_integer(queue[field], f"queue {field}")
    cache = heartbeat["cache"]
    if not isinstance(cache, dict) or set(cache) != {
        "entry_count",
        "byte_count",
        "hit_count",
        "miss_count",
    }:
        raise HeartbeatError("heartbeat cache fields are not exact")
    for field, value in cache.items():
        _require_nonnegative_integer(value, f"cache {field}")
    models = heartbeat["models"]
    if not isinstance(models, list):
        raise HeartbeatError("heartbeat model health is invalid")
    for model in models:
        _validate_model_health(model)
    health_checks = heartbeat["health_checks"]
    if not isinstance(health_checks, list):
        raise HeartbeatError("heartbeat health checks are invalid")
    for check in health_checks:
        if not isinstance(check, dict) or set(check) != {"check_id", "status", "message"}:
            raise HeartbeatError("heartbeat health-check fields are not exact")
        if not isinstance(check["check_id"], str) or _STABLE_ID.fullmatch(check["check_id"]) is None:
            raise HeartbeatError("heartbeat health-check identity is invalid")
        if check["status"] not in {"pass", "warn", "fail", "unavailable"}:
            raise HeartbeatError("heartbeat health-check status is invalid")
        if not isinstance(check["message"], str) or not 1 <= len(check["message"]) <= 500:
            raise HeartbeatError("heartbeat health-check message is invalid")


def _validate_model_health(model: object) -> None:
    if not isinstance(model, dict) or set(model) != {
        "role",
        "model_fingerprint",
        "status",
        "loaded_at",
        "last_check_at",
        "device",
        "message",
    }:
        raise HeartbeatError("model health fields are not exact")
    if model["role"] not in {"yoloe_router", "bioclip_embedder"}:
        raise HeartbeatError("model health role is invalid")
    fingerprint = model["model_fingerprint"]
    if fingerprint is not None and (
        not isinstance(fingerprint, str) or _SHA256.fullmatch(fingerprint) is None
    ):
        raise HeartbeatError("model health fingerprint is invalid")
    if model["status"] not in {
        "not_configured",
        "not_loaded",
        "loading",
        "healthy",
        "degraded",
        "blocked",
    }:
        raise HeartbeatError("model health status is invalid")
    if model["device"] not in {None, "mps", "cpu"}:
        raise HeartbeatError("model health device is invalid")
    for field in ("loaded_at", "last_check_at"):
        value = model[field]
        if field == "loaded_at" and value is None:
            continue
        _parse_utc_text(value, f"model health {field}")
    message = model["message"]
    if message is not None and (
        not isinstance(message, str) or not 1 <= len(message) <= 500
    ):
        raise HeartbeatError("model health message is invalid")


def _require_nonnegative_integer(value: object, field: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise HeartbeatError(f"{field} is invalid")


def _require_positive_integer(value: object, field: str) -> None:
    _require_nonnegative_integer(value, field)
    if value < 1:
        raise HeartbeatError(f"{field} is invalid")


def _parse_utc_text(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise HeartbeatError(f"{field} must use UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise HeartbeatError(f"{field} is invalid") from error
    _require_utc(parsed, field)
    return parsed


def _require_utc(value: datetime, field: str) -> None:
    if value.tzinfo != timezone.utc:
        raise HeartbeatError(f"{field} must use UTC")


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
