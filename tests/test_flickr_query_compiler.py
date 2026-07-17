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


class FlickrQueryCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assertions = [json.loads(line) for line in NAMES.read_text().splitlines()]
        cls.eligible = [
            row for row in cls.assertions
            if row["query_eligibility"]["eligible"] and row["taxon_rank"] in {
                "species", "genus", "family", "order", "superfamily"
            }
        ]

    def test_authoritative_pack_compiles_deterministically(self) -> None:
        first = compile_name_assertions(self.eligible)
        second = compile_name_assertions(list(reversed(self.eligible)))
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(self.eligible))
        self.assertEqual(len({row["query_definition_id"] for row in first}), len(first))

    def test_tiers_sources_trust_and_non_label_semantics_are_retained(self) -> None:
        compiled = compile_name_assertions(self.eligible)
        expected = {"species": 1, "genus": 2, "family": 3, "superfamily": 4}
        for row in compiled:
            self.assertEqual(row["tier"], expected[row["taxon_rank"]])
            self.assertTrue(row["source_assertion_id"].startswith("blna:v1:"))
            self.assertTrue(row["source_taxon_key"].startswith("bltx:v1:"))
            self.assertIn("provider", row["source"])
            self.assertIn("trust_tier", row)
            self.assertEqual(
                row["term_semantics"], "discovery_term_only_not_a_taxon_label"
            )

    def test_ineligible_homonymous_and_unsupported_rank_fail_closed(self) -> None:
        ineligible = next(
            row for row in self.assertions if not row["query_eligibility"]["eligible"]
        )
        with self.assertRaisesRegex(QueryCompilationError, "not query eligible"):
            compile_name_assertion(ineligible)
        unsupported = deepcopy(self.eligible[0])
        unsupported["taxon_rank"] = "subspecies"
        with self.assertRaisesRegex(QueryCompilationError, "no declared query tier"):
            compile_name_assertion(unsupported)

    def test_first_nations_names_require_separate_authorized_adapter(self) -> None:
        assertion = deepcopy(self.eligible[0])
        assertion["name_type"] = "first_nations_language"
        assertion["language"] = {"code": "x-community", "label": "Fixture only"}
        with self.assertRaisesRegex(QueryCompilationError, "authorized scoped"):
            compile_name_assertion(assertion)
        approvals = ROOT / "data/packs/australian_butterflies/v1/first_nations_name_decisions.jsonl"
        self.assertEqual(approvals.read_text(encoding="utf-8"), "")

    def test_compiler_performs_no_physical_request_or_label_assignment(self) -> None:
        docs = (ROOT / "packages/flickr/QUERY_PLANNER.md").read_text()
        self.assertIn("does not call Flickr", docs)
        self.assertIn("not a taxonomic or image label", docs)
        self.assertIn("Physical request deduplication is a separate step", docs)


if __name__ == "__main__":
    unittest.main()
