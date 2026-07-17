import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "FIRST_NATIONS_NAMES.md"


class FirstNationsNamePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = POLICY.read_text(encoding="utf-8")
        cls.folded = cls.policy.casefold()

    def test_required_assertion_dimensions_are_explicit(self) -> None:
        for term in (
            "language display name",
            "austlang code",
            "country/community",
            "cultural authority",
            "permitted use",
            "attribution",
            "query eligibility",
            "homonym risk",
            "review state",
            "retrieval date",
        ):
            self.assertIn(term, self.folded)

    def test_permissions_are_independent_and_blocked_by_default(self) -> None:
        for permission in (
            "private metadata storage",
            "public display",
            "search-query use",
            "redistribution",
            "research export",
            "derived/model use",
        ):
            self.assertIn(f"| {permission} | blocked |", self.folded)
        self.assertIn("approval for one purpose does not approve another", self.folded)

    def test_prohibited_shortcuts_are_named(self) -> None:
        for safeguard in (
            "machine-translate",
            "pan-aboriginal",
            "infer country/community",
            "model output",
            "majority review",
            "provider repetition",
            "aiatsis map",
        ):
            self.assertIn(safeguard, self.folded)

    def test_query_and_withdrawal_gates_are_explicit(self) -> None:
        self.assertIn("affirmative `query_use` permission", self.folded)
        self.assertIn("query term remains a", self.folded)
        self.assertIn("never becomes a species label", self.folded)
        for downstream in ("public pages", "query definitions", "caches", "exports"):
            self.assertIn(downstream, self.folded)

    def test_current_approved_count_is_zero(self) -> None:
        self.assertIn("approved assertions in the current pack: **0**", self.folded)
        self.assertIn("dataset is intentionally\nempty", self.folded)

    def test_primary_governance_sources_are_linked(self) -> None:
        for url in (
            "https://aiatsis.gov.au/research/ethical-research/code-ethics",
            "https://www.gida-global.org/careprinciples",
            "https://aiatsis.gov.au/research/languages/austlang",
            "https://localcontexts.org/labels/about-the-labels/",
        ):
            self.assertIn(url, self.policy)


if __name__ == "__main__":
    unittest.main()
