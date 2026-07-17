from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_review_schema.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/004_review_schema.test.sql"


class ReviewDatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_required_review_tables_are_closed_and_rls_enabled(self) -> None:
        tables = (
            "reviewer_profiles",
            "verification_campaigns",
            "assignments",
            "review_events",
            "consensus",
            "reviewer_reliability",
            "quality_snapshots",
        )
        for table in tables:
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertEqual(self.sql.count("bigint generated always as identity primary key"), 7)

    def test_assignments_are_independent_and_reviews_append_only(self) -> None:
        self.assertIn("assignments_reviewer_independence_key", self.sql)
        self.assertIn("assignments_review_identity_key", self.sql)
        self.assertIn("review_events_assignment_identity_fk", self.sql)
        self.assertIn("supersedes_event_pk", self.sql)
        self.assertIn(
            "grant select, insert on table public.review_events, public.consensus",
            self.sql,
        )

    def test_blinding_and_release_layers_are_explicit(self) -> None:
        for field in (
            "blind_model_label",
            "blind_model_score",
            "blind_query_term",
            "blind_source_comment",
            "blind_peer_decisions",
        ):
            self.assertIn(field, self.sql)
        self.assertIn("'community_evidence', 'qualified_consensus', 'release_consensus'", self.sql)
        self.assertIn("consensus_release_gate_check", self.sql)

    def test_reliability_is_private_domain_specific_and_non_circular(self) -> None:
        for field in ("family_taxon_key", "life_stage", "visual_domain"):
            self.assertIn(field, self.sql)
        self.assertIn("reviewer_reliability_no_circularity_check", self.sql)
        self.assertIn("shrunk_weight between 0.5 and 2", self.sql)
        self.assertNotIn("grant select on table public.reviewer_reliability to authenticated", self.sql)

    def test_audit_and_failure_discovery_snapshots_remain_distinct(self) -> None:
        self.assertIn("'representative_audit', 'targeted_failure_discovery', 'operational'", self.sql)
        self.assertIn("quality_snapshots_sampling_method_check", self.sql)
        self.assertIn("effective_sample_size", self.sql)
        self.assertIn("release_blockers", self.sql)

    def test_every_foreign_key_access_path_is_indexed(self) -> None:
        for index in (
            "verification_campaigns_project_pk_idx",
            "verification_campaigns_species_pk_idx",
            "verification_campaigns_creator_pk_idx",
            "assignments_campaign_pk_idx",
            "assignments_media_object_pk_idx",
            "assignments_reviewer_profile_pk_idx",
            "review_events_assignment_pk_idx",
            "review_events_campaign_pk_idx",
            "review_events_media_object_pk_idx",
            "review_events_reviewer_profile_pk_idx",
            "review_events_alternative_species_pk_idx",
            "review_events_supersedes_event_pk_idx",
            "consensus_campaign_pk_idx",
            "consensus_media_object_pk_idx",
            "consensus_species_pk_idx",
            "consensus_supersedes_pk_idx",
            "reviewer_reliability_reviewer_pk_idx",
            "reviewer_reliability_project_pk_idx",
            "quality_snapshots_project_pk_idx",
            "quality_snapshots_run_pk_idx",
            "quality_snapshots_campaign_pk_idx",
            "quality_snapshots_species_pk_idx",
        ):
            self.assertIn(index, self.sql)

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
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
