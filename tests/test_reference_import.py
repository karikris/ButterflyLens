from __future__ import annotations

from collections import Counter
import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
REFERENCE = PACK / "references/v1"


def load_builder():
    path = ROOT / "scripts/build_reference_import.py"
    spec = importlib.util.spec_from_file_location("build_reference_import", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.plan_path = REFERENCE / "reference_source_queries.json"
        cls.manifest_path = REFERENCE / "reference_import_manifest.json"
        cls.observation_path = REFERENCE / "imported/reference_observations.parquet"
        cls.media_path = REFERENCE / "imported/reference_media_candidates.parquet"
        cls.report_path = REFERENCE / "imported/reference_metadata_report.json"
        cls.checkpoint_path = (
            REFERENCE / "sources/biominer_reference_checkpoints.tar.gz"
        )
        cls.plan = json.loads(cls.plan_path.read_text())
        cls.manifest = json.loads(cls.manifest_path.read_text())
        cls.pack = json.loads((PACK / "manifest.json").read_text())
        cls.observations = pq.read_table(cls.observation_path)
        cls.media = pq.read_table(cls.media_path)

    def test_query_plan_is_exact_bounded_and_rebuildable(self) -> None:
        self.assertEqual(
            self.plan["schema_version"], self.builder.QUERY_PLAN_SCHEMA_VERSION
        )
        self.assertEqual(self.plan["biominer_origin_sha"], self.builder.BIOMINER_SHA)
        self.assertEqual(len(self.plan["queries"]), 742)
        self.assertEqual(
            self.plan["scope"]["species_with_exact_gbif_and_inaturalist_ids"], 371
        )
        self.assertEqual(
            self.plan["scope"]["species_excluded_for_missing_provider_identity"], 92
        )
        queries = self.plan["queries"]
        self.assertEqual(Counter(row["source"] for row in queries), {"GBIF": 371, "iNaturalist": 371})
        identities = [(row["source"], row["source_taxon_id"]) for row in queries]
        self.assertEqual(len(identities), len(set(identities)))
        for row in queries:
            self.assertTrue(row["accepted_taxon_key"].startswith("gbif:"))
            self.assertEqual(row["fallback_level"], 2)
            self.assertEqual(row["geo_cluster_id"], "australia")
            if row["source"] == "GBIF":
                self.assertEqual(row["country_codes"], ["AU"])
                self.assertEqual((row["page_size"], row["maximum_records"]), (3, 3))
            else:
                self.assertEqual(row["source_place_ids"], ["6744"])
                self.assertEqual(
                    (row["page_size"], row["maximum_records"]), (200, 200)
                )

    def test_imported_tables_reconcile_and_remain_unreviewed(self) -> None:
        self.assertEqual(self.observations.num_rows, 12_980)
        self.assertEqual(self.media.num_rows, 24_329)
        observations = self.observations.to_pylist()
        media = self.media.to_pylist()
        self.assertEqual(
            Counter(row["source"] for row in observations),
            {"GBIF": 980, "iNaturalist": 12_000},
        )
        self.assertEqual(
            Counter(row["source"] for row in media),
            {"GBIF": 1_696, "iNaturalist": 22_633},
        )
        self.assertEqual(
            Counter(row["taxon_reconciliation_status"] for row in observations),
            {"accepted_key_exact": 12_977, "conflict": 3},
        )
        self.assertEqual(
            Counter(row["licence_policy_status"] for row in media),
            {"allowed": 22_633, "unreviewed": 1_651, "quarantined": 45},
        )
        self.assertEqual({row["verification_status"] for row in media}, {"unreviewed"})
        observation_ids = {row["reference_observation_id"] for row in observations}
        self.assertEqual(len(observation_ids), len(observations))
        self.assertEqual(len({row["reference_media_id"] for row in media}), len(media))
        self.assertTrue(
            all(row["reference_observation_id"] in observation_ids for row in media)
        )

    def test_manifest_artifacts_checkpoints_and_pack_state_reconcile(self) -> None:
        self.assertEqual(
            self.manifest["schema_version"],
            self.builder.IMPORT_MANIFEST_SCHEMA_VERSION,
        )
        paths = {
            "query_plan": self.plan_path,
            "reference_observations": self.observation_path,
            "reference_media_candidates": self.media_path,
            "metadata_report": self.report_path,
            "checkpoint_archive": self.checkpoint_path,
        }
        for name, path in paths.items():
            entry = self.manifest["artifacts"][name]
            self.assertEqual(entry["physical_sha256"], self.builder.sha256_file(path))
            self.assertEqual(entry["physical_bytes"], path.stat().st_size)
        summary = self.builder.summarize_checkpoints(self.checkpoint_path)
        self.assertEqual(summary, self.manifest["biominer"]["checkpoint_summary"])
        self.assertEqual(summary["query_states"], 742)
        self.assertEqual(summary["pages"], 742)
        self.assertEqual(summary["request_count"], 769)
        self.assertEqual(summary["retry_count"], 27)
        self.assertEqual(summary["rate_limit_count"], 27)
        state = self.pack["reference_state"]
        self.assertEqual(state["manifest_sha256"], self.builder.sha256_file(self.manifest_path))
        self.assertEqual(state["observation_rows"], self.observations.num_rows)
        self.assertEqual(state["media_candidate_rows"], self.media.num_rows)
        self.assertEqual(state["images_downloaded"], 0)
        self.assertEqual(state["human_verified_media"], 0)

    def test_ala_link_and_release_block_are_not_weakened(self) -> None:
        ala = self.manifest["ala"]
        self.assertEqual(ala["normalized_occurrences"]["row_count"], 236_897)
        self.assertEqual(self.manifest["counts"]["ala_media_candidate_rows"], 0)
        self.assertIn("not_captured", ala["media_state"])
        self.assertEqual(
            self.manifest["rights"]["ala_release_state"],
            "blocked_pending_dataset_rights_resolution",
        )
        self.assertFalse(self.manifest["rights"]["media_bytes_downloaded"])
        self.assertEqual(self.manifest["counts"]["human_verified_media"], 0)


if __name__ == "__main__":
    unittest.main()
