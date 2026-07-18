from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import pyarrow.parquet as pq
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / "data/packs/australian_butterflies/v1/map"
WEB_SNAPSHOT = ROOT / "apps/web/src/map/submittedMapSnapshot.json"
SCRIPT = ROOT / "scripts/build_public_ala_map.py"
BLOCKED_UIDS = {"dr1097", "dr30019", "dr635"}

sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.contracts import canonicalize_json  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()


class PublicAlaMapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(
            (MAP / "map_manifest.json").read_text(encoding="utf-8")
        )
        cls.browser = json.loads(WEB_SNAPSHOT.read_text(encoding="utf-8"))
        cls.cells = pq.read_table(MAP / "geographic_impact_cells.parquet")
        cls.summaries = pq.read_table(
            MAP / "geographic_impact_summary.parquet"
        )
        cls.cell_rows = cls.cells.to_pylist()
        cls.summary_rows = cls.summaries.to_pylist()

        registry: Registry[object] = Registry()
        cls.schemas: dict[str, dict[str, object]] = {}
        for path in sorted((ROOT / "packages/contracts/schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            cls.schemas[schema["$id"]] = schema
            registry = registry.with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
        cls.registry = registry

    def test_manifest_and_contracts_are_valid_and_fingerprint_bound(self) -> None:
        self.assertEqual(
            self.manifest["schema_version"],
            "butterflylens-submitted-ala-map/v1",
        )
        manifest_input = deepcopy(self.manifest)
        observed = manifest_input.pop("manifest_fingerprint")
        self.assertEqual(observed, fingerprint(manifest_input))

        for schema_id, document in (
            (
                "urn:butterflylens:schema:geographic-impact-snapshot:v1.0.0",
                self.manifest["snapshot"],
            ),
            (
                "urn:butterflylens:schema:geographic-impact-query:v1.0.0",
                self.manifest["query"],
            ),
        ):
            validator = Draft202012Validator(
                self.schemas[schema_id],
                registry=self.registry,
                format_checker=FormatChecker(),
            )
            errors = sorted(
                validator.iter_errors(document), key=lambda error: list(error.path)
            )
            self.assertEqual([], [error.message for error in errors])

        query = deepcopy(self.manifest["query"])
        query_fingerprint = query.pop("query_fingerprint")
        self.assertEqual(query_fingerprint, fingerprint(query))

    def test_rights_screen_preserves_full_authoritative_baseline(self) -> None:
        counts = self.manifest["counts"]
        self.assertEqual(counts["authoritative_baseline_selected"], 236_897)
        self.assertEqual(counts["rights_screened_selected"], 220_144)
        self.assertEqual(counts["rights_excluded_selected"], 16_753)
        self.assertEqual(counts["map_eligible"], 213_310)
        self.assertEqual(counts["rights_excluded_map_eligible"], 16_717)
        self.assertTrue(self.manifest["input"]["authoritative_baseline"])
        self.assertEqual(
            self.manifest["input"]["gbif_relationship"],
            "complementary_not_merged",
        )
        rights = self.manifest["rights_screen"]
        self.assertTrue(rights["full_baseline_preserved"])
        self.assertFalse(rights["legal_conclusion"])
        self.assertEqual(
            {row["data_resource_uid"] for row in rights["excluded_datasets"]},
            BLOCKED_UIDS,
        )
        self.assertEqual(
            {
                row["data_resource_uid"]: row["selected_record_count"]
                for row in rights["excluded_datasets"]
            },
            {"dr1097": 15_268, "dr30019": 360, "dr635": 1_125},
        )

    def test_cells_are_exact_contract_valid_and_linked_to_evidence(self) -> None:
        self.assertEqual(len(self.cell_rows), 630)
        self.assertEqual(
            sum(row["counts"]["ala_baseline"]["value"] for row in self.cell_rows),
            213_310,
        )
        validator = Draft202012Validator(
            self.schemas["urn:butterflylens:schema:geographic-impact-cell:v1.0.0"],
            registry=self.registry,
            format_checker=FormatChecker(),
        )
        for row in self.cell_rows:
            with self.subTest(cell_id=row["cell_id"]):
                errors = sorted(
                    validator.iter_errors(row), key=lambda error: list(error.path)
                )
                self.assertEqual([], [error.message for error in errors])
                fingerprint_input = deepcopy(row)
                observed = fingerprint_input.pop("cell_fingerprint")
                self.assertEqual(observed, fingerprint(fingerprint_input))
                self.assertGreaterEqual(len(row["evidence_fingerprints"]), 1)
                self.assertTrue(
                    all(
                        len(value) == 64
                        and set(value) <= set("0123456789abcdef")
                        for value in row["evidence_fingerprints"]
                    )
                )
                self.assertEqual(row["public_geometry"]["status"], "generalized")
                self.assertEqual(
                    row["public_geometry"]["published_h3_resolution"], 3
                )
                self.assertFalse(row["scientific_claim_allowed"])

    def test_unavailable_layers_are_null_with_reasons_never_zero(self) -> None:
        unavailable_names = {
            "flickr_candidate",
            "yoloe_butterfly",
            "bioclip_species_candidate",
            "community_reviewed",
            "human_supported",
            "release_ready",
        }
        for row in self.cell_rows:
            for name in unavailable_names:
                count = row["counts"][name]
                self.assertEqual(count["status"], "unavailable")
                self.assertIsNone(count["value"])
                self.assertTrue(count["reason"])
            for value in row["impact"].values():
                self.assertEqual(value["status"], "unavailable")
                self.assertIsNone(value["value"])
                self.assertTrue(value["reason"])
        self.assertEqual(
            self.browser["layers"]["flickrCandidate"]["status"], "unavailable"
        )
        self.assertIn(
            "still fetching Flickr metadata",
            self.browser["layers"]["flickrCandidate"]["reason"],
        )

    def test_summary_scopes_and_sensitive_location_policy_reconcile(self) -> None:
        national = [
            row for row in self.summary_rows if row["scope_type"] == "australia"
        ]
        self.assertEqual(len(national), 1)
        self.assertEqual(national[0]["ala_baseline_count"], 213_310)
        observed_counts: dict[str, int] = {}
        for row in self.summary_rows:
            observed_counts[row["scope_type"]] = (
                observed_counts.get(row["scope_type"], 0) + 1
            )
            self.assertEqual(
                row["ala_baseline_count"],
                row["matched_taxon_record_count"]
                + row["unmatched_taxon_assertion_count"],
            )
            self.assertFalse(row["scientific_claim_allowed"])
            if row["publicly_generalised_record_count"] > 0:
                self.assertIn(
                    row["scope_type"],
                    {"australia", "state_territory", "h3_coarse"},
                )
        self.assertEqual(observed_counts, self.manifest["counts"]["summary_scope_rows"])
        self.assertEqual(
            {key: len(value) for key, value in self.browser["scopes"].items()},
            {"state": 9, "ibra": 87, "lga": 532, "h3": 630},
        )

    def test_browser_projection_publishes_only_aggregate_geometry(self) -> None:
        self.assertFalse(self.browser["policies"]["occurrenceCoordinatesPublished"])
        self.assertFalse(self.browser["policies"]["boundaryGeometryCopied"])
        self.assertFalse(self.browser["policies"]["absenceInferencePermitted"])
        self.assertFalse(self.browser["policies"]["scientificClaimAllowed"])
        self.assertEqual(len(self.browser["cells"]), 630)
        serialized = json.dumps(self.browser, sort_keys=True)
        for forbidden in (
            '"decimalLatitude"',
            '"decimalLongitude"',
            '"coordinateUncertaintyInMeters"',
        ):
            self.assertNotIn(forbidden, serialized)
        for cell in self.browser["cells"]:
            self.assertGreaterEqual(len(cell["polygon"]), 6)
            self.assertLessEqual(len(cell["records"]), 2)
            for record in cell["records"]:
                self.assertNotIn(record["dataResourceUid"], BLOCKED_UIDS)
                self.assertIn("not human verification", record["evidenceLabel"])
        snapshot_input = deepcopy(self.browser)
        observed = snapshot_input.pop("snapshotFingerprint")
        self.assertEqual(observed, fingerprint(snapshot_input))

    def test_artifact_receipts_and_parquet_schemas_match(self) -> None:
        artifacts = self.manifest["artifacts"]
        for key, path in (
            ("geographic_impact_cells", MAP / "geographic_impact_cells.parquet"),
            (
                "geographic_impact_summary",
                MAP / "geographic_impact_summary.parquet",
            ),
        ):
            receipt = artifacts[key]
            self.assertEqual(receipt["physical_sha256"], sha256_file(path))
            self.assertEqual(receipt["physical_bytes"], path.stat().st_size)
        browser_receipt = artifacts["browser_snapshot"]
        self.assertEqual(browser_receipt["physical_sha256"], sha256_file(WEB_SNAPSHOT))

        contract = json.loads(
            (MAP / "schemas/geographic_impact_summary.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            self.summaries.schema.names,
            [field["name"] for field in contract["fields"]],
        )
        self.assertEqual(
            self.cells.schema.metadata[b"schema_version"].decode(),
            "butterflylens-geographic-impact-cell:v1.0.0",
        )

    def test_checked_in_projection_rebuilds_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_path = Path(temporary)
            output_dir = temporary_path / "map"
            web_output = temporary_path / "submittedMapSnapshot.json"
            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--source-commit",
                    self.manifest["source_commit"],
                    "--output-dir",
                    str(output_dir),
                    "--web-output",
                    str(web_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            for expected, observed in (
                (
                    MAP / "geographic_impact_cells.parquet",
                    output_dir / "geographic_impact_cells.parquet",
                ),
                (
                    MAP / "geographic_impact_summary.parquet",
                    output_dir / "geographic_impact_summary.parquet",
                ),
                (
                    MAP / "schemas/geographic_impact_summary.schema.json",
                    output_dir / "schemas/geographic_impact_summary.schema.json",
                ),
                (WEB_SNAPSHOT, web_output),
            ):
                self.assertEqual(sha256_file(expected), sha256_file(observed))


if __name__ == "__main__":
    unittest.main()
