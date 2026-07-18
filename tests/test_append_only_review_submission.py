from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "supabase/migrations").glob("*_append_only_review_submission.sql")
)
DATABASE_TEST = ROOT / "supabase/tests/database/010_append_only_review_submission.test.sql"


class AppendOnlyReviewSubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_rpc_derives_private_identity_and_context_server_side(self) -> None:
        self.assertIn("create function public.submit_review_event", self.sql)
        self.assertIn("caller_auth_user_id uuid := (select auth.uid())", self.sql)
        self.assertIn("profile.auth_user_id = caller_auth_user_id", self.sql)
        self.assertIn("assignment_record.question, assignment_record.image_sha256", self.sql)
        self.assertNotRegex(self.sql, r"target_(?:reviewer|user|question|image_sha256)")

    def test_every_required_event_field_is_recorded(self) -> None:
        for field in (
            "review_event_id",
            "assignment_pk",
            "verification_campaign_pk",
            "media_object_pk",
            "reviewer_profile_pk",
            "question",
            "image_sha256",
            "decision",
            "comment",
            "confidence",
            "decided_at",
            "duration_ms",
            "supersedes_event_pk",
            "source_version",
            "model_version",
            "event_fingerprint",
        ):
            self.assertIn(field, self.sql)
        self.assertIn("model version or explicit unavailable state must be recorded", self.sql)
        self.assertIn("species.status = 'accepted'", self.sql)

    def test_submission_is_atomic_and_direct_browser_insert_is_closed(self) -> None:
        self.assertIn("for update of assignment", self.sql)
        self.assertIn("set status = 'responded'", self.sql)
        self.assertIn("revoke insert on table public.review_events from authenticated", self.sql)
        self.assertIn("drop policy if exists review_events_self_insert", self.sql)
        self.assertIn("to authenticated", self.sql)
        self.assertIn("security definer\nset search_path = ''", self.sql)

    def test_corrections_supersede_current_same_assignment_event(self) -> None:
        self.assertIn("review_events_enforce_append_lineage", self.sql)
        self.assertIn("review correction must supersede the current event", self.sql)
        self.assertIn("review correction crosses assignment identity", self.sql)
        self.assertIn("review correction time precedes the event it supersedes", self.sql)
        self.assertIn("post_disclosure_correction", self.sql)
        self.assertIn("is distinct from assignment_record.blind_payload_fingerprint", self.sql)
        self.assertNotRegex(self.sql, r"update public\.review_events|delete from public\.review_events")

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
