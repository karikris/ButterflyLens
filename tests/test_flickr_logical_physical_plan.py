from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    QueryPlanError,
    build_logical_query_association,
    compile_name_assertion,
    plan_physical_query_requests,
)


NAMES = ROOT / "data/packs/australian_butterflies/v1/name_assertions.jsonl"


class FlickrLogicalPhysicalPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        assertions = [json.loads(line) for line in NAMES.read_text().splitlines()]
        source = next(
            row
            for row in assertions
            if row["query_eligibility"]["eligible"] and row["taxon_rank"] == "species"
        )
        duplicate_term = deepcopy(source)
        duplicate_term["assertion_id"] = "blna:v1:physical-dedup-fixture"
        duplicate_term["butterflylens_key"] = "bltx:v1:physical-dedup-fixture"
        cls.definitions = (
            compile_name_assertion(source),
            compile_name_assertion(duplicate_term),
        )
        cls.associations = tuple(
            build_logical_query_association(
                definition,
                associated_taxon_key=str(definition["source_taxon_key"]),
                relationship="accepted_name",
                query_lane="australia-known",
                association_reason="authoritative accepted species name fixture",
            )
            for definition in cls.definitions
        )

    def test_physical_requests_deduplicate_while_logical_associations_survive(self) -> None:
        plan = plan_physical_query_requests(
            self.definitions,
            self.associations,
            fixed_parameters={"safe_search": 1, "media": "photos"},
        )
        self.assertEqual(len(plan["physical_requests"]), 1)
        self.assertEqual(len(plan["logical_associations"]), 2)
        self.assertEqual(len(plan["request_links"]), 2)
        self.assertEqual(
            {link["logical_query_association_id"] for link in plan["request_links"]},
            {row["logical_query_association_id"] for row in self.associations},
        )

    def test_identity_is_deterministic_and_independent_of_input_order(self) -> None:
        first = plan_physical_query_requests(self.definitions, self.associations)
        second = plan_physical_query_requests(
            reversed(self.definitions), reversed(self.associations)
        )
        self.assertEqual(first, second)

    def test_parameter_changes_create_distinct_physical_identity(self) -> None:
        first = plan_physical_query_requests(
            self.definitions, self.associations, fixed_parameters={"safe_search": 1}
        )
        second = plan_physical_query_requests(
            self.definitions, self.associations, fixed_parameters={"safe_search": 3}
        )
        self.assertNotEqual(
            first["physical_requests"][0]["request_fingerprint"],
            second["physical_requests"][0]["request_fingerprint"],
        )

    def test_secrets_and_query_overrides_fail_closed(self) -> None:
        for parameters in ({"api_key": "forbidden"}, {"text": "override"}, {"method": "x"}):
            with self.subTest(parameters=parameters):
                with self.assertRaises(QueryPlanError):
                    plan_physical_query_requests(
                        self.definitions, self.associations, fixed_parameters=parameters
                    )

    def test_tampered_association_and_unknown_definition_fail_closed(self) -> None:
        tampered = deepcopy(self.associations[0])
        tampered["associated_taxon_key"] = "bltx:v1:tampered"
        with self.assertRaisesRegex(QueryPlanError, "fingerprint mismatch"):
            plan_physical_query_requests(self.definitions, [tampered])
        with self.assertRaisesRegex(QueryPlanError, "unknown definition"):
            plan_physical_query_requests(self.definitions[:1], [self.associations[1]])

    def test_outputs_are_explicitly_unsent_and_never_labels(self) -> None:
        plan = plan_physical_query_requests(self.definitions, self.associations)
        self.assertEqual(plan["physical_requests"][0]["execution_state"], "planned_not_sent")
        self.assertTrue(
            all(
                association["query_term_is_taxon_label"] is False
                for association in plan["logical_associations"]
            )
        )


if __name__ == "__main__":
    unittest.main()
