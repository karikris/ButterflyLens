from pathlib import Path
import unittest


POLICY = (
    Path(__file__).resolve().parents[1] / "policies/reviewer-reliability.md"
).read_text(encoding="utf-8")
NORMALIZED_POLICY = " ".join(POLICY.split())


class ReviewerReliabilityPolicyTests(unittest.TestCase):
    def test_all_ten_normative_rules_are_present(self) -> None:
        for number in range(1, 11):
            self.assertIn(f"{number}. **", POLICY)

    def test_equal_weight_thresholds_domain_shrinkage_and_caps_are_exact(self) -> None:
        for phrase in (
            "weight `1.0`",
            "20 scorable control attempts",
            "5 positive and 5 negative controls",
            "10 independently overlapping items",
            "5 overlaps with an independent adjudication",
            "butterfly family, life stage, and visual domain",
            "shrink every eligible estimate toward `1.0`",
            "clamped to `[0.5, 2.0]`",
        ):
            self.assertIn(phrase, NORMALIZED_POLICY)

    def test_model_and_majority_shortcuts_are_forbidden(self) -> None:
        self.assertIn("No model-derived reliability", POLICY)
        self.assertIn("Agreement with BioCLIP, YOLOE", POLICY)
        self.assertIn("No majority-as-truth shortcut", POLICY)
        self.assertIn("cannot define correctness, ground truth", POLICY)

    def test_dissent_privacy_and_dignity_are_mandatory(self) -> None:
        self.assertIn("Preserve minority dissent", POLICY)
        self.assertIn("Keep reliability private", POLICY)
        self.assertIn("Protect reviewer dignity", POLICY)
        self.assertIn("never labels a person “bad,”", POLICY)
        self.assertIn("appeal", POLICY)

    def test_policy_does_not_claim_estimator_implementation(self) -> None:
        self.assertIn(
            "estimation and consensus implementations remain separate tasks",
            NORMALIZED_POLICY,
        )
        self.assertIn("Task 9.3 must publish the exact estimator", NORMALIZED_POLICY)


if __name__ == "__main__":
    unittest.main()
