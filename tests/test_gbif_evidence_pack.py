from __future__ import annotations

from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
GBIF = PACK / "gbif"
MANIFEST_PATH = GBIF / "gbif_evidence_manifest.json"
RECEIPT_PATH = GBIF / "gbif_download_receipt.json"


def load_builder():
    path = ROOT / "scripts/build_gbif_evidence.py"
    specification = importlib.util.spec_from_file_location("published_gbif_evidence", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("unable to load GBIF evidence builder")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class GbifEvidencePackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = load_builder()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        cls.occurrences = pq.read_table(GBIF / "gbif_occurrences.parquet")
        cls.multimedia = pq.read_table(GBIF / "gbif_multimedia.parquet")
        cls.datasets = pq.read_table(GBIF / "gbif_datasets.parquet")

    def test_manifest_and_all_artifacts_reconcile(self) -> None:
        semantic = dict(self.manifest)
        expected = semantic.pop("evidence_pack_fingerprint")
        self.assertEqual(
            hashlib.sha256(self.builder.canonical_json(semantic)).hexdigest(),
            expected,
        )
        tables = {
            "occurrences": self.occurrences,
            "multimedia": self.multimedia,
            "datasets": self.datasets,
        }
        fingerprint_fields = {
            "occurrences": "occurrence_evidence_fingerprint",
            "multimedia": "media_evidence_fingerprint",
            "datasets": "dataset_evidence_fingerprint",
        }
        for name, table in tables.items():
            artifact = self.manifest["artifacts"][name]
            path = GBIF / artifact["path"]
            self.assertEqual(artifact["physical_bytes"], path.stat().st_size)
            self.assertLess(path.stat().st_size, 100_000_000)
            self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(path))
            self.assertEqual(artifact["row_count"], table.num_rows)
            self.assertEqual(artifact["column_count"], table.num_columns)
            digest = hashlib.sha256()
            for value in table[fingerprint_fields[name]].to_pylist():
                digest.update(value.encode("ascii"))
                digest.update(b"\n")
            self.assertEqual(artifact["logical_row_fingerprint_sha256"], digest.hexdigest())
        for schema in self.manifest["schemas"].values():
            self.assertEqual(
                schema["physical_sha256"],
                self.builder.sha256_file(GBIF / schema["path"]),
            )

    def test_occurrence_projection_preserves_rights_quality_and_sensitivity(self) -> None:
        self.assertEqual(self.occurrences.num_rows, 571_755)
        ids = self.occurrences["gbif_id"].to_pylist()
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            Counter(self.occurrences["licence"].to_pylist()),
            Counter({"CC_BY_NC_4_0": 314_575, "CC_BY_4_0": 195_361, "CC0_1_0": 61_819}),
        )
        self.assertEqual(
            self.occurrences["information_withheld"].length()
            - self.occurrences["information_withheld"].null_count,
            18_317,
        )
        self.assertEqual(
            self.occurrences["data_generalizations"].length()
            - self.occurrences["data_generalizations"].null_count,
            564,
        )
        self.assertEqual(Counter(self.occurrences["has_geospatial_issues"].to_pylist())[True], 70)
        metadata = self.occurrences.schema.metadata
        self.assertEqual(
            metadata[b"schema_version"].decode(),
            self.builder.OCCURRENCE_SCHEMA_VERSION,
        )
        self.assertIn("not human verification", metadata[b"evidence_semantics"].decode())

    def test_multimedia_is_metadata_only_and_dataset_rights_reconcile(self) -> None:
        self.assertEqual(self.multimedia.num_rows, 542_052)
        self.assertEqual(len(set(self.multimedia["gbif_id"].to_pylist())), 331_178)
        self.assertEqual(self.datasets.num_rows, 126)
        self.assertEqual(sum(self.datasets["selected_occurrence_count"].to_pylist()), 571_755)
        self.assertEqual(
            Counter(self.datasets["rights_as_supplied"].to_pylist()),
            Counter(
                {
                    "http://creativecommons.org/licenses/by/4.0/legalcode": 76,
                    "http://creativecommons.org/licenses/by-nc/4.0/legalcode": 28,
                    "http://creativecommons.org/publicdomain/zero/1.0/legalcode": 22,
                }
            ),
        )
        self.assertFalse(any(GBIF.rglob("*.jpg")))
        self.assertFalse(any(GBIF.rglob("*.jpeg")))
        self.assertFalse(any(GBIF.rglob("*.png")))
        summary = self.manifest["counts"]["multimedia_licence_summary"]
        self.assertEqual(summary["supplied_rows"] + summary["missing_rows"], 542_052)
        self.assertEqual(summary["unique_supplied_values"], 256)

    def test_pack_keeps_ala_authoritative_and_release_blocked(self) -> None:
        pack = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        state = pack["gbif_state"]
        self.assertEqual(state["occurrence_rows"], 571_755)
        self.assertEqual(state["multimedia_metadata_rows"], 542_052)
        self.assertEqual(state["dataset_rows"], 126)
        self.assertEqual(state["authoritative_ala_baseline"], "ButterflyLens rebuilt baseline")
        self.assertFalse(state["gbif_replaces_ala_baseline"])
        self.assertFalse(state["media_bytes_downloaded"])
        self.assertFalse(state["flickr_api_calls_made"])
        self.assertEqual(
            state["public_release_state"],
            "blocked_pending_record_and_dataset_rights_review",
        )
        self.assertEqual(pack["ala_state"]["selected_occurrence_rows"], 236_897)
        providers = [source["provider"] for source in pack["occurrence_sources"]]
        self.assertEqual(
            providers,
            ["Atlas of Living Australia", "Global Biodiversity Information Facility"],
        )

    def test_data_rights_records_fail_closed_for_every_gbif_artifact(self) -> None:
        rights = json.loads((ROOT / "provenance/data_rights_manifest.json").read_text())
        source_id = "gbif-occurrence-download-0004170-260715120105164"
        source = next(row for row in rights["sources"] if row["source_id"] == source_id)
        self.assertIn("126 constituent", source["provider"])
        records = [row for row in rights["artifacts"] if row["source_id"] == source_id]
        self.assertEqual(len(records), 9)
        for record in records:
            path = ROOT / record["path"]
            self.assertEqual(record["fingerprint"], f"sha256:{self.builder.sha256_file(path)}")
            self.assertTrue(record["processing_allowed"])
            self.assertFalse(record["display_allowed"])
            self.assertFalse(record["redistribution_allowed"])

    def test_publish_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            pack = temporary / "manifest.json"
            rights = temporary / "data_rights_manifest.json"
            pack.write_bytes((PACK / "manifest.json").read_bytes())
            rights.write_bytes((ROOT / "provenance/data_rights_manifest.json").read_bytes())
            self.builder.publish(
                type(
                    "Arguments",
                    (),
                    {
                        "gbif_dir": GBIF,
                        "pack_manifest": pack,
                        "rights_manifest": rights,
                        "published_at": "2026-07-18T16:09:03Z",
                    },
                )()
            )
            self.assertEqual(pack.read_bytes(), (PACK / "manifest.json").read_bytes())
            self.assertEqual(
                rights.read_bytes(),
                (ROOT / "provenance/data_rights_manifest.json").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
