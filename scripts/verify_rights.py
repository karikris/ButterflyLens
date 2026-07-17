#!/usr/bin/env python3
"""Fail closed when tracked provider/data/media rights evidence is incomplete."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROVIDER_SUFFIXES = {
    ".csv",
    ".geojson",
    ".gpkg",
    ".json",
    ".jsonl",
    ".jpeg",
    ".jpg",
    ".mbtiles",
    ".parquet",
    ".pmtiles",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}
PROVIDER_ROOTS = ("data/", "demo/", "public/media/", "apps/web/public/media/")


class VerificationError(RuntimeError):
    """Raised when a release-blocking rights condition is not met."""


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return {value.decode("utf-8") for value in result.stdout.split(b"\0") if value}


def require_policy() -> None:
    path = ROOT / "DATA_RIGHTS.md"
    if not path.is_file():
        raise VerificationError("missing DATA_RIGHTS.md")
    text = path.read_text(encoding="utf-8")
    required = (
        "Flickr API Terms of Use",
        "Atlas of Living Australia",
        "GBIF Data User Agreement",
        "iNaturalist Terms of Use",
        "ABS ASGS",
        "IBRA 7",
        "Community reviews",
        "Unknown is a blocking value",
        "within 24 hours",
    )
    missing = [term for term in required if term not in text]
    if missing:
        raise VerificationError(f"DATA_RIGHTS.md is missing required evidence: {missing}")


def verify_manifest(payloads: set[str]) -> None:
    path = ROOT / "provenance/data_rights_manifest.json"
    if not path.is_file():
        raise VerificationError(
            "provider/data/media payloads are tracked without provenance/data_rights_manifest.json"
        )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {"schema_version", "generated_at", "sources", "artifacts"}
    missing = sorted(required - set(manifest)) if isinstance(manifest, dict) else sorted(required)
    if missing:
        raise VerificationError(f"data rights manifest is missing keys: {missing}")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise VerificationError("data rights manifest artifacts must be a list")
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        raise VerificationError("data rights manifest sources must be a list")
    source_ids = [
        record.get("source_id") for record in sources if isinstance(record, dict)
    ]
    if any(not source_id for source_id in source_ids) or len(source_ids) != len(
        set(source_ids)
    ):
        raise VerificationError("data rights manifest source IDs are missing or duplicated")
    records = {record.get("path"): record for record in artifacts if isinstance(record, dict)}
    absent = sorted(payloads - set(records))
    if absent:
        raise VerificationError(f"tracked payloads have no rights record: {absent[:10]}")
    required_fields = {
        "path",
        "fingerprint",
        "provider",
        "source_id",
        "licence",
        "attribution",
        "processing_allowed",
        "display_allowed",
        "redistribution_allowed",
        "removal_state",
    }
    for payload in sorted(payloads):
        record = records[payload]
        missing_fields = sorted(required_fields - set(record))
        if missing_fields:
            raise VerificationError(f"rights record for {payload} is missing: {missing_fields}")
        if record.get("licence") in {None, "", "unknown"}:
            raise VerificationError(f"rights record for {payload} has an unknown licence")
        if record.get("source_id") not in source_ids:
            raise VerificationError(f"rights record for {payload} has an unknown source_id")
        for permission in (
            "processing_allowed",
            "display_allowed",
            "redistribution_allowed",
        ):
            if not isinstance(record.get(permission), bool):
                raise VerificationError(
                    f"rights record for {payload} has non-boolean {permission}"
                )
        fingerprint = record.get("fingerprint", "")
        if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
            raise VerificationError(f"rights record for {payload} has an invalid fingerprint")
        observed = "sha256:" + hashlib.sha256((ROOT / payload).read_bytes()).hexdigest()
        if fingerprint != observed:
            raise VerificationError(f"rights record for {payload} fingerprint does not match")


def verify() -> None:
    require_policy()
    tracked = tracked_files()
    payloads = {
        path
        for path in tracked
        if path.startswith(PROVIDER_ROOTS) and Path(path).suffix.lower() in PROVIDER_SUFFIXES
    }
    if payloads:
        verify_manifest(payloads)
    print(f"rights verification: PASS (tracked_provider_payloads={len(payloads)})")


if __name__ == "__main__":
    try:
        verify()
    except (VerificationError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"rights verification: FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
