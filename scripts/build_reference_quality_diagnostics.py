#!/usr/bin/env python3
"""Build deterministic reference-bank diagnostics without model evidence."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA_VERSION = "butterflylens-reference-quality-diagnostics/v1"
MANIFEST_SCHEMA_VERSION = "butterflylens-reference-quality-manifest/v1"
TARGET_SUPPORT = 20


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


def semantic_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).rstrip(b"\n")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json(value))
    temporary.replace(path)


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("butterflylens_taxon_key", pa.string()),
            ("accepted_scientific_name", pa.string()),
            ("provider_taxon_key", pa.string()),
            ("candidate_media_count", pa.uint32()),
            ("automated_gate_eligible_count", pa.uint32()),
            ("selected_count", pa.uint32()),
            ("valid_decode_count", pa.uint32()),
            ("download_or_decode_failure_count", pa.uint32()),
            ("unique_content_count", pa.uint32()),
            ("exact_content_duplicate_excess", pa.uint32()),
            ("observer_count", pa.uint32()),
            ("cc0_selected_count", pa.uint32()),
            ("cc_by_selected_count", pa.uint32()),
            ("human_verified_count", pa.uint32()),
            ("yoloe_routed_count", pa.uint32()),
            ("yoloe_pending_count", pa.uint32()),
            ("bioclip_embedding_count", pa.uint32()),
            ("species_prototype_count", pa.uint32()),
            ("coverage_status", pa.string()),
            ("release_status", pa.string()),
            ("quality_flags", pa.list_(pa.string())),
            ("evidence_fingerprint", pa.string()),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(
        pa.Table.from_pylist(rows, schema=schema),
        temporary,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
        data_page_version="1.0",
        row_group_size=65_536,
    )
    temporary.replace(path)


def _species(taxa_path: Path) -> list[dict[str, str]]:
    rows = [
        json.loads(line)
        for line in taxa_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return sorted(
        (
            {
                "butterflylens_taxon_key": row["butterflylens_key"],
                "accepted_scientific_name": row["accepted_scientific_name"],
            }
            for row in rows
            if row["rank"] == "species" and row["taxonomic_status"] == "accepted"
        ),
        key=lambda row: row["butterflylens_taxon_key"],
    )


def build(args: argparse.Namespace) -> None:
    species = _species(args.taxa)
    decisions = pq.read_table(args.decisions).to_pylist()
    selections = pq.read_table(args.selections).to_pylist()
    objects = {
        row["reference_media_id"]: row
        for row in pq.read_table(args.media_objects).to_pylist()
    }
    yoloe_manifest = json.loads(args.yoloe_manifest.read_text(encoding="utf-8"))
    bioclip_status = json.loads(args.bioclip_status.read_text(encoding="utf-8"))

    candidate_counts: Counter[str] = Counter()
    eligible_counts: Counter[str] = Counter()
    provider_keys: dict[str, set[str]] = defaultdict(set)
    media_to_taxon: dict[str, str] = {}
    for row in decisions:
        key = row["butterflylens_taxon_key"]
        if key is None:
            continue
        candidate_counts[key] += 1
        media_to_taxon[row["reference_media_id"]] = key
        provider_keys[key].add(row["accepted_taxon_key"])
        if row["automated_gate_status"] == "eligible":
            eligible_counts[key] += 1

    selected: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selections:
        key = media_to_taxon[row["reference_media_id"]]
        selected[key].append(row)

    rows: list[dict[str, Any]] = []
    for taxon in species:
        key = taxon["butterflylens_taxon_key"]
        selected_rows = selected[key]
        valid_rows = [
            row
            for row in selected_rows
            if objects[row["reference_media_id"]]["decode_status"] == "valid"
        ]
        content = {
            objects[row["reference_media_id"]]["sha256"] for row in valid_rows
        }
        candidate_count = candidate_counts[key]
        eligible_count = eligible_counts[key]
        selected_count = len(selected_rows)
        valid_count = len(valid_rows)
        failed_count = selected_count - valid_count
        duplicate_excess = valid_count - len(content)

        if candidate_count == 0:
            coverage_status = "no_candidate_media"
        elif eligible_count == 0:
            coverage_status = "no_automated_gate_eligible_media"
        elif selected_count == 0:
            coverage_status = "eligible_not_selected"
        elif valid_count == 0:
            coverage_status = "selected_no_valid_decode"
        else:
            coverage_status = "provisional_decode_only"

        flags: list[str] = []
        if candidate_count == 0:
            flags.append("no_candidate_media")
        if eligible_count == 0:
            flags.append("no_automated_gate_eligible_media")
        if selected_count == 0:
            flags.append("no_selected_media")
        if failed_count:
            flags.append("download_or_decode_failure")
        if valid_count < TARGET_SUPPORT:
            flags.append("provisional_support_below_target_20")
        observer_count = len({row["observer_id"] for row in valid_rows})
        if valid_count and observer_count <= 1:
            flags.append("observer_diversity_low")
        if duplicate_excess:
            flags.append("exact_content_duplicate_pending_resolution")
        if valid_count:
            flags.extend(["yoloe_unfinished", "bioclip_unfinished"])
        flags.append("human_review_absent")

        payload: dict[str, Any] = {
            "butterflylens_taxon_key": key,
            "accepted_scientific_name": taxon["accepted_scientific_name"],
            "provider_taxon_key": (
                next(iter(provider_keys[key])) if len(provider_keys[key]) == 1 else None
            ),
            "candidate_media_count": candidate_count,
            "automated_gate_eligible_count": eligible_count,
            "selected_count": selected_count,
            "valid_decode_count": valid_count,
            "download_or_decode_failure_count": failed_count,
            "unique_content_count": len(content),
            "exact_content_duplicate_excess": duplicate_excess,
            "observer_count": observer_count,
            "cc0_selected_count": sum(row["licence"] == "cc0" for row in selected_rows),
            "cc_by_selected_count": sum(
                row["licence"] == "cc-by" for row in selected_rows
            ),
            "human_verified_count": 0,
            "yoloe_routed_count": 0,
            "yoloe_pending_count": valid_count,
            "bioclip_embedding_count": 0,
            "species_prototype_count": 0,
            "coverage_status": coverage_status,
            "release_status": (
                "blocked_unfinished_models_and_human_review"
                if valid_count
                else "blocked_absent_provisional_support"
            ),
            "quality_flags": flags,
        }
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                **payload,
                "evidence_fingerprint": semantic_digest(payload),
            }
        )

    write_parquet(args.output, rows)
    coverage_counts = Counter(row["coverage_status"] for row in rows)
    flag_counts = Counter(flag for row in rows for flag in row["quality_flags"])
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "published_unfinished_models_no_human_review",
        "artifact": {
            "path": "data/packs/australian_butterflies/v1/references/v1/gated/reference_quality_diagnostics.parquet",
            "physical_bytes": args.output.stat().st_size,
            "physical_sha256": sha256_file(args.output),
            "row_count": len(rows),
            "schema_version": SCHEMA_VERSION,
        },
        "dependencies": {
            "taxa_sha256": sha256_file(args.taxa),
            "decisions_sha256": sha256_file(args.decisions),
            "selections_sha256": sha256_file(args.selections),
            "media_objects_sha256": sha256_file(args.media_objects),
            "yoloe_manifest_sha256": sha256_file(args.yoloe_manifest),
            "bioclip_status_sha256": sha256_file(args.bioclip_status),
        },
        "counts": {
            "accepted_species": len(rows),
            "species_with_valid_decodes": sum(row["valid_decode_count"] > 0 for row in rows),
            "valid_decodes": sum(row["valid_decode_count"] for row in rows),
            "human_verified": 0,
            "yoloe_routed": 0,
            "bioclip_embeddings": 0,
            "coverage_statuses": dict(sorted(coverage_counts.items())),
            "quality_flags": dict(sorted(flag_counts.items())),
        },
        "policy": {
            "target_support_per_species": TARGET_SUPPORT,
            "quality_score_computed": False,
            "missing_model_evidence_is_negative_evidence": False,
            "provider_assertions_are_human_verification": False,
            "release_ready": False,
        },
        "upstream_states": {
            "yoloe": yoloe_manifest["status"],
            "bioclip": bioclip_status["status"],
        },
    }
    write_json(args.manifest_output, manifest)

    pack = json.loads(args.pack_manifest.read_text(encoding="utf-8"))
    state = pack.setdefault("reference_state", {})
    state.update(
        {
            "quality_diagnostics_status": manifest["status"],
            "quality_diagnostics_path": "references/v1/gated/reference_quality_diagnostics.parquet",
            "quality_diagnostics_sha256": manifest["artifact"]["physical_sha256"],
            "quality_manifest_path": "references/v1/reference_quality_manifest.json",
            "quality_manifest_sha256": sha256_file(args.manifest_output),
            "species_with_valid_decodes": manifest["counts"]["species_with_valid_decodes"],
            "species_without_valid_decodes": len(rows)
            - manifest["counts"]["species_with_valid_decodes"],
        }
    )
    write_json(args.pack_manifest, pack)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--taxa", type=Path, required=True)
    result.add_argument("--decisions", type=Path, required=True)
    result.add_argument("--selections", type=Path, required=True)
    result.add_argument("--media-objects", type=Path, required=True)
    result.add_argument("--yoloe-manifest", type=Path, required=True)
    result.add_argument("--bioclip-status", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--manifest-output", type=Path, required=True)
    result.add_argument("--pack-manifest", type=Path, required=True)
    result.add_argument("--generated-at", required=True)
    return result


if __name__ == "__main__":
    build(parser().parse_args())
