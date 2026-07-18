from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_layered_consensus_policy.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/014_layered_consensus_policy.test.sql"


class LayeredConsensusDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_layer_revision_weight_adjudication_and_summary_are_persisted(self) -> None:
        for field in (
            "revision",
            "reviewer_weights_applied",
            "reliability_snapshot_fingerprint",
            "adjudication_event_fingerprint",
            "layer_summary",
        ):
            self.assertIn(f"add column {field}", self.sql)
        self.assertIn("references public.adjudication_events", self.sql)

    def test_community_is_unweighted_and_qualified_methods_are_closed(self) -> None:
        self.assertIn("community evidence must remain unweighted", self.sql)
        for method in (
            "unweighted_human_counts_v1",
            "qualified_equal_weight_v1",
            "qualified_reliability_weighted_v1",
            "qualified_adjudication_v1",
            "release_gate_v1",
        ):
            self.assertIn(method, self.sql)
        self.assertIn("weighted qualified consensus requires a reliability snapshot", self.sql)

    def test_disagreement_requires_adjudication_not_weighted_majority(self) -> None:
        self.assertIn("adjudicated consensus requires exact adjudication lineage", self.sql)
        self.assertNotRegex(self.sql, r"majority|support_total\s*>\s*oppose_total")
        self.assertIn("minority_dissent_count", self.sql)

    def test_release_ready_requires_every_explicit_gate(self) -> None:
        for gate in (
            "rights_passed",
            "provenance_passed",
            "conflict_resolved",
            "quality_passed",
            "expert_gate_satisfied",
            "authorization_passed",
        ):
            self.assertIn(f'"{gate}":true', self.sql)
        self.assertIn("release consensus is missing an exact release gate", self.sql)

    def test_snapshot_lineage_is_serialized_monotonic_and_append_only(self) -> None:
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("new.revision := previous_snapshot.revision + 1", self.sql)
        self.assertIn("new.supersedes_consensus_pk := previous_snapshot.id", self.sql)
        self.assertIn("consensus snapshots are append only", self.sql)
        self.assertIn("consensus_layer_revision_key", self.sql)
        self.assertIn("consensus_current_layer_idx", self.sql)

    def test_security_definer_helpers_are_fixed_path_and_revoked(self) -> None:
        self.assertEqual(self.sql.count("security definer\nset search_path = ''"), 2)
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("model_vote_included", self.sql)
        self.assertIn("scientific_claim_allowed", self.sql)

    def test_existing_database_fixtures_use_the_versioned_method(self) -> None:
        expected = "butterflylens-layered-consensus:v1.0.0"
        for name in ("004_review_schema.test.sql", "005_map_impact_schema.test.sql"):
            fixture = (ROOT / "supabase/tests/database" / name).read_text(encoding="utf-8")
            self.assertIn(expected, fixture)
            self.assertIn("unweighted_human_counts_v1", fixture)

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
