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
    path = ROOT / "scripts/build_reference_yoloe_readiness.py"
    spec = importlib.util.spec_from_file_location(
        "build_reference_yoloe_readiness", path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceYOLOEReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.selections_path = REFERENCE / "gated/reference_download_selections.parquet"
        cls.observations_path = REFERENCE / "imported/reference_observations.parquet"
        cls.objects_path = REFERENCE / "gated/reference_media_objects.parquet"
        cls.admission_path = REFERENCE / "reference_admission_manifest.json"
        cls.readiness_path = REFERENCE / "gated/reference_yoloe_readiness.parquet"
        cls.manifest_path = REFERENCE / "reference_yoloe_readiness_manifest.json"
        cls.rows = pq.read_table(cls.readiness_path)
        cls.manifest = json.loads(cls.manifest_path.read_text())

    def test_every_selected_outcome_has_one_fail_closed_readiness_row(self) -> None:
        selected = self.pq.read_table(
            self.selections_path, columns=["reference_media_id"]
        ).column(0).to_pylist()
        rows = self.rows.to_pylist()
        self.assertEqual(len(rows), 2_910)
        self.assertEqual({row["reference_media_id"] for row in rows}, set(selected))
        self.assertEqual({row["schema_version"] for row in rows}, {self.builder.SCHEMA_VERSION})
        self.assertEqual({row["source"] for row in rows}, {"iNaturalist"})
        self.assertEqual({row["routing_status"] for row in rows}, {"blocked_not_executed"})
        self.assertEqual({row["upstream_router_source_supported"] for row in rows}, {False})
        self.assertEqual({row["human_verification_status"] for row in rows}, {"unreviewed"})
        self.assertNotIn("route", self.rows.column_names)
        self.assertNotIn("detection_route", self.rows.column_names)
        for row in rows:
            payload = {
                key: value
                for key, value in row.items()
                if key not in {"schema_version", "readiness_fingerprint"}
            }
            self.assertEqual(row["readiness_fingerprint"], self.builder.fingerprint(payload))

    def test_decode_failures_and_runtime_blockers_remain_explicit(self) -> None:
        rows = self.rows.to_pylist()
        self.assertEqual(
            Counter(row["decode_status"] for row in rows),
            {"valid": 2_906, "download_failed": 4},
        )
        self.assertTrue(
            all(
                "pinned_reference_router_accepts_gbif_only" in row["blocking_reasons"]
                and "audited_yoloe_runtime_unavailable" in row["blocking_reasons"]
                and "verified_yoloe_checkpoint_unavailable" in row["blocking_reasons"]
                for row in rows
            )
        )
        failed = [row for row in rows if row["decode_status"] != "valid"]
        self.assertEqual(len(failed), 4)
        self.assertTrue(
            all(
                "media_object_not_decoded:download_failed" in row["blocking_reasons"]
                and row["content_sha256"] is None
                and row["source_object_uri"] is None
                for row in failed
            )
        )

    def test_manifest_records_upstream_live_data_and_model_blockers(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["schema_version"], self.builder.MANIFEST_SCHEMA_VERSION)
        self.assertEqual(manifest["status"], "blocked_not_executed")
        self.assertEqual(manifest["counts"]["images_routed"], 0)
        self.assertEqual(manifest["counts"]["human_verified_media"], 0)
        self.assertFalse(manifest["runtime"]["execution_attempted"])
        self.assertFalse(manifest["runtime"]["routes_or_detections_published"])
        self.assertEqual(manifest["upstream"]["pinned_biominer_sha"], self.builder.PINNED_BIOMINER_SHA)
        self.assertEqual(manifest["upstream"]["observed_biominer_sha"], self.builder.OBSERVED_BIOMINER_SHA)
        self.assertEqual(
            manifest["upstream"]["live_gbif_support_bank_status"],
            "pending_not_available_to_copy",
        )
        self.assertFalse(manifest["upstream"]["live_artifact_copied"])
        artifact = manifest["artifact"]
        self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(self.readiness_path))
        pack = json.loads((PACK / "manifest.json").read_text())
        state = pack["reference_state"]
        self.assertEqual(state["yoloe_status"], "blocked_not_executed")
        self.assertEqual(state["images_pending_yoloe"], 2_906)
        self.assertEqual(state["images_routed"], 0)

    def test_readiness_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / self.readiness_path.name
            manifest = temporary / self.manifest_path.name
            pack = temporary / "manifest.json"
            pack.write_bytes((PACK / "manifest.json").read_bytes())
            self.builder.build(
                argparse.Namespace(
                    selections=self.selections_path,
                    observations=self.observations_path,
                    media_objects=self.objects_path,
                    admission_manifest=self.admission_path,
                    output=output,
                    manifest_output=manifest,
                    pack_manifest=pack,
                    generated_at=self.manifest["generated_at"],
                )
            )
            for actual, rebuilt in (
                (self.readiness_path, output),
                (self.manifest_path, manifest),
                (PACK / "manifest.json", pack),
            ):
                self.assertEqual(actual.read_bytes(), rebuilt.read_bytes())


if __name__ == "__main__":
    unittest.main()
