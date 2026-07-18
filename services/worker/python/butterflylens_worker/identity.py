"""Stable worker registration and directly observed machine identity."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import stat
import subprocess
import tempfile
from typing import Callable, Mapping, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json
from butterflylens.contracts.live_worker import WORKER_IDENTITY_SCHEMA_VERSION


REGISTRATION_SCHEMA_VERSION = "butterflylens-worker-registration:v1.0.0"
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STAGES = frozenset(
    {
        "metadata",
        "download",
        "media_validation",
        "deduplication",
        "yoloe",
        "full_frame",
        "bioclip",
        "scoring",
        "artifact_commit",
        "cache_cleanup",
    }
)


class IdentityError(ValueError):
    """Raised when worker identity is unstable, unsafe, or untruthful."""


@dataclass(frozen=True)
class WorkerRegistration:
    worker_id: str
    registered_at: datetime


@dataclass(frozen=True)
class WorkerCapabilities:
    supported_stage_ids: tuple[str, ...]
    max_queue_records: int
    max_queue_bytes: int
    rolling_prefetch_batches: int
    checkpoint_format: str = "parquet-manifest-v1"
    graceful_shutdown_supported: bool = True

    def record(self) -> dict[str, object]:
        _validate_capabilities(self)
        return {
            **asdict(self),
            "supported_stage_ids": list(self.supported_stage_ids),
        }


def load_or_create_registration(
    path: Path,
    *,
    now: datetime,
    random_hex: Callable[[int], str] = secrets.token_hex,
) -> WorkerRegistration:
    """Atomically create or read the worker's local stable registration."""

    _require_utc(now, "registration time")
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        return _read_registration(path)
    worker_id = f"blw:v1:{random_hex(12)}"
    if _STABLE_ID.fullmatch(worker_id) is None:
        raise IdentityError("generated worker ID is invalid")
    record = {
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "worker_id": worker_id,
        "registered_at": _utc_text(now),
    }
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    temporary_path: str | None = None
    try:
        file_descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=path.parent
        )
        try:
            os.fchmod(file_descriptor, 0o600)
            with os.fdopen(file_descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary_path, path)
            except FileExistsError:
                pass
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)
    except OSError as error:
        raise IdentityError("worker registration could not be persisted") from error
    return _read_registration(path)


def probe_machine_profile(
    *,
    mps_probe: Callable[[], tuple[bool, str | None]] | None = None,
) -> dict[str, object]:
    """Observe machine facts without inferring unavailable Apple capabilities."""

    system = platform.system().casefold()
    machine = platform.machine().casefold()
    platform_name = "macos" if system == "darwin" else "linux" if system == "linux" else None
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x86_64" if machine in {"x86_64", "amd64"} else None
    if platform_name is None or architecture is None:
        raise IdentityError("worker platform or architecture is unsupported")
    available, runtime = (mps_probe or _probe_mps)()
    if not isinstance(available, bool) or (runtime is not None and not isinstance(runtime, str)):
        raise IdentityError("MPS probe returned an invalid result")
    if available and platform_name != "macos":
        raise IdentityError("MPS cannot be asserted on a non-macOS worker")
    memory = _physical_memory_bytes(platform_name)
    chip = _chip_label(platform_name)
    record = {
        "platform": platform_name,
        "architecture": architecture,
        "os_version": platform.platform(),
        "chip_label": chip,
        "cpu_core_count": os.cpu_count() or 1,
        "unified_memory_bytes": memory,
        "mps_available": available,
        "mps_runtime": runtime,
    }
    _validate_machine_profile(record)
    return record


