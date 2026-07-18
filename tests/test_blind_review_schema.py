from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_blind_review_disclosure.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/009_blind_review_disclosure.test.sql"


class BlindReviewSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_all_required_context_is_blind_at_campaign_boundary(self) -> None:
        for field in (
            "blind_model_label",
            "blind_model_score",
            "blind_query_term",
            "blind_source_comment",
            "blind_peer_decisions",
        ):
            self.assertIn(f"new.{field}", self.sql)
        self.assertIn("verification_campaigns_enforce_blind_review", self.sql)

    def test_blind_projection_is_allowlisted_and_storage_safe(self) -> None:
        view = self.sql.split("create view public.blind_review_assignments", 1)[1]
        view = view.split("create view public.post_decision_review_disclosures", 1)[0]
        projection = view.split("as\nselect", 1)[1].split("from public.assignments", 1)[0]
        for allowed in ("campaign.question", "media.content_sha256", "media.rights_fingerprint"):
            self.assertIn(allowed, view)
        for blocked in (
            "storage_key",
            "model_label",
            "model_score",
            "query_term",
            "source_comment",
            "peer_decision",
            "auth_user_id",
            "reviewer_profile_pk",
            "assignment_sequence",
            "assignment_reason",
            "required_reviewer_role",
            "campaign_name",
        ):
            self.assertNotIn(blocked, projection)
        self.assertIn("with (security_invoker = true)", self.sql)

    def test_reveal_requires_the_same_reviewers_append_only_event(self) -> None:
        self.assertIn("review_disclosures_event_assignment_fk", self.sql)
        self.assertIn("assignment.status = 'responded'", self.sql)
        self.assertIn("event.reviewer_profile_pk = assignment.reviewer_profile_pk", self.sql)
        self.assertIn("profile.auth_user_id = (select auth.uid())", self.sql)
        self.assertNotIn("to anon", self.sql.split("grant select on table public.review_disclosures", 1)[1])

    def test_reveal_shape_has_no_reviewer_identity_or_raw_score(self) -> None:
        self.assertIn("model_score_band", self.sql)
        self.assertNotIn("raw_model_score", self.sql)
        self.assertIn("source_comment_display_allowed or source_comment_excerpt is null", self.sql)
        for count in ("peer_yes_count", "peer_no_count", "peer_uncertain_count"):
            self.assertIn(count, self.sql)
        for identity in ("peer_reviewer_id", "peer_public_name", "peer_auth_user_id"):
            self.assertNotIn(identity, self.sql)
        self.assertIn("check (not scientific_claim_allowed)", self.sql)

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
