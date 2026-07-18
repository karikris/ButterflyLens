from __future__ import annotations

import json
from pathlib import Path
import unittest

from butterflylens.contracts.sensitive_locations import (
    ProviderLocationConstraint,
    PublicLocationRequest,
    SensitiveLocationRule,
    plan_public_location,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase/migrations/20260718100000_sensitive_location_controls.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/021_sensitive_location_controls.test.sql"
POLICY = ROOT / "SENSITIVE_LOCATIONS.md"
ALA = ROOT / "data/packs/australian_butterflies/v1/ala"
FP = "a" * 64


def ala_constraint(*, ceiling: int = 3, disclosure: str = "public_generalised"):
    return ProviderLocationConstraint(
        provider="ala",
        disclosure_state=disclosure,
        location_used_for_target=True,
        maximum_public_h3_resolution=ceiling,
        provider_precision="ALA public processed generalisation",
        flickr_accuracy=None,
        resolution_mapping_version="ala-baseline-coarse-h3:v1",
        source_snapshot_fingerprint="1" * 64,
        permission_evidence_fingerprint="2" * 64,
    )


def flickr_constraint(*, ceiling: int = 5):
    return ProviderLocationConstraint(
        provider="flickr",
        disclosure_state="public_geo",
        location_used_for_target=True,
        maximum_public_h3_resolution=ceiling,
        provider_precision="Flickr accuracy 6",
        flickr_accuracy=6,
        resolution_mapping_version="flickr-accuracy-to-h3:reviewed-v1",
        source_snapshot_fingerprint="3" * 64,
        permission_evidence_fingerprint="4" * 64,
    )


def rule(*, sensitivity: str = "sensitive", ceiling: int = 3):
    return SensitiveLocationRule(
        sensitivity_state=sensitivity,
        action="generalise" if sensitivity == "sensitive" else "provider_resolution",
        maximum_public_h3_resolution=ceiling,
        allowed_scope_kinds=("australia", "h3", "state_territory"),
        minimum_public_record_count=2,
        policy_evidence_fingerprint=FP,
    )


def request(*, resolution: int = 3, precision: str = "generalised", count: int = 2):
    return PublicLocationRequest(
        scope_kind="h3",
        scope_id=f"h3:{resolution}:83be635ffffffff",
        h3_resolution=resolution,
        h3_cell="83be635ffffffff",
        source_precision=precision,
        record_count=count,
    )


class SensitiveLocationPlannerTests(unittest.TestCase):
    def test_authoritative_ala_generalisation_allows_only_the_coarse_cell(self) -> None:
        coarse = plan_public_location(
            rule=rule(), request=request(), constraints=[ala_constraint()]
        )
        local = plan_public_location(
            rule=rule(ceiling=7),
            request=request(resolution=7),
            constraints=[ala_constraint()],
        )
        self.assertEqual(coarse.publication_state, "generalised")
        self.assertEqual(coarse.h3_resolution, 3)
        self.assertEqual(local.publication_state, "withheld")
        self.assertIn("requested_h3_resolution_exceeds_ceiling", local.blocker_codes)
        self.assertIsNone(local.h3_cell)

    def test_strictest_provider_ceiling_wins(self) -> None:
        decision = plan_public_location(
            rule=rule(sensitivity="not_sensitive", ceiling=7),
            request=request(resolution=3, precision="coarse_rollup"),
            constraints=[ala_constraint(ceiling=5, disclosure="public_processed"), flickr_constraint(ceiling=3)],
            required_providers=("ala", "flickr"),
        )
        self.assertEqual(decision.effective_maximum_h3_resolution, 3)
        self.assertEqual(decision.publication_state, "generalised")

    def test_nonpublic_flickr_location_cannot_be_used(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-public provider location"):
            ProviderLocationConstraint(
                provider="flickr",
                disclosure_state="nonpublic_geo",
                location_used_for_target=True,
                maximum_public_h3_resolution=3,
                provider_precision="private",
                flickr_accuracy=None,
                resolution_mapping_version="mapping:v1",
                source_snapshot_fingerprint="3" * 64,
                permission_evidence_fingerprint="4" * 64,
            )

    def test_flickr_accuracy_never_implies_an_h3_mapping(self) -> None:
        with self.assertRaisesRegex(ValueError, "versioned resolution mapping"):
            ProviderLocationConstraint(
                provider="flickr",
                disclosure_state="public_geo",
                location_used_for_target=True,
                maximum_public_h3_resolution=3,
                provider_precision="Flickr accuracy 6",
                flickr_accuracy=6,
                resolution_mapping_version=None,
                source_snapshot_fingerprint="3" * 64,
                permission_evidence_fingerprint="4" * 64,
            )

    def test_unknown_sensitivity_and_exact_sensitive_source_fail_closed(self) -> None:
        unknown = SensitiveLocationRule(
            sensitivity_state="unknown",
            action="withhold",
            maximum_public_h3_resolution=None,
            allowed_scope_kinds=(),
            minimum_public_record_count=None,
            policy_evidence_fingerprint=FP,
        )
        unknown_decision = plan_public_location(
            rule=unknown, request=request(), constraints=[ala_constraint()]
        )
        exact_decision = plan_public_location(
            rule=rule(),
            request=request(precision="exact"),
            constraints=[ala_constraint()],
        )
        self.assertEqual(unknown_decision.publication_state, "withheld")
        self.assertEqual(exact_decision.publication_state, "withheld")
        self.assertIn("sensitive_exact_location_forbidden", exact_decision.blocker_codes)

    def test_missing_provider_and_small_aggregate_fail_closed(self) -> None:
        decision = plan_public_location(
            rule=rule(),
            request=request(count=1),
            constraints=[ala_constraint()],
            required_providers=("ala", "flickr"),
        )
        self.assertEqual(decision.publication_state, "withheld")
        self.assertIn("missing_flickr_provider_constraint", decision.blocker_codes)
        self.assertIn("minimum_public_record_count_not_met", decision.blocker_codes)

    def test_decision_fingerprint_is_order_independent_and_has_no_raw_coordinates(self) -> None:
        constraints = [ala_constraint(ceiling=5, disclosure="public_processed"), flickr_constraint(ceiling=3)]
        forward = plan_public_location(
            rule=rule(sensitivity="not_sensitive", ceiling=7),
            request=request(resolution=3, precision="coarse_rollup"),
            constraints=constraints,
            required_providers=("ala", "flickr"),
        )
        reverse = plan_public_location(
            rule=rule(sensitivity="not_sensitive", ceiling=7),
            request=request(resolution=3, precision="coarse_rollup"),
            constraints=list(reversed(constraints)),
            required_providers=("flickr", "ala"),
        )
        self.assertEqual(forward.decision_fingerprint, reverse.decision_fingerprint)
        payload = json.dumps(forward.as_dict(), sort_keys=True)
        self.assertNotIn("latitude", payload.casefold())
        self.assertNotIn("longitude", payload.casefold())

    def test_rebuilt_ala_baseline_proves_generalised_rows_are_coarse_only(self) -> None:
        manifest = json.loads((ALA / "ala_aggregation_manifest.json").read_text())
        observed = manifest["counts"]["scope_publicly_generalised_memberships"]
        self.assertEqual(observed["australia"], 375)
        self.assertEqual(observed["state_territory"], 375)
        self.assertEqual(observed["h3_coarse"], 375)
        for scope in ("ibra_region", "lga_2023_statistical_approximation", "h3_regional", "h3_local"):
            self.assertEqual(observed[scope], 0)


class SensitiveLocationDatabaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")
        cls.policy = POLICY.read_text(encoding="utf-8")

    def test_public_rls_requires_a_matching_publishable_receipt(self) -> None:
        self.assertIn("drop policy geographic_impact_public_read", self.sql)
        self.assertIn("drop policy release_candidates_public_read", self.sql)
        self.assertGreaterEqual(self.sql.count("private.has_publishable_location_receipt("), 3)
        self.assertIn("receipt.publication_state in ('publish', 'generalised')", self.sql)
        self.assertIn("used provider location does not belong to the target snapshot", self.sql)

    def test_ledgers_are_append_only_service_written_and_coordinate_free(self) -> None:
        for table in ("location_source_constraints", "location_publication_receipts"):
            self.assertIn(f"create table public.{table}", self.sql)
            self.assertIn(f"alter table public.{table} enable row level security", self.sql)
            definition = self.sql.split(f"create table public.{table}", 1)[1].split(");", 1)[0]
            self.assertNotRegex(
                definition.casefold(),
                r"\b(decimal_)?latitude\b|\b(decimal_)?longitude\b",
            )
        self.assertIn("to service_role", self.sql)
        self.assertNotIn("grant insert on table public.location", self.sql)
        self.assertIn(
            "publication_state = 'publish' and sensitivity_state = 'not_sensitive'",
            self.sql,
        )

    def test_policy_preserves_provider_and_scientific_boundaries(self) -> None:
        normalized_policy = " ".join(self.policy.split())
        for phrase in (
            "ALA public processed coordinates",
            "Flickr geo permissions",
            "No accuracy-to-H3 guess",
            "Unknown means withheld",
            "not evidence of biological absence",
        ):
            self.assertIn(phrase, normalized_policy)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        import re

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
