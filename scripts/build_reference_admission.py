#!/usr/bin/env python3
"""Plan and publish conservative automated reference-media gates.

The planner operates on frozen provider metadata and emits BioMiner's pinned
selection schema. Source image bytes are downloaded only by the pinned
BioMiner worker into an ignored cache; this adapter publishes metadata,
checksums, decode evidence, and explicit shortfalls without relabelling a
provider assertion as human verification.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import pyarrow as pa
import pyarrow.parquet as pq


BIOMINER_SHA = "d71bceabf75748a25df39d0025e8da907f295f8c"
GATE_DECISION_SCHEMA_VERSION = "butterflylens-reference-media-gate/v1"
GATE_PLAN_MANIFEST_SCHEMA_VERSION = "butterflylens-reference-gate-plan/v1"
ADMISSION_MANIFEST_SCHEMA_VERSION = "butterflylens-reference-admission-manifest/v1"
SELECTION_SCHEMA_VERSION = "reference-acquisition-selections-v1.0.0"
MEDIA_OBJECT_SCHEMA_VERSION = "reference-media-objects-v1.1.0"
DOWNLOAD_REPORT_SCHEMA_VERSION = "reference-media-download-report-v1"
ROOT_TARGET_KEY = "bltx:v1:846e98d50678dffa38d43103"
SELECTION_STRATEGY = "butterflylens-metadata-gate-diversity-v1"
SELECTION_SEED = 20_260_718
MAXIMUM_PER_SPECIES = 20
MAXIMUM_PER_OBSERVER = 50
APPROVED_INATURALIST_HOST = "inaturalist-open-data.s3.amazonaws.com"
_CC_CODE = re.compile(
    r"(?:cc[- _]*)?(?P<code>0|zero|by(?:[- _]+(?:nc|nd|sa)){0,2})"
    r"(?:[- _]+v?(?P<version>\d+(?:\.\d+)?))?\Z",
    re.IGNORECASE,
)


class ReferenceAdmissionError(RuntimeError):
    """Raised when a frozen admission contract is inconsistent."""


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def canonical_licence(value: object) -> str | None:
    text = str(value or "").strip().casefold()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme or parsed.netloc:
        if parsed.scheme not in {"http", "https"}:
            return None
        if (parsed.hostname or "").removeprefix("www.") != "creativecommons.org":
            return None
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 3 and parts[:2] == ["publicdomain", "zero"]:
            return "cc0"
        if len(parts) >= 3 and parts[0] == "licenses":
            candidate = "cc-" + parts[1]
            return candidate if candidate in _known_licences() else None
        return None
    normalized = text.replace("creative commons", "cc")
    normalized = re.sub(r"\b(?:licen[cs]e|legalcode)\b", "", normalized)
    normalized = re.sub(r"[()]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" -_")
    match = _CC_CODE.fullmatch(normalized)
    if match is None:
        return None
    code = match.group("code").replace("_", "-").replace(" ", "-")
    candidate = "cc0" if code in {"0", "zero"} else "cc-" + code
    return candidate if candidate in _known_licences() else None


def _known_licences() -> frozenset[str]:
    return frozenset(
        {
            "cc0",
            "cc-by",
            "cc-by-sa",
            "cc-by-nc",
            "cc-by-nc-sa",
            "cc-by-nd",
            "cc-by-nc-nd",
        }
    )


def licence_decision(row: dict[str, Any]) -> tuple[str, str | None, str | None]:
    supplied = [row.get("licence"), row.get("licence_uri")]
    canonical = [canonical_licence(value) for value in supplied if value]
    if not canonical:
        return "quarantined", None, "missing_media_licence"
    if any(value is None for value in canonical):
        return "quarantined", None, "unrecognised_media_licence"
    values = sorted(set(value for value in canonical if value))
    if len(values) != 1:
        return "quarantined", None, "conflicting_media_licence"
    value = values[0]
    if value not in {"cc0", "cc-by"}:
        return "denied", value, f"media_licence_not_allowed:{value}"
    if value == "cc-by" and not str(row.get("attribution") or "").strip():
        return "quarantined", value, "missing_required_attribution"
    return "allowed", value, None


def _selection_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("reference_selection_id", pa.string()),
            ("acquisition_plan_id", pa.string()),
            ("target_accepted_taxon_key", pa.string()),
            ("candidate_set_id", pa.string()),
            ("source_candidate_set_id", pa.string()),
            ("candidate_accepted_taxon_key", pa.string()),
            ("scientific_name", pa.string()),
            ("geo_cluster_id", pa.string()),
            ("life_stage", pa.string()),
            ("visual_domain", pa.string()),
            ("reference_media_id", pa.string()),
            ("reference_observation_id", pa.string()),
            ("source", pa.string()),
            ("fallback_level", pa.uint8()),
            ("selection_rank", pa.uint32()),
            ("selection_round", pa.string()),
            ("distance_to_cluster_medoid_km", pa.float64()),
            ("observer_id", pa.string()),
            ("observed_date", pa.date32()),
            ("locality", pa.string()),
            ("background_group_id", pa.string()),
            ("licence", pa.string()),
            ("source_snapshot_version", pa.string()),
            ("selection_strategy", pa.string()),
            ("selection_seed", pa.uint64()),
            ("plan_configuration_fingerprint", pa.string()),
            ("selected_at", pa.timestamp("us", tz="UTC")),
        ]
    )


def _decision_schema() -> pa.Schema:
    return pa.schema(
        [
            ("schema_version", pa.string()),
            ("reference_media_id", pa.string()),
            ("reference_observation_id", pa.string()),
            ("source", pa.string()),
            ("provider_media_id", pa.string()),
            ("accepted_taxon_key", pa.string()),
            ("butterflylens_taxon_key", pa.string()),
            ("taxon_gate_status", pa.string()),
            ("licence_policy_status", pa.string()),
            ("canonical_licence", pa.string()),
            ("licence_reason", pa.string()),
            ("provider_host", pa.string()),
            ("provider_download_policy_status", pa.string()),
            ("metadata_exclusion_reasons", pa.list_(pa.string())),
            ("observation_mirror_conflict", pa.bool_()),
            ("media_mirror_conflict", pa.bool_()),
            ("automated_gate_status", pa.string()),
            ("gate_reason_codes", pa.list_(pa.string())),
            ("selected_for_download", pa.bool_()),
            ("selection_rank", pa.uint32()),
            ("verification_status", pa.string()),
            ("evidence_fingerprint", pa.string()),
        ]
    )


def _mirror_conflicts(
    observation_groups: Path,
    media_groups: Path,
) -> tuple[set[str], set[str]]:
    observation_conflicts: set[str] = set()
    for row in pq.read_table(observation_groups).to_pylist():
        if row["taxon_conflict"]:
            observation_conflicts.update(row["gbif_reference_observation_ids"])
            observation_conflicts.update(row["inaturalist_reference_observation_ids"])
    media_conflicts: set[str] = set()
    for row in pq.read_table(media_groups).to_pylist():
        if row["metadata_conflict"]:
            media_conflicts.update(row["gbif_reference_media_ids"])
            media_conflicts.update(row["inaturalist_reference_media_ids"])
    return observation_conflicts, media_conflicts


def _selection_id(row: dict[str, Any]) -> str:
    payload = {
        "acquisition_plan_id": row["acquisition_plan_id"],
        "reference_media_id": row["reference_media_id"],
        "candidate_accepted_taxon_key": row["candidate_accepted_taxon_key"],
        "geo_cluster_id": row["geo_cluster_id"],
        "life_stage": row["life_stage"],
        "visual_domain": row["visual_domain"],
    }
    return "reference-selection:" + semantic_digest(payload).removeprefix("sha256:")


def _candidate_rank(row: dict[str, Any]) -> tuple[int, str, str]:
    media = row["media"]
    area = int(media.get("width") or 0) * int(media.get("height") or 0)
    tie = semantic_digest(
        {
            "selection_seed": SELECTION_SEED,
            "reference_media_id": media["reference_media_id"],
        }
    )
    return (-area, tie, str(media["reference_media_id"]))


def _select_candidates(
    eligible: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_taxon: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_taxon[str(row["butterflylens_taxon_key"])].append(row)
    candidates_by_taxon: dict[str, list[dict[str, Any]]] = {}
    for taxon_key, taxon_rows in sorted(by_taxon.items()):
        best_by_observation: dict[str, dict[str, Any]] = {}
        for row in taxon_rows:
            observation_id = str(row["media"]["reference_observation_id"])
            current = best_by_observation.get(observation_id)
            if current is None or _candidate_rank(row) < _candidate_rank(current):
                best_by_observation[observation_id] = row
        candidates_by_taxon[taxon_key] = sorted(
            best_by_observation.values(), key=_candidate_rank
        )
    selected: list[dict[str, Any]] = []
    selected_ids: dict[str, set[str]] = defaultdict(set)
    selected_observers: dict[str, set[str]] = defaultdict(set)
    global_observer_counts: Counter[str] = Counter()
    for rank in range(1, MAXIMUM_PER_SPECIES + 1):
        for taxon_key, candidates in sorted(candidates_by_taxon.items()):
            available = []
            for row in candidates:
                media_id = str(row["media"]["reference_media_id"])
                if media_id in selected_ids[taxon_key]:
                    continue
                observer = str(
                    row["observation"].get("observer_id") or ""
                ).strip()
                if observer and global_observer_counts[observer] >= MAXIMUM_PER_OBSERVER:
                    continue
                available.append(row)
            if not available:
                continue
            diverse = [
                row
                for row in available
                if str(row["observation"].get("observer_id") or "").strip()
                not in selected_observers[taxon_key]
            ]
            row = min(diverse or available, key=_candidate_rank)
            media_id = str(row["media"]["reference_media_id"])
            observer = str(row["observation"].get("observer_id") or "").strip()
            selected_ids[taxon_key].add(media_id)
            if observer:
                selected_observers[taxon_key].add(observer)
                global_observer_counts[observer] += 1
            row["selection_rank"] = rank
            row["selection_taxon_key"] = taxon_key
            selected.append(row)
    return selected


def plan(args: argparse.Namespace) -> None:
    crosswalk = read_jsonl(args.crosswalk)
    gbif_to_bl = {
        f"gbif:{row['gbif_taxon_key']}": row["butterflylens_key"]
        for row in crosswalk
        if row.get("gbif_taxon_key") is not None
    }
    observations = pq.read_table(args.observations).to_pylist()
    observation_by_id = {
        row["reference_observation_id"]: row for row in observations
    }
    media = pq.read_table(args.media).to_pylist()
    observation_conflicts, media_conflicts = _mirror_conflicts(
        args.observation_mirrors,
        args.media_duplicates,
    )
    decisions: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []
    decision_by_media_id: dict[str, dict[str, Any]] = {}
    for media_row in media:
        observation = observation_by_id[media_row["reference_observation_id"]]
        accepted_key = observation.get("accepted_taxon_key")
        butterflylens_key = gbif_to_bl.get(str(accepted_key))
        reasons: set[str] = set()
        if observation["taxon_reconciliation_status"] != "accepted_key_exact":
            reasons.add("taxon_reconciliation_not_exact")
        if butterflylens_key is None:
            reasons.add("accepted_taxon_not_in_crosswalk")
        observation_conflict = (
            media_row["reference_observation_id"] in observation_conflicts
        )
        if observation_conflict:
            reasons.add("observation_mirror_taxon_conflict")
        licence_status, canonical, licence_reason = licence_decision(media_row)
        if licence_status != "allowed":
            reasons.add(licence_reason or f"licence_status:{licence_status}")
        parsed = urlparse(str(media_row.get("media_identifier") or ""))
        host = parsed.hostname
        provider_allowed = (
            media_row["source"] == "iNaturalist"
            and parsed.scheme == "https"
            and host == APPROVED_INATURALIST_HOST
        )
        if not provider_allowed:
            reasons.add("provider_download_policy_not_approved")
        exclusions = sorted(
            value
            for value in str(media_row.get("exclusion_reason") or "").split(";")
            if value
        )
        reasons.update(f"import_exclusion:{value}" for value in exclusions)
        if media_row["download_status"] != "pending":
            reasons.add("download_status_not_pending")
        media_conflict = media_row["reference_media_id"] in media_conflicts
        if media_conflict:
            reasons.add("media_mirror_metadata_conflict")
        payload = {
            "reference_media_id": media_row["reference_media_id"],
            "reference_observation_id": media_row["reference_observation_id"],
            "source": media_row["source"],
            "provider_media_id": media_row["provider_media_id"],
            "accepted_taxon_key": accepted_key,
            "butterflylens_taxon_key": butterflylens_key,
            "taxon_gate_status": (
                "passed_exact_provider_assertion"
                if not {
                    "taxon_reconciliation_not_exact",
                    "accepted_taxon_not_in_crosswalk",
                    "observation_mirror_taxon_conflict",
                }
                & reasons
                else "blocked"
            ),
            "licence_policy_status": licence_status,
            "canonical_licence": canonical,
            "licence_reason": licence_reason,
            "provider_host": host,
            "provider_download_policy_status": (
                "approved" if provider_allowed else "blocked"
            ),
            "metadata_exclusion_reasons": exclusions,
            "observation_mirror_conflict": observation_conflict,
            "media_mirror_conflict": media_conflict,
            "automated_gate_status": "eligible" if not reasons else "blocked",
            "gate_reason_codes": sorted(reasons),
            "selected_for_download": False,
            "selection_rank": None,
            "verification_status": "unreviewed",
        }
        decision = {
            "schema_version": GATE_DECISION_SCHEMA_VERSION,
            **payload,
            "evidence_fingerprint": semantic_digest(payload),
        }
        decisions.append(decision)
        decision_by_media_id[media_row["reference_media_id"]] = decision
        if not reasons:
            eligible.append(
                {
                    "media": media_row,
                    "observation": observation,
                    "butterflylens_taxon_key": butterflylens_key,
                }
            )
    selected = _select_candidates(eligible)
    import_manifest_sha = sha256_file(args.import_manifest)
    policy_payload = {
        "policy_version": SELECTION_STRATEGY,
        "maximum_per_species": MAXIMUM_PER_SPECIES,
        "maximum_per_observer": MAXIMUM_PER_OBSERVER,
        "selection_seed": SELECTION_SEED,
        "licences_allowed": ["cc0", "cc-by"],
        "approved_provider_host": APPROVED_INATURALIST_HOST,
        "one_media_per_observation": True,
        "observer_diversity_first": True,
        "mirror_conflicts_block": True,
        "provider_assertions_are_human_verification": False,
    }
    plan_fingerprint = semantic_digest(
        {
            "policy": policy_payload,
            "inputs": {
                "import_manifest_sha256": import_manifest_sha,
                "observation_mirrors_sha256": sha256_file(args.observation_mirrors),
                "media_duplicates_sha256": sha256_file(args.media_duplicates),
            },
        }
    )
    candidate_set_id = "butterflylens:australian-butterflies-v1:reference-bank-v1"
    acquisition_plan_id = "reference-plan:" + semantic_digest(
        {
            "target_accepted_taxon_key": ROOT_TARGET_KEY,
            "candidate_set_id": candidate_set_id,
            "plan_configuration_fingerprint": plan_fingerprint,
        }
    ).removeprefix("sha256:")
    selected_at = datetime.fromisoformat(args.generated_at.replace("Z", "+00:00"))
    if selected_at.tzinfo is None or selected_at.utcoffset() != UTC.utcoffset(selected_at):
        raise ReferenceAdmissionError("generated-at must be a UTC timestamp")
    selection_rows: list[dict[str, Any]] = []
    source_candidate_set_id = "reference-import:" + import_manifest_sha[:32]
    for item in selected:
        media_row = item["media"]
        observation = item["observation"]
        row = {
            "schema_version": SELECTION_SCHEMA_VERSION,
            "reference_selection_id": "",
            "acquisition_plan_id": acquisition_plan_id,
            "target_accepted_taxon_key": ROOT_TARGET_KEY,
            "candidate_set_id": candidate_set_id,
            "source_candidate_set_id": source_candidate_set_id,
            "candidate_accepted_taxon_key": observation["accepted_taxon_key"],
            "scientific_name": observation["reconciled_scientific_name"],
            "geo_cluster_id": observation["geo_cluster_id"],
            "life_stage": observation["life_stage"],
            "visual_domain": "unreviewed",
            "reference_media_id": media_row["reference_media_id"],
            "reference_observation_id": media_row["reference_observation_id"],
            "source": media_row["source"],
            "fallback_level": observation["fallback_level"],
            "selection_rank": item["selection_rank"],
            "selection_round": "independent_observation",
            "distance_to_cluster_medoid_km": observation[
                "distance_to_cluster_medoid_km"
            ],
            "observer_id": observation["observer_id"],
            "observed_date": (
                observation["observed_at"].date()
                if observation["observed_at"] is not None
                else None
            ),
            "locality": observation["locality"],
            "background_group_id": None,
            "licence": media_row["licence"],
            "source_snapshot_version": media_row["source_snapshot_version"],
            "selection_strategy": SELECTION_STRATEGY,
            "selection_seed": SELECTION_SEED,
            "plan_configuration_fingerprint": plan_fingerprint,
            "selected_at": selected_at,
        }
        row["reference_selection_id"] = _selection_id(row)
        selection_rows.append(row)
        decision = decision_by_media_id[media_row["reference_media_id"]]
        decision["selected_for_download"] = True
        decision["selection_rank"] = item["selection_rank"]
        payload = {
            key: value
            for key, value in decision.items()
            if key not in {"schema_version", "evidence_fingerprint"}
        }
        decision["evidence_fingerprint"] = semantic_digest(payload)
    decisions.sort(key=lambda row: row["reference_media_id"])
    selection_rows.sort(
        key=lambda row: (
            row["candidate_accepted_taxon_key"],
            row["selection_rank"],
            row["reference_media_id"],
        )
    )
    write_parquet(args.decisions_output, decisions, _decision_schema())
    write_parquet(args.selections_output, selection_rows, _selection_schema())
    selection_counts = Counter(
        row["candidate_accepted_taxon_key"] for row in selection_rows
    )
    manifest = {
        "schema_version": GATE_PLAN_MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "download_selection_ready_provider_asserted_unreviewed",
        "candidate_semantics": (
            "provider-asserted provisional support; not human-verified identity"
        ),
        "biominer_origin_sha": BIOMINER_SHA,
        "policy": policy_payload,
        "counts": {
            "media_candidates": len(media),
            "metadata_gate_eligible": len(eligible),
            "metadata_gate_blocked": len(media) - len(eligible),
            "selected_for_download": len(selection_rows),
            "selected_species": len(selection_counts),
            "species_at_quota": sum(
                count == MAXIMUM_PER_SPECIES for count in selection_counts.values()
            ),
            "human_verified_media": 0,
        },
        "gate_status_counts": dict(
            sorted(Counter(row["automated_gate_status"] for row in decisions).items())
        ),
        "licence_status_counts": dict(
            sorted(Counter(row["licence_policy_status"] for row in decisions).items())
        ),
        "provider_policy_counts": dict(
            sorted(
                Counter(
                    row["provider_download_policy_status"] for row in decisions
                ).items()
            )
        ),
        "artifacts": {
            "gate_decisions": artifact(
                args.decisions_output,
                rows=len(decisions),
                manifest_path="gated/reference_media_gate_decisions.parquet",
            ),
            "download_selections": artifact(
                args.selections_output,
                rows=len(selection_rows),
                manifest_path="gated/reference_download_selections.parquet",
            ),
        },
        "inputs": {
            "crosswalk_sha256": sha256_file(args.crosswalk),
            "reference_observations_sha256": sha256_file(args.observations),
            "reference_media_candidates_sha256": sha256_file(args.media),
            "observation_mirrors_sha256": sha256_file(args.observation_mirrors),
            "media_duplicates_sha256": sha256_file(args.media_duplicates),
            "import_manifest_sha256": import_manifest_sha,
        },
        "acquisition_plan_id": acquisition_plan_id,
        "plan_configuration_fingerprint": plan_fingerprint,
    }
    write_json(args.manifest_output, manifest)
    print(json.dumps(manifest["counts"], sort_keys=True))


def publish(args: argparse.Namespace) -> None:
    plan_manifest = json.loads(args.plan_manifest.read_text())
    download_report = json.loads(args.download_report.read_text())
    decisions = pq.read_table(args.decisions)
    selections = pq.read_table(args.selections)
    media_objects = pq.read_table(args.media_objects)
    if media_objects.num_rows != selections.num_rows:
        raise ReferenceAdmissionError("media-object inventory does not cover selections")
    selected_ids = set(selections.column("reference_media_id").to_pylist())
    object_ids = set(media_objects.column("reference_media_id").to_pylist())
    if selected_ids != object_ids:
        raise ReferenceAdmissionError("media-object identities do not match selections")
    if set(media_objects.column("schema_version").to_pylist()) != {
        MEDIA_OBJECT_SCHEMA_VERSION
    }:
        raise ReferenceAdmissionError("unexpected BioMiner media-object schema")
    if download_report.get("schema_version") != DOWNLOAD_REPORT_SCHEMA_VERSION:
        raise ReferenceAdmissionError("unexpected BioMiner download-report schema")
    if download_report.get("status") not in {"complete", "complete_with_errors"}:
        raise ReferenceAdmissionError("BioMiner download report is not complete")
    report_counts = download_report.get("counts", {})
    if report_counts.get("selected") != selections.num_rows:
        raise ReferenceAdmissionError("download-report selection count does not match")
    if report_counts.get("rows_out") != media_objects.num_rows:
        raise ReferenceAdmissionError("download-report output count does not match")
    media_rows = media_objects.to_pylist()
    media_rows.sort(key=lambda row: row["reference_media_id"])
    write_parquet(args.media_objects_output, media_rows, media_objects.schema)
    write_json(args.download_report_output, download_report)
    decode_counts = Counter(row["decode_status"] for row in media_rows)
    licence_counts = Counter(row["licence_policy_status"] for row in media_rows)
    valid = [row for row in media_rows if row["decode_status"] == "valid"]
    failures = len(media_rows) - len(valid)
    if report_counts.get("committed") != len(valid):
        raise ReferenceAdmissionError("download-report committed count does not match")
    if report_counts.get("quarantined") != failures:
        raise ReferenceAdmissionError("download-report quarantine count does not match")
    if any(row["licence_policy_status"] != "allowed" for row in valid):
        raise ReferenceAdmissionError("valid media object escaped the allowed licence lane")
    manifest = {
        "schema_version": ADMISSION_MANIFEST_SCHEMA_VERSION,
        "generated_at": args.generated_at,
        "status": "automated_gates_complete_provider_asserted_provisional_support",
        "candidate_semantics": (
            "provider-asserted provisional support; not human-verified identity"
        ),
        "biominer": {
            "origin_sha": BIOMINER_SHA,
            "media_object_schema_version": MEDIA_OBJECT_SCHEMA_VERSION,
            "downloader": "reference-media-downloader-v2",
        },
        "policy": {
            **plan_manifest["policy"],
            "decode_success_required": True,
            "checksum_required": True,
            "source_media_bytes_committed_to_git": False,
        },
        "counts": {
            **plan_manifest["counts"],
            "download_results": len(media_rows),
            "provisional_support_candidates": len(valid),
            "download_or_decode_failures": failures,
            "unique_content_sha256": len({row["sha256"] for row in valid}),
            "source_bytes_referenced": sum(
                int(row["source_byte_count"] or 0) for row in valid
            ),
            "content_addressed_source_bytes": int(
                download_report.get("bytes", {}).get("source_objects", 0)
            ),
            "human_verified_media": 0,
        },
        "decode_status_counts": dict(sorted(decode_counts.items())),
        "download_licence_status_counts": dict(sorted(licence_counts.items())),
        "artifacts": {
            "gate_decisions": artifact(
                args.decisions,
                rows=decisions.num_rows,
                manifest_path="gated/reference_media_gate_decisions.parquet",
            ),
            "download_selections": artifact(
                args.selections,
                rows=selections.num_rows,
                manifest_path="gated/reference_download_selections.parquet",
            ),
            "media_objects": artifact(
                args.media_objects_output,
                rows=len(media_rows),
                manifest_path="gated/reference_media_objects.parquet",
            ),
            "gate_plan_manifest": artifact(
                args.plan_manifest,
                manifest_path="reference_gate_plan_manifest.json",
            ),
            "download_report": artifact(
                args.download_report_output,
                manifest_path="reference_media_download_report.json",
            ),
        },
        "inputs": {
            "normalized_biominer_media_objects_sha256": sha256_file(
                args.media_objects_output
            ),
            "normalized_biominer_download_report_sha256": sha256_file(
                args.download_report_output
            ),
            "gate_plan_manifest_sha256": sha256_file(args.plan_manifest),
        },
        "limitations": [
            "no provider assertion is human verification",
            "GBIF media download hosts remain blocked without an approved host policy",
            "decoded source bytes remain in ignored local cache pending durable object storage",
            "YOLOE routing and BioCLIP evidence are pending later subtasks",
        ],
    }
    write_json(args.manifest_output, manifest)
    pack = json.loads(args.pack_manifest.read_text())
    reference_state = pack["reference_state"]
    reference_state.setdefault("import_status", reference_state.get("status"))
    reference_state.update(
        {
            "status": manifest["status"],
            "admission_status": manifest["status"],
            "admission_manifest_path": "references/v1/reference_admission_manifest.json",
            "admission_manifest_sha256": sha256_file(args.manifest_output),
            "selected_for_download": selections.num_rows,
            "images_downloaded": len(valid),
            "download_or_decode_failures": failures,
            "human_verified_media": 0,
            "source_media_bytes_committed_to_git": False,
            "generated_at": args.generated_at,
        }
    )
    write_json(args.pack_manifest, pack)
    print(json.dumps(manifest["counts"], sort_keys=True))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    subparsers = root.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument("--crosswalk", type=Path, required=True)
    plan_parser.add_argument("--observations", type=Path, required=True)
    plan_parser.add_argument("--media", type=Path, required=True)
    plan_parser.add_argument("--observation-mirrors", type=Path, required=True)
    plan_parser.add_argument("--media-duplicates", type=Path, required=True)
    plan_parser.add_argument("--import-manifest", type=Path, required=True)
    plan_parser.add_argument("--decisions-output", type=Path, required=True)
    plan_parser.add_argument("--selections-output", type=Path, required=True)
    plan_parser.add_argument("--manifest-output", type=Path, required=True)
    plan_parser.add_argument("--generated-at", required=True)
    plan_parser.set_defaults(handler=plan)
    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--plan-manifest", type=Path, required=True)
    publish_parser.add_argument("--decisions", type=Path, required=True)
    publish_parser.add_argument("--selections", type=Path, required=True)
    publish_parser.add_argument("--media-objects", type=Path, required=True)
    publish_parser.add_argument("--media-objects-output", type=Path, required=True)
    publish_parser.add_argument("--download-report", type=Path, required=True)
    publish_parser.add_argument("--download-report-output", type=Path, required=True)
    publish_parser.add_argument("--manifest-output", type=Path, required=True)
    publish_parser.add_argument("--pack-manifest", type=Path, required=True)
    publish_parser.add_argument("--generated-at", required=True)
    publish_parser.set_defaults(handler=publish)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        args.handler(args)
    except (OSError, ValueError, KeyError, ReferenceAdmissionError) as error:
        print(f"reference admission failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
