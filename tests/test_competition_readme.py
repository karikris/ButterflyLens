from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import unittest


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
GIF = ROOT / "assets" / "readme" / "butterflylens-live-map.gif"
SNAPSHOT = ROOT / "data" / "submission" / "v1" / "submitted_snapshot.json"


class CompetitionReadmeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = README.read_text(encoding="utf-8")
        cls.hero = cls.readme.split("\n## ", maxsplit=1)[0]
        cls.snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    def test_first_screen_contains_every_competition_requirement(self) -> None:
        required = (
            "# ButterflyLens",
            "Australia’s live butterfly evidence map",
            "assets/readme/butterflylens-live-map.gif",
            'width="560"',
            "Help Verify",
            "Open Live Map",
            "Submitted replay",
            "Current worker status",
            "Unavailable",
            "Measured result",
            "GPT-5.6",
            "Codex",
            "Architecture",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.hero)

    def test_hero_buttons_link_to_the_public_judge_routes(self) -> None:
        public = "https://karikris.github.io/ButterflyLens/"
        self.assertIn(f"[**Help Verify →**]({public}#verify)", self.hero)
        self.assertIn(f"[**Open Live Map →**]({public}#live)", self.hero)
        self.assertIn(f"[**Run Submitted Replay →**]({public})", self.hero)

    def test_measured_result_and_worker_state_match_the_frozen_snapshot(self) -> None:
        species = self.snapshot["pack"]["accepted_species"]
        self.assertEqual(species, 463)
        self.assertIn(f"**{species} accepted species**", self.hero)
        self.assertEqual(self.snapshot["worker"]["state"], "unavailable")
        self.assertIn("no authenticated heartbeat is attached", self.hero)
        self.assertIn("makes no model call", self.hero)
        self.assertNotIn("50,000", self.hero)
        self.assertNotIn("worker online", self.hero.lower())

    def test_architecture_keeps_optional_live_services_out_of_replay_dependency(self) -> None:
        for boundary in (
            "authoritative ALA baseline + unsent Flickr query plan",
            "optional M5 screening",
            "blind human review",
            "committed map/export",
            "not required to judge it",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, self.hero)

    def test_map_gif_is_small_fingerprinted_and_actually_animated(self) -> None:
        content = GIF.read_bytes()
        self.assertEqual(content[:6], b"GIF89a")
        self.assertEqual(struct.unpack_from("<HH", content, 6), (960, 540))
        self.assertEqual(content.count(b"\x21\xf9\x04"), 8)
        self.assertLessEqual(len(content), 500_000)
        self.assertEqual(len(content), 327_789)
        self.assertEqual(
            hashlib.sha256(content).hexdigest(),
            "223e3f21d0a82b41d801ef470edfe31b999ff21457d1949885ab56f5444ebc1d",
        )


if __name__ == "__main__":
    unittest.main()
