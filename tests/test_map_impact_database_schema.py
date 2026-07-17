from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next((ROOT / "supabase/migrations").glob("*_map_impact_schema.sql"))
DATABASE_TEST = ROOT / "supabase/tests/database/005_map_impact_schema.test.sql"


class MapImpactDatabaseSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_required_map_release_tables_are_append_only_and_rls_enabled(self) -> None:
        for table in ("geographic_impact", "release_candidates"):
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
        self.assertIn(
            "grant select, insert on table public.geographic_impact, public.release_candidates",
            self.sql,
        )
        self.assertEqual(self.sql.count("bigint generated always as identity primary key"), 2)

    def test_rebuilt_ala_baseline_and_submitted_live_identity_are_closed(self) -> None:
        self.assertIn("ala_baseline_authority text not null default 'butterflylens_rebuilt'", self.sql)
        self.assertIn("ala_baseline_authority = 'butterflylens_rebuilt'", self.sql)
        self.assertIn("snapshot_mode in ('submitted', 'live')", self.sql)
        self.assertIn("geographic_impact_mode_heartbeat_check", self.sql)
        self.assertIn("source_commit ~ '^[0-9a-f]{40}$'", self.sql)

    def test_missing_counts_and_flags_cannot_be_fabricated_as_zero_or_false(self) -> None:
        for stem in (
            "ala_count",
            "flickr_count",
            "yoloe_count",
            "bioclip_count",
            "community_count",
            "human_count",
            "release_count",
            "potential_gap",
            "human_additional",
            "release_additional",
        ):
            self.assertIn(f"geographic_impact_{stem}_check", self.sql)
        self.assertIn("'unavailable', 'withheld', 'not_applicable'", self.sql)

    def test_public_geography_has_no_raw_coordinate_columns(self) -> None:
        for forbidden in ("latitude", "longitude", "decimal_latitude", "decimal_longitude"):
            self.assertNotIn(forbidden, self.sql.casefold())
        self.assertIn("source_precision", self.sql)
        self.assertIn("public_cell_id", self.sql)

    def test_release_candidates_are_blocked_until_every_gate_passes(self) -> None:
        for field in (
            "human_supported_identity",
            "qualified_consensus_passed",
            "expert_review_passed",
            "coordinate_valid",
            "date_valid",
            "duplicate_independence_passed",
            "rights_provenance_passed",
            "quality_threshold_passed",
            "no_unresolved_conflict",
            "evidence_packet_complete",
        ):
            self.assertIn(field, self.sql)
        self.assertIn("release_candidates_gate_equivalence_check", self.sql)
        self.assertIn("authorization_role in ('curator', 'administrator')", self.sql)

    def test_every_foreign_key_access_path_is_indexed(self) -> None:
        for index in (
            "geographic_impact_project_pk_idx",
            "geographic_impact_run_pk_idx",
            "geographic_impact_species_pk_idx",
            "geographic_impact_quality_snapshot_pk_idx",
            "geographic_impact_worker_heartbeat_pk_idx",
            "release_candidates_project_pk_idx",
            "release_candidates_run_pk_idx",
            "release_candidates_species_pk_idx",
            "release_candidates_media_object_pk_idx",
            "release_candidates_consensus_pk_idx",
            "release_candidates_quality_snapshot_pk_idx",
            "release_candidates_geographic_impact_pk_idx",
            "release_candidates_supersedes_pk_idx",
            "release_candidates_authorizer_pk_idx",
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
