from __future__ import annotations

import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "supabase/migrations").glob("*_reviewer_reliability_estimates.sql")
)
DATABASE_TEST = ROOT / "supabase/tests/database/013_reviewer_reliability_estimates.test.sql"


class ReviewerReliabilityDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_every_required_measure_and_domain_field_is_persisted(self) -> None:
        for field in (
            "source_provider",
            "sample_count",
            "decisive_count",
            "positive_control_count",
            "negative_control_count",
            "control_accuracy",
            "sensitivity",
            "specificity",
            "pairwise_agreement",
            "krippendorff_alpha",
            "adjudicated_overlap",
            "interval_level",
            "evidence_fingerprint",
            "evidence_cutoff",
            "blockers",
        ):
            self.assertIn(f"add column {field}", self.sql)

    def test_minimum_evidence_and_class_thresholds_match_policy(self) -> None:
        for expression in (
            "new.control_count >= 20",
            "new.positive_control_count >= 5",
            "new.negative_control_count >= 5",
            "new.overlap_count >= 10",
            "new.adjudicated_count >= 5",
            "new.positive_control_count >= 10",
            "new.negative_control_count >= 10",
        ):
            self.assertIn(expression, self.sql)
        self.assertIn("insufficient evidence must preserve equal weight and blockers", self.sql)

    def test_snapshots_are_append_only_monotonic_and_serialized(self) -> None:
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("snapshot_revision := previous_snapshot.snapshot_revision + 1", self.sql)
        self.assertIn("supersedes_reliability_pk := previous_snapshot.id", self.sql)
        self.assertIn("reviewer reliability snapshots are append only", self.sql)
        self.assertIn("reviewer_reliability_domain_revision_key", self.sql)
        self.assertIn("reviewer_reliability_current_domain_idx", self.sql)

    def test_privacy_and_non_circularity_are_database_invariants(self) -> None:
        for fragment in (
            "'visibility' is distinct from 'private'",
            "'public_ranking_allowed') is distinct from 'false'::jsonb",
            "'model_agreement_used') is distinct from 'false'::jsonb",
            "'majority_agreement_alone_used') is distinct from 'false'::jsonb",
            "'scientific_claim_allowed') is distinct from 'false'::jsonb",
        ):
            self.assertIn(fragment, self.sql)
        self.assertNotRegex(self.sql, r"grant (?:insert|update|delete).*authenticated")

    def test_fixed_search_path_helpers_are_not_browser_callable(self) -> None:
        self.assertEqual(self.sql.count("security definer\nset search_path = ''"), 2)
        self.assertIn("from public, anon, authenticated", self.sql)

    def test_contract_cap_matches_normative_policy(self) -> None:
        contract = json.loads(
            (
                ROOT / "packages/contracts/schemas/verification-contracts.schema.json"
            ).read_text(encoding="utf-8")
        )
        weight = contract["$defs"]["reviewer_reliability"]["properties"][
            "applied_weight"
        ]["anyOf"][0]
        self.assertEqual(weight["minimum"], 0.5)
        self.assertEqual(weight["maximum"], 2)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\(|is\(|throws_ok\(|lives_ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, plan)
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
