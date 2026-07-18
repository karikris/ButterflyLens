from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.community import (  # noqa: E402
    ContributorIdentity,
    ContributionEvent,
    ContributorImpactError,
    compile_contributor_impact,
)


MIGRATION = ROOT / "supabase/migrations/20260718052000_contributor_impact_experience.sql"
DATABASE_TEST = ROOT / "supabase/tests/database/017_contributor_impact_experience.test.sql"
NOW = datetime(2026, 7, 18, 5, 30, tzinfo=timezone.utc)


class ContributorImpactExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sql = MIGRATION.read_text(encoding="utf-8")
        cls.database_test = DATABASE_TEST.read_text(encoding="utf-8")

    def test_compiler_counts_unique_effective_evidence_categories(self) -> None:
        events = [
            review("a", media="media:1", species=("species:1",), regions=("ibra:1",), control="c"),
            review("b", media="media:1", species=("species:1", "species:2"), regions=("ibra:2",)),
            replace(review("d", media="media:old"), effective=False),
            resolution("e", conflict="conflict:1", species=("species:2",), regions=("ibra:2",)),
        ]
        result = compile_contributor_impact(events, identity=expert_identity(), calculated_at=NOW)

        self.assertEqual(result["reviewed_image_count"], 1)
        self.assertEqual(result["resolved_conflict_count"], 1)
        self.assertEqual(result["species_helped_count"], 2)
        self.assertEqual(result["region_helped_count"], 2)
        self.assertEqual(result["control_coverage_count"], 1)
        self.assertEqual(result["expert_contribution_count"], 3)
        self.assertEqual(result["source_event_fingerprints"], sorted(("a" * 64, "b" * 64, "e" * 64)))

    def test_nonexpert_has_explicit_not_applicable_expert_state(self) -> None:
        identity = replace(expert_identity(), role="reviewer", qualification_state="unverified")
        result = compile_contributor_impact([review("a")], identity=identity, calculated_at=NOW)
        self.assertEqual(result["expert_contribution_state"], "not_applicable")
        self.assertIsNone(result["expert_contribution_count"])
        self.assertFalse(result["ranking_permitted"])
        self.assertFalse(result["speed_metric_permitted"])
        self.assertFalse(result["scientific_claim_allowed"])

    def test_projection_is_order_stable_and_fingerprint_sensitive(self) -> None:
        events = [review("a"), resolution("b", conflict="conflict:1")]
        first = compile_contributor_impact(events, identity=expert_identity(), calculated_at=NOW)
        second = compile_contributor_impact(list(reversed(events)), identity=expert_identity(), calculated_at=NOW)
        self.assertEqual(first, second)
        changed = compile_contributor_impact([review("a")], identity=expert_identity(), calculated_at=NOW)
        self.assertNotEqual(first["projection_fingerprint"], changed["projection_fingerprint"])

    def test_duplicate_or_malformed_lineage_fails_closed(self) -> None:
        with self.assertRaisesRegex(ContributorImpactError, "duplicate contribution"):
            compile_contributor_impact([review("a"), review("a")], identity=expert_identity(), calculated_at=NOW)
        with self.assertRaisesRegex(ContributorImpactError, "requires a conflict"):
            compile_contributor_impact(
                [replace(review("b"), kind="conflict_resolution")],
                identity=expert_identity(),
                calculated_at=NOW,
            )

    def test_database_is_self_only_append_only_and_has_no_speed_or_rank_value(self) -> None:
        self.assertIn("enable row level security", self.sql)
        self.assertIn("contributor_impact_snapshots_self_read", self.sql)
        self.assertIn("with (security_invoker = true)", self.sql)
        self.assertIn("contributor impact snapshots are append only", self.sql)
        self.assertIn("and not ranking_permitted", self.sql)
        self.assertIn("and not speed_metric_permitted", self.sql)
        self.assertNotRegex(self.sql, r"grant .* to anon")
        self.assertNotIn("security definer", self.sql.casefold())
        for forbidden in ("duration_ms", "reviewer_rank", "reviews_per_hour"):
            self.assertNotIn(forbidden, self.sql)

    def test_pgtap_plan_matches_assertion_count(self) -> None:
        plan = int(re.search(r"select plan\((\d+)\)", self.database_test).group(1))
        assertions = len(re.findall(r"^select (?:has_|col_|ok\(|is\(|throws_ok\()", self.database_test, flags=re.MULTILINE))
        self.assertEqual(assertions, plan)
        self.assertTrue(self.database_test.rstrip().endswith("rollback;"))


def expert_identity() -> ContributorIdentity:
    return ContributorIdentity(
        reviewer_profile_id="reviewer:fixture",
        project_id="project:butterflylens",
        role="expert",
        qualification_state="verified",
    )


def review(
    digest: str,
    *,
    media: str = "media:fixture",
    species: tuple[str, ...] = (),
    regions: tuple[str, ...] = (),
    control: str | None = None,
) -> ContributionEvent:
    return ContributionEvent(
        event_fingerprint=digest * 64,
        kind="review",
        media_object_id=media,
        species_ids=species,
        region_ids=regions,
        control_fingerprint=None if control is None else control * 64,
        expert_eligible=True,
    )


def resolution(
    digest: str,
    *,
    conflict: str,
    species: tuple[str, ...] = (),
    regions: tuple[str, ...] = (),
) -> ContributionEvent:
    return ContributionEvent(
        event_fingerprint=digest * 64,
        kind="conflict_resolution",
        media_object_id="media:conflict",
        species_ids=species,
        region_ids=regions,
        conflict_id=conflict,
        expert_eligible=True,
    )


if __name__ == "__main__":
    unittest.main()
