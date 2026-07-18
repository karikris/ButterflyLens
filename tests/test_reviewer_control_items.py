from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_reviewer_control_items.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/012_reviewer_control_items.test.sql"


class ReviewerControlItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_all_required_control_kinds_are_closed(self) -> None:
        for kind in (
            "known_butterfly", "known_non_butterfly", "ambiguous_image",
            "duplicate", "media_failure", "life_stage",
        ):
            self.assertIn(f"('{kind}',", self.sql)
        self.assertIn("reviewer_control_items_shape_check", self.sql)

    def test_controls_are_private_blind_and_evidence_bound(self) -> None:
        self.assertIn("campaign.campaign_kind <> 'reviewer_control'", self.sql)
        for field in (
            "blind_model_label", "blind_model_score", "blind_query_term",
            "blind_source_comment", "blind_peer_decisions",
        ):
            self.assertIn(field, self.sql)
        self.assertIn("evidence_fingerprint", self.sql)
        self.assertIn("evidence_citation", self.sql)
        self.assertIn("check (not scientific_claim_allowed)", self.sql)
        self.assertNotIn("grant select on table private.reviewer_control_items to authenticated", self.sql)

    def test_control_assignments_are_exact_hidden_bindings(self) -> None:
        self.assertIn("assignment.verification_campaign_pk = control.verification_campaign_pk", self.sql)
        self.assertIn("assignment.media_object_pk = control.media_object_pk", self.sql)
        self.assertIn("control_set.status = 'active'", self.sql)
        self.assertIn("reviewer_control_assignments_assignment_key", self.sql)

    def test_ground_truth_is_immutable_and_model_free(self) -> None:
        self.assertIn("reviewer control evidence is immutable", self.sql)
        self.assertIn("reviewer_control_items_reject_mutation", self.sql)
        self.assertNotRegex(self.sql, r"(?:bioclip|yolo|model_vote|model_evidence)")

    def test_foreign_key_paths_are_indexed(self) -> None:
        for index in (
            "reviewer_control_sets_project_pk_idx",
            "reviewer_control_items_set_pk_idx",
            "reviewer_control_items_campaign_pk_idx",
            "reviewer_control_items_media_pk_idx",
            "reviewer_control_items_duplicate_media_pk_idx",
            "reviewer_control_assignments_assignment_pk_idx",
        ):
            self.assertIn(index, self.sql)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(re.findall(
            r"^select (?:has_|col_|ok\(|is\(|throws_ok\(|lives_ok\()",
            self.database_test, flags=re.MULTILINE,
        ))
        self.assertEqual(assertions, plan)
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
