from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase/migrations"
DATABASE_TEST = ROOT / "supabase/tests/database/001_core_project_run.test.sql"


class CoreDatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        matches = sorted(MIGRATIONS.glob("*_core_project_run_schema.sql"))
        if len(matches) != 1:
            raise AssertionError(f"expected one core migration, found {matches}")
        cls.migration = matches[0].read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_core_tables_use_typed_identity_and_timezone_columns(self) -> None:
        self.assertIn("create table public.projects", self.migration)
        self.assertIn("create table public.runs", self.migration)
        self.assertEqual(
            self.migration.count("bigint generated always as identity primary key"),
            2,
        )
        self.assertGreaterEqual(self.migration.count("timestamptz"), 5)
        self.assertNotRegex(self.migration, r"\bserial\b")
        self.assertNotRegex(self.migration, r'create table\s+"')

    def test_wire_contract_vocabularies_and_invariants_are_closed(self) -> None:
        for value in (
            "butterflylens-project:v1.0.0",
            "butterflylens-run:v1.0.0",
            "taxonomy_pack",
            "ala_baseline",
            "reference_bank",
            "flickr_discovery",
            "vision_pipeline",
            "geographic_impact",
            "quality_snapshot",
            "release_export",
            "full_pipeline",
            "queued",
            "leased",
            "cancelling",
            "cancelled",
            "succeeded",
            "failed",
        ):
            self.assertIn(f"'{value}'", self.migration)
        for constraint in (
            "runs_requested_actor_check",
            "runs_queued_state_check",
            "runs_active_state_check",
            "runs_terminal_state_check",
            "runs_failure_state_check",
            "runs_success_state_check",
            "runs_timestamp_order_check",
        ):
            self.assertIn(constraint, self.migration)

    def test_foreign_keys_are_indexed_and_deletes_are_restricted(self) -> None:
        self.assertIn(
            "project_pk bigint not null references public.projects (id) on delete restrict",
            self.migration,
        )
        self.assertIn(
            "created_by uuid references auth.users (id) on delete restrict",
            self.migration,
        )
        self.assertIn("projects_created_by_idx", self.migration)
        self.assertIn("runs_project_pk_requested_at_idx", self.migration)
        self.assertIn("runs_active_status_idx", self.migration)

    def test_rls_and_privileges_fail_closed_until_policy_subtask(self) -> None:
        self.assertIn("alter table public.projects enable row level security", self.migration)
        self.assertIn("alter table public.runs enable row level security", self.migration)
        self.assertIn(
            "from public, anon, authenticated",
            self.migration,
        )
        self.assertIn("to service_role", self.migration)
        self.assertNotIn("create policy", self.migration.casefold())
        self.assertNotIn("security definer", self.migration.casefold())
        self.assertNotIn("auth.role()", self.migration)

    def test_pgtap_suite_has_matching_plan_and_transaction_boundary(self) -> None:
        match = re.search(r"select plan\((\d+)\)", self.database_test)
        self.assertIsNotNone(match)
        assertions = len(
            re.findall(
                r"^select (?:has_|col_|ok\(|is\(|throws_ok\()",
                self.database_test,
                flags=re.MULTILINE,
            )
        )
        self.assertEqual(assertions, int(match.group(1)))
        self.assertTrue(self.database_test.startswith("begin;"))
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


if __name__ == "__main__":
    unittest.main()
