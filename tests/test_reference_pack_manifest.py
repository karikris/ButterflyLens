from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
REFERENCE = PACK / "references/v1"
MANIFEST = REFERENCE / "reference_bank_manifest.json"


def load_publisher():
    path = ROOT / "scripts/publish_reference_pack.py"
    spec = importlib.util.spec_from_file_location("reference_publisher", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReferencePackManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publisher = load_publisher()
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_inventory_is_closed_and_fingerprinted(self) -> None:
        expected = sorted(
            path.relative_to(REFERENCE).as_posix()
            for path in REFERENCE.rglob("*")
            if path.is_file() and path.name not in self.publisher.EXCLUDED_NAMES
        )
        artifacts = self.manifest["artifacts"]
        self.assertEqual([row["path"] for row in artifacts], expected)
        self.assertEqual(len(artifacts), 20)
        for row in artifacts:
            path = REFERENCE / row["path"]
            self.assertEqual(row["physical_bytes"], path.stat().st_size)
            self.assertEqual(row["physical_sha256"], self.publisher.sha256_file(path))

    def test_counts_and_unfinished_states_are_truthful(self) -> None:
        counts = self.manifest["counts"]
        self.assertEqual(counts["candidate_observations"], 12_980)
        self.assertEqual(counts["candidate_media"], 24_329)
        self.assertEqual(counts["selected_media"], 2_910)
        self.assertEqual(counts["valid_decodes"], 2_906)
        self.assertEqual(counts["human_verified_media"], 0)
        self.assertEqual(counts["yoloe_routes"], 0)
        self.assertEqual(counts["bioclip_embeddings"], 0)
        self.assertEqual(counts["species_prototypes"], 0)
        self.assertFalse(self.manifest["policy"]["flickr_api_calls_made"])
        self.assertFalse(self.manifest["policy"]["release_ready"])
        self.assertEqual(
            self.manifest["policy"]["authoritative_ala_baseline"],
            "ButterflyLens rebuilt baseline",
        )

    def test_root_manifest_binds_bank_manifest_and_fingerprint(self) -> None:
        pack = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        state = pack["reference_state"]
        digest = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        self.assertEqual(state["bank_manifest_sha256"], digest)
        self.assertEqual(
            state["bank_fingerprint"], self.manifest["reference_bank_fingerprint"]
        )
        artifact = pack["artifacts"]["references/v1/reference_bank_manifest.json"]
        self.assertEqual(artifact["physical_sha256"], digest)

    def test_publish_replay_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / MANIFEST.name
            pack = temporary / "manifest.json"
            pack.write_bytes((PACK / "manifest.json").read_bytes())
            self.publisher.publish(
                argparse.Namespace(
                    reference_dir=REFERENCE,
                    admission_manifest=REFERENCE / "reference_admission_manifest.json",
                    yoloe_manifest=REFERENCE / "reference_yoloe_readiness_manifest.json",
                    bioclip_status=REFERENCE / "reference_bioclip_status.json",
                    quality_manifest=REFERENCE / "reference_quality_manifest.json",
                    output=output,
                    pack_manifest=pack,
                    generated_at=self.manifest["generated_at"],
                )
            )
            self.assertEqual(MANIFEST.read_bytes(), output.read_bytes())
            self.assertEqual((PACK / "manifest.json").read_bytes(), pack.read_bytes())


if __name__ == "__main__":
    unittest.main()
