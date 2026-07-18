from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets/video/butterflylens-demo.v1.json"
CAPTIONS_PATH = ROOT / "assets/video/butterflylens-demo.en-AU.srt"
SCRIPT_PATH = ROOT / "DEMO_VIDEO.md"
README_PATH = ROOT / "README.md"

REQUIRED_SEQUENCE = [
    "ala_baseline",
    "flickr_live_stream",
    "m5_pipeline",
    "butterfly_verification",
    "map_update",
    "repeated_reviewers",
    "quality_interval",
    "gpt_5_6_analysis",
    "geographic_impact",
    "evidence_export",
    "codex_provenance",
]


def _milliseconds(value: str) -> int:
    hours, minutes, remainder = value.split(":")
    seconds, milliseconds = remainder.split(",")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds) * 1_000
        + int(milliseconds)
    )


def _caption_cues() -> list[tuple[int, int, str]]:
    blocks = re.split(r"\n\s*\n", CAPTIONS_PATH.read_text(encoding="utf-8").strip())
    cues: list[tuple[int, int, str]] = []
    expected_index = 1
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            raise AssertionError(f"invalid caption block: {block!r}")
        if int(lines[0]) != expected_index:
            raise AssertionError(f"expected caption {expected_index}, found {lines[0]}")
        match = re.fullmatch(
            r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
            lines[1],
        )
        if match is None:
            raise AssertionError(f"invalid caption time: {lines[1]!r}")
        cues.append((_milliseconds(match[1]), _milliseconds(match[2]), " ".join(lines[2:])))
        expected_index += 1
    return cues


class DemoVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.script = SCRIPT_PATH.read_text(encoding="utf-8")

    def test_manifest_pins_the_submitted_product_and_publication_boundary(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["schema_version"], "butterflylens-demo-video/v1")
        self.assertRegex(manifest["source_commit"], r"^[0-9a-f]{40}$")
        subprocess.run(
            ["git", "cat-file", "-e", f'{manifest["source_commit"]}^{{commit}}'],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(manifest["capture"]["status"], "not_recorded")
        self.assertFalse(manifest["capture"]["credentials_permitted"])
        self.assertFalse(manifest["capture"]["private_worker_telemetry_permitted"])
        self.assertFalse(manifest["capture"]["active_flickr_output_permitted"])
        self.assertEqual(manifest["audio"]["status"], "scripted_not_recorded")
        self.assertEqual(manifest["publication"]["status"], "not_uploaded")
        self.assertIsNone(manifest["publication"]["youtube_url"])
        self.assertTrue(manifest["publication"]["human_approval_required"])

    def test_timeline_is_exact_contiguous_and_in_required_sequence(self) -> None:
        manifest = self.manifest
        shots = manifest["shots"]
        self.assertEqual([shot["id"] for shot in shots], REQUIRED_SEQUENCE)
        self.assertEqual([shot["sequence"] for shot in shots], list(range(1, 12)))
        self.assertEqual(manifest["duration_ms"], 168_000)
        self.assertLess(manifest["duration_ms"], 180_000)
        self.assertGreaterEqual(
            manifest["duration_ms"], manifest["target_duration_ms"]["minimum"]
        )
        self.assertLessEqual(
            manifest["duration_ms"], manifest["target_duration_ms"]["maximum"]
        )
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["start_ms"], cursor, shot["id"])
            self.assertGreater(shot["end_ms"], shot["start_ms"], shot["id"])
            self.assertTrue(shot["visual_proof"], shot["id"])
            self.assertTrue(shot["truth_boundary"], shot["id"])
            cursor = shot["end_ms"]
        self.assertEqual(cursor, manifest["duration_ms"])

    def test_working_product_exceeds_two_thirds(self) -> None:
        manifest = self.manifest
        measured = sum(
            shot["end_ms"] - shot["start_ms"]
            for shot in manifest["shots"]
            if shot["working_product"]
        )
        self.assertEqual(measured, manifest["working_product_ms"])
        self.assertEqual(measured, 160_000)
        self.assertAlmostEqual(
            measured / manifest["duration_ms"],
            manifest["working_product_fraction"],
            places=9,
        )
        self.assertGreaterEqual(
            manifest["working_product_fraction"],
            manifest["required_working_product_fraction"],
        )

    def test_every_evidence_source_is_present_and_fingerprinted(self) -> None:
        for source in self.manifest["evidence_sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(digest, source["sha256"], source["path"])

    def test_captions_cover_the_full_cut_without_gaps_or_overlap(self) -> None:
        cues = _caption_cues()
        self.assertEqual(len(cues), 22)
        cursor = 0
        for start, end, text in cues:
            self.assertEqual(start, cursor)
            self.assertGreater(end, start)
            self.assertTrue(text.strip())
            words = re.findall(r"[\w’'-]+", text, flags=re.UNICODE)
            words_per_second = len(words) / ((end - start) / 1_000)
            self.assertLessEqual(words_per_second, 3.2, text)
            cursor = end
        self.assertEqual(cursor, self.manifest["duration_ms"])

    def test_script_names_required_roles_and_scientific_boundaries(self) -> None:
        normalized_script = re.sub(r"\s+", " ", self.script.replace("\n> ", " "))
        required = [
            "ALA baseline",
            "Flickr live stream",
            "M5 pipeline",
            "Butterfly verification",
            "Map update",
            "Repeated reviewers",
            "Quality interval",
            "GPT-5.6 analysis",
            "Geographic impact",
            "Evidence export",
            "Codex provenance",
            "Discovery candidate ≠ occurrence",
            "Draft review ≠ stored evidence ≠ map release",
            "unavailable—not zero",
            "Model not invoked",
            "does not mean biological absence",
            "no public YouTube URL",
        ]
        for phrase in required:
            self.assertIn(phrase, normalized_script)
        self.assertNotIn("50,000", self.script)
        self.assertNotIn("50000", self.script)

    def test_script_does_not_claim_the_video_is_complete(self) -> None:
        self.assertIn(
            "not recorded,\n> narrated, reviewed as a final cut, or uploaded",
            self.script,
        )
        self.assertIn("The final human-approved recording and public upload remain required.", self.script)
        self.assertIn("Do not label the script", self.script)

    def test_readme_links_the_video_packet_without_claiming_a_finished_video(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        first_screen = readme.split("## Judge the working product", maxsplit=1)[0]
        self.assertIn("[**Video Script →**](DEMO_VIDEO.md)", first_screen)
        self.assertNotIn("YouTube", first_screen)


if __name__ == "__main__":
    unittest.main()
