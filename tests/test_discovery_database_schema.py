from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_discovery_schema.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/002_discovery_schema.test.sql"


class DiscoveryDatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_required_discovery_tables_are_closed_and_rls_enabled(self) -> None:
        tables = (
            "species",
            "name_assertions",
            "query_definitions",
            "query_associations",
            "api_requests",
            "flickr_photos",
        )
        for table in tables:
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertEqual(self.sql.count("bigint generated always as identity primary key"), 6)

    def test_logical_and_physical_queries_remain_separate(self) -> None:
        self.assertIn("query_definition_pk bigint not null", self.sql)
        self.assertIn("species_pk bigint not null", self.sql)
        self.assertIn("runs_run_id", (ROOT / "supabase/migrations/20260717211043_core_project_run_schema.sql").read_text())
        self.assertIn("api_requests_run_fingerprint_key", self.sql)
        self.assertIn("query_associations_logical_key", self.sql)
        self.assertIn("query_associations_not_label_check", self.sql)

    def test_secrets_rights_and_source_identity_fail_closed(self) -> None:
        self.assertEqual(self.sql.count("no_secrets_check"), 3)
        self.assertIn("flickr_photos_unknown_blocks_use_check", self.sql)
        self.assertIn("flickr_photos_one_current_idx", self.sql)
        self.assertIn("flickr_photos_source_fingerprint_key", self.sql)
        self.assertNotIn("create policy", self.sql.casefold())
        self.assertNotIn("security definer", self.sql.casefold())

    def test_every_foreign_key_access_path_is_indexed(self) -> None:
        for index in (
            "species_project_pk_idx",
            "name_assertions_project_pk_idx",
            "name_assertions_species_pk_idx",
            "query_definitions_project_pk_idx",
            "query_definitions_source_name_assertion_pk_idx",
            "query_associations_query_definition_pk_idx",
            "query_associations_species_pk_idx",
            "query_associations_name_assertion_pk_idx",
            "api_requests_run_pk_requested_at_idx",
            "api_requests_query_definition_pk_idx",
            "api_requests_retry_of_request_pk_idx",
            "flickr_photos_api_request_pk_idx",
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
