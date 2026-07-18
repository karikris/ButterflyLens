"""On-demand macOS Keychain reads that never use a shell or environment."""

from __future__ import annotations

import re
import subprocess
from typing import Callable, Sequence


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")


class KeychainError(RuntimeError):
    """Raised without including secret values or command output."""


class KeychainSecretProvider:
    def __init__(
        self,
        *,
        command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._command_runner = command_runner

    def read(self, *, service: str, account: str) -> str:
        """Read one generic-password value into memory only when requested."""

        if _IDENTIFIER.fullmatch(service) is None or _IDENTIFIER.fullmatch(account) is None:
            raise KeychainError("Keychain service or account identifier is invalid")
        arguments: Sequence[str] = (
            "/usr/bin/security",
            "find-generic-password",
            "-s",
            service,
            "-a",
            account,
            "-w",
        )
        try:
            completed = self._command_runner(
                arguments,
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.SubprocessError) as error:
            raise KeychainError("Keychain item is unavailable") from error
        secret = completed.stdout.rstrip("\r\n")
        if not secret or "\x00" in secret:
            raise KeychainError("Keychain item returned no usable value")
        return secret
