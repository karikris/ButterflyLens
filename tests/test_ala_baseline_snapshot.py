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

    def test_normalization_policy_helpers(self) -> None:
        self.assertEqual(
            self.builder.evidence_category("MACHINE_OBSERVATION"),
            "machine_observation",
        )
        self.assertEqual(
            self.builder.evidence_category("FOSSIL_SPECIMEN"),
            "fossil_specimen",
        )
        self.assertEqual(
            self.builder.temporal_evidence_band(1899, 2026),
            "pre_1900_historical",
        )
        self.assertEqual(
            self.builder.spatial_eligibility(
                has_coordinates=True,
                coordinate_in_range=True,
                spatially_valid=True,
                publicly_generalised=True,
            ),
            "eligible_generalised_coarse_only",
        )
        self.assertEqual(
            self.builder.spatial_eligibility(
                has_coordinates=False,
                coordinate_in_range=False,
                spatially_valid=False,
                publicly_generalised=False,
            ),
            "excluded_missing_coordinates",
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


class AlaNormalizedOccurrenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.path = ALA / "ala_baseline_occurrences.parquet"
        cls.manifest = json.loads(
            (ALA / "ala_normalization_manifest.json").read_text(encoding="utf-8")
        )
        cls.source_receipt = json.loads(
            (ALA / "ala_snapshot_receipt.json").read_text(encoding="utf-8")
        )
        cls.schema_contract = json.loads(
            (ALA / "schemas/ala_baseline_occurrence.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.parquet = pq.ParquetFile(cls.path)

    def test_manifest_schema_and_physical_artifact_reconcile(self) -> None:
        artifact = self.manifest["artifact"]
        self.assertEqual(self.manifest["snapshot_id"], self.source_receipt["snapshot_id"])
        self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(self.path))
        self.assertEqual(artifact["physical_bytes"], self.path.stat().st_size)
        self.assertEqual(artifact["row_count"], self.source_receipt["download"]["row_count"])
        self.assertEqual(artifact["row_count"], self.parquet.metadata.num_rows)
        self.assertEqual(artifact["row_group_count"], self.parquet.metadata.num_row_groups)
        self.assertEqual(artifact["column_count"], self.parquet.metadata.num_columns)
        schema_path = ALA / "schemas/ala_baseline_occurrence.schema.json"
        self.assertEqual(
            self.manifest["schema"]["physical_sha256"],
            self.builder.sha256_file(schema_path),
        )
        expected_names = [field["name"] for field in self.schema_contract["fields"]]
        self.assertEqual(self.parquet.schema_arrow.names, expected_names)
        metadata = self.parquet.schema_arrow.metadata
        self.assertEqual(metadata[b"schema_version"].decode(), self.builder.NORMALIZED_SCHEMA_VERSION)
        self.assertEqual(metadata[b"evidence_label"].decode(), "ALA baseline occurrence evidence")

    def test_identifiers_taxon_state_and_row_fingerprints(self) -> None:
        table = self.pq.read_table(
            self.path,
            columns=[
                "ala_record_id",
                "normalized_occurrence_fingerprint",
                "butterflylens_taxon_key",
                "taxon_match_state",
            ],
        )
        identifiers = table.column("ala_record_id").to_pylist()
        self.assertEqual(identifiers, sorted(identifiers))
        self.assertEqual(len(identifiers), len(set(identifiers)))
        fingerprints = table.column("normalized_occurrence_fingerprint").to_pylist()
        self.assertTrue(
            all(
                len(value) == 64 and set(value) <= set("0123456789abcdef")
                for value in fingerprints
            )
        )
        keys = table.column("butterflylens_taxon_key").to_pylist()
        states = table.column("taxon_match_state").to_pylist()
        for key, state in zip(keys, states, strict=True):
            self.assertEqual(key is not None, state == "exact_ala_taxon_concept_crosswalk")

    def test_quality_rights_and_source_counts_reconcile(self) -> None:
        table = self.pq.read_table(
            self.path,
            columns=[
                "licence",
                "quality_assertions",
                "quality_assertion_count",
                "evidence_category",
                "sensitive_status",
                "spatial_aggregation_eligibility",
            ],
        )
        licences = table.column("licence").to_pylist()
        self.assertEqual(set(licences), set(self.builder.ALLOWED_PUBLIC_LICENCES))
        assertions = table.column("quality_assertions").to_pylist()
        assertion_counts = table.column("quality_assertion_count").to_pylist()
        self.assertTrue(
            all(len(values) == count for values, count in zip(assertions, assertion_counts, strict=True))
        )
        for name in (
            "licence",
            "evidence_category",
            "sensitive_status",
            "spatial_aggregation_eligibility",
        ):
            observed: dict[str, int] = {}
            for value in table.column(name).to_pylist():
                observed[value] = observed.get(value, 0) + 1
            self.assertEqual(observed, self.manifest["counts"][name])

    def test_generalised_coordinates_never_receive_all_resolution_eligibility(self) -> None:
        table = self.pq.read_table(
            self.path,
            columns=[
                "coordinates_publicly_generalised",
                "spatial_aggregation_eligibility",
            ],
        )
        generalised = table.column("coordinates_publicly_generalised").to_pylist()
        eligibility = table.column("spatial_aggregation_eligibility").to_pylist()
        for is_generalised, state in zip(generalised, eligibility, strict=True):
            if is_generalised:
                self.assertNotEqual(state, "eligible_all_configured_resolutions")

    def test_sampled_semantic_fingerprints_are_recomputable(self) -> None:
        table = self.pq.read_table(self.path)
        indexes = (0, table.num_rows // 2, table.num_rows - 1)
        for index in indexes:
            row = table.slice(index, 1).to_pylist()[0]
            fingerprint = row.pop("normalized_occurrence_fingerprint")
            self.assertEqual(
                fingerprint,
                self.builder.sha256_bytes(self.builder.canonical_json(row)),
            )


if __name__ == "__main__":
    unittest.main()
