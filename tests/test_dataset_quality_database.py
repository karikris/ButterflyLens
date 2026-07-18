from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = next(
    (ROOT / "supabase/migrations").glob("*_dataset_quality_estimates.sql")
)
DATABASE_TEST = ROOT / "supabase/tests/database/015_dataset_quality_estimates.test.sql"


class DatasetQualityDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_sampling_design_uncertainty_and_group_fields_are_persisted(self) -> None:
        for field in (
            "sampling_plan_id",
            "audit_evidence_fingerprint",
            "sampling_design",
            "representative",
            "blind",
            "confidence_level",
            "interval_method",
            "bootstrap_replicates",
            "bootstrap_seed_fingerprint",
            "resampling_group_count",
            "population_estimate_allowed",
            "estimate_payload",
        ):
            self.assertIn(f"add column {field}", self.sql)

    def test_targeted_queue_is_structurally_denied_population_estimates(self) -> None:
        self.assertIn("targeted failure discovery cannot become a population estimate", self.sql)
        self.assertIn("new.snapshot_kind = 'targeted_failure_discovery'", self.sql)
        for field in (
            "new.precision_estimate is not null",
            "new.effective_sample_size is not null",
            "new.population_estimate_allowed",
        ):
            self.assertIn(field, self.sql)

    def test_representative_estimate_requires_probability_and_group_evidence(self) -> None:
        for fragment in (
            "hajek_inverse_inclusion_probability_v1",
            "stratified_owner_observation_group_bootstrap_v1",
            "new.confidence_level is distinct from 0.95",
            "new.resampling_group_count < 2",
            "'grouping_keys' ? 'owner_id'",
            "'grouping_keys' ? 'observation_id'",
            "jsonb_array_length(new.estimate_payload -> 'sampling_strata')",
        ):
            self.assertIn(fragment, self.sql)

    def test_model_votes_and_scientific_claims_are_denied(self) -> None:
        self.assertIn("'model_vote_included'", self.sql)
        self.assertIn("'scientific_claim_allowed'", self.sql)
        self.assertIn("is distinct from 'false'::jsonb", self.sql)

    def test_snapshots_are_append_only_serialized_and_monotonic(self) -> None:
        self.assertIn("pg_advisory_xact_lock", self.sql)
        self.assertIn("new.snapshot_revision := previous_snapshot.snapshot_revision + 1", self.sql)
        self.assertIn("new.supersedes_quality_snapshot_pk := previous_snapshot.id", self.sql)
        self.assertIn("quality snapshots are append only", self.sql)
        self.assertIn("quality_snapshots_plan_revision_key", self.sql)

    def test_security_definer_helpers_are_fixed_path_and_revoked(self) -> None:
        self.assertEqual(self.sql.count("security definer\nset search_path = ''"), 2)
        self.assertIn("from public, anon, authenticated", self.sql)

    def test_existing_fixtures_use_the_separate_targeted_lane(self) -> None:
        for name in ("004_review_schema.test.sql", "005_map_impact_schema.test.sql"):
            fixture = (ROOT / "supabase/tests/database" / name).read_text(encoding="utf-8")
            self.assertIn("butterflylens-dataset-quality-estimator:v1.0.0", fixture)
            self.assertIn("targeted_failure_discovery", fixture)
            self.assertIn("population_estimate_allowed', false", fixture)

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
