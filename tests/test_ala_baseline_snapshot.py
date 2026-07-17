from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_ala_baseline.py"
PACK = ROOT / "data/packs/australian_butterflies/v1"
ALA = PACK / "ala"


def load_builder():
    specification = importlib.util.spec_from_file_location("ala_baseline", SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load ALA baseline builder")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


class AlaBaselinePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()

    def test_public_query_is_explicit_and_rights_safe(self) -> None:
        parameters = self.builder.public_request_parameters()
        query = [value for key, value in parameters if key == "q"]
        filters = [value for key, value in parameters if key == "fq"]
        self.assertEqual(query, [f"lsid:{self.builder.ALA_ROOT_TAXON_ID}"])
        self.assertEqual(filters, list(self.builder.FILTER_QUERIES))
        self.assertIn("country:Australia", filters)
        self.assertIn(self.builder.LICENCE_FILTER, filters)
        self.assertNotIn("CC-BY-NC", self.builder.ALLOWED_PUBLIC_LICENCES)
        self.assertNotIn("CC-BY-ND 4.0 (Int)", self.builder.ALLOWED_PUBLIC_LICENCES)
        self.assertNotIn("CC-BY-SA 4.0 (Int)", self.builder.ALLOWED_PUBLIC_LICENCES)
        self.assertIn(("disableAllQualityFilters", "true"), parameters)
        self.assertIn(("mintDoi", "false"), parameters)
        self.assertIn(("emailNotify", "false"), parameters)
        self.assertNotIn("email", {key for key, _ in parameters})

    def test_required_evidence_and_context_fields_are_requested(self) -> None:
        required = {
            "id",
            "occurrenceID",
            "taxonConceptID",
            "dataProviderUid",
            "dataResourceUid",
            "decimalLatitude",
            "decimalLongitude",
            "coordinateUncertaintyInMeters",
            "eventDate",
            "basisOfRecord",
            "license",
            "sensitive",
            "spatiallyValid",
            "assertions",
        }
        self.assertTrue(required.issubset(self.builder.DOWNLOAD_FIELDS))
        self.assertEqual(
            self.builder.EXTRA_FIELDS,
            (self.builder.IBRA_FIELD, self.builder.LGA_FIELD),
        )

    def test_checked_in_snapshot_receipt(self) -> None:
        if not (ALA / "ala_snapshot_receipt.json").exists():
            self.skipTest("frozen archive is added by the acquisition step")
        receipt = json.loads(
            (ALA / "ala_snapshot_receipt.json").read_text(encoding="utf-8")
        )
        archive = ALA / receipt["download"]["archive_path"]
        attribution = json.loads(
            (ALA / "ala_attribution.json").read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["schema_version"], self.builder.SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(receipt["taxon_scope"]["ala_taxon_id"], self.builder.ALA_ROOT_TAXON_ID)
        self.assertEqual(receipt["download"]["archive_sha256"], self.builder.sha256_file(archive))
        self.assertEqual(
            receipt["download"]["row_count"],
            receipt["download"]["expected_record_count"],
        )
        self.assertEqual(attribution["snapshot_id"], receipt["snapshot_id"])
        self.assertIsNone(attribution["doi"])
        self.assertFalse(receipt["query_policy"]["contact_email_persisted"])
        self.assertFalse(receipt["query_policy"]["doi_minted"])
        public_parameters = self.builder.public_request_parameters()
        self.assertEqual(
            receipt["query_policy"]["public_request_fingerprint"],
            self.builder.sha256_bytes(self.builder.canonical_json(public_parameters)),
        )
        crosswalk = ROOT / receipt["taxon_scope"]["input_crosswalk_path"]
        expected_snapshot_fingerprint = self.builder.sha256_bytes(
            self.builder.canonical_json(
                {
                    "endpoint": self.builder.ALA_DOWNLOAD_ENDPOINT,
                    "parameters": public_parameters,
                    "archive_sha256": receipt["download"]["archive_sha256"],
                    "crosswalk_sha256": self.builder.sha256_file(crosswalk),
                }
            )
        )
        self.assertEqual(receipt["snapshot_fingerprint"], expected_snapshot_fingerprint)
        self.assertTrue(receipt["snapshot_id"].endswith(expected_snapshot_fingerprint[:12]))
        self.assertRegex(receipt["submitted_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertRegex(receipt["retrieved_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertNotIn(
            "toffekari@gmail.com",
            (ALA / "ala_snapshot_receipt.json").read_text(encoding="utf-8"),
        )
        self.assertGreater(receipt["download"]["dataset_count"], 0)
        self.assertEqual(
            sum(receipt["download"]["licence_counts"].values()),
            receipt["download"]["row_count"],
        )
        inspection = self.builder.inspect_archive(archive)
        for key in (
            "row_count",
            "dataset_count",
            "citation_entry_count",
            "licence_counts",
            "basis_of_record_counts",
            "sensitive_counts",
            "spatial_validity_counts",
            "missing_latitude_count",
            "missing_longitude_count",
        ):
            self.assertEqual(inspection[key], receipt["download"][key])
        self.assertEqual(
            set(inspection["licence_counts"]),
            set(self.builder.ALLOWED_PUBLIC_LICENCES),
        )
        for contract in receipt["provider_contracts"].values():
            path = contract.get("path")
            if path:
                if "response_sha256" in contract:
                    self.assertRegex(contract["response_sha256"], r"^[0-9a-f]{64}$")
                else:
                    self.assertTrue(contract.get("layers"))
                self.assertEqual(
                    contract["physical_sha256"],
                    self.builder.sha256_file(ALA / path),
                )
        layers = receipt["provider_contracts"]["spatial_layers"]["layers"]
        self.assertEqual(
            [layer["index_field"] for layer in layers],
            [self.builder.IBRA_FIELD, self.builder.LGA_FIELD],
        )
        self.assertTrue(
            all(
                layer["licence_url"]
                == "https://creativecommons.org/licenses/by/4.0/"
                for layer in layers
            )
        )


if __name__ == "__main__":
    unittest.main()
