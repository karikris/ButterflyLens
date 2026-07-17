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
import re
import tarfile
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


BIOMINER_SHA = "d71bceabf75748a25df39d0025e8da907f295f8c"
QUERY_PLAN_SCHEMA_VERSION = "butterflylens-reference-query-plan/v1"
IMPORT_MANIFEST_SCHEMA_VERSION = "butterflylens-reference-import-manifest/v1"
DEDUPLICATION_MANIFEST_SCHEMA_VERSION = (
    "butterflylens-reference-metadata-deduplication-manifest/v1"
)
OBSERVATION_MIRROR_SCHEMA_VERSION = "butterflylens-observation-mirror-group/v1"
MEDIA_DUPLICATE_SCHEMA_VERSION = "butterflylens-media-duplicate-candidate/v1"
BIOMINER_OBSERVATION_SCHEMA_VERSION = "reference-observations-v1.2.0"
BIOMINER_MEDIA_SCHEMA_VERSION = "reference-media-candidates-v1.0.0"
AUSTRALIA_INATURALIST_PLACE_ID = "6744"
GBIF_PAGE_SIZE = 3
INATURALIST_PAGE_SIZE = 200
GBIF_MAXIMUM_RECORDS_PER_QUERY = GBIF_PAGE_SIZE
INATURALIST_MAXIMUM_RECORDS_PER_QUERY = INATURALIST_PAGE_SIZE
_INAT_OBSERVATION = re.compile(r"inaturalist(?:\.org)?/observations/(\d+)")
_INAT_PHOTO = re.compile(r"(?:inaturalist[^/]*/photos/|/photos/)(\d+)(?:/|\D|$)")


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


def write_parquet(path: Path, rows: list[dict[str, Any]], schema: pa.Schema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows, schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=9,
        use_dictionary=True,
        write_statistics=True,
        version="2.6",
        data_page_version="1.0",
        row_group_size=65_536,
    )


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


