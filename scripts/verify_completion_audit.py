#!/usr/bin/env python3
"""Verify the fixed ButterflyLens completion boundary and fail closed."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "provenance" / "completion_audit.v1.json"
EXPECTED_COMMIT = "7a2c2eba61cd10034096e006cdb04fd5018a2b10"
EXPECTED_TREE = "fc29c3de542b63cb3905ab4059e16a2d81548138"
EXPECTED_GOAL_SHA256 = (
    "898dbe5ec3520d1425bf5d0f891c49d6f7615318ed28b35b16f7513684a3fa40"
)
EXPECTED_SESSION_ID = "019f7038-92ae-7021-8318-53ca97648404"

CRITERIA = (
    "ButterflyLens is a new public repository.",
    "All work is committed directly to main.",
    "Every subtask has its own commit.",
    "Main is pushed after every task.",
    "No force push occurs.",
    "Every imported component has source repository and SHA.",
    "Build Week baseline and delta are clear.",
    "Primary GPT-5.6 Codex Session ID is recorded.",
    "Every taxon has a stable identity.",
    "Every name assertion has provenance and trust.",
    "First Nations names are never invented or generalized.",
    "Every Flickr request is fingerprinted.",
    "Logical and physical queries remain separate.",
    "Every source photo has immutable source identity.",
    "Every downloaded image has SHA-256.",
    "Duplicate groups are preserved.",
    "Every model artifact is fingerprinted.",
    "Every review event is append-only.",
    "Every map cell links to evidence.",
    "No candidate is silently promoted to an occurrence.",
    "One token bucket covers all Flickr methods.",
    "Hard usage never exceeds 3,500 calls/hour.",
    "Normal planned usage does not exceed 3,000.",
    "Reserve is tracked.",
    "Geo pages use the provider limit.",
    "Queries reaching the search-result ceiling are partitioned.",
    "Search terms are not treated as labels.",
    "Australia-known species run first.",
    "Global out-of-range species use a separate hypothesis lane.",
    "Public pages display no more than 30 Flickr images.",
    "Attribution and required notice are visible.",
    "BioCLIP runs locally from Hugging Face weights by default.",
    "Flickr images are not uploaded to Hugging Face by default.",
    "YOLOE is a router, not a species classifier.",
    "BioCLIP loads once per worker.",
    "Embeddings are reused.",
    "Candidate unions preserve query, geography and visual reasons.",
    "Higher-rank scores do not catastrophically prune species.",
    "Raw similarities are not displayed as probabilities.",
    "Evidence maturity is visible.",
    "Multiple independent reviewers can receive the same image.",
    "Reviews are blinded where required.",
    "Review events bind user, image, question and version.",
    "Skip is not decisive.",
    "Can't view is not decisive.",
    "Conflicts are preserved.",
    "Expert adjudication exists.",
    "Guests cannot release scientific records.",
    "Contributor celebration does not reward speed.",
    "Reviewer reliability is private and domain-specific.",
    "Reviewer reliability never uses model agreement as truth.",
    "Reliability weighting begins only after sufficient evidence.",
    "Representative audit and failure discovery are separate.",
    "Sampling probabilities are retained.",
    "Confidence intervals identify their method.",
    "Effective sample size is reported.",
    "Reviewer agreement is calculated only when valid.",
    "Species-level quality is visible.",
    "Release requires configured quality gates.",
    'No "more votes guarantee accuracy" claim exists.',
    "ALA is the blue baseline.",
    "Flickr is amber.",
    "National view uses a heat map.",
    "Lower scopes support bubbles and records.",
    "State drilldown works.",
    "IBRA drilldown works.",
    "LGA drilldown works.",
    "H3 drilldown works.",
    "Candidate, reviewed and release-ready states differ.",
    "Potential contribution is not called a new occurrence.",
    "Submitted and live snapshots are distinct.",
    "The map continues working when the M5 is offline.",
    "GPT-5.6 is a meaningful runtime component.",
    "GPT-5.6 uses deterministic evidence tools.",
    "GPT-5.6 cites artifacts.",
    "GPT-5.6 does not identify species from memory.",
    "GPT-5.6 cannot fabricate map counts.",
    "GPT-5.6 can explain community impact.",
    "GPT-5.6 can recommend the next review batch.",
    "Stored judge replay works without credentials.",
    "Agent evaluations pass.",
    "M5 worker has a heartbeat.",
    "Worker restarts automatically.",
    "Pipeline resumes after interruption.",
    "No committed API request is repeated.",
    "No committed image is redownloaded unnecessarily.",
    "No unchanged embedding is recomputed.",
    "The public site is not hosted from the M5.",
    "Submitted snapshot remains immutable.",
    "Live updates are append-only and timestamped.",
    "README clearly explains Codex and GPT-5.6.",
    "Public demo requires no private credentials.",
    "Video is under three minutes.",
    "Video shows the real product.",
    "Judges can review an image.",
    "Judges can explore the map.",
    "Judges can inspect the live worker.",
    "Judges can use GPT-5.6 replay.",
    "All displayed metrics come from artifacts.",
    "ButterflyLens is demonstrably distinct from BioMiner and TaxaLens.",
)

STATUS_IDS = {
    "satisfied": frozenset(
        {
            *range(1, 12),
            13,
            16,
            18,
            20,
            *range(21, 32),
            33,
            34,
            39,
            40,
            *range(41, 61),
            70,
            71,
            *range(74, 81),
            84,
            85,
            86,
            88,
            89,
            91,
            92,
            95,
            98,
            99,
            100,
        }
    ),
    "partial": frozenset({12, 14, 15, 69, 72, 81, 82, 83, 90}),
    "blocked_by_user_instruction": frozenset({17, 32, 35, 36, 37, 38, 87}),
    "blocked_external": frozenset(
        {19, *range(61, 69), 73, 93, 94, 96, 97}
    ),
}

ARTIFACTS = (
    ("taxonomy", "australian_butterfly_taxa.parquet"),
    ("taxonomy", "taxon_crosswalk.parquet"),
    ("taxonomy", "name_assertions.parquet"),
    ("taxonomy", "First Nations name-review manifest"),
    ("taxonomy", "pack_manifest.json"),
    ("ala", "ala_baseline_occurrences.parquet"),
    ("ala", "ala_baseline_cells.parquet"),
    ("ala", "ala_dataset_manifest.parquet"),
    ("ala", "ala_attribution.json"),
    ("ala", "ala_snapshot_manifest.json"),
    ("flickr", "flickr_query_definitions.parquet"),
    ("flickr", "flickr_physical_requests.parquet"),
    ("flickr", "flickr_query_associations.parquet"),
    ("flickr", "flickr_api_ledger.parquet"),
    ("flickr", "flickr_photos.parquet"),
    ("flickr", "flickr_geography.parquet"),
    ("flickr", "flickr_comments.parquet"),
    ("media_and_models", "media_objects.parquet"),
    ("media_and_models", "duplicate_groups.parquet"),
    ("media_and_models", "yoloe_routes.parquet"),
    ("media_and_models", "full_frame_inputs.parquet"),
    ("media_and_models", "bioclip_embeddings.parquet"),
    ("media_and_models", "species_prototypes.parquet"),
    ("media_and_models", "candidate_scores.parquet"),
    ("media_and_models", "reference_quality_diagnostics.parquet"),
    ("verification", "verification_campaigns.parquet"),
    ("verification", "verification_assignments.parquet"),
    ("verification", "review_events.parquet"),
    ("verification", "review_consensus.parquet"),
    ("verification", "reviewer_reliability.parquet"),
    ("verification", "quality_snapshots.parquet"),
    ("map", "geographic_impact_cells.parquet"),
    ("map", "geographic_impact_summary.parquet"),
    ("map", "map_manifest.json"),
    ("release", "release_candidates.parquet"),
    ("release", "evidence_packets/"),
    ("release", "Darwin Core export"),
    ("release", "release_manifest.json"),
    ("operations", "worker_heartbeats.parquet or database view"),
    ("operations", "stage_metrics.parquet"),
    ("operations", "live_status.json"),
    ("operations", "submitted_snapshot.json"),
    ("openai", "tool_contracts.json"),
    ("openai", "stored_analyst_replay.json"),
    ("openai", "agent_evaluation.json"),
    ("openai", "model_usage.jsonl"),
)

ARTIFACT_STATUS_NAMES = {
    "present": frozenset(
        {
            "First Nations name-review manifest",
            "ala_baseline_occurrences.parquet",
            "ala_baseline_cells.parquet",
            "ala_dataset_manifest.parquet",
            "ala_attribution.json",
            "ala_snapshot_manifest.json",
            "reference_quality_diagnostics.parquet",
            "submitted_snapshot.json",
            "tool_contracts.json",
            "agent_evaluation.json",
            "model_usage.jsonl",
        }
    ),
    "present_equivalent": frozenset(
        {
            "australian_butterfly_taxa.parquet",
            "taxon_crosswalk.parquet",
            "name_assertions.parquet",
            "pack_manifest.json",
            "media_objects.parquet",
            "duplicate_groups.parquet",
            "stored_analyst_replay.json",
        }
    ),
    "blocked_by_user_instruction": frozenset(
        {
            "yoloe_routes.parquet",
            "full_frame_inputs.parquet",
            "bioclip_embeddings.parquet",
            "species_prototypes.parquet",
            "candidate_scores.parquet",
        }
    ),
}
ARTIFACT_STATUS_NAMES["blocked_external"] = frozenset(
    name
    for _, name in ARTIFACTS
    if not any(name in names for names in ARTIFACT_STATUS_NAMES.values())
)


class CompletionAuditError(RuntimeError):
    """Raised when the fixed completion audit is incomplete or inconsistent."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise CompletionAuditError(message)


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_object(value: Any, label: str) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object")
    return value


