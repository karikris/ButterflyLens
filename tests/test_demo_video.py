from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets/video/butterflylens-demo.v2.json"
CAPTIONS_PATH = ROOT / "assets/video/butterflylens-demo.v2.en-AU.srt"
LEGACY_MANIFEST_PATH = ROOT / "assets/video/butterflylens-demo.v1.json"
LEGACY_CAPTIONS_PATH = ROOT / "assets/video/butterflylens-demo.en-AU.srt"
SCRIPT_PATH = ROOT / "DEMO_VIDEO.md"
README_PATH = ROOT / "README.md"
MAP_SNAPSHOT_PATH = ROOT / "apps/web/src/map/submittedMapSnapshot.json"
SUBMITTED_SNAPSHOT_PATH = ROOT / "data/submission/v1/submitted_snapshot.json"
QUALITY_SNAPSHOT_PATH = ROOT / "apps/web/src/quality/submittedQualityProjection.json"
REPLAY_PATH = ROOT / "packages/openai/submitted-replays.v1.json"

LEGACY_MANIFEST_SHA256 = "2c4a5711dfc54bddd16c9fe4a4a53e683fa8d879dc7d0ad07f275fa530d57318"
LEGACY_CAPTIONS_SHA256 = "dccdcc81bfaf1df7374160dd085b8129ed0bc4abb053fc04014291cb67998e48"

