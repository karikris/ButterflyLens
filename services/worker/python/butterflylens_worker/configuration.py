"""Strict non-secret configuration loading for the development worker."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import stat


_ALLOWED = frozenset(
    {
        "BUTTERFLYLENS_HEARTBEAT_SECONDS",
        "BUTTERFLYLENS_MAX_QUEUE_RECORDS",
        "BUTTERFLYLENS_MAX_QUEUE_BYTES",
        "BUTTERFLYLENS_PREFETCH_BATCHES",
    }
)
_SECRET_NAME = re.compile(r"(secret|token|password|api[_-]?key|credential)", re.I)


class ConfigurationError(ValueError):
    """Raised when a launch environment is executable, secret-bearing, or invalid."""


@dataclass(frozen=True)
class WorkerServiceConfiguration:
    heartbeat_seconds: float = 30.0
    max_queue_records: int = 512
    max_queue_bytes: int = 2 * 1024**3
    prefetch_batches: int = 2


def load_environment_file(path: Path) -> WorkerServiceConfiguration:
    """Parse an allowlisted KEY=VALUE file without shell evaluation."""

    values: dict[str, str] = {}
    try:
        path = Path(path)
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
            raise ConfigurationError("worker environment must be a regular file")
        if stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ConfigurationError("worker environment permissions are too broad")
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ConfigurationError("worker environment file is unreadable") from error
    for line_number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigurationError(f"environment line {line_number} is not KEY=VALUE")
        key, value = (part.strip() for part in line.split("=", 1))
        if _SECRET_NAME.search(key):
            raise ConfigurationError("secrets are forbidden in the environment file")
        if key not in _ALLOWED:
            raise ConfigurationError(f"environment key is not allowlisted: {key}")
        if key in values:
            raise ConfigurationError(f"environment key is duplicated: {key}")
        if not value or any(character in value for character in "\x00\r\n`$;|&<>"):
            raise ConfigurationError(f"environment value is unsafe: {key}")
        values[key] = value
    configuration = WorkerServiceConfiguration(
        heartbeat_seconds=_positive_float(
            values.get("BUTTERFLYLENS_HEARTBEAT_SECONDS", "30"),
            "heartbeat seconds",
        ),
        max_queue_records=_positive_int(
            values.get("BUTTERFLYLENS_MAX_QUEUE_RECORDS", "512"),
            "queue records",
        ),
        max_queue_bytes=_positive_int(
            values.get("BUTTERFLYLENS_MAX_QUEUE_BYTES", str(2 * 1024**3)),
            "queue bytes",
        ),
        prefetch_batches=_bounded_int(
            values.get("BUTTERFLYLENS_PREFETCH_BATCHES", "2"),
            "prefetch batches",
            minimum=0,
            maximum=4,
        ),
    )
    if configuration.heartbeat_seconds < 5 or configuration.heartbeat_seconds > 300:
        raise ConfigurationError("heartbeat seconds must be between 5 and 300")
    return configuration


def _positive_float(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise ConfigurationError(f"{field} is invalid") from error
    if parsed <= 0 or parsed != parsed or parsed == float("inf"):
        raise ConfigurationError(f"{field} must be finite and positive")
    return parsed


def _positive_int(value: str, field: str) -> int:
    return _bounded_int(value, field, minimum=1, maximum=2**63 - 1)


def _bounded_int(value: str, field: str, *, minimum: int, maximum: int) -> int:
    if not value.isdigit():
        raise ConfigurationError(f"{field} is invalid")
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        raise ConfigurationError(f"{field} is outside its permitted range")
    return parsed
