#!/usr/bin/env python3
"""Render and validate the development launchd plist with absolute paths."""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
from xml.sax.saxutils import escape


PLACEHOLDERS = (
    "PYTHON",
    "ENVIRONMENT_FILE",
    "STATE_DIR",
    "REPOSITORY",
    "PYTHONPATH",
    "STDOUT_LOG",
    "STDERR_LOG",
)


def render(template: Path, output: Path, values: dict[str, Path]) -> None:
    if set(values) != set(PLACEHOLDERS):
        raise ValueError("launchd renderer values are not exact")
    document = template.read_text(encoding="utf-8")
    for name in PLACEHOLDERS:
        value = values[name]
        if not value.is_absolute() or "\x00" in str(value):
            raise ValueError(f"launchd path must be absolute: {name}")
        document = document.replace(f"__{name}__", escape(str(value)))
    if "__" in document:
        raise ValueError("launchd template retains a placeholder")
    parsed = plistlib.loads(document.encode())
    if parsed.get("Label") != "com.karikris.butterflylens.worker":
        raise ValueError("launchd label is invalid")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = output.with_suffix(".plist.tmp")
    temporary.write_bytes(document.encode())
    temporary.chmod(0o600)
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    for name in PLACEHOLDERS:
        parser.add_argument(f"--{name.lower().replace('_', '-')}", type=Path, required=True)
    arguments = parser.parse_args()
    values = {name: getattr(arguments, name.lower()) for name in PLACEHOLDERS}
    render(arguments.template, arguments.output, values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
