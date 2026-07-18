#!/usr/bin/env python3
"""Build the second immutable ButterflyLens completion audit."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.verify_completion_audit import AUDIT_PATH as HISTORICAL_AUDIT_PATH
from scripts.verify_current_completion_audit import (
    ARTIFACT_UPGRADES,
    AUDIT_PATH,
    CRITERION_UPGRADES,
    EXPECTED_AUDIT_ID,
    EXPECTED_COMMIT,
    EXPECTED_GENERATED_AT,
    EXPECTED_TREE,
    verify_payload,
)


def build() -> dict[str, Any]:
    observed_tree = subprocess.run(
        ["git", "show", "-s", "--format=%T", EXPECTED_COMMIT],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if observed_tree != EXPECTED_TREE:
        raise ValueError("current audit commit no longer resolves to the fixed tree")

    audit = deepcopy(json.loads(HISTORICAL_AUDIT_PATH.read_text(encoding="utf-8")))
    audit.update(
        {
            "audit_id": EXPECTED_AUDIT_ID,
            "generated_at": EXPECTED_GENERATED_AT,
            "audited_commit": EXPECTED_COMMIT,
            "audited_tree": EXPECTED_TREE,
        }
    )
    audit["authoritative_boundaries"] = {
        "ala": (
            "The rebuilt ButterflyLens ALA baseline remains authoritative; the "
            "public map is a separate conservative rights-screened aggregate."
        ),
        "gbif": (
            "The fingerprinted GBIF Parquet pack is complementary and is not "
            "silently merged into or substituted for the ALA baseline."
        ),
        "biominer": (
            "BioMiner is still fetching Flickr metadata; no partial output was "
            "inspected or copied."
        ),
        "flickr": "No Flickr API call was made by this goal.",
        "models": (
            "YOLOE and BioCLIP remain unfinished_not_run by explicit user direction."
        ),
    }

    for criterion in audit["criteria"]:
        override = CRITERION_UPGRADES.get(criterion["id"])
        if override is not None:
            criterion.update(deepcopy(override))
    for artifact in audit["minimum_artifacts"]:
        override = ARTIFACT_UPGRADES.get(artifact["required"])
        if override is not None:
            artifact.update(deepcopy(override))

    criterion_counts = Counter(row["status"] for row in audit["criteria"])
    audit["criteria_summary"] = {
        "total": len(audit["criteria"]),
        **{
            status: criterion_counts[status]
            for status in (
                "satisfied",
                "partial",
                "blocked_by_user_instruction",
                "blocked_external",
            )
        },
    }
    artifact_counts = Counter(row["status"] for row in audit["minimum_artifacts"])
    audit["artifact_summary"] = {
        "total": len(audit["minimum_artifacts"]),
        **{
            status: artifact_counts[status]
            for status in (
                "present",
                "present_equivalent",
                "blocked_by_user_instruction",
                "blocked_external",
            )
        },
    }
    audit["goal_complete"] = all(
        row["status"] == "satisfied" for row in audit["criteria"]
    ) and all(
        row["status"] in {"present", "present_equivalent"}
        for row in audit["minimum_artifacts"]
    )
    verify_payload(audit)
    return audit


def encoded(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = encoded(build())
    if args.check:
        if not AUDIT_PATH.is_file() or AUDIT_PATH.read_text(encoding="utf-8") != rendered:
            raise SystemExit("current completion audit is not the deterministic build")
        print(f"verified {AUDIT_PATH.relative_to(ROOT)}")
        return
    AUDIT_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {AUDIT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
