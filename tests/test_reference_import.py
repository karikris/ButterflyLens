from __future__ import annotations

from collections import Counter
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
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
        cls.observation_mirrors_path = (
            REFERENCE
            / "deduplicated/reference_observation_mirror_groups.parquet"
        )
        cls.media_duplicates_path = (
            REFERENCE
            / "deduplicated/reference_media_duplicate_candidates.parquet"
        )
        cls.deduplication_manifest_path = (
            REFERENCE / "reference_deduplication_manifest.json"
        )
        cls.plan = json.loads(cls.plan_path.read_text())
        cls.manifest = json.loads(cls.manifest_path.read_text())
        cls.pack = json.loads((PACK / "manifest.json").read_text())
        cls.observations = pq.read_table(cls.observation_path)
        cls.media = pq.read_table(cls.media_path)
        cls.observation_mirrors = pq.read_table(cls.observation_mirrors_path)
        cls.media_duplicates = pq.read_table(cls.media_duplicates_path)
        cls.deduplication_manifest = json.loads(
            cls.deduplication_manifest_path.read_text()
        )

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

    def test_metadata_deduplication_links_exact_provider_identities(self) -> None:
        rows = self.observation_mirrors.to_pylist()
        self.assertEqual(len(rows), 10_453)
        self.assertEqual(
            Counter(
                tuple(
                    source
                    for source, members in (
                        ("ALA", row["ala_record_ids"]),
                        ("GBIF", row["gbif_reference_observation_ids"]),
                        (
                            "iNaturalist",
                            row["inaturalist_reference_observation_ids"],
                        ),
                    )
                    if members
                )
                for row in rows
            ),
            {
                ("ALA", "iNaturalist"): 10_377,
                ("ALA", "GBIF", "iNaturalist"): 52,
                ("ALA", "GBIF"): 16,
                ("GBIF", "iNaturalist"): 8,
            },
        )
        self.assertEqual(Counter(row["source_count"] for row in rows), {2: 10_401, 3: 52})
        self.assertEqual(sum(row["taxon_conflict"] for row in rows), 5)
        self.assertEqual(
            Counter(row["resolution_state"] for row in rows),
            {
                "same_provider_observation_metadata_link": 10_448,
                "taxon_conflict_review_required": 5,
            },
        )

    def test_duplicate_candidates_do_not_claim_media_equivalence(self) -> None:
        rows = self.media_duplicates.to_pylist()
        self.assertEqual(len(rows), 93)
        self.assertEqual(Counter(row["member_count"] for row in rows), {2: 93})
        self.assertEqual(
            Counter(tuple(row["canonical_licences"]) for row in rows),
            {("cc-by",): 78, ("cc0",): 14, ("cc-by", "cc-by-nc"): 1},
        )
        self.assertEqual(sum(row["metadata_conflict"] for row in rows), 1)
        self.assertTrue(
            all(
                row["exact_bytes_equal"] is None
                and row["perceptual_duplicate"] is None
                and row["canonical_reference_media_id"] is None
                for row in rows
            )
        )
        self.assertEqual(
            self.builder._canonical_licence(
                "http://creativecommons.org/licenses/by/4.0/"
            ),
            "cc-by",
        )

    def test_deduplication_fingerprints_and_manifests_reconcile(self) -> None:
        for rows, id_field, prefix, payload_fields in (
            (
                self.observation_mirrors.to_pylist(),
                "observation_mirror_group_id",
                "observation-mirror",
                (
                    "provider_identity_type",
                    "provider_identity",
                    "ala_record_ids",
                    "gbif_reference_observation_ids",
                    "inaturalist_reference_observation_ids",
                    "butterflylens_taxon_keys",
                ),
            ),
            (
                self.media_duplicates.to_pylist(),
                "media_duplicate_candidate_id",
                "media-duplicate-candidate",
                (
                    "provider_observation_id",
                    "provider_photo_id",
                    "gbif_reference_media_ids",
                    "inaturalist_reference_media_ids",
                    "butterflylens_taxon_keys",
                    "canonical_licences",
                ),
            ),
        ):
            ids = []
            for row in rows:
                payload = {field: row[field] for field in payload_fields}
                expected = self.builder._identity(prefix, payload)
                self.assertEqual(row[id_field], expected)
                self.assertEqual(
                    row["evidence_fingerprint"],
                    "sha256:" + expected.rsplit(":", 1)[1],
                )
                ids.append(row[id_field])
            self.assertEqual(len(ids), len(set(ids)))

        manifest = self.deduplication_manifest
        self.assertEqual(
            manifest["schema_version"],
            self.builder.DEDUPLICATION_MANIFEST_SCHEMA_VERSION,
        )
        self.assertFalse(manifest["policy"]["byte_or_perceptual_deduplication_claimed"])
        self.assertFalse(manifest["policy"]["canonical_media_selected"])
        paths = {
            "observation_mirror_groups": self.observation_mirrors_path,
            "media_duplicate_candidates": self.media_duplicates_path,
        }
        for name, path in paths.items():
            artifact = manifest["artifacts"][name]
            self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(path))
            self.assertEqual(artifact["physical_bytes"], path.stat().st_size)
        state = self.pack["reference_state"]
        self.assertEqual(
            state["deduplication_manifest_sha256"],
            self.builder.sha256_file(self.deduplication_manifest_path),
        )
        self.assertEqual(state["observation_mirror_groups"], 10_453)
        self.assertEqual(state["media_duplicate_candidates"], 93)

    def test_metadata_deduplication_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            observation_output = temporary / self.observation_mirrors_path.name
            media_output = temporary / self.media_duplicates_path.name
            manifest_output = temporary / self.deduplication_manifest_path.name
            pack_output = temporary / "manifest.json"
            pack_output.write_bytes((PACK / "manifest.json").read_bytes())
            self.builder.deduplicate_metadata(
                argparse.Namespace(
                    crosswalk=PACK / "crosswalk.jsonl",
                    ala_occurrences=PACK / "ala/ala_baseline_occurrences.parquet",
                    observations=self.observation_path,
                    media=self.media_path,
                    observation_output=observation_output,
                    media_output=media_output,
                    manifest=manifest_output,
                    pack_manifest=pack_output,
                    generated_at=self.deduplication_manifest["generated_at"],
                )
            )
            for actual, rebuilt in (
                (self.observation_mirrors_path, observation_output),
                (self.media_duplicates_path, media_output),
                (self.deduplication_manifest_path, manifest_output),
                (PACK / "manifest.json", pack_output),
            ):
                self.assertEqual(actual.read_bytes(), rebuilt.read_bytes())


if __name__ == "__main__":
    unittest.main()
