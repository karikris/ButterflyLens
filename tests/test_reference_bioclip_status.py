import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/packs/australian_butterflies/v1"
STATUS = PACK / "references/v1/reference_bioclip_status.json"


class ReferenceBioCLIPStatusTests(unittest.TestCase):
    def test_bioclip_is_explicitly_unfinished_without_model_artifacts(self) -> None:
        status = json.loads(STATUS.read_text(encoding="utf-8"))

        self.assertEqual(
            status["status"], "skipped_unfinished_by_goal_instruction"
        )
        self.assertEqual(
            status["artifact_counts"],
            {"bioclip_embeddings": 0, "species_prototypes": 0, "support_rows": 0},
        )
        self.assertFalse(status["model_execution"]["runtime_loaded"])
        self.assertFalse(status["model_execution"]["embeddings_produced"])
        self.assertIsNone(status["model_execution"]["model_id"])
        self.assertIsNone(status["model_execution"]["checkpoint"])
        self.assertIsNone(status["model_execution"]["weights_sha256"])

    def test_pack_manifest_binds_the_skip_record(self) -> None:
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        state = manifest["reference_state"]
        digest = hashlib.sha256(STATUS.read_bytes()).hexdigest()

        self.assertEqual(
            state["bioclip_status"], "skipped_unfinished_by_goal_instruction"
        )
        self.assertEqual(state["bioclip_status_sha256"], digest)
        self.assertEqual(
            state["bioclip_status_path"],
            "references/v1/reference_bioclip_status.json",
        )


if __name__ == "__main__":
    unittest.main()
