from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_community_reviewer_accounts.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/007_community_reviewer_accounts.test.sql"


class CommunityAuthSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_registration_rpc_is_fixed_path_and_narrowly_executable(self) -> None:
        self.assertIn("create function public.register_reviewer", self.sql)
        self.assertIn("security definer\nset search_path = ''", self.sql)
        self.assertIn("caller_auth_user_id uuid := (select auth.uid())", self.sql)
        self.assertIn("from public, anon, authenticated", self.sql)
        self.assertIn("to authenticated", self.sql)
        self.assertNotIn("auth.role()", self.sql)
        self.assertNotIn("user_metadata", self.sql)
        self.assertNotIn("raw_user_meta_data", self.sql)

    def test_anonymous_auth_users_cannot_register(self) -> None:
        self.assertIn("not coalesce(auth_user.is_anonymous, false)", self.sql)
        self.assertIn("reviewer registration requires a permanent account", self.sql)
        self.assertIn("using errcode = '42501'", self.sql)

    def test_self_service_can_create_only_active_base_reviewer(self) -> None:
        self.assertIn("enrollment_kind = 'self_service'", self.sql)
        self.assertIn("and role = 'reviewer'", self.sql)
        self.assertIn("and status = 'active'", self.sql)
        self.assertIn("'reviewer',\n      'active',\n      'unverified'", self.sql)
        self.assertNotRegex(
            self.sql,
            r"requested_(?:role|qualification)|target_(?:role|qualification)",
        )

    def test_public_names_are_pseudonymous_contact_free_values(self) -> None:
        self.assertIn("reviewer_profiles_public_name_pseudonym_check", self.sql)
        self.assertIn("reviewer_profiles_public_name_ci_key", self.sql)
        self.assertIn("public_name = btrim(public_name)", self.sql)
        self.assertIn("position('@' in public_name) = 0", self.sql)
        self.assertIn("public name must be a 2-80 character pseudonym", self.sql)

    def test_registration_is_idempotent_and_targets_active_projects(self) -> None:
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("where profile.auth_user_id = caller_auth_user_id", self.sql)
        self.assertIn("where membership.project_pk = target_project_pk", self.sql)
        self.assertIn("and project.status = 'active'", self.sql)
        self.assertIn("if profile_pk is null then", self.sql)
        self.assertIn("if membership_external_id is null then", self.sql)

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
