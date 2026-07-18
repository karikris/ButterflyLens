from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "supabase/migrations").glob("*_repeated_independent_assignments.sql")
)
DATABASE_TEST = (
    ROOT / "supabase/tests/database/008_repeated_independent_assignments.test.sql"
)


class RepeatedAssignmentSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_defaults_cover_every_required_assignment_class(self) -> None:
        for row in (
            "('ordinary_image', 2, 2, 2, 2, 0, false)",
            "('disagreement', 3, 3, 3, 3, 0, false)",
            "('potential_gap', 3, 3, 5, 4, 0, false)",
            "('reference_image', 2, 2, 2, 2, 0, false)",
            "('high_impact_release', 3, 3, 5, 4, 2, true)",
        ):
            self.assertIn(row, self.sql)
        self.assertIn("repeated-independent-v1", self.sql)

    def test_campaign_policy_is_fail_closed(self) -> None:
        self.assertIn("verification_campaigns_enforce_assignment_policy", self.sql)
        self.assertIn("campaign review count violates repeated assignment policy", self.sql)
        self.assertIn("campaign requires more qualified independent reviews", self.sql)
        self.assertIn("campaign expert gate violates repeated assignment policy", self.sql)

    def test_assignment_rounds_are_independent_and_role_gated(self) -> None:
        self.assertIn("assignments_enforce_repeated_independence", self.sql)
        self.assertIn("assignment exceeds campaign independent review count", self.sql)
        self.assertIn("active_assignment_count >= 2 then 'conflict'", self.sql)
        self.assertIn("active_assignment_count >= campaign.target_review_count", self.sql)
        self.assertIn("assignment sequence must be the next independent round", self.sql)
        self.assertIn("new.assignment_reason := expected_reason", self.sql)
        self.assertIn("new.required_reviewer_role := expected_role", self.sql)
        self.assertIn("profile_qualification <> 'verified'", self.sql)
        self.assertIn("member_role not in ('expert', 'curator', 'administrator')", self.sql)
        self.assertIn("assignment identity and policy fields are immutable", self.sql)

    def test_progress_is_server_only_and_does_not_return_identity(self) -> None:
        self.assertIn("create function private.review_assignment_progress", self.sql)
        self.assertIn("to service_role", self.sql)
        self.assertIn("from public, anon, authenticated", self.sql)
        for private_field in ("reviewer_id", "reviewer_profile_pk", "decision"):
            returns = self.sql.split("returns table (", 1)[1].split(")\nlanguage sql", 1)[0]
            self.assertNotIn(private_field, returns)

    def test_existing_uniqueness_remains_the_independence_backstop(self) -> None:
        original = next((ROOT / "supabase/migrations").glob("*_review_schema.sql"))
        original_sql = original.read_text(encoding="utf-8")
        self.assertIn("assignments_reviewer_independence_key", original_sql)
        self.assertIn("assignments_sequence_key", original_sql)

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
