from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "JUDGE_GUIDE.md"
README = ROOT / "README.md"
SNAPSHOT = ROOT / "data/submission/v1/submitted_snapshot.json"
OPERATIONS = ROOT / "apps/web/src/operations/submittedOperationsSnapshot.json"
MONITORING = ROOT / "apps/web/src/operations/submittedMonitoringSnapshot.json"
QUALITY = ROOT / "apps/web/src/quality/submittedQualityProjection.json"
REPLAY = ROOT / "packages/openai/submitted-replays.v1.json"
MAP = ROOT / "apps/web/src/map/submittedMapSnapshot.json"


class JudgeGuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.guide = GUIDE.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        cls.operations = json.loads(OPERATIONS.read_text(encoding="utf-8"))
        cls.monitoring = json.loads(MONITORING.read_text(encoding="utf-8"))
        cls.quality = json.loads(QUALITY.read_text(encoding="utf-8"))
        cls.replay = json.loads(REPLAY.read_text(encoding="utf-8"))
        cls.map = json.loads(MAP.read_text(encoding="utf-8"))

    def test_readme_links_the_guide_from_its_first_screen(self) -> None:
        hero = self.readme.split("\n## ", maxsplit=1)[0]
        self.assertIn("[**Judge Guide →**](JUDGE_GUIDE.md)", hero)

    def test_route_has_exactly_eight_contiguous_steps_totalling_ninety_seconds(self) -> None:
        rows = re.findall(
            r"^\| ([1-8]) \| (\d):(\d{2})–(\d):(\d{2}) \| \*\*(.+?)\.\*\*",
            self.guide,
            flags=re.MULTILINE,
        )
        self.assertEqual(len(rows), 8)
        expected_actions = (
            "View the Australia map",
            "Compare ALA and Flickr",
            "Inspect one submitted ALA cell",
            "Review a butterfly image",
            "Watch community evidence update",
            "Inspect quality",
            "Ask the GPT-5.6 evidence route what is missing",
            "Inspect the live M5 worker",
        )
        previous_end = 0
        for index, (step, sm, ss, em, es, action) in enumerate(rows, 1):
            start = int(sm) * 60 + int(ss)
            end = int(em) * 60 + int(es)
            self.assertEqual(int(step), index)
            self.assertEqual(start, previous_end)
            self.assertEqual(action, expected_actions[index - 1])
            self.assertGreater(end, start)
            previous_end = end
        self.assertEqual(previous_end, 90)

    def test_route_uses_real_public_anchors_and_exact_stored_questions(self) -> None:
        for anchor in (
            "#live",
            "#operations",
            "#verify",
            "#contributors",
            "#quality",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(
                    f"https://karikris.github.io/ButterflyLens/{anchor}",
                    self.guide,
                )
        questions = {
            question
            for case in self.replay["cases"]
            for question in case["accepted_questions"]
        }
        for question in (
            "Can ALA and Flickr counts be compared yet?",
            "Which species should receive the next reference review?",
        ):
            self.assertIn(question, questions)
            self.assertIn(f"“{question}”", self.guide)

    def test_expected_counts_and_fingerprints_match_the_frozen_evidence(self) -> None:
        self.assertEqual(self.snapshot["pack"]["accepted_species"], 463)
        ala_counts = self.snapshot["ala_baseline"]["counts"]
        self.assertEqual(ala_counts["selected_occurrence_rows"], 236_897)
        self.assertEqual(ala_counts["spatially_eligible_rows"], 230_027)
        self.assertEqual(ala_counts["aggregate_cell_rows"], 23_744)
        self.assertEqual(ala_counts["dataset_resources"], 53)
        self.assertEqual(self.quality["referenceDiagnostics"]["validDecodes"], 2_906)
        self.assertEqual(self.quality["referenceDiagnostics"]["humanVerifiedSpecies"], 0)
        self.assertEqual(self.map["snapshotId"], "snapshot:submitted-ala-public-map-20260719")
        self.assertEqual(self.map["counts"]["rightsScreenedSelected"], 220_144)
        self.assertEqual(self.map["counts"]["mapEligible"], 213_310)
        self.assertEqual(self.map["counts"]["mapCells"], 630)
        for value in (
            self.snapshot["snapshot_fingerprint"],
            self.operations["submittedSnapshot"]["artifactFingerprint"],
            "236,897",
            "230,027",
            "23,744",
            "2,906",
            "220,144",
            "213,310",
            "630",
            self.map["snapshotFingerprint"],
        ):
            with self.subTest(value=value):
                self.assertIn(str(value), self.guide)

    def test_map_and_unavailable_services_are_documented_as_boundaries(self) -> None:
        self.assertFalse(
            self.snapshot["map_counts"]["public_projection"]["occurrence_layer_visible"]
        )
        self.assertIsNone(
            self.snapshot["map_counts"]["public_projection"]["displayed_cell_count"]
        )
        self.assertEqual(
            self.map["rights"]["state"],
            "public_projection_available_with_flagged_datasets_excluded",
        )
        self.assertFalse(self.map["policies"]["occurrenceCoordinatesPublished"])
        self.assertFalse(self.map["policies"]["absenceInferencePermitted"])
        self.assertEqual(self.monitoring["heartbeat"]["state"], "unavailable")
        self.assertIsNone(self.monitoring["heartbeat"]["observedAt"])
        normalized_guide = " ".join(self.guide.split())
        for phrase in (
            "The cell is evidence coverage, not a coverage-gap",
            "Only local draft state changes",
            "Model not invoked",
            "Current result: stop at step 1",
            "No authenticated live snapshot or M5 heartbeat is attached",
            "Unavailable is not offline, failed, or zero",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, normalized_guide)
        self.assertNotIn("50,000", self.guide)
        self.assertNotIn("worker online", self.guide.lower())

    def test_guide_contains_every_required_supporting_section(self) -> None:
        for heading in (
            "## The 90-second route",
            "## Expected Submitted state",
            "## Submitted versus Live",
            "## Optional live-worker path",
            "## Technical route",
            "## Rights, privacy, and provenance",
            "## Current limitations",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.guide)
        for local_link in re.findall(r"\[[^]]+\]\(([^):#]+\.md)\)", self.guide):
            with self.subTest(local_link=local_link):
                self.assertTrue((ROOT / local_link).is_file())


if __name__ == "__main__":
    unittest.main()
