#!/usr/bin/env python3
"""Prepare one offline ALA contribution archive; never submit it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts.ala_contribution import (  # noqa: E402
    ala_contribution_request_from_dict,
    build_ala_contribution_package,
)
from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Prepare a governed ALA handoff archive without submitting it."
    )
    value.add_argument("--input", required=True, type=Path, help="Exact JSON request")
    value.add_argument(
        "--darwin-core-archive",
        required=True,
        type=Path,
        help="Exact ButterflyLens Darwin Core evidence archive",
    )
    value.add_argument("--output", required=True, type=Path, help="Destination .zip")
    return value


def main() -> int:
    arguments = parser().parse_args()
    try:
        payload = json.loads(arguments.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("ALA preparation request must be a JSON object")
        request = ala_contribution_request_from_dict(payload)
        package = build_ala_contribution_package(
            request,
            arguments.darwin_core_archive.read_bytes(),
        )
        package.write_atomic(arguments.output)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(f"ALA contribution preparation failed: {error}", file=sys.stderr)
        return 1
    receipt = {
        "archive_path": str(arguments.output),
        "archive_sha256": package.archive_sha256,
        "package_fingerprint": package.package_fingerprint,
        "preparation_state": package.preparation_state,
        "publication_state": "prepared_not_published",
        "provider_submission_state": "not_submitted",
        "human_submission_required": True,
    }
    sys.stdout.buffer.write(canonicalize_json(receipt) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
