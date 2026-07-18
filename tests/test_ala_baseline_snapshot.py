from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import unittest
from collections import Counter
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


class AlaAggregatedCellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import h3
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest(
                "locked H3 and PyArrow dependencies are not installed"
            ) from error
        cls.builder = load_builder()
        cls.h3 = h3
        cls.pq = pq
        cls.path = ALA / "ala_baseline_cells.parquet"
        cls.manifest = json.loads(
            (ALA / "ala_aggregation_manifest.json").read_text(encoding="utf-8")
        )
        cls.normalization_manifest = json.loads(
            (ALA / "ala_normalization_manifest.json").read_text(encoding="utf-8")
        )
        cls.schema_contract = json.loads(
            (ALA / "schemas/ala_baseline_cell.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.parquet = pq.ParquetFile(cls.path)
        cls.table = pq.read_table(cls.path)

    def test_manifest_schema_and_physical_artifact_reconcile(self) -> None:
        artifact = self.manifest["artifact"]
        self.assertEqual(
            self.manifest["snapshot_id"],
            self.normalization_manifest["snapshot_id"],
        )
        self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(self.path))
        self.assertEqual(artifact["physical_bytes"], self.path.stat().st_size)
        self.assertEqual(artifact["row_count"], self.parquet.metadata.num_rows)
        self.assertEqual(artifact["row_group_count"], self.parquet.metadata.num_row_groups)
        self.assertEqual(artifact["column_count"], self.parquet.metadata.num_columns)
        schema_path = ALA / "schemas/ala_baseline_cell.schema.json"
        self.assertEqual(
            self.manifest["schema"]["physical_sha256"],
            self.builder.sha256_file(schema_path),
        )
        expected_names = [field["name"] for field in self.schema_contract["fields"]]
        self.assertEqual(self.parquet.schema_arrow.names, expected_names)
        metadata = self.parquet.schema_arrow.metadata
        self.assertEqual(
            metadata[b"schema_version"].decode(),
            self.builder.AGGREGATED_SCHEMA_VERSION,
        )
        self.assertEqual(metadata[b"h3_resolutions"].decode(), "coarse=3,regional=5,local=7")

    def test_scope_inventory_and_memberships_reconcile(self) -> None:
        expected_scope_types = {
            "australia",
            "state_territory",
            "ibra_region",
            "lga_2023_statistical_approximation",
            "h3_coarse",
            "h3_regional",
            "h3_local",
        }
        scope_types = self.table.column("scope_type").to_pylist()
        self.assertEqual(set(scope_types), expected_scope_types)
        observed_rows = {
            scope_type: scope_types.count(scope_type)
            for scope_type in expected_scope_types
        }
        self.assertEqual(observed_rows, self.manifest["counts"]["scope_rows"])
        observed_memberships = {scope_type: 0 for scope_type in expected_scope_types}
        for scope_type, count in zip(
            scope_types,
            self.table.column("record_count").to_pylist(),
            strict=True,
        ):
            observed_memberships[scope_type] += count
        self.assertEqual(
            observed_memberships,
            self.manifest["counts"]["scope_record_memberships"],
        )
        self.assertEqual(observed_memberships["australia"], 230_027)
        self.assertEqual(observed_memberships["h3_coarse"], 230_027)
        self.assertEqual(observed_memberships["h3_regional"], 229_652)
        self.assertEqual(observed_memberships["h3_local"], 229_652)

    def test_generalised_rows_are_coarse_only(self) -> None:
        observed = {}
        for scope_type in set(self.table.column("scope_type").to_pylist()):
            observed[scope_type] = sum(
                row["publicly_generalised_record_count"]
                for row in self.table.select(
                    ["scope_type", "publicly_generalised_record_count"]
                ).to_pylist()
                if row["scope_type"] == scope_type
            )
        self.assertEqual(
            observed,
            self.manifest["counts"]["scope_publicly_generalised_memberships"],
        )
        self.assertEqual(observed["australia"], 375)
        self.assertEqual(observed["state_territory"], 375)
        self.assertEqual(observed["h3_coarse"], 375)
        for scope_type in (
            "ibra_region",
            "lga_2023_statistical_approximation",
            "h3_regional",
            "h3_local",
        ):
            self.assertEqual(observed[scope_type], 0)

    def test_h3_cells_resolution_centers_and_parents_are_valid(self) -> None:
        resolution_by_type = {
            "h3_coarse": 3,
            "h3_regional": 5,
            "h3_local": 7,
        }
        for row in self.table.select(
            [
                "scope_type",
                "h3_resolution",
                "h3_cell_id",
                "parent_h3_cell_id",
                "cell_center_latitude",
                "cell_center_longitude",
            ]
        ).to_pylist():
            scope_type = row["scope_type"]
            if scope_type not in resolution_by_type:
                self.assertIsNone(row["h3_resolution"])
                self.assertIsNone(row["h3_cell_id"])
                continue
            resolution = resolution_by_type[scope_type]
            cell_id = row["h3_cell_id"]
            self.assertEqual(row["h3_resolution"], resolution)
            self.assertTrue(self.h3.is_valid_cell(cell_id))
            self.assertEqual(self.h3.get_resolution(cell_id), resolution)
            self.assertEqual(
                (row["cell_center_latitude"], row["cell_center_longitude"]),
                tuple(self.h3.cell_to_latlng(cell_id)),
            )
            if resolution == 3:
                self.assertIsNone(row["parent_h3_cell_id"])
            else:
                parent_resolution = 3 if resolution == 5 else 5
                self.assertEqual(
                    row["parent_h3_cell_id"],
                    self.h3.cell_to_parent(cell_id, parent_resolution),
                )

    def test_aggregate_counts_fingerprints_and_national_lineage(self) -> None:
        scope_ids = self.table.column("scope_id").to_pylist()
        self.assertEqual(len(scope_ids), len(set(scope_ids)))
        rows = self.table.to_pylist()
        count_fields = list(self.builder.EVIDENCE_COUNT_FIELDS.values())
        for row in rows:
            self.assertEqual(
                row["record_count"],
                row["matched_taxon_record_count"]
                + row["unmatched_taxon_assertion_count"],
            )
            self.assertEqual(
                row["record_count"],
                sum(row[field] for field in count_fields),
            )
            self.assertEqual(
                row["record_count"],
                row["coordinate_uncertainty_known_count"]
                + row["coordinate_uncertainty_missing_count"],
            )
        for index in (0, len(rows) // 2, len(rows) - 1):
            row = dict(rows[index])
            fingerprint = row.pop("aggregate_fingerprint")
            self.assertEqual(
                fingerprint,
                self.builder.sha256_bytes(self.builder.canonical_json(row)),
            )

        digest = hashlib.sha256()
        occurrence_table = self.pq.read_table(
            ALA / "ala_baseline_occurrences.parquet",
            columns=[
                "normalized_occurrence_fingerprint",
                "spatial_aggregation_eligibility",
            ],
        )
        for row in occurrence_table.to_pylist():
            if row["spatial_aggregation_eligibility"].startswith("eligible_"):
                digest.update(row["normalized_occurrence_fingerprint"].encode("ascii"))
                digest.update(b"\n")
        australia = next(row for row in rows if row["scope_type"] == "australia")
        self.assertEqual(australia["source_record_fingerprint_digest"], digest.hexdigest())


class AlaPublishedSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.dataset_path = ALA / "ala_dataset_manifest.parquet"
        cls.dataset_table = pq.read_table(cls.dataset_path)
        cls.dataset_schema = json.loads(
            (ALA / "schemas/ala_dataset_manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        cls.snapshot = json.loads(
            (ALA / "ala_snapshot_manifest.json").read_text(encoding="utf-8")
        )
        cls.receipt = json.loads(
            (ALA / "ala_snapshot_receipt.json").read_text(encoding="utf-8")
        )
        cls.pack_manifest = json.loads(
            (PACK / "manifest.json").read_text(encoding="utf-8")
        )

    def test_dataset_schema_snapshot_and_pack_manifest_reconcile(self) -> None:
        artifact = self.snapshot["artifacts"]["dataset_manifest"]
        self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(self.dataset_path))
        self.assertEqual(artifact["physical_bytes"], self.dataset_path.stat().st_size)
        self.assertEqual(artifact["row_count"], self.dataset_table.num_rows)
        expected_names = [field["name"] for field in self.dataset_schema["fields"]]
        self.assertEqual(self.dataset_table.schema.names, expected_names)
        metadata = self.dataset_table.schema.metadata
        self.assertEqual(
            metadata[b"schema_version"].decode(),
            self.builder.DATASET_SCHEMA_VERSION,
        )
        snapshot_copy = dict(self.snapshot)
        fingerprint = snapshot_copy.pop("snapshot_manifest_fingerprint")
        self.assertEqual(
            fingerprint,
            self.builder.sha256_bytes(self.builder.canonical_json(snapshot_copy)),
        )
        ala_state = self.pack_manifest["ala_state"]
        self.assertEqual(ala_state["snapshot_id"], self.snapshot["snapshot_id"])
        self.assertEqual(
            ala_state["snapshot_manifest_sha256"],
            self.builder.sha256_file(ALA / "ala_snapshot_manifest.json"),
        )
        self.assertEqual(ala_state["status"], "built_rights_review_required")
        ala_source = next(
            source
            for source in self.pack_manifest["occurrence_sources"]
            if source["provider"] == self.builder.ALA_PROVIDER
        )
        self.assertEqual(
            ala_source,
            {
                "path": "ala/ala_snapshot_receipt.json",
                "physical_sha256": self.builder.sha256_file(
                    ALA / "ala_snapshot_receipt.json"
                ),
                "retrieved_at": self.receipt["retrieved_at"],
                "provider": self.builder.ALA_PROVIDER,
                "snapshot_id": self.receipt["snapshot_id"],
                "snapshot_fingerprint": self.receipt["snapshot_fingerprint"],
            },
        )

    def test_dataset_uid_citation_counts_and_licences_reconcile(self) -> None:
        rows = self.dataset_table.to_pylist()
        uids = [row["data_resource_uid"] for row in rows]
        self.assertEqual(uids, sorted(uids))
        self.assertEqual(len(uids), len(set(uids)))
        self.assertEqual(len(rows), self.receipt["download"]["dataset_count"])
        self.assertEqual(
            sum(row["selected_record_count"] for row in rows),
            self.receipt["download"]["row_count"],
        )
        licence_counts: Counter[str] = Counter()
        for row in rows:
            self.assertTrue(row["citation_count_matches_selected"])
            self.assertEqual(row["citation_record_count"], row["selected_record_count"])
            self.assertEqual(
                row["selected_record_count"],
                sum(row[field] for field in self.builder.LICENCE_COUNT_FIELDS.values()),
            )
            for licence, field in self.builder.LICENCE_COUNT_FIELDS.items():
                licence_counts[licence] += row[field]
        self.assertEqual(
            dict(sorted(licence_counts.items())),
            self.receipt["download"]["licence_counts"],
        )

    def test_dataset_rows_preserve_exact_receipts_and_fingerprints(self) -> None:
        dataset_by_uid = {
            row["data_resource_uid"]: row
            for row in self.receipt["download"]["datasets"]
        }
        citation_by_uid = {
            row["uid"]: row
            for row in self.receipt["download"]["citation_entries"]
        }
        for row in self.dataset_table.to_pylist():
            uid = row["data_resource_uid"]
            citation = citation_by_uid[uid]
            self.assertEqual(row["citation"], citation["citation"])
            self.assertEqual(row["citation_rights"], citation["rights"])
            self.assertEqual(row["data_generalisations"], citation["data_generalisations"])
            self.assertEqual(row["information_withheld"], citation["information_withheld"])
            self.assertEqual(row["download_limit"], citation["download_limit"])
            self.assertEqual(
                row["source_dataset_receipt_fingerprint"],
                self.builder.sha256_bytes(
                    self.builder.canonical_json(
                        {"dataset": dataset_by_uid[uid], "citation": citation}
                    )
                ),
            )
            semantic_row = dict(row)
            fingerprint = semantic_row.pop("dataset_manifest_fingerprint")
            self.assertEqual(
                fingerprint,
                self.builder.sha256_bytes(self.builder.canonical_json(semantic_row)),
            )

    def test_rights_conflicts_are_explicit_and_block_public_release(self) -> None:
        rows = self.dataset_table.to_pylist()
        flagged = [
            row for row in rows if row["citation_restrictive_rights_terms_detected"]
        ]
        self.assertEqual(
            {row["data_resource_uid"] for row in flagged},
            {"dr1097", "dr30019", "dr635"},
        )
        self.assertEqual(sum(row["selected_record_count"] for row in flagged), 16_753)
        self.assertTrue(
            all(
                row["public_product_rights_review_state"]
                == "blocked_pending_citation_rights_resolution"
                for row in flagged
            )
        )
        self.assertEqual(
            self.snapshot["rights"]["downstream_public_product_release_state"],
            "blocked_pending_dataset_rights_resolution",
        )
        self.assertIn(
            "not a legal conclusion",
            self.snapshot["rights"]["citation_restrictive_rights_screening"],
        )
        self.assertEqual(
            sum(row["information_withheld"] is not None for row in rows), 4
        )
        self.assertEqual(
            sum(row["data_generalisations"] is not None for row in rows), 1
        )

    def test_snapshot_artifact_inventory_and_scientific_policies(self) -> None:
        for artifact in self.snapshot["artifacts"].values():
            path = ALA / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(
                artifact["physical_sha256"],
                self.builder.sha256_file(path),
            )
            self.assertEqual(artifact["physical_bytes"], path.stat().st_size)
        self.assertFalse(
            self.snapshot["policies"]["provider_taxon_assertions_are_human_verification"]
        )
        self.assertFalse(self.snapshot["policies"]["absence_inference_permitted"])
        self.assertFalse(self.snapshot["policies"]["boundary_geometry_copied"])
        self.assertEqual(self.snapshot["counts"]["citation_entries"], 84)
        self.assertEqual(self.snapshot["counts"]["non_dataset_citation_entries"], 31)


if __name__ == "__main__":
    unittest.main()
