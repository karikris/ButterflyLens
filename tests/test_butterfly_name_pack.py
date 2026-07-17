import hashlib
import importlib.util
import json
import sys
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
SCRIPT = ROOT / "scripts/build_butterfly_names.py"


def load_builder():
    specification = importlib.util.spec_from_file_location("butterfly_names", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load name-pack builder")
    module = importlib.util.module_from_spec(specification)
    scripts_path = str(ROOT / "scripts")
    sys.path.insert(0, scripts_path)
    try:
        specification.loader.exec_module(module)
    finally:
        sys.path.remove(scripts_path)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ButterflyNamePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()
        cls.taxa = [
            json.loads(line)
            for line in (PACK / "taxa.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        cls.crosswalk = [
            json.loads(line)
            for line in (PACK / "crosswalk.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        cls.profiles = json.loads(
            (PACK / "sources/ala_species_profiles.json").read_text(encoding="utf-8")
        )
        cls.assertions = [
            json.loads(line)
            for line in (PACK / "name_assertions.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        cls.manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))

    def test_profile_snapshot_covers_only_exact_crosswalk_identifiers(self) -> None:
        expected = [
            (row["butterflylens_key"], row["ala_taxon_id"])
            for row in self.crosswalk
            if row["ala_taxon_id"]
        ]
        observed = [
            (profile["butterflylens_key"], profile["ala_taxon_id"])
            for profile in self.profiles["profiles"]
        ]
        self.assertEqual(observed, expected)
        self.assertEqual(self.profiles["profile_count"], len(observed))
        self.assertEqual(
            self.profiles["input_crosswalk_sha256"], sha256(PACK / "crosswalk.jsonl")
        )

    def test_profile_snapshot_excludes_media_and_occurrence_payloads(self) -> None:
        expected_keys = {
            "taxonConcept",
            "taxonName",
            "classification",
            "synonyms",
            "commonNameSingle",
            "commonNames",
            "variants",
            "linkIdentifier",
        }
        for receipt in self.profiles["profiles"]:
            self.assertEqual(set(receipt["profile"]), expected_keys)
            self.assertRegex(receipt["response_sha256"], r"^[0-9a-f]{64}$")
            serialized = json.dumps(receipt["profile"]).casefold()
            for forbidden in ("occurrenceid", "decimallatitude", "photographer"):
                self.assertNotIn(forbidden, serialized)

    def test_every_taxon_has_one_accepted_scientific_name(self) -> None:
        accepted = [
            assertion
            for assertion in self.assertions
            if assertion["name_type"] == "accepted_scientific"
        ]
        self.assertEqual(len(accepted), len(self.taxa))
        self.assertEqual(
            [(row["butterflylens_key"], row["accepted_scientific_name"]) for row in self.taxa],
            [(row["butterflylens_key"], row["name"]) for row in accepted],
        )

    def test_synonyms_retain_provider_name_identity_and_response_receipt(self) -> None:
        profiles = {
            profile["butterflylens_key"]: profile
            for profile in self.profiles["profiles"]
        }
        synonyms = [
            assertion
            for assertion in self.assertions
            if assertion["name_type"] == "scientific_synonym"
        ]
        self.assertTrue(synonyms)
        for assertion in synonyms:
            profile = profiles[assertion["butterflylens_key"]]
            self.assertEqual(
                assertion["source"]["source_response_sha256"],
                profile["response_sha256"],
            )
            self.assertEqual(
                assertion["source"]["source_version"],
                "sha256:" + sha256(PACK / "sources/ala_species_profiles.json"),
            )
            self.assertIsNotNone(assertion["provider_name_id"])
            self.assertEqual(assertion["trust_tier"], "provider_linked_synonym")
            self.assertEqual(assertion["review_state"], "source_assertion_unreviewed")

    def test_assertions_have_required_governance_fields_and_stable_ids(self) -> None:
        required = {
            "butterflylens_key",
            "name",
            "language",
            "region",
            "source",
            "trust_tier",
            "query_eligibility",
            "homonym_risk",
            "review_state",
            "retrieval_date",
        }
        ids = []
        for assertion in self.assertions:
            self.assertTrue(required.issubset(assertion))
            self.assertEqual(assertion["language"]["code"], "zxx")
            self.assertEqual(assertion["region"]["code"], "AU")
            self.assertEqual(
                assertion["assertion_id"], self.builder.assertion_identifier(assertion)
            )
            ids.append(assertion["assertion_id"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_cross_taxon_collisions_are_not_query_eligible(self) -> None:
        keys_by_name = defaultdict(set)
        for assertion in self.assertions:
            keys_by_name[assertion["normalized_name"]].add(
                assertion["butterflylens_key"]
            )
        for assertion in self.assertions:
            collision = len(keys_by_name[assertion["normalized_name"]]) > 1
            self.assertEqual(
                assertion["homonym_risk"] == "cross_taxon_collision", collision
            )
            self.assertEqual(assertion["query_eligibility"]["eligible"], not collision)

    def test_manifest_fingerprints_and_counts_name_artifacts(self) -> None:
        artifacts = self.manifest["artifacts"]
        profiles = artifacts["sources/ala_species_profiles.json"]
        names = artifacts["name_assertions.jsonl"]
        self.assertEqual(
            profiles["physical_sha256"],
            sha256(PACK / "sources/ala_species_profiles.json"),
        )
        self.assertEqual(
            names["physical_sha256"], sha256(PACK / "name_assertions.jsonl")
        )
        self.assertEqual(names["row_count"], len(self.assertions))
        self.assertEqual(
            names["type_counts"], dict(sorted(Counter(
                assertion["name_type"] for assertion in self.assertions
            ).items()))
        )
        self.assertEqual(self.manifest["name_state"]["scientific_names"], "built")
        self.assertEqual(
            self.manifest["name_state"]["english_vernacular_names"], "not_built"
        )


if __name__ == "__main__":
    unittest.main()
