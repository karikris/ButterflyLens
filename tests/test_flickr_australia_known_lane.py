from __future__ import annotations

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import QueryLaneError, build_australia_known_lane  # noqa: E402


PACK = ROOT / "data/packs/australian_butterflies/v1"


class FlickrAustraliaKnownLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.taxa = [json.loads(line) for line in (PACK / "taxa.jsonl").read_text().splitlines()]
        cls.assertions = [
            json.loads(line) for line in (PACK / "name_assertions.jsonl").read_text().splitlines()
        ]
        manifest = json.loads((PACK / "manifest.json").read_text())
        cls.lane = build_australia_known_lane(
            cls.taxa,
            cls.assertions,
            source_pack_id=manifest["pack_id"],
            source_taxa_sha256=manifest["artifacts"]["taxa.jsonl"]["physical_sha256"],
            source_name_assertions_sha256=manifest["artifacts"]["name_assertions.jsonl"][
                "physical_sha256"
            ],
        )

    def test_authoritative_pack_counts_and_tiers_are_exact(self) -> None:
        self.assertEqual(self.lane["counts"]["accepted_species"], 463)
        self.assertEqual(self.lane["counts"]["query_definitions"], 1876)
        self.assertEqual(
            self.lane["counts"]["definitions_by_tier"],
            {"1": 1409, "2": 458, "3": 7, "4": 2, "5": 0},
        )
        self.assertEqual(self.lane["counts"]["logical_associations"], 4997)
        self.assertEqual(self.lane["counts"]["physical_requests"], 1754)
        self.assertEqual(self.lane["counts"]["request_links"], 4997)
        self.assertEqual(
            self.lane["counts"]["associations_by_tier"],
            {"1": 1409, "2": 2069, "3": 593, "4": 926, "5": 0},
        )

    def test_every_association_targets_an_accepted_species(self) -> None:
        accepted_species = {
            row["butterflylens_key"]
            for row in self.taxa
            if row["rank"] == "species" and row["taxonomic_status"] == "accepted"
        }
        observed = {
            row["associated_taxon_key"] for row in self.lane["logical_associations"]
        }
        self.assertEqual(observed, accepted_species)
        self.assertTrue(
            all(row["query_term_is_taxon_label"] is False for row in self.lane["logical_associations"])
        )

    def test_broader_terms_expand_to_authoritative_descendants(self) -> None:
        species_by_ancestor: Counter[str] = Counter()
        for taxon in self.taxa:
            if taxon["rank"] != "species":
                continue
            for ancestor in taxon["parent_path"]:
                species_by_ancestor[ancestor["butterflylens_key"]] += 1
        associations_by_definition = Counter(
            row["query_definition_id"] for row in self.lane["logical_associations"]
        )
        for definition in self.lane["query_definitions"]:
            expected = (
                1
                if definition["taxon_rank"] == "species"
                else species_by_ancestor[definition["source_taxon_key"]]
            )
            self.assertEqual(associations_by_definition[definition["query_definition_id"]], expected)

    def test_scope_does_not_claim_photo_geography_or_absence(self) -> None:
        self.assertEqual(self.lane["lane_id"], "australia_known")
        self.assertFalse(self.lane["scope"]["photo_location_filter_implied"])
        self.assertFalse(self.lane["scope"]["absence_inference_permitted"])
        self.assertEqual(self.lane["execution_state"], "planned_not_sent")
        self.assertTrue(
            all(row["execution_state"] == "planned_not_sent" for row in self.lane["physical_requests"])
        )

    def test_rebuild_is_deterministic(self) -> None:
        source = self.lane["source_pack"]
        replay = build_australia_known_lane(
            reversed(self.taxa),
            reversed(self.assertions),
            source_pack_id=source["pack_id"],
            source_taxa_sha256=source["taxa_sha256"],
            source_name_assertions_sha256=source["name_assertions_sha256"],
        )
        self.assertEqual(replay, self.lane)

    def test_missing_hierarchy_and_non_authoritative_taxa_fail_closed(self) -> None:
        missing_parent = deepcopy(self.taxa)
        missing_parent.pop(0)
        source = self.lane["source_pack"]
        with self.assertRaisesRegex(QueryLaneError, "ancestor|parent"):
            build_australia_known_lane(
                missing_parent,
                self.assertions,
                source_pack_id=source["pack_id"],
                source_taxa_sha256=source["taxa_sha256"],
                source_name_assertions_sha256=source["name_assertions_sha256"],
            )
        non_authoritative = deepcopy(self.taxa)
        non_authoritative[0]["taxonomic_status"] = "provisional"
        with self.assertRaisesRegex(QueryLaneError, "authoritative"):
            build_australia_known_lane(
                non_authoritative,
                self.assertions,
                source_pack_id=source["pack_id"],
                source_taxa_sha256=source["taxa_sha256"],
                source_name_assertions_sha256=source["name_assertions_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
