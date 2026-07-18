from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from scripts.build_current_completion_audit import build, encoded
from scripts.verify_completion_audit import AUDIT_PATH as HISTORICAL_AUDIT_PATH
from scripts.verify_current_completion_audit import (
    ARTIFACT_UPGRADES,
    AUDIT_PATH,
    CRITERION_UPGRADES,
    EXPECTED_COMMIT,
    EXPECTED_TREE,
    UPGRADED_ARTIFACTS,
    UPGRADED_CRITERION_IDS,
    CompletionAuditError,
    verify,
    verify_payload,
)


ROOT = Path(__file__).resolve().parents[1]


class CurrentCompletionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        cls.historical = json.loads(
            HISTORICAL_AUDIT_PATH.read_text(encoding="utf-8")
        )

    def test_current_audit_verifies_at_exact_pushed_boundary(self) -> None:
        result = verify()
        self.assertEqual(result["audited_commit"], EXPECTED_COMMIT)
        self.assertEqual(result["audited_tree"], EXPECTED_TREE)
        self.assertEqual(
            result["criteria"],
            {
                "total": 100,
                "satisfied": 80,
                "partial": 8,
                "blocked_by_user_instruction": 7,
                "blocked_external": 5,
            },
        )
        self.assertEqual(
            result["minimum_artifacts"],
            {
                "total": 46,
                "present": 14,
                "present_equivalent": 7,
                "blocked_by_user_instruction": 5,
                "blocked_external": 20,
            },
        )
        self.assertFalse(result["goal_complete"])

    def test_checked_in_audit_is_the_deterministic_build(self) -> None:
        self.assertEqual(AUDIT_PATH.read_text(encoding="utf-8"), encoded(build()))

    def test_only_proven_map_criteria_change_from_historical_audit(self) -> None:
        changed = {
            current["id"]
            for historical, current in zip(
                self.historical["criteria"], self.audit["criteria"], strict=True
            )
            if historical != current
        }
        self.assertEqual(changed, UPGRADED_CRITERION_IDS)
        for criterion_id in UPGRADED_CRITERION_IDS:
            row = self.audit["criteria"][criterion_id - 1]
            self.assertEqual(row["status"], "satisfied")
            self.assertEqual(row["next_action"], None)
            self.assertEqual(
                row,
                {
                    **self.historical["criteria"][criterion_id - 1],
                    **CRITERION_UPGRADES[criterion_id],
                },
            )
        self.assertEqual(self.audit["criteria"][61]["status"], "blocked_external")
        self.assertIn("Flickr", self.audit["criteria"][61]["criterion"])

    def test_only_named_map_artifacts_change_from_historical_audit(self) -> None:
        changed = {
            current["required"]
            for historical, current in zip(
                self.historical["minimum_artifacts"],
                self.audit["minimum_artifacts"],
                strict=True,
            )
            if historical != current
        }
        self.assertEqual(changed, UPGRADED_ARTIFACTS)
        for row in self.audit["minimum_artifacts"]:
            if row["required"] in UPGRADED_ARTIFACTS:
                self.assertEqual(row["status"], "present")
                self.assertEqual(row["status"], ARTIFACT_UPGRADES[row["required"]]["status"])

    def test_false_completion_and_unproven_flickr_upgrade_are_rejected(self) -> None:
        completed = copy.deepcopy(self.audit)
        completed["goal_complete"] = True
        with self.assertRaisesRegex(
            CompletionAuditError,
            "goal_complete differs from the deterministic completion rule",
        ):
            verify_payload(completed)

        flickr = copy.deepcopy(self.audit)
        flickr["criteria"][61]["status"] = "satisfied"
        flickr["criteria"][61]["next_action"] = None
        with self.assertRaisesRegex(
            CompletionAuditError, "current criterion 62 status differs"
        ):
            verify_payload(flickr)

    def test_wrong_boundary_and_future_evidence_are_rejected(self) -> None:
        wrong_commit = copy.deepcopy(self.audit)
        wrong_commit["audited_commit"] = "0" * 40
        with self.assertRaisesRegex(
            CompletionAuditError, "audited_commit differs from current boundary"
        ):
            verify_payload(wrong_commit)

        future = copy.deepcopy(self.audit)
        future["criteria"][18]["evidence"] = [
            "provenance/completion_audit.v2.json"
        ]
        with self.assertRaisesRegex(
            CompletionAuditError, "absent at audited commit"
        ):
            verify_payload(future)

    def test_release_security_verifies_historical_and_current_boundaries(self) -> None:
        security = (ROOT / "scripts/verify_release_security.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"verify_completion_audit.py"', security)
        self.assertIn('"verify_current_completion_audit.py"', security)

    def test_status_document_names_current_and_historical_audits(self) -> None:
        status = (ROOT / "COMPLETION_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("completion_audit.v2.json", status)
        self.assertIn("completion_audit.v1.json", status)
        self.assertIn("80 of 100", status)
        self.assertIn("goal remains incomplete", status)


if __name__ == "__main__":
    unittest.main()
