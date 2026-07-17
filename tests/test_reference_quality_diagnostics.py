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
    path = ROOT / "scripts/build_reference_quality_diagnostics.py"
    spec = importlib.util.spec_from_file_location("quality_builder", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferenceQualityDiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import pyarrow.parquet as pq
        except ImportError as error:
            raise unittest.SkipTest("locked PyArrow dependency is not installed") from error
        cls.builder = load_builder()
        cls.pq = pq
        cls.output = REFERENCE / "gated/reference_quality_diagnostics.parquet"
        cls.manifest_path = REFERENCE / "reference_quality_manifest.json"
        cls.rows = pq.read_table(cls.output).to_pylist()
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_all_accepted_species_have_one_diagnostic(self) -> None:
        self.assertEqual(len(self.rows), 463)
        self.assertEqual(
            len({row["butterflylens_taxon_key"] for row in self.rows}), 463
        )
        self.assertEqual(
            Counter(row["coverage_status"] for row in self.rows),
            {
                "provisional_decode_only": 237,
                "no_candidate_media": 126,
                "no_automated_gate_eligible_media": 100,
            },
        )

    def test_counts_reconcile_without_model_or_human_evidence(self) -> None:
        self.assertEqual(sum(row["selected_count"] for row in self.rows), 2_910)
        self.assertEqual(sum(row["valid_decode_count"] for row in self.rows), 2_906)
        self.assertEqual(
            sum(row["download_or_decode_failure_count"] for row in self.rows), 4
        )
        self.assertEqual(sum(row["human_verified_count"] for row in self.rows), 0)
        self.assertEqual(sum(row["yoloe_routed_count"] for row in self.rows), 0)
        self.assertEqual(sum(row["yoloe_pending_count"] for row in self.rows), 2_906)
        self.assertEqual(sum(row["bioclip_embedding_count"] for row in self.rows), 0)
        self.assertEqual(sum(row["species_prototype_count"] for row in self.rows), 0)
        self.assertNotIn("quality_score", self.rows[0])
        self.assertNotIn("accuracy", self.rows[0])

    def test_fingerprints_manifest_and_root_state_reconcile(self) -> None:
        for row in self.rows:
            payload = {
                key: value
                for key, value in row.items()
                if key not in {"schema_version", "evidence_fingerprint"}
            }
            self.assertEqual(
                row["evidence_fingerprint"], self.builder.semantic_digest(payload)
            )
        artifact = self.manifest["artifact"]
        self.assertEqual(artifact["physical_sha256"], self.builder.sha256_file(self.output))
        self.assertFalse(self.manifest["policy"]["quality_score_computed"])
        self.assertFalse(self.manifest["policy"]["release_ready"])
        pack = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        state = pack["reference_state"]
        self.assertEqual(state["quality_diagnostics_sha256"], artifact["physical_sha256"])
        self.assertEqual(
            state["quality_manifest_sha256"],
            self.builder.sha256_file(self.manifest_path),
        )

    def test_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / self.output.name
            manifest = temporary / self.manifest_path.name
            pack = temporary / "manifest.json"
            pack.write_bytes((PACK / "manifest.json").read_bytes())
            self.builder.build(
                argparse.Namespace(
                    taxa=PACK / "taxa.jsonl",
                    decisions=REFERENCE / "gated/reference_media_gate_decisions.parquet",
                    selections=REFERENCE / "gated/reference_download_selections.parquet",
                    media_objects=REFERENCE / "gated/reference_media_objects.parquet",
                    yoloe_manifest=REFERENCE / "reference_yoloe_readiness_manifest.json",
                    bioclip_status=REFERENCE / "reference_bioclip_status.json",
                    output=output,
                    manifest_output=manifest,
                    pack_manifest=pack,
                    generated_at=self.manifest["generated_at"],
                )
            )
            self.assertEqual(self.output.read_bytes(), output.read_bytes())
            self.assertEqual(self.manifest_path.read_bytes(), manifest.read_bytes())
            self.assertEqual((PACK / "manifest.json").read_bytes(), pack.read_bytes())


if __name__ == "__main__":
    unittest.main()
