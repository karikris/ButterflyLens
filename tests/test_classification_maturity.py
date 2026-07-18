from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens_worker import (  # noqa: E402
    ClassificationMaturityError,
    available_state,
    build_classification_maturity,
    unavailable_state,
    validate_classification_maturity,
)


NOW = datetime(2026, 7, 18, 1, 0, tzinfo=timezone.utc)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def all_available(value: bool = True) -> dict[str, dict[str, object]]:
    fields = (
        "butterfly_detected",
        "species_candidate_available",
        "community_reviewed",
        "quality_estimate_available",
        "expert_reviewed",
        "release_ready",
    )
    return {
        field: available_state(value, evidence_fingerprints=[digest(field)])
        for field in fields
    }


class ClassificationMaturityTests(unittest.TestCase):
    def build(self, maturity: dict[str, dict[str, object]]) -> dict[str, object]:
        return build_classification_maturity(
            image_id="flickr:photo:fixture",
            source_record_fingerprint=digest("source"),
            observed_at=NOW,
            maturity=maturity,
        )

    def test_unfinished_models_are_unavailable_not_false(self) -> None:
        maturity = all_available(False)
        maturity["butterfly_detected"] = unavailable_state(
            "YOLOE is unfinished and was not run"
        )
        maturity["species_candidate_available"] = unavailable_state(
            "BioCLIP is unfinished and was not run"
        )
        projection = self.build(maturity)
        for field in ("butterfly_detected", "species_candidate_available"):
            state = projection["maturity"][field]  # type: ignore[index]
            self.assertEqual(state["status"], "unavailable")
            self.assertIsNone(state["value"])
        validate_classification_maturity(projection)

    def test_release_ready_requires_every_preceding_state_true(self) -> None:
        maturity = all_available()
        projection = self.build(maturity)
        self.assertTrue(projection["maturity"]["release_ready"]["value"])  # type: ignore[index]
        maturity["expert_reviewed"] = available_state(
            False, evidence_fingerprints=[digest("expert:no")]
        )
        with self.assertRaisesRegex(
            ClassificationMaturityError, "every preceding maturity state"
        ):
            self.build(maturity)

    def test_available_and_unavailable_shapes_fail_closed(self) -> None:
        maturity = all_available(False)
        maturity["quality_estimate_available"] = available_state(
            True, evidence_fingerprints=[]
        )
        with self.assertRaisesRegex(ClassificationMaturityError, "requires a boolean"):
            self.build(maturity)
        maturity = all_available(False)
        maturity["quality_estimate_available"] = {
            "status": "unavailable",
            "value": False,
            "reason": "not estimated",
            "evidence_fingerprints": [],
        }
        with self.assertRaisesRegex(ClassificationMaturityError, "null value"):
            self.build(maturity)

    def test_projection_is_deterministic_and_canonicalizes_evidence_order(self) -> None:
        maturity = all_available(False)
        maturity["community_reviewed"] = available_state(
            True,
            evidence_fingerprints=[digest("review:two"), digest("review:one")],
        )
        first = self.build(maturity)
        maturity["community_reviewed"] = available_state(
            True,
            evidence_fingerprints=[digest("review:one"), digest("review:two")],
        )
        self.assertEqual(first, self.build(maturity))

    def test_tampering_unknown_states_and_duplicate_evidence_are_rejected(self) -> None:
        projection = self.build(all_available(False))
        tampered = deepcopy(projection)
        tampered["maturity"]["community_reviewed"]["value"] = True  # type: ignore[index]
        with self.assertRaisesRegex(ClassificationMaturityError, "fingerprint mismatch"):
            validate_classification_maturity(tampered)
        maturity = all_available(False)
        maturity["invented_state"] = available_state(
            False, evidence_fingerprints=[digest("invented")]
        )
        with self.assertRaisesRegex(ClassificationMaturityError, "inventory"):
            self.build(maturity)
        maturity = all_available(False)
        repeated = digest("repeated")
        maturity["expert_reviewed"] = available_state(
            False, evidence_fingerprints=[repeated, repeated]
        )
        with self.assertRaisesRegex(ClassificationMaturityError, "repeat"):
            self.build(maturity)

    def test_projection_module_has_no_model_or_provider_execution(self) -> None:
        source = (
            ROOT
            / "services/worker/python/butterflylens_worker/classification_maturity.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "torch",
            "requests",
            "httpx",
            "aiohttp",
            "from_pretrained",
            "flickr.photos",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
