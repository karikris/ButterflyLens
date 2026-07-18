#!/usr/bin/env python3
"""Build a deterministic, prepared-not-published Darwin Core evidence archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts.darwin_core_export import (  # noqa: E402
    build_darwin_core_evidence_package,
    darwin_core_export_request_from_dict,
)
from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Build a governed Darwin Core Archive without publishing or submitting it."
    )
    value.add_argument("--input", required=True, type=Path, help="Exact JSON request")
    value.add_argument("--output", required=True, type=Path, help="Destination .zip")
    return value


def main() -> int:
    arguments = parser().parse_args()
    try:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("export request must be a JSON object")
        request = darwin_core_export_request_from_dict(payload)
        package = build_darwin_core_evidence_package(request)
        package.write_atomic(arguments.output)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"Darwin Core export failed: {error}", file=sys.stderr)
        return 1
    receipt = {
        "archive_path": str(arguments.output),
        "archive_sha256": package.archive_sha256,
        "package_fingerprint": package.package_fingerprint,
        "publication_state": "prepared_not_published",
        "provider_submission_state": "not_submitted",
    }
    sys.stdout.buffer.write(canonicalize_json(receipt) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
