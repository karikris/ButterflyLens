from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from scripts.freeze_submitted_snapshot import (
    SNAPSHOT_PATH,
    SnapshotFreezeError,
    build_submitted_snapshot,
    validate_snapshot_fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]


class SubmittedSnapshotFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    def test_checked_in_snapshot_is_exactly_reproducible(self) -> None:
        self.assertEqual(
            self.snapshot,
            build_submitted_snapshot(
                source_commit=self.snapshot["source"]["commit"],
                frozen_at=self.snapshot["frozen_at"],
            ),
        )
        validate_snapshot_fingerprint(self.snapshot)

    def test_ala_and_map_counts_retain_the_rights_boundary(self) -> None:
        ala = self.snapshot["ala_baseline"]
        self.assertEqual(ala["authority"], "ButterflyLens rebuilt baseline")
        self.assertEqual(ala["counts"]["selected_occurrence_rows"], 236_897)
        self.assertEqual(ala["counts"]["spatially_eligible_rows"], 230_027)
        self.assertEqual(ala["counts"]["aggregate_cell_rows"], 23_744)
        self.assertEqual(
            ala["rights"]["review_required_dataset_uids"],
            ["dr1097", "dr30019", "dr635"],
        )
        public = self.snapshot["map_counts"]["public_projection"]
        self.assertFalse(public["occurrence_layer_visible"])
        self.assertIsNone(public["displayed_occurrence_count"])
        self.assertIsNone(public["displayed_cell_count"])
        self.assertIsNone(public["admitted_flickr_candidate_count"])
        self.assertFalse(public["unavailable_is_zero"])

    def test_flickr_plan_is_complete_deterministic_and_unsent(self) -> None:
        plan = self.snapshot["flickr_query_plan"]
        self.assertEqual(plan["execution_state"], "planned_not_sent")
        self.assertEqual(plan["network_calls_made_by_freeze"], 0)
        self.assertEqual(
            plan["lane_fingerprint"],
            "044e5c09d13b5e4ab7f966b46c447a0c5e29fb6f12f02e449e0672b0a27ad524",
        )
        self.assertEqual(plan["counts"]["query_definitions"], 1_876)
        self.assertEqual(plan["counts"]["logical_associations"], 4_997)
        self.assertEqual(plan["counts"]["physical_requests"], 1_754)
        self.assertEqual(plan["counts"]["request_links"], 4_997)
        self.assertFalse(plan["active_external_fetch_included"])
        self.assertEqual(
            plan["global_out_of_range_state"],
            "blocked_pending_authoritative_global_source",
        )

    def test_pack_worker_and_model_versions_do_not_invent_runtime_state(self) -> None:
        self.assertEqual(self.snapshot["pack"]["pack_id"], "australian-butterflies-v1")
        self.assertEqual(self.snapshot["pack"]["version"], "v1")
        self.assertEqual(self.snapshot["pack"]["accepted_species"], 463)
        worker = self.snapshot["worker"]
        self.assertEqual(worker["state"], "unavailable")
        self.assertIsNone(worker["version"]["semantic_version"])
        self.assertRegex(worker["version"]["implementation"]["git_tree_sha"], r"^[0-9a-f]{40}$")
        self.assertIsNone(worker["identity_fingerprint"])
        self.assertEqual(worker["configured_models"], [])
        models = self.snapshot["models"]
        self.assertEqual(models["yoloe"]["status"], "blocked_not_executed")
        self.assertIsNone(models["yoloe"]["revision"])
        self.assertIsNone(models["yoloe"]["weights_sha256"])
        self.assertEqual(
            models["bioclip"]["status"], "skipped_unfinished_by_goal_instruction"
        )
        self.assertIsNone(models["bioclip"]["model_id"])
        self.assertFalse(models["openai_analyst"]["model_invoked"])
        self.assertEqual(models["openai_analyst"]["network_calls"], 0)

    def test_review_is_a_rights_cleared_local_draft_not_stored_truth(self) -> None:
        review = self.snapshot["review_state"]
        self.assertEqual(review["state"], "local_draft_only_no_stored_review")
        self.assertTrue(review["fixture_available"])
        self.assertEqual(review["fixture_rights"]["licenseName"], "CC BY-SA 4.0")
        self.assertEqual(review["stored_review_events"], 0)
        self.assertEqual(review["completed_consensus_records"], 0)
        self.assertEqual(review["representative_reviewed_sample"], 0)
        self.assertEqual(review["decisive_reviews"], 0)
        self.assertEqual(review["human_verified_media"], 0)
        self.assertFalse(review["community_writes_enabled"])
        self.assertFalse(review["scientific_claim_allowed"])

    def test_every_source_has_physical_and_git_identity(self) -> None:
        source_shas = self.snapshot["source_shas"]
        self.assertEqual(source_shas["hash_algorithms"]["physical"], "sha256")
        self.assertEqual(
            source_shas["hash_algorithms"]["git_objects"],
            "repository_object_format_sha1",
        )
        paths = [row["path"] for row in source_shas["artifacts"]]
        self.assertEqual(paths, list(dict.fromkeys(paths)))
        self.assertGreaterEqual(len(paths), 17)
        for row in source_shas["artifacts"]:
            self.assertRegex(row["physical_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["git_blob_sha"], r"^[0-9a-f]{40}$")
            self.assertRegex(row["last_changed_commit"], r"^[0-9a-f]{40}$")

    def test_fingerprint_rejects_tampering_and_release_stays_blocked(self) -> None:
        self.assertTrue(self.snapshot["immutable"])
        self.assertFalse(self.snapshot["release"]["release_ready"])
        self.assertEqual(
            self.snapshot["release"]["community_live_and_data_release"], "blocked"
        )
        tampered = deepcopy(self.snapshot)
        tampered["map_counts"]["public_projection"]["displayed_occurrence_count"] = 0
        with self.assertRaisesRegex(SnapshotFreezeError, "fingerprint mismatch"):
            validate_snapshot_fingerprint(tampered)


if __name__ == "__main__":
    unittest.main()