def build_worker_identity(
    registration: WorkerRegistration,
    *,
    machine_profile: Mapping[str, object],
    capabilities: WorkerCapabilities,
    configured_models: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    """Build a fingerprinted identity; configured does not mean loaded or healthy."""

    if _STABLE_ID.fullmatch(registration.worker_id) is None:
        raise IdentityError("worker registration ID is invalid")
    _require_utc(registration.registered_at, "registration time")
    profile = dict(machine_profile)
    _validate_machine_profile(profile)
    models = [dict(model) for model in configured_models]
    _validate_models(models)
    preimage = {
        "schema_version": WORKER_IDENTITY_SCHEMA_VERSION,
        "worker_id": registration.worker_id,
        "registered_at": _utc_text(registration.registered_at),
        "machine_profile": profile,
        "capabilities": capabilities.record(),
        "configured_models": models,
        "scientific_claim_allowed": False,
    }
    return {**preimage, "identity_fingerprint": _digest(preimage)}


def _read_registration(path: Path) -> WorkerRegistration:
    try:
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise IdentityError("worker registration must be a regular file")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise IdentityError("worker registration permissions are too broad")
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise IdentityError("worker registration is unreadable") from error
    if not isinstance(record, dict) or set(record) != {
        "schema_version",
        "worker_id",
        "registered_at",
    }:
        raise IdentityError("worker registration fields are not exact")
    if record["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise IdentityError("worker registration version is unsupported")
    worker_id = record["worker_id"]
    if not isinstance(worker_id, str) or _STABLE_ID.fullmatch(worker_id) is None:
        raise IdentityError("persisted worker ID is invalid")
    return WorkerRegistration(worker_id, _parse_utc(record["registered_at"]))


def _validate_capabilities(capabilities: WorkerCapabilities) -> None:
    stages = capabilities.supported_stage_ids
    if not stages or len(stages) != len(set(stages)) or any(stage not in _STAGES for stage in stages):
        raise IdentityError("worker stage capabilities are invalid")
    if capabilities.max_queue_records < 1 or capabilities.max_queue_bytes < 1:
        raise IdentityError("worker queue capacity must be positive")
    if not 0 <= capabilities.rolling_prefetch_batches <= 4:
        raise IdentityError("rolling prefetch count must be zero to four")
    if capabilities.checkpoint_format != "parquet-manifest-v1":
        raise IdentityError("worker checkpoint format is unsupported")
    if capabilities.graceful_shutdown_supported is not True:
        raise IdentityError("graceful shutdown support is required")


def _validate_machine_profile(profile: Mapping[str, object]) -> None:
    required = {
        "platform",
        "architecture",
        "os_version",
        "chip_label",
        "cpu_core_count",
        "unified_memory_bytes",
        "mps_available",
        "mps_runtime",
    }
    if set(profile) != required:
        raise IdentityError("machine profile fields are not exact")
    if profile["platform"] not in {"macos", "linux"} or profile["architecture"] not in {"arm64", "x86_64"}:
        raise IdentityError("machine profile platform is invalid")
    for field in ("os_version", "chip_label"):
        if not isinstance(profile[field], str) or not str(profile[field]).strip():
            raise IdentityError(f"machine profile {field} is invalid")
    for field in ("cpu_core_count", "unified_memory_bytes"):
        if not isinstance(profile[field], int) or isinstance(profile[field], bool) or int(profile[field]) < 1:
            raise IdentityError(f"machine profile {field} is invalid")
    if not isinstance(profile["mps_available"], bool):
        raise IdentityError("machine profile MPS flag is invalid")
    if profile["mps_runtime"] is not None and (
        not isinstance(profile["mps_runtime"], str) or not str(profile["mps_runtime"]).strip()
    ):
        raise IdentityError("machine profile MPS runtime is invalid")
    if profile["mps_available"] and profile["platform"] != "macos":
        raise IdentityError("non-macOS machine cannot claim MPS")


def _validate_models(models: list[dict[str, object]]) -> None:
    roles: set[object] = set()
    required = {
        "role",
        "model_id",
        "revision",
        "weights_sha256",
        "preprocessing_fingerprint",
        "licence_status",
        "device",
    }
    for model in models:
        if set(model) != required or model["role"] not in {"yoloe_router", "bioclip_embedder"}:
            raise IdentityError("configured model fields are invalid")
        if model["role"] in roles:
            raise IdentityError("configured model role is duplicated")
        roles.add(model["role"])
        for field in ("weights_sha256", "preprocessing_fingerprint"):
            if not isinstance(model[field], str) or _SHA256.fullmatch(str(model[field])) is None:
                raise IdentityError("configured model fingerprint is invalid")
        if model["licence_status"] not in {"approved", "blocked"} or model["device"] not in {"mps", "cpu"}:
            raise IdentityError("configured model status is invalid")
        if not isinstance(model["model_id"], str) or not str(model["model_id"]).strip():
            raise IdentityError("configured model ID is invalid")
        if not isinstance(model["revision"], str) or not str(model["revision"]).strip():
            raise IdentityError("configured model revision is invalid")


def _probe_mps() -> tuple[bool, str | None]:
    try:
        torch = importlib.import_module("torch")
        available = bool(torch.backends.mps.is_available())
    except (ImportError, AttributeError, RuntimeError):
        return False, None
    return available, f"torch={torch.__version__};mps_built={bool(torch.backends.mps.is_built())}"


def _physical_memory_bytes(platform_name: str) -> int:
    if platform_name == "macos":
        value = _sysctl("hw.memsize")
        if value.isdigit() and int(value) > 0:
            return int(value)
    try:
        return int(os.sysconf("SC_PHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
    except (OSError, ValueError):
        raise IdentityError("physical memory could not be observed") from None


def _chip_label(platform_name: str) -> str:
    if platform_name == "macos":
        for name in ("machdep.cpu.brand_string", "hw.model"):
            value = _sysctl(name)
            if value:
                return value[:160]
    return (platform.processor() or platform.machine() or "unknown-processor")[:160]


def _sysctl(name: str) -> str:
    try:
        return subprocess.run(
            ["sysctl", "-n", name],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return ""


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise IdentityError("registration timestamp must use UTC")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise IdentityError("registration timestamp is invalid") from error
    _require_utc(parsed, "registration timestamp")
    return parsed


def _require_utc(value: datetime, field: str) -> None:
    if value.tzinfo != timezone.utc:
        raise IdentityError(f"{field} must use UTC")


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
