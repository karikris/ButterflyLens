from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718093000_community_moderation.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/020_community_moderation.test.sql"
POLICY = ROOT / "MODERATION.md"


class ModerationWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.policy = POLICY.read_text(encoding="utf-8")

    def test_exact_report_hide_suspension_audit_appeal_and_note_actions_exist(self) -> None:
        for action in (
            "reported",
            "content_hidden",
            "content_restored",
            "reviewer_suspended",
            "reviewer_reinstated",
            "review_audit_opened",
            "review_audit_completed",
            "appeal_submitted",
            "appeal_upheld",
            "appeal_denied",
            "curator_note_added",
            "case_closed",
        ):
            self.assertIn(f"'{action}'", self.sql)
        for function in (
            "report_review_comment",
            "open_review_audit_case",
            "appeal_moderation_case",
            "moderate_community_case",
            "add_moderation_curator_note",
        ):
            self.assertIn(f"create function public.{function}", self.sql)

    def test_reporter_detail_and_curator_note_content_have_separate_private_access(self) -> None:
        self.assertIn("create table private.moderation_reporters", self.sql)
        self.assertIn("reporter identity and detail remain private", self.sql)
        self.assertNotIn("reporter_reviewer_profile_pk", self._table("moderation_cases"))
        self.assertIn("'Community report: ' || replace(target_reason_category", self.sql)
        self.assertNotIn("target_reason_summary text", self._function("report_review_comment"))
        self.assertIn("moderation_curator_notes_curator_read", self.sql)
        self.assertNotIn("moderation_curator_notes_party_read", self.sql)
        self.assertIn("Note text is visible only to authorized", self.policy)

    def test_review_events_are_retained_and_only_projection_hides_comment_text(self) -> None:
        view = self.sql.split("create view public.moderated_review_comments", 1)[1]
        self.assertIn("then null", view)
        self.assertIn("review.event_fingerprint as retained_review_event_fingerprint", view)
        self.assertNotRegex(self.sql, r"(?i)(update|delete from) public\.review_events")
        self.assertIn("Hiding never updates or deletes the underlying", self.policy)
        self.assertIn("moderation ledgers are append only", self.sql)

    def test_suspension_is_project_scoped_and_preserves_prior_evidence(self) -> None:
        self.assertIn("update public.project_memberships", self.sql)
        self.assertIn("set status = 'paused'", self.sql)
        self.assertIn("set status = 'active'", self.sql)
        self.assertNotRegex(self.sql, r"update public\.reviewer_profiles")
        self.assertIn("target_membership.role not in ('reviewer', 'expert')", self.sql)
        self.assertIn("curator cannot moderate their own membership", self.sql)
        self.assertIn("Other project memberships and all earlier evidence remain", self.policy)

    def test_appeal_remains_available_to_paused_target_and_resolution_is_atomic(self) -> None:
        appeal = self._function("appeal_moderation_case")
        self.assertIn("profile.auth_user_id = caller_auth_user_id", appeal)
        self.assertNotIn("membership.status = 'active'", appeal)
        moderate = self._function("moderate_community_case")
        self.assertIn("visibility_effect := 'restored'", moderate)
        self.assertIn("membership_effect := 'reinstated'", moderate)
        self.assertIn("appeal decision lacks one unresolved exact appeal", moderate)

    def test_audit_and_moderation_cannot_create_reliability_or_scientific_truth(self) -> None:
        self.assertIn("not scientific_claim_allowed", self.sql)
        self.assertNotRegex(self.sql, r"(?i)(insert into|update) public\.reviewer_reliability")
        self.assertNotRegex(self.sql, r"(?i)(insert into|update) public\.consensus")
        self.assertIn("Moderation is not scientific truth", self.policy)
        self.assertIn("An audit is not a reliability estimate", self.policy)

    def test_rls_and_rpc_only_mutation_boundary_are_closed(self) -> None:
        for table in (
            "moderation_cases",
            "moderation_events",
            "moderation_appeals",
            "moderation_curator_notes",
        ):
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertNotRegex(self.sql, r"grant (?:insert|update|delete).* to authenticated")
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("to authenticated;", self.sql)
        self.assertIn("security definer", self.sql)
        self.assertIn("set search_path = ''", self.sql)
        self.assertNotRegex(self.sql, r"grant select .* to anon")

    def test_event_sequence_fingerprints_and_effects_are_fail_closed(self) -> None:
        for phrase in (
            "moderation event sequence must be contiguous",
            "unique sorted SHA-256 values",
            "visibility_effect in ('unchanged', 'hidden', 'restored')",
            "membership_effect in ('unchanged', 'suspended', 'reinstated')",
            "closed moderation case cannot change",
            "case_fingerprint ~ '^[0-9a-f]{64}$'",
            "event_fingerprint ~ '^[0-9a-f]{64}$'",
        ):
            self.assertIn(phrase, self.sql)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, plan)
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))

    def test_policy_and_public_links_are_versioned_and_reachable(self) -> None:
        self.assertIn("butterflylens-community-moderation:v1.0.0", self.policy)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        shell = (ROOT / "apps/web/src/shell/PublicShell.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("[community safeguards and moderation policy](MODERATION.md)", readme)
        self.assertIn(
            "https://github.com/karikris/ButterflyLens/blob/main/MODERATION.md",
            shell,
        )

    def _table(self, name: str) -> str:
        start = self.sql.index(f"create table public.{name}")
        return self.sql[start : self.sql.index(";", start)]

    def _function(self, name: str) -> str:
        start = self.sql.index(f"create function public.{name}")
        return self.sql[start : self.sql.index("end;\n$$;", start)]


if __name__ == "__main__":
    unittest.main()
