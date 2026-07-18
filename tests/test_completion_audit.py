from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.verify_completion_audit import (
    ARTIFACTS,
    AUDIT_PATH,
    CRITERIA,
    CompletionAuditError,
    verify,
    verify_payload,
)


ROOT = Path(__file__).resolve().parents[1]


class CompletionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

    def test_fixed_audit_verifies_and_remains_incomplete(self) -> None:
        result = verify()
        self.assertEqual(result["criteria"]["total"], 100)
        self.assertEqual(result["criteria"]["satisfied"], 70)
        self.assertEqual(result["minimum_artifacts"]["total"], 46)
        self.assertFalse(result["goal_complete"])

    def test_exact_goal_criteria_and_artifact_names_are_retained(self) -> None:
        self.assertEqual(
            [row["criterion"] for row in self.audit["criteria"]],
            list(CRITERIA),
        )
        self.assertEqual(
            [
                (row["category"], row["required"])
                for row in self.audit["minimum_artifacts"]
            ],
            list(ARTIFACTS),
        )

    def test_false_completion_claim_is_rejected(self) -> None:
        altered = copy.deepcopy(self.audit)
        altered["goal_complete"] = True
        with self.assertRaisesRegex(
            CompletionAuditError,
            "goal_complete differs from the deterministic completion rule",
        ):
            verify_payload(altered)

        weakened = copy.deepcopy(self.audit)
        weakened["completion_rule"] = "operator says complete"
        with self.assertRaisesRegex(
            CompletionAuditError,
            "completion_rule differs from fixed boundary",
        ):
            verify_payload(weakened)

    def test_missing_criterion_and_status_upgrade_are_rejected(self) -> None:
        missing = copy.deepcopy(self.audit)
        missing["criteria"].pop()
        with self.assertRaisesRegex(CompletionAuditError, "exactly 100"):
            verify_payload(missing)

        upgraded = copy.deepcopy(self.audit)
        upgraded["criteria"][11]["status"] = "satisfied"
        upgraded["criteria"][11]["next_action"] = None
        with self.assertRaisesRegex(
            CompletionAuditError,
            "criterion 12 status differs",
        ):
            verify_payload(upgraded)

    def test_untracked_or_future_evidence_is_rejected(self) -> None:
        altered = copy.deepcopy(self.audit)
        altered["criteria"][0]["evidence"] = ["COMPLETION_STATUS.md"]
        with self.assertRaisesRegex(
            CompletionAuditError,
            "absent at audited commit",
        ):
            verify_payload(altered)

    def test_summary_drift_and_unsafe_paths_are_rejected(self) -> None:
        drifted = copy.deepcopy(self.audit)
        drifted["artifact_summary"]["present"] += 1
        with self.assertRaisesRegex(CompletionAuditError, "artifact summary differs"):
            verify_payload(drifted)

        unsafe = copy.deepcopy(self.audit)
        unsafe["criteria"][0]["evidence"] = ["../outside"]
        with self.assertRaisesRegex(CompletionAuditError, "unsafe evidence path"):
            verify_payload(unsafe)

    def test_json_schema_declares_closed_fixed_collections(self) -> None:
        schema = json.loads(
            (ROOT / "provenance" / "completion-audit.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["criteria"]["minItems"], 100)
        self.assertEqual(schema["properties"]["criteria"]["maxItems"], 100)
        self.assertEqual(schema["properties"]["minimum_artifacts"]["minItems"], 46)
        self.assertEqual(schema["properties"]["minimum_artifacts"]["maxItems"], 46)

    def test_release_security_gate_invokes_completion_verifier(self) -> None:
        security = (ROOT / "scripts" / "verify_release_security.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def verify_completion_boundary()", security)
        self.assertIn("verify_completion_boundary()\n    public_tables", security)


if __name__ == "__main__":
    unittest.main()
