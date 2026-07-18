#!/usr/bin/env python3
"""Build and verify the immutable credential-free Submitted snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = ROOT / "packages" / "contracts" / "python"
sys.path.insert(0, str(CONTRACT_ROOT))

from butterflylens.contracts.fingerprint import canonicalize_json  # noqa: E402
from butterflylens.contracts.live_worker import (  # noqa: E402
    WORKER_IDENTITY_SCHEMA_VERSION,
)
from butterflylens.flickr import build_australia_known_lane  # noqa: E402


SNAPSHOT_SCHEMA_VERSION = "butterflylens-submitted-snapshot:v1.0.0"
SNAPSHOT_PATH = ROOT / "data" / "submission" / "v1" / "submitted_snapshot.json"
REPOSITORY = "karikris/ButterflyLens"
_SHA1 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class SnapshotFreezeError(RuntimeError):
    """Raised when a source or submitted-snapshot invariant is broken."""


def git_output(*arguments: str, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout if binary else completed.stdout.decode("utf-8").strip()


def source_bytes(source_commit: str, path: str) -> bytes:
    return bytes(git_output("show", f"{source_commit}:{path}", binary=True))


def source_json(source_commit: str, path: str) -> dict[str, Any]:
    value = json.loads(source_bytes(source_commit, path))
    if not isinstance(value, dict):
        raise SnapshotFreezeError(f"source JSON is not an object: {path}")
    return value


def source_jsonl(source_commit: str, path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in source_bytes(source_commit, path).decode("utf-8").splitlines():
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise SnapshotFreezeError(f"source JSONL row is not an object: {path}")
        rows.append(value)
    return rows


def git_object(source_commit: str, path: str) -> str:
    value = str(git_output("rev-parse", f"{source_commit}:{path}"))
    if _SHA1.fullmatch(value) is None:
        raise SnapshotFreezeError(f"invalid Git object for {path}")
    return value


def latest_path_commit(source_commit: str, path: str) -> str:
    value = str(
        git_output("log", "-1", "--format=%H", source_commit, "--", path)
    )
    if _SHA1.fullmatch(value) is None:
        raise SnapshotFreezeError(f"source commit is unavailable for {path}")
    return value


def artifact_ref(source_commit: str, path: str) -> dict[str, str]:
    payload = source_bytes(source_commit, path)
    return {
        "path": path,
        "physical_sha256": hashlib.sha256(payload).hexdigest(),
        "git_blob_sha": git_object(source_commit, path),
        "last_changed_commit": latest_path_commit(source_commit, path),
    }


def tree_ref(source_commit: str, path: str) -> dict[str, str]:
    return {
        "path": path,
        "git_tree_sha": git_object(source_commit, path),
        "last_changed_commit": latest_path_commit(source_commit, path),
    }


def build_submitted_snapshot(
    *,
    source_commit: str,
    frozen_at: str,
) -> dict[str, Any]:
    """Build the freeze from one committed source tree without provider calls."""

    source_commit = str(git_output("rev-parse", f"{source_commit}^{{commit}}"))
    if _SHA1.fullmatch(source_commit) is None or _UTC.fullmatch(frozen_at) is None:
        raise SnapshotFreezeError("a full source commit and UTC freeze time are required")
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as error:
        raise SnapshotFreezeError("source commit is not an ancestor of HEAD") from error

    pack_path = "data/packs/australian_butterflies/v1/manifest.json"
    taxa_path = "data/packs/australian_butterflies/v1/taxa.jsonl"
    names_path = "data/packs/australian_butterflies/v1/name_assertions.jsonl"
    ala_path = "data/packs/australian_butterflies/v1/ala/ala_snapshot_manifest.json"
    operations_path = "apps/web/src/operations/submittedOperationsSnapshot.json"
    monitoring_path = "apps/web/src/operations/submittedMonitoringSnapshot.json"
    quality_path = "apps/web/src/quality/submittedQualityProjection.json"
    review_media_path = "apps/web/src/review/reviewMediaManifest.json"
    rights_path = "provenance/data_rights_manifest.json"
    yoloe_path = (
        "data/packs/australian_butterflies/v1/references/v1/"
        "reference_yoloe_readiness_manifest.json"
    )
    bioclip_path = (
        "data/packs/australian_butterflies/v1/references/v1/"
        "reference_bioclip_status.json"
    )
    reference_bank_path = (
        "data/packs/australian_butterflies/v1/references/v1/"
        "reference_bank_manifest.json"
    )
    global_flickr_path = "packages/flickr/global_out_of_range_status.json"
    openai_requirements_path = "packages/openai/implementation-requirements.v1.json"
    openai_replay_path = "packages/openai/submitted-replays.v1.json"
    worker_contract_path = "packages/contracts/schemas/live-worker-contracts.schema.json"
    privacy_path = "policies/community-privacy-policy.v1.json"

    pack = source_json(source_commit, pack_path)
    ala = source_json(source_commit, ala_path)
    operations = source_json(source_commit, operations_path)
    monitoring = source_json(source_commit, monitoring_path)
    quality = source_json(source_commit, quality_path)
    review_media = source_json(source_commit, review_media_path)
    yoloe = source_json(source_commit, yoloe_path)
    bioclip = source_json(source_commit, bioclip_path)
    reference_bank = source_json(source_commit, reference_bank_path)
    global_flickr = source_json(source_commit, global_flickr_path)
    openai_requirements = source_json(source_commit, openai_requirements_path)
    openai_replay = source_json(source_commit, openai_replay_path)
    privacy = source_json(source_commit, privacy_path)

    taxa = source_jsonl(source_commit, taxa_path)
    names = source_jsonl(source_commit, names_path)
    lane = build_australia_known_lane(
        taxa,
        names,
        source_pack_id=str(pack["pack_id"]),
        source_taxa_sha256=str(pack["artifacts"]["taxa.jsonl"]["physical_sha256"]),
        source_name_assertions_sha256=str(
            pack["artifacts"]["name_assertions.jsonl"]["physical_sha256"]
        ),
    )
    common_request_parameters = {
        key: value
        for key, value in lane["physical_requests"][0]["normalized_parameters"].items()
        if key != "text"
    }
    if any(
        {
            key: value
            for key, value in request["normalized_parameters"].items()
            if key != "text"
        }
        != common_request_parameters
        for request in lane["physical_requests"]
    ):
        raise SnapshotFreezeError("Flickr plan has inconsistent fixed parameters")

    source_artifact_paths = (
        pack_path,
        taxa_path,
        names_path,
        ala_path,
        operations_path,
        monitoring_path,
        quality_path,
        review_media_path,
        rights_path,
        yoloe_path,
        bioclip_path,
        reference_bank_path,
        global_flickr_path,
        openai_requirements_path,
        openai_replay_path,
        worker_contract_path,
        privacy_path,
    )
    source_artifacts = [
        artifact_ref(source_commit, path) for path in source_artifact_paths
    ]
    blockers = [f"community_privacy:{item}" for item in privacy["launch_blockers"]]
    blockers.extend(
        f"ala_dataset_rights:{uid}"
        for uid in ala["rights"]["citation_restrictive_rights_review_required_uids"]
    )
    blockers.extend(
        (
            "yoloe:blocked_not_executed",
            "bioclip:skipped_unfinished_by_goal_instruction",
        )
    )

    document: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": "butterflylens-submitted-20260718-v1",
        "snapshot_mode": "submitted",
        "frozen_at": frozen_at,
        "immutable": True,
        "source": {
            "repository": REPOSITORY,
            "commit": source_commit,
            "git_tree_sha": str(git_output("rev-parse", f"{source_commit}^{{tree}}")),
        },
        "ala_baseline": {
            "authority": "ButterflyLens rebuilt baseline",
            "semantics": "ALA baseline occurrence evidence; not complete ground truth",
            "snapshot_id": ala["snapshot_id"],
            "snapshot_fingerprint": ala["snapshot_fingerprint"],
            "generated_at": ala["generated_at"],
            "manifest": artifact_ref(source_commit, ala_path),
            "source_archive": ala["artifacts"]["source_archive"],
            "counts": {
                "selected_occurrence_rows": ala["counts"]["selected_occurrence_rows"],
                "spatially_eligible_rows": ala["counts"]["spatially_eligible_rows"],
                "aggregate_cell_rows": ala["artifacts"]["aggregate_cells"]["row_count"],
                "aggregate_scope_rows": ala["counts"]["aggregate_scope_rows"],
                "dataset_resources": ala["counts"]["dataset_resources"],
            },
            "rights": {
                "release_state": ala["rights"]["downstream_public_product_release_state"],
                "review_required_dataset_uids": ala["rights"][
                    "citation_restrictive_rights_review_required_uids"
                ],
                "review_required_records": ala["counts"]["rights_review_required_records"],
            },
        },
        "flickr_query_plan": {
            "schema_version": lane["schema_version"],
            "lane_id": lane["lane_id"],
            "scope": lane["scope"],
            "execution_state": lane["execution_state"],
            "network_calls_made_by_freeze": 0,
            "lane_fingerprint": lane["lane_fingerprint"],
            "fixed_parameters": common_request_parameters,
            "counts": lane["counts"],
            "source_pack": lane["source_pack"],
            "planner_source": tree_ref(
                source_commit, "packages/contracts/python/butterflylens/flickr"
            ),
            "global_out_of_range_state": global_flickr["status"],
            "active_external_fetch_included": False,
            "active_external_fetch_reason": (
                "No complete immutable Flickr handoff is part of the source commit."
            ),
        },
        "pack": {
            "pack_id": pack["pack_id"],
            "version": "v1",
            "schema_version": pack["schema_version"],
            "generated_at": pack["generated_at"],
            "accepted_species": pack["artifacts"]["taxa.jsonl"]["rank_counts"]["species"],
            "manifest": artifact_ref(source_commit, pack_path),
            "git_tree": tree_ref(
                source_commit, "data/packs/australian_butterflies/v1"
            ),
        },
        "worker": {
            "state": monitoring["heartbeat"]["state"],
            "state_reason": monitoring["heartbeat"]["reason"],
            "version": {
                "semantic_version": None,
                "version_state": "git_tree_and_contract_only_no_separate_package_version",
                "identity_contract": WORKER_IDENTITY_SCHEMA_VERSION,
                "implementation": tree_ref(source_commit, "services/worker"),
                "contract": artifact_ref(source_commit, worker_contract_path),
            },
            "identity_fingerprint": None,
            "heartbeat_observed_at": None,
            "configured_models": [],
            "scientific_claim_allowed": False,
        },
        "models": {
            "yoloe": {
                "status": yoloe["status"],
                "model_id": None,
                "revision": yoloe["runtime"]["model_revision"],
                "weights_sha256": yoloe["runtime"]["checkpoint_sha256"],
                "execution_attempted": yoloe["runtime"]["execution_attempted"],
                "manifest": artifact_ref(source_commit, yoloe_path),
            },
            "bioclip": {
                "status": bioclip["status"],
                "model_id": bioclip["model_execution"]["model_id"],
                "revision": bioclip["model_execution"]["model_revision"],
                "weights_sha256": bioclip["model_execution"]["weights_sha256"],
                "runtime_loaded": bioclip["model_execution"]["runtime_loaded"],
                "manifest": artifact_ref(source_commit, bioclip_path),
            },
            "openai_analyst": {
                "configured_model_id": openai_requirements["model"]["explicit_id"],
                "family_alias": openai_requirements["model"]["family_alias"],
                "submitted_mode": openai_replay["mode"],
                "model_invoked": openai_replay["source"]["model_invoked"],
                "network_calls": openai_replay["source"]["network_calls"],
                "live_model_state": openai_requirements["evaluation_policy"][
                    "current_suite"
                ]["live_model_state"],
                "requirements": artifact_ref(source_commit, openai_requirements_path),
                "replay": artifact_ref(source_commit, openai_replay_path),
            },
        },
        "review_state": {
            "state": "local_draft_only_no_stored_review",
            "fixture_available": operations["review"]["available"],
            "fixture_item_id": operations["review"]["itemId"],
            "fixture_media_sha256": operations["review"]["mediaSha256"],
            "fixture_rights": review_media["rights"],
            "stored_review_events": 0,
            "completed_consensus_records": 0,
            "representative_reviewed_sample": quality["reviewedSample"],
            "decisive_reviews": quality["decisiveReviews"],
            "human_verified_media": reference_bank["counts"]["human_verified_media"],
            "community_writes_enabled": privacy["community_write_access"],
            "scientific_claim_allowed": False,
            "media_manifest": artifact_ref(source_commit, review_media_path),
        },
        "map_counts": {
            "snapshot_id": operations["map"]["snapshotId"],
            "snapshot_fingerprint": operations["map"]["artifactFingerprint"],
            "render_state": operations["map"]["renderState"],
            "release_state": operations["map"]["releaseState"],
            "authoritative_internal": {
                "accepted_species": pack["artifacts"]["taxa.jsonl"]["rank_counts"][
                    "species"
                ],
                "ala_selected_occurrence_rows": ala["counts"][
                    "selected_occurrence_rows"
                ],
                "ala_spatially_eligible_rows": ala["counts"][
                    "spatially_eligible_rows"
                ],
                "ala_aggregate_cell_rows": ala["artifacts"]["aggregate_cells"][
                    "row_count"
                ],
                "ala_scope_rows": ala["counts"]["aggregate_scope_rows"],
            },
            "public_projection": {
                "occurrence_layer_visible": operations["map"][
                    "occurrenceLayerVisible"
                ],
                "displayed_occurrence_count": None,
                "displayed_cell_count": None,
                "admitted_flickr_candidate_count": None,
                "unavailable_is_zero": False,
                "reason": operations["map"]["reason"],
            },
            "absence_inference_permitted": operations["map"][
                "absenceInferencePermitted"
            ],
        },
        "source_shas": {
            "hash_algorithms": {
                "physical": "sha256",
                "git_objects": "repository_object_format_sha1",
            },
            "artifacts": source_artifacts,
            "upstream": {
                "biominer_reference_origin_commit": reference_bank["origin"]["commit"],
                "taxalens_review_media_origin_commit": review_media["origin"]["commit"],
            },
        },
        "release": {
            "static_submitted_replay": "verified",
            "community_live_and_data_release": "blocked",
            "release_ready": False,
            "blockers": sorted(blockers),
        },
        "excluded_active_work": [
            "BioMiner incomplete ButterflyLens GBIF/Flickr/model handoff",
            "external active Flickr fetch and all partial results",
            "YOLOE routes weights and detections",
            "BioCLIP weights embeddings prototypes and scores",
            "live worker identity heartbeat and resource metrics",
            "stored community reviews consensus and release candidates",
        ],
    }
    document["snapshot_fingerprint"] = "sha256:" + hashlib.sha256(
        canonicalize_json(document)
    ).hexdigest()
    validate_snapshot_fingerprint(document)
    return document


def validate_snapshot_fingerprint(document: dict[str, Any]) -> None:
    fingerprint = document.get("snapshot_fingerprint")
    if not isinstance(fingerprint, str) or not fingerprint.startswith("sha256:"):
        raise SnapshotFreezeError("snapshot fingerprint is missing")
    preimage = {key: value for key, value in document.items() if key != "snapshot_fingerprint"}
    expected = "sha256:" + hashlib.sha256(canonicalize_json(preimage)).hexdigest()
    if fingerprint != expected:
        raise SnapshotFreezeError("snapshot fingerprint mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=SNAPSHOT_PATH)
    parser.add_argument("--source-commit")
    parser.add_argument("--frozen-at")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.check:
        checked = json.loads(output.read_text(encoding="utf-8"))
        validate_snapshot_fingerprint(checked)
        rebuilt = build_submitted_snapshot(
            source_commit=str(checked["source"]["commit"]),
            frozen_at=str(checked["frozen_at"]),
        )
        if checked != rebuilt:
            raise SnapshotFreezeError("checked-in submitted snapshot is not reproducible")
        print(
            "submitted snapshot verification: PASS "
            f"(snapshot_id={checked['snapshot_id']}, "
            f"fingerprint={checked['snapshot_fingerprint']})"
        )
        return
    if args.source_commit is None or args.frozen_at is None:
        raise SnapshotFreezeError("generation requires --source-commit and --frozen-at")
    document = build_submitted_snapshot(
        source_commit=args.source_commit,
        frozen_at=args.frozen_at,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    try:
        display_path: Path | str = output.relative_to(ROOT)
    except ValueError:
        display_path = output
    print(
        "submitted snapshot generated: "
        f"{display_path} ({document['snapshot_fingerprint']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (
        KeyError,
        OSError,
        SnapshotFreezeError,
        subprocess.SubprocessError,
        TypeError,
        ValueError,
    ) as error:
        raise SystemExit(f"submitted snapshot: FAIL: {error}") from error
