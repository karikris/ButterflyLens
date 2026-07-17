from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    QueryCompilationError,
    compile_name_assertion,
    compile_name_assertions,
)


NAMES = ROOT / "data/packs/australian_butterflies/v1/name_assertions.jsonl"


class FlickrQueryEligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assertions = [json.loads(line) for line in NAMES.read_text().splitlines()]
        cls.eligible_species = next(
            row
            for row in cls.assertions
            if row["taxon_rank"] == "species"
            and row["name_type"] == "accepted_scientific"
            and row["query_eligibility"]["eligible"]
        )

    def test_every_supported_authoritative_eligible_row_passes_independently(self) -> None:
        supported = {"species", "genus", "family", "order", "superfamily"}
        rows = [
            row
            for row in self.assertions
            if row["taxon_rank"] in supported and row["query_eligibility"]["eligible"]
        ]
        self.assertEqual(len(rows), 1876)
        for row in rows:
            compiled = compile_name_assertion(row)
            self.assertTrue(str(compiled["homonym_risk"]).startswith("none_detected"))
            self.assertNotIn("pending", str(compiled["eligibility_reason"]))

    def test_boolean_flip_cannot_bypass_excluded_homonym_or_weak_term(self) -> None:
        excluded = [row for row in self.assertions if not row["query_eligibility"]["eligible"]]
        risks = {row["homonym_risk"] for row in excluded}
        self.assertEqual(risks, {"cross_taxon_collision", "single_token_vernacular"})
        for risk in risks:
            assertion = deepcopy(next(row for row in excluded if row["homonym_risk"] == risk))
            assertion["query_eligibility"] = {
                "eligible": True,
                "reason": "manually_flipped_without_resolving_risk",
            }
            with self.assertRaisesRegex(QueryCompilationError, "homonym risk"):
                compile_name_assertion(assertion)

    def test_normalization_trust_language_and_reason_are_independent_gates(self) -> None:
        mutations = (
            ("normalized_name", "not the canonical name", "normalized query name"),
            ("trust_tier", "unreviewed_provider_assertion", "trust is insufficient"),
            ("language", {"code": "en", "label": "Wrong"}, "language must be zxx"),
            (
                "query_eligibility",
                {"eligible": True, "reason": "excluded_but_boolean_true"},
                "contradictory",
            ),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                assertion = deepcopy(self.eligible_species)
                assertion[field] = value
                with self.assertRaisesRegex(QueryCompilationError, message):
                    compile_name_assertion(assertion)

    def test_cross_taxon_collision_is_recomputed_across_compilation_batch(self) -> None:
        second = deepcopy(self.eligible_species)
        second["assertion_id"] = "blna:v1:eligibility-collision-fixture"
        second["butterflylens_key"] = "bltx:v1:eligibility-collision-fixture"
        with self.assertRaisesRegex(QueryCompilationError, "multiple taxa"):
            compile_name_assertions([self.eligible_species, second])

    def test_same_taxon_duplicate_term_keeps_both_logical_definitions(self) -> None:
        second = deepcopy(self.eligible_species)
        second["assertion_id"] = "blna:v1:same-taxon-duplicate-fixture"
        definitions = compile_name_assertions([self.eligible_species, second])
        self.assertEqual(len(definitions), 2)
        self.assertEqual(len({row["source_taxon_key"] for row in definitions}), 1)
        self.assertEqual(len({row["normalized_query_text"] for row in definitions}), 1)


if __name__ == "__main__":
    unittest.main()
