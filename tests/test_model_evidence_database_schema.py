from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_model_evidence_schema.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/003_model_evidence_schema.test.sql"


class ModelEvidenceDatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_required_model_and_worker_tables_are_closed_and_rls_enabled(self) -> None:
        tables = (
            "media_objects",
            "duplicate_groups",
            "duplicate_group_members",
            "pipeline_stages",
            "worker_leases",
            "worker_heartbeats",
            "model_evidence",
        )
        for table in tables:
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertEqual(self.sql.count("bigint generated always as identity primary key"), 7)

    def test_media_rights_content_and_storage_fail_closed(self) -> None:
        self.assertIn("media_objects_content_shape_check", self.sql)
        self.assertIn("media_objects_rights_gate_check", self.sql)
        self.assertIn("media_objects_storage_key_check", self.sql)
        self.assertIn("media_objects_fingerprint_key", self.sql)
        self.assertIn("duplicate_group_members_pair_key", self.sql)

    def test_worker_leases_are_fenced_and_heartbeats_append_only(self) -> None:
        self.assertIn("lease_revision bigint not null", self.sql)
        self.assertIn("fencing_token_sha256 text not null", self.sql)
        self.assertIn("worker_leases_one_current_idx", self.sql)
        self.assertIn("worker_heartbeats_fingerprint_key", self.sql)
        self.assertNotIn("fencing_token text", self.sql)
        self.assertIn(
            "public.duplicate_group_members, public.worker_heartbeats, public.model_evidence\n"
            "to service_role",
            self.sql,
        )

    def test_model_outputs_cannot_be_fabricated_from_unfinished_state(self) -> None:
        self.assertIn("'blocked', 'skipped_unfinished'", self.sql)
        self.assertIn("model_evidence_completed_shape_check", self.sql)
        self.assertIn("model_evidence_unfinished_shape_check", self.sql)
        self.assertIn("calibrator_fingerprint", self.sql)
        self.assertIn("this migration performs no model execution", self.sql.casefold())

    def test_every_foreign_key_access_path_is_indexed(self) -> None:
        for index in (
            "media_objects_project_pk_idx",
            "media_objects_run_pk_idx",
            "media_objects_flickr_photo_pk_idx",
            "media_objects_parent_media_pk_idx",
            "duplicate_groups_project_pk_idx",
            "duplicate_groups_run_pk_idx",
            "duplicate_groups_representative_media_pk_idx",
            "duplicate_group_members_group_pk_idx",
            "duplicate_group_members_media_pk_idx",
            "pipeline_stages_run_pk_idx",
            "worker_leases_pipeline_stage_pk_idx",
            "worker_heartbeats_worker_lease_pk_idx",
            "worker_heartbeats_pipeline_stage_pk_idx",
            "model_evidence_pipeline_stage_pk_idx",
            "model_evidence_media_object_pk_idx",
            "model_evidence_species_pk_idx",
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
