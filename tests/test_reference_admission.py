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
    path = ROOT / "scripts/build_reference_admission.py"
    spec = importlib.util.spec_from_file_location("build_reference_admission", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceAdmissionPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.decisions_path = REFERENCE / "gated/reference_media_gate_decisions.parquet"
        cls.selections_path = REFERENCE / "gated/reference_download_selections.parquet"
        cls.plan_manifest_path = REFERENCE / "reference_gate_plan_manifest.json"
        cls.decisions = pq.read_table(cls.decisions_path)
        cls.selections = pq.read_table(cls.selections_path)
        cls.plan_manifest = json.loads(cls.plan_manifest_path.read_text())

    def test_gate_decisions_are_complete_conservative_and_unreviewed(self) -> None:
        rows = self.decisions.to_pylist()
        self.assertEqual(len(rows), 24_329)
        self.assertEqual(len({row["reference_media_id"] for row in rows}), len(rows))
        self.assertEqual({row["verification_status"] for row in rows}, {"unreviewed"})
        self.assertEqual(
            Counter(row["automated_gate_status"] for row in rows),
            {"eligible": 22_378, "blocked": 1_951},
        )
        self.assertEqual(
            Counter(row["licence_policy_status"] for row in rows),
            {"allowed": 22_780, "denied": 1_504, "quarantined": 45},
        )
        self.assertEqual(
            Counter(row["provider_download_policy_status"] for row in rows),
            {"approved": 22_633, "blocked": 1_696},
        )
        self.assertTrue(
            all(
                row["source"] == "iNaturalist"
                and row["provider_host"]
                == self.builder.APPROVED_INATURALIST_HOST
                and row["licence_policy_status"] == "allowed"
                and not row["gate_reason_codes"]
                for row in rows
                if row["automated_gate_status"] == "eligible"
            )
        )

    def test_mirror_conflicts_and_noncommercial_licences_block(self) -> None:
        rows = self.decisions.to_pylist()
        observation_conflicts = [
            row for row in rows if row["observation_mirror_conflict"]
        ]
        media_conflicts = [row for row in rows if row["media_mirror_conflict"]]
        self.assertGreaterEqual(len(observation_conflicts), 1)
        self.assertEqual(len(media_conflicts), 2)
        self.assertTrue(
            all(row["automated_gate_status"] == "blocked" for row in observation_conflicts)
        )
        self.assertTrue(
            all(row["automated_gate_status"] == "blocked" for row in media_conflicts)
        )
        denied = [row for row in rows if row["licence_policy_status"] == "denied"]
        self.assertTrue(denied)
        self.assertTrue(
            all(
                row["canonical_licence"]
                in {"cc-by-nc", "cc-by-nc-sa", "cc-by-nc-nd"}
                for row in denied
            )
        )

    def test_selection_is_balanced_unique_and_content_addressed(self) -> None:
        rows = self.selections.to_pylist()
        self.assertEqual(len(rows), 2_910)
        self.assertEqual(len({row["reference_media_id"] for row in rows}), len(rows))
        self.assertEqual(
            len({row["reference_observation_id"] for row in rows}), len(rows)
        )
        self.assertEqual({row["source"] for row in rows}, {"iNaturalist"})
        self.assertEqual({row["life_stage"] for row in rows}, {"unknown"})
        counts = Counter(row["candidate_accepted_taxon_key"] for row in rows)
        self.assertEqual(len(counts), 237)
        self.assertEqual(sum(count == 20 for count in counts.values()), 86)
        self.assertLessEqual(max(counts.values()), self.builder.MAXIMUM_PER_SPECIES)
        observer_counts = Counter(row["observer_id"] for row in rows)
        self.assertLessEqual(
            max(observer_counts.values()), self.builder.MAXIMUM_PER_OBSERVER
        )
        for row in rows:
            self.assertEqual(row["reference_selection_id"], self.builder._selection_id(row))

    def test_gate_plan_manifest_and_fingerprints_reconcile(self) -> None:
        manifest = self.plan_manifest
        self.assertEqual(
            manifest["schema_version"],
            self.builder.GATE_PLAN_MANIFEST_SCHEMA_VERSION,
        )
        self.assertFalse(
            manifest["policy"]["provider_assertions_are_human_verification"]
        )
        self.assertEqual(manifest["counts"]["human_verified_media"], 0)
        for name, path in (
            ("gate_decisions", self.decisions_path),
            ("download_selections", self.selections_path),
        ):
            entry = manifest["artifacts"][name]
            self.assertEqual(entry["physical_sha256"], self.builder.sha256_file(path))
            self.assertEqual(entry["physical_bytes"], path.stat().st_size)
        for row in self.decisions.to_pylist():
            payload = {
                key: value
                for key, value in row.items()
                if key not in {"schema_version", "evidence_fingerprint"}
            }
            self.assertEqual(row["evidence_fingerprint"], self.builder.semantic_digest(payload))

    def test_gate_plan_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            decisions = temporary / self.decisions_path.name
            selections = temporary / self.selections_path.name
            manifest = temporary / self.plan_manifest_path.name
            self.builder.plan(
                argparse.Namespace(
                    crosswalk=PACK / "crosswalk.jsonl",
                    observations=REFERENCE
                    / "imported/reference_observations.parquet",
                    media=REFERENCE / "imported/reference_media_candidates.parquet",
                    observation_mirrors=REFERENCE
                    / "deduplicated/reference_observation_mirror_groups.parquet",
                    media_duplicates=REFERENCE
                    / "deduplicated/reference_media_duplicate_candidates.parquet",
                    import_manifest=REFERENCE / "reference_import_manifest.json",
                    decisions_output=decisions,
                    selections_output=selections,
                    manifest_output=manifest,
                    generated_at=self.plan_manifest["generated_at"],
                )
            )
            for actual, rebuilt in (
                (self.decisions_path, decisions),
                (self.selections_path, selections),
                (self.plan_manifest_path, manifest),
            ):
                self.assertEqual(actual.read_bytes(), rebuilt.read_bytes())


class ReferenceAdmissionPublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.decisions_path = REFERENCE / "gated/reference_media_gate_decisions.parquet"
        cls.selections_path = REFERENCE / "gated/reference_download_selections.parquet"
        cls.objects_path = REFERENCE / "gated/reference_media_objects.parquet"
        cls.plan_manifest_path = REFERENCE / "reference_gate_plan_manifest.json"
        cls.admission_manifest_path = REFERENCE / "reference_admission_manifest.json"
        cls.download_report_path = REFERENCE / "reference_media_download_report.json"
        cls.selections = pq.read_table(cls.selections_path)
        cls.objects = pq.read_table(cls.objects_path)
        cls.manifest = json.loads(cls.admission_manifest_path.read_text())
        cls.report = json.loads(cls.download_report_path.read_text())

    def test_media_objects_cover_selection_and_pass_automated_gates(self) -> None:
        selected_ids = set(self.selections.column("reference_media_id").to_pylist())
        rows = self.objects.to_pylist()
        valid = [row for row in rows if row["decode_status"] == "valid"]
        failed = [row for row in rows if row["decode_status"] != "valid"]
        self.assertEqual(len(rows), 2_910)
        self.assertEqual({row["reference_media_id"] for row in rows}, selected_ids)
        self.assertEqual(
            {row["schema_version"] for row in rows},
            {self.builder.MEDIA_OBJECT_SCHEMA_VERSION},
        )
        self.assertEqual(len(valid), 2_906)
        self.assertEqual(len(failed), 4)
        self.assertEqual({row["decode_status"] for row in failed}, {"download_failed"})
        self.assertEqual({row["quarantine_reason"] for row in failed}, {"http_status_404"})
        self.assertTrue(
            all(
                row["source_object_uri"] is None
                and row["sha256"] is None
                and row["perceptual_hash"] is None
                for row in failed
            )
        )
        self.assertEqual({row["licence_policy_status"] for row in rows}, {"allowed"})
        self.assertTrue(all(row["download_attempt_count"] >= 1 for row in rows))
        self.assertTrue(all(row["source_byte_count"] > 0 for row in valid))
        self.assertTrue(all(row["decoded_width"] > 0 for row in valid))
        self.assertTrue(all(row["decoded_height"] > 0 for row in valid))
        self.assertTrue(
            all(
                row["sha256"].startswith("sha256:")
                and len(row["sha256"]) == len("sha256:") + 64
                and row["perceptual_hash"].startswith("dhash128-v1:")
                and len(row["perceptual_hash"]) == len("dhash128-v1:") + 32
                for row in valid
            )
        )
        self.assertTrue(
            all(
                row["source_object_uri"].startswith(
                    "cache/reference/v1/downloads/source_objects/sha256/"
                )
                for row in valid
            )
        )

    def test_download_report_and_admission_manifest_reconcile(self) -> None:
        self.assertEqual(
            self.report["schema_version"],
            self.builder.DOWNLOAD_REPORT_SCHEMA_VERSION,
        )
        self.assertEqual(self.report["status"], "complete_with_errors")
        self.assertEqual(self.report["counts"]["selected"], 2_910)
        self.assertEqual(self.report["counts"]["committed"], 2_906)
        self.assertEqual(self.report["counts"]["quarantined"], 4)
        self.assertEqual(self.report["counts"]["retries"], 0)
        self.assertEqual(self.report["quarantine_reason_counts"], {"http_status_404": 4})
        self.assertEqual(
            self.manifest["schema_version"],
            self.builder.ADMISSION_MANIFEST_SCHEMA_VERSION,
        )
        self.assertEqual(self.manifest["counts"]["human_verified_media"], 0)
        self.assertEqual(self.manifest["counts"]["provisional_support_candidates"], 2_906)
        self.assertEqual(self.manifest["counts"]["download_or_decode_failures"], 4)
        self.assertFalse(
            self.manifest["policy"]["source_media_bytes_committed_to_git"]
        )
        pack = json.loads((PACK / "manifest.json").read_text())
        state = pack["reference_state"]
        self.assertEqual(state["status"], self.manifest["status"])
        self.assertEqual(
            state["import_status"], "candidate_metadata_imported_no_media_downloads"
        )
        self.assertEqual(state["images_downloaded"], 2_906)
        self.assertEqual(state["download_or_decode_failures"], 4)
        self.assertEqual(state["human_verified_media"], 0)
        self.assertEqual(
            state["admission_manifest_sha256"],
            self.builder.sha256_file(self.admission_manifest_path),
        )
        for name, path in (
            ("gate_decisions", self.decisions_path),
            ("download_selections", self.selections_path),
            ("media_objects", self.objects_path),
            ("gate_plan_manifest", self.plan_manifest_path),
            ("download_report", self.download_report_path),
        ):
            entry = self.manifest["artifacts"][name]
            self.assertEqual(entry["physical_sha256"], self.builder.sha256_file(path))
            self.assertEqual(entry["physical_bytes"], path.stat().st_size)

    def test_source_image_collection_is_not_in_reference_pack(self) -> None:
        image_suffixes = {".avif", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".webp"}
        tracked_evidence = [path for path in REFERENCE.rglob("*") if path.is_file()]
        self.assertFalse(
            [path for path in tracked_evidence if path.suffix.casefold() in image_suffixes]
        )

    def test_publication_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            objects = temporary / self.objects_path.name
            report = temporary / self.download_report_path.name
            manifest = temporary / self.admission_manifest_path.name
            pack = temporary / "manifest.json"
            pack.write_bytes((PACK / "manifest.json").read_bytes())
            self.builder.publish(
                argparse.Namespace(
                    plan_manifest=self.plan_manifest_path,
                    decisions=self.decisions_path,
                    selections=self.selections_path,
                    media_objects=self.objects_path,
                    media_objects_output=objects,
                    download_report=self.download_report_path,
                    download_report_output=report,
                    manifest_output=manifest,
                    pack_manifest=pack,
                    generated_at=self.manifest["generated_at"],
                )
            )
            for actual, rebuilt in (
                (self.objects_path, objects),
                (self.download_report_path, report),
                (self.admission_manifest_path, manifest),
                (PACK / "manifest.json", pack),
            ):
                self.assertEqual(actual.read_bytes(), rebuilt.read_bytes())


if __name__ == "__main__":
    unittest.main()
