#!/usr/bin/env python3
"""Plan and publish the provisional reference metadata import.

BioMiner owns provider polling and normalization.  This adapter compiles the
ButterflyLens taxon scope into BioMiner's pinned query contract, then validates
and fingerprints the returned artifacts without relabelling provider
assertions as verified identifications.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any

import pyarrow.parquet as pq


BIOMINER_SHA = "d71bceabf75748a25df39d0025e8da907f295f8c"
QUERY_PLAN_SCHEMA_VERSION = "butterflylens-reference-query-plan/v1"
IMPORT_MANIFEST_SCHEMA_VERSION = "butterflylens-reference-import-manifest/v1"
BIOMINER_OBSERVATION_SCHEMA_VERSION = "reference-observations-v1.2.0"
BIOMINER_MEDIA_SCHEMA_VERSION = "reference-media-candidates-v1.0.0"
AUSTRALIA_INATURALIST_PLACE_ID = "6744"
GBIF_PAGE_SIZE = 3
INATURALIST_PAGE_SIZE = 200
GBIF_MAXIMUM_RECORDS_PER_QUERY = GBIF_PAGE_SIZE
INATURALIST_MAXIMUM_RECORDS_PER_QUERY = INATURALIST_PAGE_SIZE


class ReferenceImportError(RuntimeError):
    """Raised when the reference import contract is violated."""


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def build_query_plan(args: argparse.Namespace) -> None:
    rows = read_jsonl(args.crosswalk)
    species = [row for row in rows if row.get("rank") == "species"]
    eligible = [
        row
        for row in species
        if row.get("gbif_taxon_key") is not None
        and row.get("inaturalist_taxon_id") is not None
    ]
    queries: list[dict[str, Any]] = []
    for row in eligible:
        accepted_key = f"gbif:{row['gbif_taxon_key']}"
        common = {
            "accepted_taxon_key": accepted_key,
            "scientific_name": row["accepted_scientific_name"],
            "geo_cluster_id": "australia",
            "fallback_level": 2,
            "source_snapshot_version": args.source_snapshot_version,
        }
        queries.append(
            {
                "source": "GBIF",
                **common,
                "page_size": GBIF_PAGE_SIZE,
                "maximum_records": GBIF_MAXIMUM_RECORDS_PER_QUERY,
                "source_taxon_id": str(row["gbif_taxon_key"]),
                "country_codes": ["AU"],
            }
        )
        queries.append(
            {
                "source": "iNaturalist",
                **common,
                "page_size": INATURALIST_PAGE_SIZE,
                "maximum_records": INATURALIST_MAXIMUM_RECORDS_PER_QUERY,
                "source_taxon_id": str(row["inaturalist_taxon_id"]),
                "source_place_ids": [AUSTRALIA_INATURALIST_PLACE_ID],
            }
        )
    queries.sort(
        key=lambda row: (
            row["source"],
            row["scientific_name"],
            row["source_taxon_id"],
        )
    )
    plan = {
        "schema_version": QUERY_PLAN_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "candidate_semantics": (
            "provider taxon assertions and media candidates; not human verification"
        ),
        "biominer_origin_sha": BIOMINER_SHA,
        "scope": {
            "crosswalk_path": args.crosswalk.as_posix(),
            "crosswalk_sha256": sha256_file(args.crosswalk),
            "species_rows": len(species),
            "species_with_exact_gbif_and_inaturalist_ids": len(eligible),
            "species_excluded_for_missing_provider_identity": len(species) - len(eligible),
            "country": "Australia",
            "inaturalist_place_id": AUSTRALIA_INATURALIST_PLACE_ID,
        },
        "limits": {
            "gbif_page_size": GBIF_PAGE_SIZE,
            "inaturalist_page_size": INATURALIST_PAGE_SIZE,
            "gbif_maximum_records_per_query": GBIF_MAXIMUM_RECORDS_PER_QUERY,
            "inaturalist_maximum_records_per_query": (
                INATURALIST_MAXIMUM_RECORDS_PER_QUERY
            ),
            "images_downloaded": 0,
        },
        "queries": queries,
    }
    write_json(args.output, plan)
    print(
        json.dumps(
            {
                "query_count": len(queries),
                "species_count": len(eligible),
                "sha256": sha256_file(args.output),
            },
            sort_keys=True,
        )
    )


def artifact(path: Path, *, rows: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path.as_posix(),
        "physical_bytes": path.stat().st_size,
        "physical_sha256": sha256_file(path),
    }
    if rows is not None:
        result["row_count"] = rows
    return result


def summarize_checkpoints(path: Path) -> dict[str, Any]:
    totals = Counter()
    provider_states = Counter()
    with tarfile.open(path, "r:gz") as archive:
        state_members = sorted(
            (
                member
                for member in archive.getmembers()
                if member.name.endswith("/state.json")
            ),
            key=lambda member: member.name,
        )
        for member in state_members:
            handle = archive.extractfile(member)
            if handle is None:
                raise ReferenceImportError("checkpoint archive state is unreadable")
            state = json.load(handle)
            if not state.get("complete"):
                raise ReferenceImportError("checkpoint archive contains incomplete query")
            provider_states[state["source"]] += 1
            totals["query_states"] += 1
            for page in state["pages"]:
                totals["pages"] += 1
                for field in ("request_count", "retry_count", "rate_limit_count"):
                    totals[field] += int(page[field])
    return {
        **dict(sorted(totals.items())),
        "provider_query_states": dict(sorted(provider_states.items())),
    }


def publish_import(args: argparse.Namespace) -> None:
    plan = json.loads(args.query_plan.read_text())
    if plan.get("schema_version") != QUERY_PLAN_SCHEMA_VERSION:
        raise ReferenceImportError("unexpected query-plan schema")
    observations = pq.read_table(args.observations)
    media = pq.read_table(args.media)
    required_observation_columns = {
        "schema_version",
        "reference_observation_id",
        "source",
        "source_observation_id",
        "accepted_taxon_key",
        "taxon_reconciliation_status",
        "source_record_hash",
        "source_query_fingerprint",
    }
    required_media_columns = {
        "schema_version",
        "reference_media_id",
        "reference_observation_id",
        "source",
        "provider_media_id",
        "media_identifier",
        "licence",
        "licence_policy_status",
        "verification_status",
    }
    if not required_observation_columns <= set(observations.schema.names):
        raise ReferenceImportError("BioMiner observation columns are incomplete")
    if not required_media_columns <= set(media.schema.names):
        raise ReferenceImportError("BioMiner media columns are incomplete")
    observation_rows = observations.to_pylist()
    media_rows = media.to_pylist()
    if any(
        row["schema_version"] != BIOMINER_OBSERVATION_SCHEMA_VERSION
        for row in observation_rows
    ):
        raise ReferenceImportError("BioMiner observation schema version drift")
    if any(row["schema_version"] != BIOMINER_MEDIA_SCHEMA_VERSION for row in media_rows):
        raise ReferenceImportError("BioMiner media schema version drift")
    sources = {"GBIF", "iNaturalist"}
    if {row["source"] for row in observation_rows} - sources:
        raise ReferenceImportError("unexpected observation provider")
    if {row["source"] for row in media_rows} - sources:
        raise ReferenceImportError("unexpected media provider")
    observation_ids = {row["reference_observation_id"] for row in observation_rows}
    if any(row["reference_observation_id"] not in observation_ids for row in media_rows):
        raise ReferenceImportError("media row references an absent observation")
    if any(row["verification_status"] != "unreviewed" for row in media_rows):
        raise ReferenceImportError("metadata import must remain unreviewed")
    ala_manifest = json.loads(args.ala_snapshot_manifest.read_text())
    ala_occurrences = ala_manifest["artifacts"]["normalized_occurrences"]
    provider_observation_counts = Counter(row["source"] for row in observation_rows)
    provider_media_counts = Counter(row["source"] for row in media_rows)
    reconciliation_counts = Counter(
        row["taxon_reconciliation_status"] for row in observation_rows
    )
    licence_policy_counts = Counter(row["licence_policy_status"] for row in media_rows)
    report = json.loads(args.metadata_report.read_text())
    checkpoint_summary = summarize_checkpoints(args.checkpoint_archive)
    if checkpoint_summary["query_states"] != len(plan["queries"]):
        raise ReferenceImportError("checkpoint archive does not cover every query")
    manifest = {
        "schema_version": IMPORT_MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "candidate_metadata_imported_no_media_downloads",
        "candidate_semantics": (
            "provider assertions and candidate media; not human-verified reference labels"
        ),
        "biominer": {
            "origin_sha": BIOMINER_SHA,
            "command": "biominer references fetch-metadata",
            "observation_schema_version": BIOMINER_OBSERVATION_SCHEMA_VERSION,
            "media_schema_version": BIOMINER_MEDIA_SCHEMA_VERSION,
            "report_schema_version": report.get("schema_version"),
            "checkpoint_summary": checkpoint_summary,
        },
        "counts": {
            "query_count": len(plan["queries"]),
            "queried_species": plan["scope"][
                "species_with_exact_gbif_and_inaturalist_ids"
            ],
            "provider_observations": dict(sorted(provider_observation_counts.items())),
            "provider_media_candidates": dict(sorted(provider_media_counts.items())),
            "taxon_reconciliation_status": dict(sorted(reconciliation_counts.items())),
            "licence_policy_status": dict(sorted(licence_policy_counts.items())),
            "observation_rows": len(observation_rows),
            "media_candidate_rows": len(media_rows),
            "images_downloaded": 0,
            "human_verified_media": 0,
            "ala_candidate_observation_rows": ala_occurrences["row_count"],
            "ala_media_candidate_rows": 0,
        },
        "ala": {
            "source": "frozen Task 2.3 normalized occurrence evidence",
            "snapshot_id": ala_manifest["snapshot_id"],
            "snapshot_manifest_path": args.ala_snapshot_manifest.as_posix(),
            "snapshot_manifest_sha256": sha256_file(args.ala_snapshot_manifest),
            "normalized_occurrences": ala_occurrences,
            "media_state": (
                "not_captured_by_the_frozen_2.3_source_contract; no ALA media label "
                "or URL is inferred"
            ),
        },
        "rights": {
            "accepted_inaturalist_photo_licences_at_import": ["cc0", "cc-by"],
            "gbif_media_licences": "preserved verbatim; automated gate pending 2.4.3",
            "ala_release_state": ala_manifest["rights"][
                "downstream_public_product_release_state"
            ],
            "media_bytes_downloaded": False,
        },
        "artifacts": {
            "query_plan": artifact(args.query_plan),
            "reference_observations": artifact(
                args.observations, rows=observations.num_rows
            ),
            "reference_media_candidates": artifact(args.media, rows=media.num_rows),
            "metadata_report": artifact(args.metadata_report),
            "checkpoint_archive": artifact(args.checkpoint_archive),
        },
    }
    write_json(args.output, manifest)
    pack = json.loads(args.pack_manifest.read_text())
    pack["reference_state"] = {
        "status": manifest["status"],
        "generated_at": args.generated_at,
        "manifest_path": "references/v1/reference_import_manifest.json",
        "manifest_sha256": sha256_file(args.output),
        "observation_rows": observations.num_rows,
        "media_candidate_rows": media.num_rows,
        "images_downloaded": 0,
        "human_verified_media": 0,
    }
    write_json(args.pack_manifest, pack)
    print(
        json.dumps(
            {
                "manifest_sha256": sha256_file(args.output),
                "observation_rows": observations.num_rows,
                "media_candidate_rows": media.num_rows,
            },
            sort_keys=True,
        )
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subparsers = root.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--crosswalk", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--source-snapshot-version", required=True)
    plan.add_argument("--generated-at", required=True)
    plan.set_defaults(handler=build_query_plan)
    publish = subparsers.add_parser("publish")
    publish.add_argument("--query-plan", type=Path, required=True)
    publish.add_argument("--observations", type=Path, required=True)
    publish.add_argument("--media", type=Path, required=True)
    publish.add_argument("--metadata-report", type=Path, required=True)
    publish.add_argument("--checkpoint-archive", type=Path, required=True)
    publish.add_argument("--ala-snapshot-manifest", type=Path, required=True)
    publish.add_argument("--pack-manifest", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    publish.add_argument("--generated-at", required=True)
    publish.set_defaults(handler=publish_import)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (OSError, ValueError, KeyError, ReferenceImportError) as error:
        print(f"reference import failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
