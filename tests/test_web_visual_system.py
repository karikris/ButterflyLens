from __future__ import annotations

import json
import math
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"
DESIGN = WEB / "design-system"
SHELL = WEB / "shell"
SPECIES = WEB / "species"
FLICKR = WEB / "flickr"
COMMUNITY = WEB / "community"
CONTRACT = DESIGN / "visualSystem.json"


class WebVisualSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.foundation = (DESIGN / "foundations.css").read_text(encoding="utf-8")
        cls.primitives = (DESIGN / "primitives.css").read_text(encoding="utf-8")
        cls.shell = (SHELL / "publicShell.css").read_text(encoding="utf-8")
        cls.species = (SPECIES / "speciesDirectory.css").read_text(encoding="utf-8")
        cls.flickr = (FLICKR / "flickrDisplayBoundary.css").read_text(encoding="utf-8")
        cls.community = (COMMUNITY / "contributorExperience.css").read_text(encoding="utf-8")
        cls.page = (WEB / "styles.css").read_text(encoding="utf-8")
        cls.all_css = "\n".join(
            (
                cls.foundation,
                cls.primitives,
                cls.shell,
                cls.species,
                cls.flickr,
                cls.community,
                cls.page,
            )
        )

    def test_contract_palette_is_exactly_projected_to_css(self) -> None:
        self.assertEqual(
            self.contract["schemaVersion"], "butterflylens-visual-system:v1.0.0"
        )
        for name, value in self.contract["palette"].items():
            self.assertRegex(
                self.foundation,
                rf"--{re.escape(name)}:\s*{re.escape(value)};",
                name,
            )
        index = (ROOT / "apps/web/index.html").read_text(encoding="utf-8")
        self.assertIn(
            f'<meta name="theme-color" content="{self.contract["browserThemeColor"]}"',
            index,
        )
        self.assertEqual(
            self.contract["browserThemeColor"],
            self.contract["palette"]["bl-eucalypt-850"],
        )

    def test_declared_text_pairs_meet_wcag_aa_contrast(self) -> None:
        palette = self.contract["palette"]
        threshold = self.contract["accessibility"]["normalTextMinimumContrast"]
        for foreground, background in self.contract["normalTextContrastPairs"]:
            ratio = contrast(palette[foreground], palette[background])
            self.assertGreaterEqual(ratio, threshold, (foreground, background, ratio))

    def test_no_gradient_or_scientific_image_filter_is_present(self) -> None:
        self.assertNotRegex(self.all_css.lower(), r"gradient\s*\(")
        self.assertNotRegex(self.all_css.lower(), r"\bfilter\s*:")
        self.assertFalse(self.contract["photography"]["pixelAlterationAllowed"])
        self.assertIn("bl-photo-frame", self.primitives)

    def test_focus_motion_forced_colour_and_target_rules_are_explicit(self) -> None:
        accessibility = self.contract["accessibility"]
        self.assertIn(
            f"outline: {accessibility['focusOutlineCssPixels']}px solid",
            self.foundation,
        )
        self.assertIn("@media (forced-colors: active)", self.foundation)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.foundation)
        self.assertIn(
            f"--bl-target-min: {accessibility['minimumTargetCssPixels'] / 16:g}rem",
            self.foundation,
        )

    def test_desktop_and_mobile_reflow_anchors_are_implemented(self) -> None:
        accessibility = self.contract["accessibility"]
        self.assertEqual(
            accessibility["responsiveViewports"],
            [
                {"width": 1280, "height": 720, "label": "desktop_judge_replay"},
                {"width": 390, "height": 844, "label": "mobile_portrait"},
            ],
        )
        self.assertIn(
            f"min-width: {accessibility['minimumViewportCssPixels'] / 16:g}rem",
            self.foundation,
        )
        for breakpoint in accessibility["responsiveBreakpointsCssPixels"]:
            self.assertIn(f"@media (max-width: {breakpoint}px)", self.page)
        main = (WEB / "main.tsx").read_text(encoding="utf-8")
        self.assertLess(
            main.index("./design-system/foundations.css"),
            main.index("./styles.css"),
        )


def contrast(first: str, second: str) -> float:
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def luminance(colour: str) -> float:
    channels = []
    for offset in (1, 3, 5):
        channel = int(colour[offset : offset + 2], 16) / 255
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else math.pow((channel + 0.055) / 1.055, 2.4)
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


if __name__ == "__main__":
    unittest.main()
