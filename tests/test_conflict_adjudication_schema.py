from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "supabase/migrations").glob("*_conflict_adjudication_workflow.sql")
)
DATABASE_TEST = ROOT / "supabase/tests/database/011_conflict_adjudication_workflow.test.sql"


class ConflictAdjudicationSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_conflicts_snapshot_exact_effective_dissent(self) -> None:
        for table in (
            "review_conflicts",
            "review_conflict_events",
            "adjudication_assignments",
            "adjudication_events",
        ):
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertIn("create function private.open_review_conflict", self.sql)
        self.assertIn("not exists (\n        select 1 from public.review_events correction", self.sql)
        self.assertIn("count(distinct reviewer_profile_pk)", self.sql)
        self.assertIn("count(distinct row(decision, alternative_species_pk))", self.sql)
        self.assertIn("independent conflicting effective reviews do not exist", self.sql)
        self.assertIn(
            "grant execute on function private.open_review_conflict(text, text, text, text)\n"
            "to service_role",
            self.sql,
        )
        self.assertNotIn(
            "grant select, insert on table public.review_conflicts", self.sql
        )

    def test_adjudicator_is_qualified_and_not_a_source_reviewer(self) -> None:
        self.assertIn("adjudicator must be independent of conflicting reviews", self.sql)
        self.assertIn("member_record.qualification_state <> 'verified'", self.sql)
        self.assertIn("member_record.role not in ('expert', 'curator', 'administrator')", self.sql)
        self.assertIn("resolved conflict cannot be assigned again", self.sql)
        self.assertIn("terminal adjudication assignment cannot be reopened", self.sql)
        self.assertIn("adjudication response timestamp is immutable", self.sql)
        self.assertIn("adjudication_assignments_one_active_idx", self.sql)

    def test_submission_derives_identity_and_conflict_lineage(self) -> None:
        self.assertIn("create function public.submit_adjudication_event", self.sql)
        self.assertIn("caller_auth_user_id uuid := (select auth.uid())", self.sql)
        self.assertIn("profile.auth_user_id = caller_auth_user_id", self.sql)
        self.assertIn("array_agg(source.event_fingerprint order by source.event_fingerprint)", self.sql)
        self.assertIn("array_agg(source.reviewer_profile_pk order by source.event_fingerprint)", self.sql)
        self.assertNotRegex(self.sql, r"target_(?:adjudicator|reviewer|question|image_sha256)")

    def test_adjudication_is_append_only_and_cannot_erase_dissent(self) -> None:
        self.assertIn("adjudication events are append only", self.sql)
        self.assertIn("adjudication_events_reject_mutation", self.sql)
        self.assertIn("adjudication_events_enforce_lineage", self.sql)
        self.assertIn("source_event_fingerprints", self.sql)
        self.assertIn("conflicting_reviewer_profile_pks", self.sql)
        self.assertIn("independence_check = 'passed'", self.sql)
        self.assertIn("check (not scientific_claim_allowed)", self.sql)
        self.assertNotRegex(self.sql, r"(?:update|delete from) public\.review_events")

    def test_browser_can_only_use_safe_assignment_and_submission_surfaces(self) -> None:
        self.assertIn("with (security_invoker = true)", self.sql)
        self.assertIn("create view public.my_adjudication_queue", self.sql)
        view_sql = self.sql.split("create view public.my_adjudication_queue", 1)[1]
        view_sql = view_sql.split("revoke all on table public.my_adjudication_queue", 1)[0]
        for hidden in ("reviewer_profile_pk", "auth_user_id", "decision", "comment", "model_version"):
            self.assertNotIn(hidden, view_sql)
        self.assertIn("false as scientific_claim_allowed", view_sql)
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("to authenticated", self.sql)
        self.assertIn("revoke all on table public.my_adjudication_queue", self.sql)

    def test_every_new_foreign_key_access_path_is_indexed(self) -> None:
        for index in (
            "review_conflicts_campaign_pk_idx",
            "review_conflicts_media_object_pk_idx",
            "review_conflict_events_event_pk_idx",
            "review_conflict_events_reviewer_pk_idx",
            "adjudication_assignments_adjudicator_pk_idx",
            "adjudication_events_conflict_pk_idx",
            "adjudication_events_adjudicator_pk_idx",
            "adjudication_events_campaign_pk_idx",
            "adjudication_events_media_object_pk_idx",
            "adjudication_events_alternative_species_pk_idx",
        ):
            self.assertIn(index, self.sql)

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
