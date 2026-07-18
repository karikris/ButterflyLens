from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies/layered-consensus.md"


class LayeredConsensusPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = POLICY.read_text(encoding="utf-8")
        cls.flat = " ".join(cls.text.split())

    def test_three_layers_and_versioned_method_are_explicit(self) -> None:
        for term in (
            "butterflylens-layered-consensus-policy:v1.0.0",
            "butterflylens-layered-consensus:v1.0.0",
            "Community evidence",
            "Qualified consensus",
            "Release consensus",
        ):
            self.assertIn(term, self.flat)

    def test_community_is_unweighted_and_weighted_majority_is_not_truth(self) -> None:
        self.assertIn("unweighted count", self.text)
        self.assertIn("weighted majority", self.text)
        self.assertIn("never resolves disagreement", self.text)
        self.assertIn("never enter reliability or consensus truth", self.flat)

    def test_dissent_and_exact_independent_adjudication_are_preserved(self) -> None:
        for term in (
            "independent qualified adjudicator",
            "every exact conflicting decisive event fingerprint",
            "source dissent retained",
            "does not rewrite the unweighted community",
        ):
            self.assertIn(term, self.flat)

    def test_release_requires_all_gates_and_cannot_override_conflict(self) -> None:
        for term in (
            "rights",
            "provenance",
            "conflict-resolution",
            "quality",
            "expert",
            "release-authorization",
            "cannot mark unresolved human evidence as resolved",
        ):
            self.assertIn(term, self.flat)


if __name__ == "__main__":
    unittest.main()