def _require_exact_keys(
    value: dict[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    _require(actual == expected, f"{label} keys differ: {sorted(actual ^ expected)}")


def _validate_evidence_paths(
    evidence: Any, *, label: str, tracked_at_boundary: set[str]
) -> None:
    _require(isinstance(evidence, list) and evidence, f"{label} needs evidence")
    _require(
        len(evidence) == len(set(evidence)),
        f"{label} has duplicate evidence paths",
    )
    for path in evidence:
        _require(isinstance(path, str) and path, f"{label} has invalid evidence path")
        parsed = PurePosixPath(path)
        _require(
            not parsed.is_absolute() and ".." not in parsed.parts,
            f"{label} has unsafe evidence path: {path}",
        )
        _require(
            path in tracked_at_boundary,
            f"{label} evidence is absent at audited commit: {path}",
        )


def verify_payload(payload: Any) -> dict[str, Any]:
    """Validate one parsed completion audit against the fixed evidence boundary."""

    audit = _require_object(payload, "audit")
    _require_exact_keys(
        audit,
        {
            "schema_version",
            "audit_id",
            "generated_at",
            "repository",
            "branch",
            "audited_commit",
            "audited_tree",
            "source_goal_sha256",
            "primary_session_id",
            "requested_model",
            "requested_reasoning_effort",
            "goal_complete",
            "completion_rule",
            "status_definitions",
            "criteria_summary",
            "artifact_summary",
            "authoritative_boundaries",
            "criteria",
            "minimum_artifacts",
        },
        "audit",
    )
    exact_scalars = {
        "schema_version": "butterflylens-completion-audit/v1.0.0",
        "audit_id": "butterflylens-18.2.1",
        "generated_at": "2026-07-18T16:33:29Z",
        "repository": "karikris/ButterflyLens",
        "branch": "main",
        "audited_commit": EXPECTED_COMMIT,
        "audited_tree": EXPECTED_TREE,
        "source_goal_sha256": EXPECTED_GOAL_SHA256,
        "primary_session_id": EXPECTED_SESSION_ID,
        "requested_model": "gpt-5.6-sol",
        "requested_reasoning_effort": "xhigh",
        "completion_rule": (
            "goal_complete may be true only when all 100 criteria are satisfied "
            "and every minimum artifact is present or an explicitly accepted "
            "equivalent"
        ),
    }
    for field, expected in exact_scalars.items():
        _require(audit[field] == expected, f"{field} differs from fixed boundary")

    _require(
        _git("show", "-s", "--format=%T", EXPECTED_COMMIT) == EXPECTED_TREE,
        "audited commit does not resolve to audited tree",
    )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_COMMIT, "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    tracked_at_boundary = set(
        _git("ls-tree", "-r", "--name-only", EXPECTED_COMMIT).splitlines()
    )

    statuses = _require_object(audit["status_definitions"], "status_definitions")
    _require(
        set(statuses) == set(STATUS_IDS),
        "criterion status definitions differ",
    )
    _require(
        all(isinstance(value, str) and value for value in statuses.values()),
        "criterion status definitions must be non-empty",
    )

    criteria = audit["criteria"]
    _require(isinstance(criteria, list), "criteria must be an array")
    _require(len(criteria) == 100, "criteria must contain exactly 100 rows")
    observed_statuses: Counter[str] = Counter()
    for expected_id, expected_text in enumerate(CRITERIA, start=1):
        row = _require_object(criteria[expected_id - 1], f"criterion {expected_id}")
        _require_exact_keys(
            row,
            {"id", "category", "criterion", "status", "evidence", "rationale", "next_action"},
            f"criterion {expected_id}",
        )
        _require(row["id"] == expected_id, f"criterion ID {expected_id} is missing")
        _require(
            row["criterion"] == expected_text,
            f"criterion {expected_id} text differs",
        )
        expected_status = next(
            status for status, ids in STATUS_IDS.items() if expected_id in ids
        )
        _require(
            row["status"] == expected_status,
            f"criterion {expected_id} status differs from fixed audit",
        )
        observed_statuses[row["status"]] += 1
        _require(
            isinstance(row["category"], str) and row["category"],
            f"criterion {expected_id} needs a category",
        )
        _require(
            isinstance(row["rationale"], str) and row["rationale"],
            f"criterion {expected_id} needs a rationale",
        )
        if row["status"] == "satisfied":
            _require(
                row["next_action"] is None,
                f"satisfied criterion {expected_id} cannot have a next action",
            )
        else:
            _require(
                isinstance(row["next_action"], str) and row["next_action"],
                f"criterion {expected_id} needs a next action",
            )
        _validate_evidence_paths(
            row["evidence"],
            label=f"criterion {expected_id}",
            tracked_at_boundary=tracked_at_boundary,
        )

    expected_criterion_summary = {
        "total": 100,
        **{status: len(ids) for status, ids in STATUS_IDS.items()},
    }
    _require(
        audit["criteria_summary"] == expected_criterion_summary,
        "criteria summary differs from fixed audit",
    )
    _require(
        dict(observed_statuses)
        == {status: len(ids) for status, ids in STATUS_IDS.items()},
        "criterion status counts drifted",
    )

    artifacts = audit["minimum_artifacts"]
    _require(isinstance(artifacts, list), "minimum_artifacts must be an array")
    _require(len(artifacts) == 46, "minimum_artifacts must contain exactly 46 rows")
    observed_artifact_statuses: Counter[str] = Counter()
    for index, (expected_category, expected_name) in enumerate(ARTIFACTS):
        row = _require_object(artifacts[index], f"artifact {expected_name}")
        _require_exact_keys(
            row,
            {"category", "required", "status", "evidence", "note"},
            f"artifact {expected_name}",
        )
        _require(
            (row["category"], row["required"]) == (expected_category, expected_name),
            f"minimum artifact {index + 1} differs",
        )
        expected_status = next(
            status
            for status, names in ARTIFACT_STATUS_NAMES.items()
            if expected_name in names
        )
        _require(
            row["status"] == expected_status,
            f"artifact {expected_name} status differs from fixed audit",
        )
        observed_artifact_statuses[row["status"]] += 1
        _require(
            isinstance(row["note"], str) and row["note"],
            f"artifact {expected_name} needs a note",
        )
        _validate_evidence_paths(
            row["evidence"],
            label=f"artifact {expected_name}",
            tracked_at_boundary=tracked_at_boundary,
        )

    expected_artifact_summary = {
        "total": 46,
        **{
            status: len(names)
            for status, names in ARTIFACT_STATUS_NAMES.items()
        },
    }
    _require(
        audit["artifact_summary"] == expected_artifact_summary,
        "artifact summary differs from fixed audit",
    )
    _require(
        dict(observed_artifact_statuses)
        == {
            status: len(names)
            for status, names in ARTIFACT_STATUS_NAMES.items()
        },
        "artifact status counts drifted",
    )

    all_criteria_satisfied = observed_statuses == Counter({"satisfied": 100})
    all_artifacts_available = set(observed_artifact_statuses) <= {
        "present",
        "present_equivalent",
    }
    derived_goal_complete = all_criteria_satisfied and all_artifacts_available
    _require(
        audit["goal_complete"] is derived_goal_complete,
        "goal_complete differs from the deterministic completion rule",
    )
    _require(
        audit["goal_complete"] is False,
        "fixed boundary cannot be represented as complete",
    )

    boundaries = _require_object(
        audit["authoritative_boundaries"], "authoritative_boundaries"
    )
    _require_exact_keys(
        boundaries, {"ala", "gbif", "biominer", "flickr", "models"},
        "authoritative_boundaries",
    )
    required_boundary_terms = {
        "ala": "authoritative",
        "gbif": "complementary",
        "biominer": "still fetching Flickr metadata",
        "flickr": "No Flickr API call",
        "models": "unfinished_not_run",
    }
    for name, term in required_boundary_terms.items():
        _require(
            term in boundaries[name],
            f"{name} authoritative boundary omits {term!r}",
        )

    return {
        "audit_id": audit["audit_id"],
        "audited_commit": audit["audited_commit"],
        "audited_tree": audit["audited_tree"],
        "criteria": expected_criterion_summary,
        "minimum_artifacts": expected_artifact_summary,
        "goal_complete": False,
    }


def verify(path: Path = AUDIT_PATH) -> dict[str, Any]:
    """Read and validate a completion audit file."""

    return verify_payload(json.loads(path.read_text(encoding="utf-8")))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=AUDIT_PATH,
        help="completion audit JSON (default: tracked audit)",
    )
    arguments = parser.parse_args()
    try:
        result = verify(arguments.path)
    except (
        CompletionAuditError,
        json.JSONDecodeError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"completion audit verification failed: {exc}")
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
