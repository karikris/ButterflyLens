from __future__ import annotations

import re
import json
from pathlib import Path
import unittest

from butterflylens.contracts.occurrence_release import (
    RELEASE_GATE_NAMES,
    ReleaseGateEvidence,
    plan_occurrence_release,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718110000_occurrence_release_policy.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/023_occurrence_release_policy.test.sql"
POLICY = ROOT / "OCCURRENCE_RELEASE.md"


def passed_gates() -> list[ReleaseGateEvidence]:
    return [
        ReleaseGateEvidence(
            gate_name=name,
            passed=True,
            evidence_fingerprints=(f"{index:x}" * 64,),
            blocker_code=None,
        )
        for index, name in enumerate(RELEASE_GATE_NAMES, 1)
    ]


class OccurrenceReleasePlannerTests(unittest.TestCase):
    def test_every_evidenced_gate_is_required_for_release_ready(self) -> None:
        decision = plan_occurrence_release(passed_gates())
        self.assertEqual(decision.release_state, "release_ready_occurrence_candidate")
        self.assertFalse(decision.published_occurrence)
        self.assertFalse(decision.scientific_claim_allowed)
        self.assertEqual(tuple(g.gate_name for g in decision.gate_results), RELEASE_GATE_NAMES)
        self.assertEqual(len(decision.evidence_fingerprints), len(RELEASE_GATE_NAMES))
        self.assertIn("release_ready_occurrence_candidate", json.dumps(decision.as_dict()))

    def test_failed_gate_blocks_with_stable_reason(self) -> None:
        gates = passed_gates()
        gates[0] = ReleaseGateEvidence(
            gate_name=gates[0].gate_name,
            passed=False,
            evidence_fingerprints=(),
            blocker_code="coordinate_date_evidence_invalid",
        )
        decision = plan_occurrence_release(gates)
        self.assertEqual(decision.release_state, "blocked")
        self.assertEqual(decision.blocker_codes, ("coordinate_date_evidence_invalid",))

    def test_missing_duplicate_or_unknown_gate_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be exact"):
            plan_occurrence_release(passed_gates()[:-1])
        duplicate = passed_gates()
        duplicate[-1] = duplicate[0]
        with self.assertRaisesRegex(ValueError, "must be exact|must be unique"):
            plan_occurrence_release(duplicate)
        with self.assertRaisesRegex(ValueError, "unsupported occurrence release gate"):
            ReleaseGateEvidence("invented", True, ("a" * 64,), None)  # type: ignore[arg-type]

    def test_passed_gate_requires_sorted_unique_fingerprinted_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            ReleaseGateEvidence(RELEASE_GATE_NAMES[0], True, (), None)
        with self.assertRaisesRegex(ValueError, "sorted and unique"):
            ReleaseGateEvidence(
                RELEASE_GATE_NAMES[0], True, ("b" * 64, "a" * 64), None
            )

    def test_decision_fingerprint_is_order_independent(self) -> None:
        forward = plan_occurrence_release(passed_gates())
        reverse = plan_occurrence_release(list(reversed(passed_gates())))
        self.assertEqual(forward.decision_fingerprint, reverse.decision_fingerprint)
        self.assertRegex(forward.decision_fingerprint, r"^[0-9a-f]{64}$")


class OccurrenceReleaseDatabasePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.policy = " ".join(POLICY.read_text(encoding="utf-8").split())

    def test_database_receipt_requires_every_goal_gate(self) -> None:
        for gate in RELEASE_GATE_NAMES:
            self.assertIn(f'"{gate}": true', self.sql)
        for message in (
            "human-supported identity",
            "qualified consensus",
            "configured expert release gate",
            "coordinate and date evidence",
            "representative evidence",
            "unresolved human conflict",
            "rights or removal gate failed",
            "evidence packet does not match",
        ):
            self.assertIn(message, self.sql)

    def test_receipt_is_exact_immutable_private_evidence(self) -> None:
        self.assertIn("occurrence release receipts are append only", self.sql)
        self.assertIn("evidence lineage must be exact, sorted, and unique", self.sql)
        self.assertIn("to service_role", self.sql)
        self.assertNotIn(
            "grant insert on table public.occurrence_release_receipts to authenticated",
            self.sql,
        )
        self.assertIn("check (not published_occurrence)", self.sql)
        self.assertIn("check (not scientific_claim_allowed)", self.sql)

    def test_public_release_requires_location_takedown_and_release_receipts(self) -> None:
        self.assertIn("drop policy release_candidates_public_read", self.sql)
        for helper in (
            "private.has_publishable_location_receipt('release_candidate', id)",
            "not private.has_media_takedown_for_release(id)",
            "private.has_occurrence_release_receipt(id)",
        ):
            self.assertIn(helper, self.sql)

    def test_policy_distinguishes_candidate_from_publication_and_models(self) -> None:
        for phrase in (
            "still not a published occurrence",
            "Missing, stale, unverifiable, unrelated, or unknown evidence blocks release",
            "Provider assertion and machine screening are not human support",
            "weighting alone cannot resolve conflict",
            "blind representative audit—not targeted failure discovery",
            "YOLOE and BioCLIP remain unfinished",
        ):
            self.assertIn(phrase, self.policy)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\(|is\(|throws_ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, plan)


if __name__ == "__main__":
    unittest.main()
