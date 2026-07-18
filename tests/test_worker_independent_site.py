from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
OPERATIONS = ROOT / "apps/web/src/operations"


class WorkerIndependentSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.snapshot = json.loads(
            (OPERATIONS / "submittedOperationsSnapshot.json").read_text(
                encoding="utf-8"
            )
        )
        cls.catalogue = json.loads(
            (ROOT / "apps/web/src/species/submittedSpeciesCatalogue.json").read_text(
                encoding="utf-8"
            )
        )
        cls.ala = json.loads(
            (
                ROOT
                / "data/packs/australian_butterflies/v1/ala/ala_snapshot_manifest.json"
            ).read_text(encoding="utf-8")
        )
        cls.review = json.loads(
            (ROOT / "apps/web/src/review/reviewMediaManifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_site_is_explicitly_available_without_worker(self) -> None:
        self.assertEqual(
            self.snapshot["site"],
            {
                "available": True,
                "committedDataQueryable": True,
                "workerRequired": False,
            },
        )
        self.assertEqual(self.snapshot["workerFallback"]["status"], "unavailable")
        self.assertIsNone(self.snapshot["workerFallback"]["heartbeatObservedAt"])

    def test_submitted_snapshot_matches_authoritative_catalogue(self) -> None:
        submitted = self.snapshot["submittedSnapshot"]
        self.assertEqual(submitted["snapshotId"], self.catalogue["catalogueId"])
        self.assertEqual(submitted["speciesCount"], self.catalogue["speciesCount"])
        self.assertEqual(
            submitted["artifactFingerprint"],
            self.catalogue["catalogueFingerprint"].removeprefix("sha256:"),
        )
        self.assertEqual(submitted["generatedAt"], self.catalogue["generatedAt"])

    def test_map_matches_rebuilt_ala_snapshot_and_preserves_rights_gate(self) -> None:
        map_snapshot = self.snapshot["map"]
        self.assertEqual(map_snapshot["snapshotId"], self.ala["snapshot_id"])
        self.assertEqual(
            map_snapshot["artifactFingerprint"], self.ala["snapshot_fingerprint"]
        )
        self.assertEqual(map_snapshot["generatedAt"], self.ala["generated_at"])
        self.assertEqual(
            map_snapshot["releaseState"],
            self.ala["rights"]["downstream_public_product_release_state"],
        )
        self.assertFalse(map_snapshot["occurrenceLayerVisible"])
        self.assertFalse(map_snapshot["absenceInferencePermitted"])
        encoded = json.dumps(map_snapshot, sort_keys=True)
        for forbidden in ("decimalLatitude", "decimalLongitude", "selected_occurrence_rows"):
            self.assertNotIn(forbidden, encoded)

    def test_review_route_matches_the_rights_cleared_bundled_fixture(self) -> None:
        review = self.snapshot["review"]
        self.assertTrue(review["available"])
        self.assertEqual(review["href"], "#verify")
        self.assertEqual(review["mediaSha256"], self.review["sha256"])

    def test_operations_surface_does_not_poll_or_execute_worker_code(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                OPERATIONS / "OperationsDashboard.tsx",
                OPERATIONS / "operationsModel.ts",
            )
        )
        for forbidden in (
            "fetch(",
            "XMLHttpRequest",
            "EventSource",
            "WebSocket",
            "supabase.auth",
            "worker.postMessage",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
