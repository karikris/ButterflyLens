from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECK_PATH = ROOT / "PITCH_DECK.md"
DEVPOST_PATH = ROOT / "DEVPOST_ENTRY.md"
README_PATH = ROOT / "README.md"
SNAPSHOT_PATH = ROOT / "data/submission/v1/submitted_snapshot.json"
QUALITY_PATH = ROOT / "apps/web/src/quality/submittedQualityProjection.json"

WINNING_LINE = (
    "ButterflyLens brings machine screening, community expertise, and Australia’s "
    "national biodiversity evidence together to reveal where public imagery could "
    "strengthen butterfly knowledge."
)


def _normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n> ", " ")).strip()


class SubmissionEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.deck = DECK_PATH.read_text(encoding="utf-8")
        cls.devpost = DEVPOST_PATH.read_text(encoding="utf-8")
        cls.readme = README_PATH.read_text(encoding="utf-8")
        cls.snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        cls.quality = json.loads(QUALITY_PATH.read_text(encoding="utf-8"))

    def test_winning_line_is_exact_in_both_submission_documents(self) -> None:
        for document in (self.deck, self.devpost):
            normalized = _normalized(document)
            self.assertIn(WINNING_LINE, normalized)
            self.assertEqual(normalized.count(WINNING_LINE), 2 if document == self.deck else 1)

    def test_deck_has_ten_ordered_complete_slides(self) -> None:
        headings = re.findall(r"^## Slide (\d+) — (.+)$", self.deck, flags=re.MULTILINE)
        self.assertEqual([int(number) for number, _ in headings], list(range(1, 11)))
        self.assertEqual(self.deck.count("### On slide"), 10)
        self.assertEqual(self.deck.count("### Speaker note"), 10)
        self.assertEqual(self.deck.count("### Visual and proof"), 10)
        for required_title in (
            "Look closer",
            "The evidence gap is a workflow problem",
            "The working product fails closed",
            "Architecture: evidence before inference",
            "Bounded model explains; Codex makes the system inspectable",
            "Measured Submitted evidence",
            "What is real, and what remains to earn",
        ):
            self.assertIn(required_title, [title for _, title in headings])

    def test_devpost_has_paste_ready_sections(self) -> None:
        required = [
            "Project name",
            "Tagline",
            "Category",
            "Winning line",
            "Short description",
            "Inspiration",
            "What it does",
            "How we built it",
            "How we used Bounded model",
            "How we used Codex",
            "Challenges we ran into",
            "Accomplishments we are proud of",
            "What we learned",
            "What is next",
            "Public links",
            "Technology",
            "Credits, data, and licences",
            "Public claims ledger",
            "Submission preflight",
        ]
        headings = re.findall(r"^## (.+)$", self.devpost, flags=re.MULTILINE)
        for title in required:
            self.assertIn(title, headings)
        self.assertIn("Work and Productivity", self.devpost)
        self.assertIn("Discover, review, and strengthen Australia’s butterfly data.", self.devpost)

    def test_public_numbers_match_the_frozen_artifacts(self) -> None:
        counts = self.snapshot["ala_baseline"]["counts"]
        flickr = self.snapshot["flickr_query_plan"]["counts"]
        expected = {
            "463": self.snapshot["pack"]["accepted_species"],
            "236,897": counts["selected_occurrence_rows"],
            "230,027": counts["spatially_eligible_rows"],
            "23,744": counts["aggregate_cell_rows"],
            "1,876": flickr["query_definitions"],
            "1,754": flickr["physical_requests"],
            "2,906": self.quality["referenceDiagnostics"]["validDecodes"],
        }
        self.assertEqual(self.quality["referenceDiagnostics"]["humanVerifiedSpecies"], 0)
        for rendered, value in expected.items():
            self.assertEqual(rendered, f"{value:,}")
            self.assertIn(rendered, self.deck)
        for rendered in ("463", "236,897", "1,876", "1,754", "2,906"):
            self.assertIn(rendered, self.devpost)
        for document in (self.deck, self.devpost):
            self.assertIn("0 human-verified species", document)
            self.assertNotIn("50,000", document)
            self.assertNotIn("50000", document)

    def test_roles_and_fail_closed_boundaries_are_explicit(self) -> None:
        for document in (self.deck, self.devpost):
            normalized = _normalized(document)
            for phrase in (
                "Search results are hypotheses—not biodiversity records.",
                "Model not invoked",
                "YOLOE and BioCLIP",
                "public occurrence layer",
                "representative quality",
                "public YouTube",
            ):
                self.assertIn(phrase, normalized)
            self.assertIn("Bounded model", document)
            self.assertIn("Codex", document)
            self.assertIn("unfinished", document.lower())

    def test_links_are_public_and_readme_exposes_the_materials(self) -> None:
        for url in (
            "https://karikris.github.io/ButterflyLens/",
            "https://karikris.github.io/ButterflyLens/#verify",
            "https://karikris.github.io/ButterflyLens/#explore",
            "https://github.com/karikris/ButterflyLens",
        ):
            self.assertIn(url, self.devpost)
        self.assertNotRegex(self.devpost, r"https://(?:www\.)?(?:youtube\.com|youtu\.be)/")
        for link in (
            "[10-slide pitch deck](PITCH_DECK.md)",
            "[Devpost entry copy](DEVPOST_ENTRY.md)",
            "[2:48 video production script](DEMO_VIDEO.md)",
        ):
            self.assertIn(link, self.readme)
        for path in ("JUDGE_GUIDE.md", "PITCH_DECK.md", "DEVPOST_ENTRY.md", "DEMO_VIDEO.md"):
            self.assertTrue((ROOT / path).is_file(), path)

    def test_copy_does_not_claim_unfinished_outputs(self) -> None:
        normalized = _normalized(self.devpost)
        self.assertIn("not ready to submit as complete", normalized)
        self.assertIn("not yet available — public YouTube upload required", normalized)
        self.assertIn("No Flickr API call is part of this goal", normalized)
        self.assertIn("does not claim a live public database", normalized.lower())
        self.assertIn("overall scientific/data release readiness", normalized)


if __name__ == "__main__":
    unittest.main()
