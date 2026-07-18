#!/usr/bin/env python3
"""Verify the current immutable ButterflyLens completion boundary."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_completion_audit import (
    ARTIFACTS,
    ARTIFACT_STATUS_NAMES,
    AUDIT_PATH as HISTORICAL_AUDIT_PATH,
    CRITERIA,
    EXPECTED_GOAL_SHA256,
    EXPECTED_SESSION_ID,
    STATUS_IDS,
    CompletionAuditError,
    _git,
    _require,
    _require_exact_keys,
    _require_object,
    _validate_evidence_paths,
)


AUDIT_PATH = ROOT / "provenance" / "completion_audit.v2.json"
SCHEMA_PATH = ROOT / "provenance" / "completion-audit.schema.json"
EXPECTED_COMMIT = "45fb5ac07dcd51852c9e92217667f3f5052868fe"
EXPECTED_TREE = "aa93a6abf058d15c0ef80c7bde241a3355cfe024"
EXPECTED_AUDIT_ID = "butterflylens-18.5.1"
EXPECTED_GENERATED_AT = "2026-07-18T18:24:16Z"
UPGRADED_CRITERION_IDS = frozenset({19, 61, 63, 64, 65, 66, 67, 68, 72, 96})
UPGRADED_ARTIFACTS = frozenset(
    {
        "geographic_impact_cells.parquet",
        "geographic_impact_summary.parquet",
        "map_manifest.json",
    }
)


CRITERION_UPGRADES: dict[int, dict[str, Any]] = {
    19: {
        "status": "satisfied",
        "evidence": [
            "data/packs/australian_butterflies/v1/map/geographic_impact_cells.parquet",
            "data/packs/australian_butterflies/v1/map/map_manifest.json",
            "tests/test_public_ala_map.py",
        ],
        "rationale": (
            "All 630 submitted ALA H3 cells carry one or more exact evidence "
            "fingerprints, validate against the geographic-impact contract, and "
            "retain a cell fingerprint."
        ),
        "next_action": None,
    },
    61: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/submittedEvidenceMap.css",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
        ],
        "rationale": (
            "The rights-screened Submitted map renders ALA baseline evidence as "
            "blue filled H3 cells with an exact accessible table."
        ),
        "next_action": None,
    },
    63: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
        ],
        "rationale": (
            "The national Submitted view renders all 630 coarse H3 cells as an "
            "offline aggregate heatmap backed by 213,310 map-eligible ALA rows."
        ),
        "next_action": None,
    },
    64: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
        ],
        "rationale": (
            "Lower scopes expose proportional bubbles, exact tables, selected "
            "scope details, and coordinate-free provider-record samples."
        ),
        "next_action": None,
    },
    65: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
        ],
        "rationale": (
            "The public map provides nine exact state and territory rows with "
            "filtering, selection, counts, and synchronized details."
        ),
        "next_action": None,
    },
    66: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
        ],
        "rationale": (
            "The public map provides 87 exact IBRA v7 rows with filtering, "
            "selection, counts, and synchronized details."
        ),
        "next_action": None,
    },
    67: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
        ],
        "rationale": (
            "The public map provides 532 exact LGA 2023 statistical-approximation "
            "rows with filtering, selection, counts, and a visible qualification."
        ),
        "next_action": None,
    },
    68: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/src/map/SubmittedEvidenceMap.test.tsx",
            "apps/web/src/map/submittedMapSnapshot.json",
        ],
        "rationale": (
            "The public map provides 630 exact coarse H3 rows synchronized with "
            "the selectable map and selected-cell evidence card."
        ),
        "next_action": None,
    },
    72: {
        "status": "satisfied",
        "evidence": [
            "apps/web/src/App.tsx",
            "apps/web/src/communityJourney.e2e.test.tsx",
            "apps/web/e2e/public-experience.browser.spec.ts",
        ],
        "rationale": (
            "The committed map is bundled with the static site and passes the "
            "credential-free journey and seven worker-independent browser variants."
        ),
        "next_action": None,
    },
    96: {
        "status": "satisfied",
        "evidence": [
            "JUDGE_GUIDE.md",
            "apps/web/src/map/SubmittedEvidenceMap.tsx",
            "apps/web/e2e/public-experience.browser.spec.ts",
        ],
        "rationale": (
            "The public judge route opens the submitted national heatmap, exact "
            "lower-scope drilldowns, and selected-cell evidence without credentials."
        ),
        "next_action": None,
    },
}


ARTIFACT_UPGRADES: dict[str, dict[str, Any]] = {
    "geographic_impact_cells.parquet": {
        "status": "present",
        "evidence": [
            "data/packs/australian_butterflies/v1/map/geographic_impact_cells.parquet",
            "data/packs/australian_butterflies/v1/map/map_manifest.json",
            "tests/test_public_ala_map.py",
        ],
        "note": (
            "The named artifact contains 630 contract-valid rights-screened ALA "
            "H3 cells with exact evidence fingerprints."
        ),
    },
    "geographic_impact_summary.parquet": {
        "status": "present",
        "evidence": [
            "data/packs/australian_butterflies/v1/map/geographic_impact_summary.parquet",
            "data/packs/australian_butterflies/v1/map/map_manifest.json",
            "tests/test_public_ala_map.py",
        ],
        "note": (
            "The named artifact contains 23,484 exact Australia, state/territory, "
            "IBRA, LGA-approximation, and H3 aggregate rows."
        ),
    },
    "map_manifest.json": {
        "status": "present",
        "evidence": [
            "data/packs/australian_butterflies/v1/map/map_manifest.json",
            "apps/web/src/map/submittedMapSnapshot.json",
            "tests/test_public_ala_map.py",
        ],
        "note": (
            "The named manifest fingerprints the two Parquets and browser snapshot "
            "while preserving the authoritative baseline and rights exclusions."
        ),
    },
}


def _current_status_ids() -> dict[str, frozenset[int]]:
    result = {name: set(ids) for name, ids in STATUS_IDS.items()}
    for criterion_id in UPGRADED_CRITERION_IDS:
        for ids in result.values():
            ids.discard(criterion_id)
        result["satisfied"].add(criterion_id)
    return {name: frozenset(ids) for name, ids in result.items()}


def _current_artifact_status_names() -> dict[str, frozenset[str]]:
    result = {name: set(values) for name, values in ARTIFACT_STATUS_NAMES.items()}
    for artifact_name in UPGRADED_ARTIFACTS:
        for names in result.values():
            names.discard(artifact_name)
        result["present"].add(artifact_name)
    return {name: frozenset(values) for name, values in result.items()}


CURRENT_STATUS_IDS = _current_status_ids()
CURRENT_ARTIFACT_STATUS_NAMES = _current_artifact_status_names()


def verify_payload(payload: Any) -> dict[str, Any]:
    """Validate the second audit against its exact immutable Git boundary."""

    audit = _require_object(payload, "current audit")
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
        "current audit",
    )
    expected_scalars = {
        "schema_version": "butterflylens-completion-audit/v1.0.0",
        "audit_id": EXPECTED_AUDIT_ID,
        "generated_at": EXPECTED_GENERATED_AT,
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
    for field, expected in expected_scalars.items():
        _require(audit[field] == expected, f"{field} differs from current boundary")

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(audit),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    _require(not errors, f"current audit schema failed: {errors[0].message if errors else ''}")

    _require(
        _git("show", "-s", "--format=%T", EXPECTED_COMMIT) == EXPECTED_TREE,
        "current audited commit does not resolve to audited tree",
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

    historical = json.loads(HISTORICAL_AUDIT_PATH.read_text(encoding="utf-8"))
    criteria = audit["criteria"]
    _require(isinstance(criteria, list) and len(criteria) == 100, "current criteria must contain exactly 100 rows")
    observed_statuses: Counter[str] = Counter()
    for expected_id, expected_text in enumerate(CRITERIA, start=1):
        row = _require_object(criteria[expected_id - 1], f"current criterion {expected_id}")
        _require_exact_keys(
            row,
            {"id", "category", "criterion", "status", "evidence", "rationale", "next_action"},
            f"current criterion {expected_id}",
        )
        _require(row["id"] == expected_id, f"current criterion ID {expected_id} is missing")
        _require(row["criterion"] == expected_text, f"current criterion {expected_id} text differs")
        expected_status = next(
            status for status, ids in CURRENT_STATUS_IDS.items() if expected_id in ids
        )
        _require(row["status"] == expected_status, f"current criterion {expected_id} status differs")
        _validate_evidence_paths(
            row["evidence"],
            label=f"current criterion {expected_id}",
            tracked_at_boundary=tracked_at_boundary,
        )
        if expected_id in UPGRADED_CRITERION_IDS:
            _require(row == {**historical["criteria"][expected_id - 1], **CRITERION_UPGRADES[expected_id]}, f"current criterion {expected_id} upgrade differs")
        else:
            _require(row == historical["criteria"][expected_id - 1], f"current criterion {expected_id} changed without evidence transition")
        observed_statuses[row["status"]] += 1

    expected_criterion_summary = {
        "total": 100,
        **{status: len(ids) for status, ids in CURRENT_STATUS_IDS.items()},
    }
    _require(audit["criteria_summary"] == expected_criterion_summary, "current criteria summary differs")
    _require(dict(observed_statuses) == {status: len(ids) for status, ids in CURRENT_STATUS_IDS.items()}, "current criterion status counts drifted")

    artifacts = audit["minimum_artifacts"]
    _require(isinstance(artifacts, list) and len(artifacts) == 46, "current minimum artifacts must contain exactly 46 rows")
    observed_artifact_statuses: Counter[str] = Counter()
    for index, (expected_category, expected_name) in enumerate(ARTIFACTS):
        row = _require_object(artifacts[index], f"current artifact {expected_name}")
        _require_exact_keys(row, {"category", "required", "status", "evidence", "note"}, f"current artifact {expected_name}")
        _require((row["category"], row["required"]) == (expected_category, expected_name), f"current artifact {index + 1} differs")
        expected_status = next(
            status
            for status, names in CURRENT_ARTIFACT_STATUS_NAMES.items()
            if expected_name in names
        )
        _require(row["status"] == expected_status, f"current artifact {expected_name} status differs")
        _validate_evidence_paths(
            row["evidence"],
            label=f"current artifact {expected_name}",
            tracked_at_boundary=tracked_at_boundary,
        )
        if expected_name in UPGRADED_ARTIFACTS:
            _require(row == {**historical["minimum_artifacts"][index], **ARTIFACT_UPGRADES[expected_name]}, f"current artifact {expected_name} upgrade differs")
        else:
            _require(row == historical["minimum_artifacts"][index], f"current artifact {expected_name} changed without evidence transition")
        observed_artifact_statuses[row["status"]] += 1

    expected_artifact_summary = {
        "total": 46,
        **{
            status: len(names)
            for status, names in CURRENT_ARTIFACT_STATUS_NAMES.items()
        },
    }
    _require(audit["artifact_summary"] == expected_artifact_summary, "current artifact summary differs")
    _require(dict(observed_artifact_statuses) == {status: len(names) for status, names in CURRENT_ARTIFACT_STATUS_NAMES.items()}, "current artifact status counts drifted")

    derived_complete = all(row["status"] == "satisfied" for row in criteria) and all(
        row["status"] in {"present", "present_equivalent"} for row in artifacts
    )
    _require(audit["goal_complete"] is derived_complete, "current goal_complete differs from the deterministic completion rule")
    _require(audit["goal_complete"] is False, "current audit must retain the unfinished goal boundary")
    return {
        "audit_id": audit["audit_id"],
        "audited_commit": audit["audited_commit"],
        "audited_tree": audit["audited_tree"],
        "criteria": audit["criteria_summary"],
        "minimum_artifacts": audit["artifact_summary"],
        "goal_complete": audit["goal_complete"],
    }


def verify(path: Path = AUDIT_PATH) -> dict[str, Any]:
    return verify_payload(json.loads(path.read_text(encoding="utf-8")))


def main() -> None:
    print(json.dumps(verify(), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (CompletionAuditError, OSError, KeyError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit(f"current completion audit verification: FAIL: {error}") from error
