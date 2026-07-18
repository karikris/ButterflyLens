from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policies/representative-audit.md"


class RepresentativeAuditPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = POLICY.read_text(encoding="utf-8")

    def test_representative_and_targeted_lanes_are_explicitly_separate(self) -> None:
        self.assertIn("representative_audit", self.text)
        self.assertIn("targeted_failure_discovery", self.text)
        self.assertIn("must never be reported as a population-quality estimate", self.text)

    def test_required_design_evidence_and_estimators_are_named(self) -> None:
        for phrase in (
            "inclusion probabilities",
            "sampling-frame fingerprint",
            "owner_id",
            "observation_id",
            "Hájek weighted proportion",
            "Kish weight-inequality diagnostic",
            "grouped interval",
            "2,000 replicates",
        ):
            self.assertIn(phrase, self.text)

    def test_unfinished_model_work_cannot_enter_quality_votes(self) -> None:
        self.assertIn("YOLOE and BioCLIP remain unfinished", self.text)
        self.assertIn("Model output is never an audit vote", self.text)


if __name__ == "__main__":
    unittest.main()
