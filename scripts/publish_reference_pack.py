#!/usr/bin/env python3
"""Publish the closed provisional-reference inventory and pack fingerprint."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


SCHEMA_VERSION = "butterflylens-reference-bank-manifest/v1"
EXCLUDED_NAMES = {"README.md", "reference_bank_manifest.json"}


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value))
    temporary.replace(path)


def _schema_and_rows(path: Path) -> tuple[str, int | None]:
    if path.suffix == ".parquet":
        table = pq.read_table(path, columns=["schema_version"])
        versions = set(table.column("schema_version").to_pylist())
        if len(versions) != 1:
            raise ValueError(f"{path} does not contain exactly one schema version")
        return str(next(iter(versions))), table.num_rows
    if path.suffix == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        return str(value.get("schema_version", "json/unversioned")), 1
    if path.name.endswith(".tar.gz"):
        return "biominer-reference-checkpoint-archive/binary", None
    raise ValueError(f"unsupported reference artifact: {path}")


def _inventory(reference_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in reference_dir.rglob("*") if item.is_file()):
        if path.name in EXCLUDED_NAMES:
            continue
        relative = path.relative_to(reference_dir).as_posix()
        schema_version, row_count = _schema_and_rows(path)
        row: dict[str, Any] = {
            "path": relative,
            "physical_bytes": path.stat().st_size,
            "physical_sha256": sha256_file(path),
            "schema_version": schema_version,
        }
        if row_count is not None:
            row["row_count"] = row_count
        rows.append(row)
    return rows


def publish(args: argparse.Namespace) -> None:
    inventory = _inventory(args.reference_dir)
    admission = json.loads(args.admission_manifest.read_text(encoding="utf-8"))
    yoloe = json.loads(args.yoloe_manifest.read_text(encoding="utf-8"))
    bioclip = json.loads(args.bioclip_status.read_text(encoding="utf-8"))
    quality = json.loads(args.quality_manifest.read_text(encoding="utf-8"))
    fingerprint_payload = {
        "artifacts": inventory,
        "source_media_bytes_committed_to_git": False,
        "human_verified_media": 0,
        "yoloe_status": yoloe["status"],
        "bioclip_status": bioclip["status"],
        "quality_status": quality["status"],
    }
    bank_fingerprint = hashlib.sha256(
        canonical_json(fingerprint_payload).rstrip(b"\n")
    ).hexdigest()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "pack_id": "australian-butterflies-v1/reference-bank-v1",
        "generated_at": args.generated_at,
        "status": "provisional_unverified_yoloe_bioclip_unfinished",
        "reference_bank_fingerprint": bank_fingerprint,
        "origin": {
            "repository": "karikris/BioMiner",
            "commit": "d71bceabf75748a25df39d0025e8da907f295f8c",
        },
        "artifacts": inventory,
        "counts": {
            "artifact_count": len(inventory),
            "candidate_observations": 12_980,
            "candidate_media": 24_329,
            "selected_media": admission["counts"]["selected_for_download"],
            "valid_decodes": admission["counts"]["provisional_support_candidates"],
            "download_or_decode_failures": admission["counts"][
                "download_or_decode_failures"
            ],
            "accepted_species": quality["counts"]["accepted_species"],
            "species_with_valid_decodes": quality["counts"][
                "species_with_valid_decodes"
            ],
            "human_verified_media": 0,
            "yoloe_routes": 0,
            "bioclip_embeddings": 0,
            "species_prototypes": 0,
        },
        "states": {
            "admission": admission["status"],
            "yoloe": yoloe["status"],
            "bioclip": bioclip["status"],
            "quality": quality["status"],
        },
        "policy": {
            "source_media_bytes_committed_to_git": False,
            "provider_assertions_are_human_verification": False,
            "flickr_api_calls_made": False,
            "missing_model_evidence_is_negative_evidence": False,
            "authoritative_ala_baseline": "ButterflyLens rebuilt baseline",
            "release_ready": False,
        },
        "release_blockers": [
            "human_reference_review_absent",
            "yoloe_unfinished",
            "bioclip_unfinished",
            "durable_private_source_media_storage_pending",
            "reference_coverage_incomplete",
        ],
    }
    write_json(args.output, manifest)

    pack = json.loads(args.pack_manifest.read_text(encoding="utf-8"))
    relative = "references/v1/reference_bank_manifest.json"
    pack.setdefault("artifacts", {})[relative] = {
        "physical_sha256": sha256_file(args.output),
        "row_count": 1,
        "schema_version": SCHEMA_VERSION,
    }
    pack.setdefault("reference_state", {}).update(
        {
            "bank_manifest_path": relative,
            "bank_manifest_sha256": sha256_file(args.output),
            "bank_fingerprint": bank_fingerprint,
            "bank_status": manifest["status"],
            "status": admission["status"],
        }
    )
    write_json(args.pack_manifest, pack)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--reference-dir", type=Path, required=True)
    result.add_argument("--admission-manifest", type=Path, required=True)
    result.add_argument("--yoloe-manifest", type=Path, required=True)
    result.add_argument("--bioclip-status", type=Path, required=True)
    result.add_argument("--quality-manifest", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--pack-manifest", type=Path, required=True)
    result.add_argument("--generated-at", required=True)
    return result


if __name__ == "__main__":
    publish(parser().parse_args())
