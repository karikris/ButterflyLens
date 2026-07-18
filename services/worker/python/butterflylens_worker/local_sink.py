"""Private append-only development heartbeat sink."""

from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import stat
from typing import Mapping


class LocalSinkError(RuntimeError):
    """Raised when a development heartbeat cannot be durably appended."""


class LocalJsonlHeartbeatSink:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    def append_heartbeat(self, heartbeat: Mapping[str, object]) -> dict[str, object]:
        encoded = (json.dumps(dict(heartbeat), sort_keys=True, separators=(",", ":")) + "\n").encode()
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(self.path, flags, 0o600)
            with os.fdopen(descriptor, "ab", closefd=True) as handle:
                metadata = os.fstat(handle.fileno())
                if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
                    raise LocalSinkError("heartbeat ledger is not a private regular file")
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except OSError as error:
            raise LocalSinkError("heartbeat ledger append failed") from error
        return {
            "storage_state": "persisted",
            "heartbeat_id": heartbeat["heartbeat_id"],
            "heartbeat_fingerprint": heartbeat["heartbeat_fingerprint"],
        }
