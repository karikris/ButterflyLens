from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/packs/australian_butterflies/v1/references/v1"
PROJECTION = ROOT / "apps/web/src/quality/submittedQualityProjection.json"


class QualityDashboardProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
        cls.quality_path = REFERENCE / "reference_quality_manifest.json"
        cls.quality = json.loads(cls.quality_path.read_text(encoding="utf-8"))
        cls.bank = json.loads(
            (REFERENCE / "reference_bank_manifest.json").read_text(encoding="utf-8")
        )

    def test_source_fingerprints_and_authoritative_baseline_are_exact(self) -> None:
        provenance = self.projection["provenance"]
        self.assertEqual(
            provenance["qualityManifestSha256"],
            hashlib.sha256(self.quality_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            provenance["referenceBankFingerprint"],
            self.bank["reference_bank_fingerprint"],
        )
        self.assertEqual(
            provenance["authoritativeBaseline"],
            self.bank["policy"]["authoritative_ala_baseline"],
        )
        self.assertEqual(
            provenance["qualityManifestGeneratedAt"], self.quality["generated_at"]
        )

    def test_reference_counts_and_flags_are_a_lossless_projection(self) -> None:
        diagnostics = self.projection["referenceDiagnostics"]
        counts = self.quality["counts"]
        self.assertEqual(diagnostics["acceptedSpecies"], counts["accepted_species"])
        self.assertEqual(
            diagnostics["speciesWithValidDecodes"],
            counts["species_with_valid_decodes"],
        )
        self.assertEqual(diagnostics["humanVerifiedSpecies"], counts["human_verified"])
        self.assertEqual(diagnostics["validDecodes"], counts["valid_decodes"])
        self.assertEqual(
            {row["flagId"]: row["affectedSpecies"] for row in diagnostics["flags"]},
            counts["quality_flags"],
        )

    def test_release_blockers_are_projected_without_waiver(self) -> None:
        self.assertEqual(
            self.projection["releaseBlockers"], self.bank["release_blockers"]
        )
        self.assertFalse(self.quality["policy"]["release_ready"])
        self.assertFalse(self.bank["policy"]["release_ready"])

    def test_submitted_replay_withholds_unsupported_estimates(self) -> None:
        self.assertEqual(self.projection["status"], "unavailable")
        self.assertEqual(self.projection["reviewedSample"], 0)
        self.assertEqual(self.projection["decisiveReviews"], 0)
        self.assertIsNone(self.projection["precision"]["estimate"])
        self.assertIsNone(self.projection["precision"]["interval"])
        self.assertIsNone(self.projection["reviewerAgreement"]["pairwiseAgreement"])
        self.assertIsNone(self.projection["speciesQuality"]["estimate"])
        self.assertIsNone(
            self.projection["provenance"]["qualitySnapshotFingerprint"]
        )

    def test_targeted_and_unfinished_model_boundaries_remain_explicit(self) -> None:
        self.assertTrue(self.projection["targetedQueueSeparate"])
        self.assertFalse(self.projection["modelVoteIncluded"])
        self.assertFalse(self.projection["scientificClaimAllowed"])
        flag_ids = {
            row["flagId"] for row in self.projection["referenceDiagnostics"]["flags"]
        }
        self.assertIn("yoloe_unfinished", flag_ids)
        self.assertIn("bioclip_unfinished", flag_ids)
        self.assertEqual(
            self.bank["states"]["yoloe"], "blocked_not_executed"
        )
        self.assertEqual(
            self.bank["states"]["bioclip"],
            "skipped_unfinished_by_goal_instruction",
        )


if __name__ == "__main__":
    unittest.main()