def artifact(
    path: Path,
    *,
    rows: int | None = None,
    manifest_path: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": manifest_path or path.as_posix(),
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


def _inat_observation_id(*values: object) -> str | None:
    for value in values:
        match = _INAT_OBSERVATION.search(str(value or ""))
        if match:
            return match.group(1)
    return None


def _inat_photo_id(row: dict[str, Any]) -> str | None:
    match = _INAT_PHOTO.search(str(row.get("media_identifier") or ""))
    if match:
        return match.group(1)
    provider_id = str(row.get("provider_media_id") or "")
    return provider_id if row.get("source") == "iNaturalist" and provider_id.isdigit() else None


def _identity(prefix: str, payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(payload).rstrip(b"\n")).hexdigest()
    return f"{prefix}:{digest}"


def _canonical_licence(value: object) -> str | None:
    text = str(value or "").casefold().replace("_", "-")
    if not text:
        return None
    aliases = {
        "cc0": ("cc0", "publicdomain/zero"),
        "cc-by": ("cc-by", "licenses/by/", "cc by"),
        "cc-by-sa": ("cc-by-sa", "licenses/by-sa/", "cc by sa"),
        "cc-by-nd": ("cc-by-nd", "licenses/by-nd/", "cc by nd"),
        "cc-by-nc": ("cc-by-nc", "licenses/by-nc/", "cc by nc"),
        "cc-by-nc-sa": (
            "cc-by-nc-sa",
            "licenses/by-nc-sa/",
            "cc by nc sa",
        ),
        "cc-by-nc-nd": (
            "cc-by-nc-nd",
            "licenses/by-nc-nd/",
            "cc by nc nd",
        ),
    }
    for name in (
        "cc-by-nc-nd",
        "cc-by-nc-sa",
        "cc-by-nc",
        "cc-by-nd",
        "cc-by-sa",
        "cc-by",
        "cc0",
    ):
        if any(alias in text for alias in aliases[name]):
            return name
    return text.rstrip("/")


def deduplicate_metadata(args: argparse.Namespace) -> None:
    crosswalk = read_jsonl(args.crosswalk)
    gbif_to_bl = {
        f"gbif:{row['gbif_taxon_key']}": row["butterflylens_key"]
        for row in crosswalk
        if row.get("gbif_taxon_key") is not None
    }
    observations = pq.read_table(args.observations).to_pylist()
    media = pq.read_table(args.media).to_pylist()
    groups: dict[str, dict[str, set[str]]] = {}

    def group(identity: str) -> dict[str, set[str]]:
        return groups.setdefault(
            identity,
            {"ALA": set(), "GBIF": set(), "iNaturalist": set(), "taxon_keys": set()},
        )

    ala_columns = [
        "ala_record_id",
        "source_occurrence_id",
        "source_reference",
        "butterflylens_taxon_key",
    ]
    for row in pq.read_table(args.ala_occurrences, columns=ala_columns).to_pylist():
        identity = _inat_observation_id(row["source_occurrence_id"], row["source_reference"])
        if identity:
            target = group(identity)
            target["ALA"].add(row["ala_record_id"])
            if row["butterflylens_taxon_key"]:
                target["taxon_keys"].add(row["butterflylens_taxon_key"])
    observation_by_id = {row["reference_observation_id"]: row for row in observations}
    for row in observations:
        identity = (
            str(row["source_observation_id"])
            if row["source"] == "iNaturalist"
            else _inat_observation_id(row["source_record_url"])
        )
        if identity:
            target = group(identity)
            target[row["source"]].add(row["reference_observation_id"])
            taxon_key = gbif_to_bl.get(row["accepted_taxon_key"])
            if taxon_key:
                target["taxon_keys"].add(taxon_key)
    observation_rows = []
    for identity, members in sorted(groups.items()):
        present = [source for source in ("ALA", "GBIF", "iNaturalist") if members[source]]
        if len(present) < 2:
            continue
        taxon_keys = sorted(members["taxon_keys"])
        payload = {
            "provider_identity_type": "inaturalist_observation",
            "provider_identity": identity,
            "ala_record_ids": sorted(members["ALA"]),
            "gbif_reference_observation_ids": sorted(members["GBIF"]),
            "inaturalist_reference_observation_ids": sorted(members["iNaturalist"]),
            "butterflylens_taxon_keys": taxon_keys,
        }
        conflict = len(taxon_keys) > 1
        observation_rows.append(
            {
                "schema_version": OBSERVATION_MIRROR_SCHEMA_VERSION,
                "observation_mirror_group_id": _identity("observation-mirror", payload),
                **payload,
                "source_count": len(present),
                "member_count": sum(len(members[source]) for source in present),
                "taxon_conflict": conflict,
                "resolution_state": (
                    "taxon_conflict_review_required"
                    if conflict
                    else "same_provider_observation_metadata_link"
                ),
                "evidence_fingerprint": "sha256:"
                + hashlib.sha256(canonical_json(payload).rstrip(b"\n")).hexdigest(),
            }
        )
    media_groups: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
    for row in media:
        observation = observation_by_id[row["reference_observation_id"]]
        obs_identity = (
            str(observation["source_observation_id"])
            if observation["source"] == "iNaturalist"
            else _inat_observation_id(observation["source_record_url"])
        )
        photo_identity = _inat_photo_id(row)
        if obs_identity and photo_identity:
            media_groups.setdefault(
                (obs_identity, photo_identity), {"GBIF": [], "iNaturalist": []}
            )[row["source"]].append(row)
    media_rows = []
    for (obs_identity, photo_identity), members in sorted(media_groups.items()):
        if not members["GBIF"] or not members["iNaturalist"]:
            continue
        all_rows = members["GBIF"] + members["iNaturalist"]
        taxon_keys = sorted(
            {
                gbif_to_bl[
                    observation_by_id[row["reference_observation_id"]][
                        "accepted_taxon_key"
                    ]
                ]
                for row in all_rows
                if observation_by_id[row["reference_observation_id"]][
                    "accepted_taxon_key"
                ]
                in gbif_to_bl
            }
        )
        licences = sorted(
            {
                value
                for value in (
                    _canonical_licence(row["licence"]) for row in all_rows
                )
                if value
            }
        )
        payload = {
            "provider_observation_id": obs_identity,
            "provider_photo_id": photo_identity,
            "gbif_reference_media_ids": sorted(
                row["reference_media_id"] for row in members["GBIF"]
            ),
            "inaturalist_reference_media_ids": sorted(
                row["reference_media_id"] for row in members["iNaturalist"]
            ),
            "butterflylens_taxon_keys": taxon_keys,
            "canonical_licences": licences,
        }
        conflict = len(taxon_keys) > 1 or len(licences) > 1
        media_rows.append(
            {
                "schema_version": MEDIA_DUPLICATE_SCHEMA_VERSION,
                "media_duplicate_candidate_id": _identity("media-duplicate-candidate", payload),
                **payload,
                "member_count": len(all_rows),
                "metadata_conflict": conflict,
                "exact_bytes_equal": None,
                "perceptual_duplicate": None,
                "canonical_reference_media_id": None,
                "resolution_state": (
                    "metadata_conflict_review_required"
                    if conflict
                    else "provider_mirror_pending_byte_validation"
                ),
                "evidence_fingerprint": "sha256:"
                + hashlib.sha256(canonical_json(payload).rstrip(b"\n")).hexdigest(),
            }
        )
    observation_schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("observation_mirror_group_id", pa.string()),
            ("provider_identity_type", pa.string()),
            ("provider_identity", pa.string()),
            ("ala_record_ids", pa.list_(pa.string())),
            ("gbif_reference_observation_ids", pa.list_(pa.string())),
            ("inaturalist_reference_observation_ids", pa.list_(pa.string())),
            ("butterflylens_taxon_keys", pa.list_(pa.string())),
            ("source_count", pa.uint8()),
            ("member_count", pa.uint32()),
            ("taxon_conflict", pa.bool_()),
            ("resolution_state", pa.string()),
            ("evidence_fingerprint", pa.string()),
        ]
    )
    media_schema = pa.schema(
        [
            ("schema_version", pa.string()),
            ("media_duplicate_candidate_id", pa.string()),
            ("provider_observation_id", pa.string()),
            ("provider_photo_id", pa.string()),
            ("gbif_reference_media_ids", pa.list_(pa.string())),
            ("inaturalist_reference_media_ids", pa.list_(pa.string())),
            ("butterflylens_taxon_keys", pa.list_(pa.string())),
            ("canonical_licences", pa.list_(pa.string())),
            ("member_count", pa.uint32()),
            ("metadata_conflict", pa.bool_()),
            ("exact_bytes_equal", pa.bool_()),
            ("perceptual_duplicate", pa.bool_()),
            ("canonical_reference_media_id", pa.string()),
            ("resolution_state", pa.string()),
            ("evidence_fingerprint", pa.string()),
        ]
    )
    write_parquet(args.observation_output, observation_rows, observation_schema)
    write_parquet(args.media_output, media_rows, media_schema)
    manifest = {
        "schema_version": DEDUPLICATION_MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "metadata_links_complete_byte_deduplication_pending",
        "policy": {
            "provider_identity": "exact iNaturalist observation and photo identifiers only",
            "byte_or_perceptual_deduplication_claimed": False,
            "canonical_media_selected": False,
            "taxon_conflicts_block": True,
        },
        "counts": {
            "observation_mirror_groups": len(observation_rows),
            "observation_taxon_conflicts": sum(row["taxon_conflict"] for row in observation_rows),
            "media_duplicate_candidates": len(media_rows),
            "media_metadata_conflicts": sum(row["metadata_conflict"] for row in media_rows),
        },
        "artifacts": {
            "observation_mirror_groups": artifact(
                args.observation_output,
                rows=len(observation_rows),
                manifest_path=(
                    "deduplicated/reference_observation_mirror_groups.parquet"
                ),
            ),
            "media_duplicate_candidates": artifact(
                args.media_output,
                rows=len(media_rows),
                manifest_path=(
                    "deduplicated/reference_media_duplicate_candidates.parquet"
                ),
            ),
        },
        "inputs": {
            "ala_occurrences_sha256": sha256_file(args.ala_occurrences),
            "reference_observations_sha256": sha256_file(args.observations),
            "reference_media_candidates_sha256": sha256_file(args.media),
            "crosswalk_sha256": sha256_file(args.crosswalk),
            "biominer_origin_sha": BIOMINER_SHA,
        },
    }
    write_json(args.manifest, manifest)
    pack = json.loads(args.pack_manifest.read_text())
    pack["reference_state"].update(
        {
            "deduplication_status": manifest["status"],
            "deduplication_manifest_path": (
                "references/v1/reference_deduplication_manifest.json"
            ),
            "deduplication_manifest_sha256": sha256_file(args.manifest),
            **manifest["counts"],
        }
    )
    write_json(args.pack_manifest, pack)
    print(json.dumps(manifest["counts"], sort_keys=True))


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
    deduplicate = subparsers.add_parser("deduplicate-metadata")
    deduplicate.add_argument("--crosswalk", type=Path, required=True)
    deduplicate.add_argument("--ala-occurrences", type=Path, required=True)
    deduplicate.add_argument("--observations", type=Path, required=True)
    deduplicate.add_argument("--media", type=Path, required=True)
    deduplicate.add_argument("--observation-output", type=Path, required=True)
    deduplicate.add_argument("--media-output", type=Path, required=True)
    deduplicate.add_argument("--manifest", type=Path, required=True)
    deduplicate.add_argument("--pack-manifest", type=Path, required=True)
    deduplicate.add_argument("--generated-at", required=True)
    deduplicate.set_defaults(handler=deduplicate_metadata)
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