REQUIRED_SEQUENCE = [
    "ala_baseline",
    "flickr_live_stream",
    "m5_pipeline",
    "butterfly_verification",
    "map_update",
    "repeated_reviewers",
    "quality_interval",
    "bounded_model_analysis",
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


def _git_bytes(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout


class DemoVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.script = SCRIPT_PATH.read_text(encoding="utf-8")
        cls.map_snapshot = json.loads(MAP_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        cls.submitted_snapshot = json.loads(
            SUBMITTED_SNAPSHOT_PATH.read_text(encoding="utf-8")
        )
        cls.quality_snapshot = json.loads(
            QUALITY_SNAPSHOT_PATH.read_text(encoding="utf-8")
        )
        cls.replays = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))

    def test_manifest_pins_the_submitted_product_and_publication_boundary(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["schema_version"], "butterflylens-demo-video/v2")
        self.assertRegex(manifest["source_commit"], r"^[0-9a-f]{40}$")
        subprocess.run(
            ["git", "cat-file", "-e", f'{manifest["source_commit"]}^{{commit}}'],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", manifest["source_commit"], "HEAD"],
            cwd=ROOT,
            check=True,
        )
        self.assertEqual(manifest["capture"]["status"], "not_recorded")
        self.assertFalse(manifest["capture"]["credentials_permitted"])
        self.assertFalse(manifest["capture"]["private_worker_telemetry_permitted"])
        self.assertFalse(manifest["capture"]["active_flickr_output_permitted"])
        self.assertFalse(manifest["capture"]["unfinished_model_output_permitted"])
        self.assertEqual(manifest["audio"]["status"], "scripted_not_recorded")
        self.assertEqual(manifest["publication"]["status"], "not_uploaded")
        self.assertIsNone(manifest["publication"]["youtube_url"])
        self.assertTrue(manifest["publication"]["human_approval_required"])

    def test_v1_packet_is_preserved_as_historical_evidence(self) -> None:
        self.assertEqual(
            hashlib.sha256(LEGACY_MANIFEST_PATH.read_bytes()).hexdigest(),
            LEGACY_MANIFEST_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(LEGACY_CAPTIONS_PATH.read_bytes()).hexdigest(),
            LEGACY_CAPTIONS_SHA256,
        )
        self.assertEqual(
            self.manifest["supersedes"]["manifest"],
            "assets/video/butterflylens-demo.v1.json",
        )
        self.assertIn("predates", self.manifest["supersedes"]["reason"])

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
            self.assertTrue(shot["capture_source_paths"], shot["id"])
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

    def test_every_evidence_source_matches_the_pinned_commit(self) -> None:
        commit = self.manifest["source_commit"]
        for source in self.manifest["evidence_sources"]:
            path = ROOT / source["path"]
            self.assertTrue(path.is_file(), source["path"])
            current_bytes = path.read_bytes()
            pinned_bytes = _git_bytes(commit, source["path"])
            self.assertEqual(current_bytes, pinned_bytes, source["path"])
            self.assertEqual(
                hashlib.sha256(pinned_bytes).hexdigest(),
                source["sha256"],
                source["path"],
            )

    def test_every_capture_source_exists_at_the_pinned_commit(self) -> None:
        commit = self.manifest["source_commit"]
        paths = {
            path
            for shot in self.manifest["shots"]
            for path in shot["capture_source_paths"]
        }
        for path in paths:
            self.assertTrue(_git_bytes(commit, path), path)

    def test_measured_claims_are_derived_from_pinned_artifacts(self) -> None:
        claims = self.manifest["measured_claims"]
        map_counts = self.map_snapshot["counts"]
        self.assertEqual(
            claims["authoritative_ala_selected_rows"],
            self.submitted_snapshot["ala_baseline"]["counts"]["selected_occurrence_rows"],
        )
        self.assertEqual(claims["rights_screened_selected_rows"], map_counts["rightsScreenedSelected"])
        self.assertEqual(claims["map_eligible_ala_rows"], map_counts["mapEligible"])
        self.assertEqual(claims["coarse_h3_cells"], map_counts["mapCells"])
        self.assertEqual(claims["rights_excluded_selected_rows"], map_counts["rightsExcludedSelected"])

        selected_scope = next(
            scope
            for scope in self.map_snapshot["scopes"]["h3"]
            if scope["scopeId"] == claims["selected_h3_scope_id"]
        )
        selected_cell = next(
            cell
            for cell in self.map_snapshot["cells"]
            if f'h3:3:{cell["cellId"]}' == claims["selected_h3_scope_id"]
        )
        self.assertEqual(claims["selected_h3_ala_rows"], selected_scope["count"])
        self.assertEqual(claims["selected_h3_ala_rows"], selected_cell["count"])
        self.assertEqual(
            claims["selected_h3_evidence_fingerprint"],
            f'sha256:{selected_cell["evidenceFingerprint"]}',
        )

        diagnostics = self.quality_snapshot["referenceDiagnostics"]
        self.assertEqual(claims["accepted_species"], diagnostics["acceptedSpecies"])
        self.assertEqual(claims["valid_reference_decodes"], diagnostics["validDecodes"])
        self.assertEqual(claims["human_verified_species"], diagnostics["humanVerifiedSpecies"])
        self.assertIsNone(claims["flickr_candidate_count"])
        self.assertIsNone(claims["ala_flickr_difference"])

        self.assertEqual(
            self.manifest["submitted_snapshot_fingerprint"],
            self.submitted_snapshot["snapshot_fingerprint"],
        )
        self.assertEqual(
            self.manifest["submitted_map_snapshot_fingerprint"],
            f'sha256:{self.map_snapshot["snapshotFingerprint"]}',
        )

    def test_analyst_shot_uses_the_map_grounded_model_free_replay(self) -> None:
        replay = next(
            case
            for case in self.replays["cases"]
            if "Can ALA and Flickr counts be compared yet?" in case["accepted_questions"]
        )
        statements = " ".join(claim["statement"] for claim in replay["response"]["claims"])
        self.assertIn("213,310", statements)
        self.assertIn("No completed immutable national Flickr candidate count", statements)
        self.assertIn("count difference is unavailable", statements)
        self.assertFalse(replay["response"]["replay"]["model_invoked"])
        self.assertEqual(replay["response"]["replay"]["response_calls"], 0)

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
            "Flickr candidate stream",
            "M5 pipeline",
            "Butterfly verification",
            "Map update boundary",
            "Repeated reviewers",
            "Quality interval",
            "Bounded model analysis",
            "Geographic impact",
            "Evidence export",
            "Codex provenance",
            "Discovery candidate ≠ occurrence",
            "Draft review ≠ stored evidence ≠ map release",
            "unavailable—not zero",
            "Model not invoked",
            "not biological absence",
            "no public YouTube URL",
        ]
        for phrase in required:
            self.assertIn(phrase, normalized_script)
        self.assertNotIn("50,000", self.script)
        self.assertNotIn("50000", self.script)
        self.assertNotIn("Occurrence layer withheld", self.script)
        self.assertNotIn("No selectable impact cell is released yet", self.script)

    def test_script_does_not_claim_the_video_is_complete(self) -> None:
        self.assertIn(
            "not recorded,\n> narrated, reviewed as a final cut, or uploaded",
            self.script,
        )
        self.assertIn(
            "The final human-approved recording and public upload remain required.",
            self.script,
        )
        self.assertIn("Do not label the script", self.script)

    def test_readme_links_the_video_packet_without_claiming_a_finished_video(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        first_screen = readme.split("## Judge the working product", maxsplit=1)[0]
        self.assertIn("[**Video Script →**](DEMO_VIDEO.md)", first_screen)
        self.assertNotIn("YouTube", first_screen)


if __name__ == "__main__":
    unittest.main()
