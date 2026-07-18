from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "apps/web/src/species/submittedSpeciesCatalogue.json"


def load_builder():
    path = ROOT / "scripts/build_species_catalogue.py"
    specification = importlib.util.spec_from_file_location("species_catalogue", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load species catalogue builder")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


BUILDER = load_builder()


class SpeciesCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalogue = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))

    def test_checked_in_projection_fingerprint_is_valid(self) -> None:
        fingerprinted = dict(self.catalogue)
        fingerprint = fingerprinted.pop("catalogueFingerprint")
        self.assertEqual(
            fingerprint,
            "sha256:"
            + hashlib.sha256(BUILDER.canonical_json(fingerprinted)).hexdigest(),
        )

    @unittest.skipUnless(
        importlib.util.find_spec("pyarrow"),
        "project PyArrow environment is required for deterministic rebuild",
    )
    def test_checked_in_projection_is_deterministic_from_frozen_sources(self) -> None:
        operations = json.loads(
            (ROOT / "apps/web/src/operations/submittedOperationsSnapshot.json").read_text(
                encoding="utf-8"
            )
        )
        source_commit = operations["submittedSnapshot"]["sourceCommit"]
        with tempfile.TemporaryDirectory() as temporary_directory:
            frozen_rights = Path(temporary_directory) / "data_rights_manifest.json"
            frozen_rights.write_bytes(
                subprocess.run(
                    [
                        "git",
                        "show",
                        f"{source_commit}:provenance/data_rights_manifest.json",
                    ],
                    cwd=ROOT,
                    check=True,
                    capture_output=True,
                ).stdout
            )
            self.assertEqual(
                BUILDER.sha256_file(frozen_rights),
                self.catalogue["sourceFingerprints"]["dataRightsManifest"],
            )
            rebuilt = BUILDER.build_catalogue(
                rights_path=frozen_rights,
                generated_at=self.catalogue["generatedAt"],
            )
        self.assertEqual(rebuilt, self.catalogue)

    def test_rebuilt_baseline_contains_all_accepted_species_once(self) -> None:
        self.assertEqual(
            self.catalogue["authoritativeBaseline"],
            "ButterflyLens rebuilt baseline",
        )
        self.assertEqual(self.catalogue["speciesCount"], 463)
        species = self.catalogue["species"]
        self.assertEqual(len(species), 463)
        self.assertEqual(len({row["key"] for row in species}), 463)
        self.assertEqual(len({row["slug"] for row in species}), 463)
        self.assertTrue(
            all(
                "family" in row["hierarchy"] and "genus" in row["hierarchy"]
                for row in species
            )
        )

    def test_provider_identifiers_and_names_remain_conservative(self) -> None:
        for species in self.catalogue["species"]:
            for provider in species["crosswalk"]["providers"]:
                self.assertEqual(
                    provider["identifier"] is not None,
                    provider["state"] == "matched",
                )
            self.assertTrue(
                all(
                    name["reviewState"] == "source_assertion_unreviewed"
                    for name in species["englishNames"]
                )
            )
            self.assertNotIn("firstNationsNames", species)

    def test_unreleased_evidence_and_unfinished_models_are_not_claims(self) -> None:
        states = self.catalogue["states"]
        self.assertEqual(states["firstNationsNames"], "empty_no_authorized_source")
        self.assertEqual(
            states["alaOccurrenceEvidence"],
            "withheld_pending_dataset_rights_resolution",
        )
        self.assertFalse(states["scientificClaimAllowed"])
        self.assertEqual(states["yoloe"], "unfinished")
        self.assertEqual(states["bioclip"], "unfinished")

        ala = self.catalogue["alaOccurrenceBoundary"]
        self.assertIsNone(ala["displayedOccurrenceCount"])
        self.assertFalse(ala["absenceInferencePermitted"])
        self.assertEqual(
            set(ala["rightsReviewRequiredDatasetUids"]),
            {"dr1097", "dr30019", "dr635"},
        )

        reference = self.catalogue["referenceBoundary"]
        self.assertEqual(reference["humanVerifiedCount"], 0)
        self.assertFalse(reference["qualityScoreComputed"])
        self.assertFalse(reference["releaseReady"])
        self.assertTrue(
            all(
                species["referenceCoverage"]["humanVerifiedCount"] == 0
                for species in self.catalogue["species"]
            )
        )


if __name__ == "__main__":
    unittest.main()
