from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"
SHELL = WEB / "shell/PublicShell.tsx"
SHELL_CSS = WEB / "shell/publicShell.css"

EXPECTED_NAVIGATION = [
    ("Explore", "#explore"),
    ("Verify", "#verify"),
    ("Species", "#species"),
    ("Live", "#live"),
    ("Quality", "#quality"),
    ("Contributors", "#contributors"),
    ("Ask ButterflyLens", "#ask-butterflylens"),
    ("About", "#about"),
]


class PublicShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.shell = SHELL.read_text(encoding="utf-8")
        cls.css = SHELL_CSS.read_text(encoding="utf-8")

    def test_primary_navigation_is_exact_and_declared_once(self) -> None:
        actual = re.findall(
            r"\{ label: '([^']+)', href: '(#[a-z-]+)'(?:, current: true)? \}",
            self.shell,
        )
        self.assertEqual(actual, EXPECTED_NAVIGATION)
        self.assertEqual(self.shell.count('<nav className="primary-navigation"'), 1)

    def test_every_navigation_fragment_has_a_real_document_target(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                WEB / "App.tsx",
                WEB / "review/ReviewLanding.tsx",
                WEB / "quality/QualityDashboard.tsx",
                WEB / "species/SpeciesDirectory.tsx",
                WEB / "community/ContributorExperience.tsx",
                WEB / "analyst/AskButterflyLens.tsx",
                SHELL,
            )
        )
        target_ids = set(re.findall(r'\bid="([a-z-]+)"', source))
        self.assertTrue({href[1:] for _, href in EXPECTED_NAVIGATION} <= target_ids)

    def test_shell_navigation_reflows_without_a_duplicate_mobile_menu(self) -> None:
        self.assertRegex(
            self.css,
            r"(?s)\.primary-navigation\s*\{[^}]*overflow-x:\s*auto;",
        )
        self.assertIn("min-width: max-content", self.css)
        self.assertIn("@media (max-width: 820px)", self.css)
        self.assertIn("@media (max-width: 520px)", self.css)

    def test_skip_brand_and_navigation_targets_use_the_visual_contract(self) -> None:
        for selector in ("skip-link", "brand", "primary-navigation a"):
            self.assertRegex(
                self.css,
                rf"(?s)\.{re.escape(selector)}\s*\{{[^}}]*"
                r"min-height:\s*var\(--bl-target-min\);",
            )
        self.assertIn('<a className="skip-link" href="#main-content">', self.shell)
        self.assertIn('<main id="main-content" tabIndex={-1}>', self.shell)


if __name__ == "__main__":
    unittest.main()
