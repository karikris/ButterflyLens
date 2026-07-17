from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import QueryLaneError, build_global_out_of_range_lane  # noqa: E402


PACK = ROOT / "data/packs/australian_butterflies/v1"


class FlickrGlobalOutOfRangeLaneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.australia_names = [
            json.loads(line) for line in (PACK / "name_assertions.jsonl").read_text().splitlines()
        ]
        cls.pack_manifest = json.loads((PACK / "manifest.json").read_text())
        cls.taxa_sha256 = cls.pack_manifest["artifacts"]["taxa.jsonl"]["physical_sha256"]
        cls.snapshot_sha256 = "a" * 64
        cls.fixture = cls._fixture_assertion(
            assertion_id="global:assertion:1",
            taxon_key="global:taxon:1",
            name="Fixturea externa",
        )

    @classmethod
    def _fixture_assertion(
        cls, *, assertion_id: str, taxon_key: str, name: str
    ) -> dict[str, object]:
        return {
            "assertion_id": assertion_id,
            "butterflylens_key": taxon_key,
            "name": name,
            "normalized_name": name.casefold(),
            "name_type": "accepted_scientific",
            "taxon_rank": "species",
            "language": {"code": "zxx", "label": "Scientific name"},
            "region": {"code": "GLOBAL", "label": "Global authority", "scope": "snapshot"},
            "trust_tier": "accepted_global_authority",
            "homonym_risk": "none_detected_in_snapshot",
            "query_eligibility": {
                "eligible": True,
                "reason": "accepted_unique_global_species_fixture",
            },
            "source": {
                "provider": "Fixture global authority",
                "dataset": "Contract fixture only",
                "snapshot_sha256": cls.snapshot_sha256,
            },
            "australia_scope": {
                "status": "not_currently_known",
                "basis": "authoritative_checklist_complement",
                "comparison_pack_id": cls.pack_manifest["pack_id"],
                "comparison_taxa_sha256": cls.taxa_sha256,
            },
        }

    def _build(self, assertions: list[dict[str, object]]) -> dict[str, object]:
        return build_global_out_of_range_lane(
            assertions,
            self.australia_names,
            source_snapshot_id="fixture-global-snapshot",
            source_snapshot_sha256=self.snapshot_sha256,
            australia_pack_id=self.pack_manifest["pack_id"],
            australia_taxa_sha256=self.taxa_sha256,
        )

    def test_admitted_species_is_tier_five_non_label_and_unsent(self) -> None:
        lane = self._build([self.fixture])
        self.assertEqual(lane["counts"]["definitions_by_tier"], {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1})
        self.assertEqual(lane["counts"]["query_definitions"], 1)
        self.assertEqual(lane["counts"]["physical_requests"], 1)
        self.assertEqual(lane["query_definitions"][0]["tier"], 5)
        self.assertFalse(lane["logical_associations"][0]["query_term_is_taxon_label"])
        self.assertEqual(lane["execution_state"], "planned_not_sent")
        self.assertFalse(lane["scope"]["biological_absence_claimed"])

    def test_ineligible_and_non_out_of_range_rows_are_excluded(self) -> None:
        ineligible = deepcopy(self.fixture)
        ineligible["assertion_id"] = "global:assertion:ineligible"
        ineligible["query_eligibility"] = {"eligible": False, "reason": "weak_fixture"}
        known = deepcopy(self.fixture)
        known["assertion_id"] = "global:assertion:known"
        known["australia_scope"]["status"] = "known_from_australia"
        lane = self._build([ineligible, known])
        self.assertEqual(lane["counts"]["query_definitions"], 0)
        self.assertEqual(lane["counts"]["physical_requests"], 0)

    def test_homonyms_non_species_and_weak_trust_fail_closed(self) -> None:
        mutations = (
            ("homonym_risk", "cross_taxon_collision"),
            ("taxon_rank", "genus"),
            ("trust_tier", "unreviewed_provider_assertion"),
        )
        for field, value in mutations:
            with self.subTest(field=field):
                assertion = deepcopy(self.fixture)
                assertion[field] = value
                with self.assertRaises(QueryLaneError):
                    self._build([assertion])

    def test_australian_name_collision_and_stale_comparison_fail_closed(self) -> None:
        collision = deepcopy(self.fixture)
        australian_species = next(
            row
            for row in self.australia_names
            if row["taxon_rank"] == "species" and row["name_type"] == "accepted_scientific"
        )
        collision["normalized_name"] = australian_species["normalized_name"]
        collision["name"] = australian_species["name"]
        with self.assertRaisesRegex(QueryLaneError, "collides"):
            self._build([collision])
        stale = deepcopy(self.fixture)
        stale["australia_scope"]["comparison_taxa_sha256"] = "b" * 64
        with self.assertRaisesRegex(QueryLaneError, "stale"):
            self._build([stale])

    def test_cross_row_global_homonym_claim_fails_closed(self) -> None:
        collision = self._fixture_assertion(
            assertion_id="global:assertion:collision",
            taxon_key="global:taxon:collision",
            name=str(self.fixture["name"]),
        )
        with self.assertRaisesRegex(QueryLaneError, "homonym collision"):
            self._build([self.fixture, collision])

    def test_replay_is_deterministic_and_status_is_truthful(self) -> None:
        second = self._fixture_assertion(
            assertion_id="global:assertion:2",
            taxon_key="global:taxon:2",
            name="Fixturea remota",
        )
        self.assertEqual(self._build([self.fixture, second]), self._build([second, self.fixture]))
        status = json.loads(
            (ROOT / "packages/flickr/global_out_of_range_status.json").read_text()
        )
        self.assertEqual(status["status"], "blocked_pending_authoritative_global_source")
        self.assertEqual(status["admission"]["admitted_global_species"], 0)
        self.assertEqual(status["admission"]["flickr_calls_made"], 0)


if __name__ == "__main__":
    unittest.main()
