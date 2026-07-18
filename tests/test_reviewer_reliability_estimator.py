from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "packages/verification/python"))

from butterflylens_verification import (  # noqa: E402
    AdjudicatedResolution,
    ControlAttempt,
    PeerRating,
    ReliabilityDomain,
    ReliabilityEvidenceError,
    ReviewerOverlap,
    estimate_reviewer_reliability,
    reliability_storage_fields,
)


FIXTURE = json.loads(
    (ROOT / "tests/fixtures/reviewer_reliability_cases.json").read_text(
        encoding="utf-8"
    )
)
RECORDED_AT = "2026-07-18T02:30:00Z"
REVIEWER_ID = "reviewer:one"


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def domain() -> ReliabilityDomain:
    return ReliabilityDomain(**FIXTURE["domain"])


def evidence(case_name: str) -> tuple[list[ControlAttempt], list[ReviewerOverlap]]:
    case = FIXTURE[case_name]
    controls: list[ControlAttempt] = []
    index = 0
    for expected, actual_values in (
        ("yes", case["positive_actual"]),
        ("no", case["negative_actual"]),
    ):
        for actual in actual_values:
            controls.append(
                ControlAttempt(
                    item_id=f"control:{index:02d}",
                    control_kind=(
                        "known_butterfly" if expected == "yes" else "known_non_butterfly"
                    ),
                    expected_decision=expected,
                    actual_decision=actual,
                    control_fingerprint=digest(f"control-definition:{index}"),
                    event_fingerprint=digest(f"control-event:{index}"),
                )
            )
            index += 1
    overlaps: list[ReviewerOverlap] = []
    for overlap_index, row in enumerate(case["overlaps"]):
        reviewer_fingerprint = digest(f"reviewer-event:{overlap_index}")
        peer_fingerprint = digest(f"peer-event:{overlap_index}")
        adjudication = None
        if row["adjudicated"] is not None:
            adjudication = AdjudicatedResolution(
                adjudicator_id=f"reviewer:adjudicator-{overlap_index}",
                label=row["adjudicated"],
                event_fingerprint=digest(f"adjudication-event:{overlap_index}"),
                source_event_fingerprints=(reviewer_fingerprint, peer_fingerprint),
            )
        overlaps.append(
            ReviewerOverlap(
                item_id=f"overlap:{overlap_index:02d}",
                reviewer_label=row["reviewer"],
                reviewer_event_fingerprint=reviewer_fingerprint,
                peer_ratings=(
                    PeerRating(
                        reviewer_id=f"reviewer:peer-{overlap_index}",
                        label=row["peer"],
                        event_fingerprint=peer_fingerprint,
                    ),
                ),
                adjudication=adjudication,
            )
        )
    return controls, overlaps


def estimate(case_name: str = "estimated_case") -> dict[str, object]:
    controls, overlaps = evidence(case_name)
    return estimate_reviewer_reliability(
        reliability_id=f"reliability:{case_name.replace('_', '-')}",
        reviewer_id=REVIEWER_ID,
        domain=domain(),
        controls=controls,
        overlaps=overlaps,
        recorded_at=RECORDED_AT,
    )


class ReviewerReliabilityEstimatorTests(unittest.TestCase):
    def test_estimated_case_measures_every_required_metric(self) -> None:
        result = estimate()
        metrics = result["metrics"]
        self.assertEqual(result["availability"], "estimated")
        self.assertEqual(result["sample_count"], 30)
        self.assertEqual(result["control_count"], 20)
        self.assertAlmostEqual(metrics["control_accuracy"], 0.85)
        self.assertAlmostEqual(metrics["sensitivity"], 0.9)
        self.assertAlmostEqual(metrics["specificity"], 0.8)
        self.assertAlmostEqual(metrics["pairwise_agreement"], 0.8)
        self.assertAlmostEqual(metrics["adjudicated_overlap"], 0.8)
        self.assertIsInstance(metrics["krippendorff_alpha"], float)
        self.assertEqual(metrics["metric_blockers"], [])
        self.assertAlmostEqual(result["estimate"], 0.8)
        self.assertAlmostEqual(result["applied_weight"], 1.2)
        self.assertAlmostEqual(result["shrinkage_fraction"], 20 / 45)
        self.assertLess(result["interval"]["lower"], result["estimate"])
        self.assertGreater(result["interval"]["upper"], result["estimate"])

    def test_insufficient_evidence_returns_unavailable_equal_weight_boundary(self) -> None:
        result = estimate("insufficient_case")
        self.assertEqual(result["availability"], "unavailable")
        self.assertIsNone(result["estimate"])
        self.assertIsNone(result["interval"])
        self.assertIsNone(result["applied_weight"])
        self.assertIsNone(result["shrinkage_fraction"])
        self.assertEqual(
            result["blockers"],
            [
                "adjudicated_overlap_below_minimum",
                "control_attempts_below_minimum",
                "negative_controls_below_minimum",
                "overlap_items_below_minimum",
                "positive_controls_below_minimum",
            ],
        )
        self.assertIn(
            "sensitivity_positive_controls_below_minimum",
            result["metrics"]["metric_blockers"],
        )

    def test_input_order_does_not_change_metrics_or_evidence_fingerprint(self) -> None:
        controls, overlaps = evidence("estimated_case")
        forward = estimate_reviewer_reliability(
            reliability_id="reliability:stable-order",
            reviewer_id=REVIEWER_ID,
            domain=domain(),
            controls=controls,
            overlaps=overlaps,
            recorded_at=RECORDED_AT,
        )
        reverse = estimate_reviewer_reliability(
            reliability_id="reliability:stable-order",
            reviewer_id=REVIEWER_ID,
            domain=domain(),
            controls=list(reversed(controls)),
            overlaps=list(reversed(overlaps)),
            recorded_at=RECORDED_AT,
        )
        self.assertEqual(forward, reverse)
        self.assertRegex(forward["evidence_fingerprint"], r"^[0-9a-f]{64}$")

    def test_independence_and_exact_adjudication_lineage_fail_closed(self) -> None:
        controls, overlaps = evidence("estimated_case")
        first = overlaps[0]
        self_peer = ReviewerOverlap(
            item_id=first.item_id,
            reviewer_label=first.reviewer_label,
            reviewer_event_fingerprint=first.reviewer_event_fingerprint,
            peer_ratings=(
                PeerRating(
                    reviewer_id=REVIEWER_ID,
                    label="yes",
                    event_fingerprint=digest("self-peer"),
                ),
            ),
        )
        with self.assertRaisesRegex(ReliabilityEvidenceError, "independent"):
            estimate_reviewer_reliability(
                reliability_id="reliability:self-peer",
                reviewer_id=REVIEWER_ID,
                domain=domain(),
                controls=controls,
                overlaps=[self_peer],
                recorded_at=RECORDED_AT,
            )

    def test_closed_vocabularies_and_cross_item_event_reuse_fail_closed(self) -> None:
        controls, overlaps = evidence("estimated_case")
        invalid_control = ControlAttempt(
            item_id="control:invalid-kind",
            control_kind="known_butterfly",
            expected_decision="no",
            actual_decision="no",
            control_fingerprint=digest("invalid-control"),
            event_fingerprint=digest("invalid-control-event"),
        )
        with self.assertRaisesRegex(ReliabilityEvidenceError, "closed kind"):
            estimate_reviewer_reliability(
                reliability_id="reliability:invalid-control",
                reviewer_id=REVIEWER_ID,
                domain=domain(),
                controls=[invalid_control],
                overlaps=overlaps,
                recorded_at=RECORDED_AT,
            )

        first, second = overlaps[:2]
        reused = ReviewerOverlap(
            item_id=second.item_id,
            reviewer_label=second.reviewer_label,
            reviewer_event_fingerprint=first.reviewer_event_fingerprint,
            peer_ratings=second.peer_ratings,
            adjudication=None,
        )
        with self.assertRaisesRegex(ReliabilityEvidenceError, "across items"):
            estimate_reviewer_reliability(
                reliability_id="reliability:reused-event",
                reviewer_id=REVIEWER_ID,
                domain=domain(),
                controls=controls,
                overlaps=[first, reused],
                recorded_at=RECORDED_AT,
            )
        broken = ReviewerOverlap(
            item_id=first.item_id,
            reviewer_label=first.reviewer_label,
            reviewer_event_fingerprint=first.reviewer_event_fingerprint,
            peer_ratings=first.peer_ratings,
            adjudication=AdjudicatedResolution(
                adjudicator_id="reviewer:independent",
                label="yes",
                event_fingerprint=digest("broken-adjudication"),
                source_event_fingerprints=(first.reviewer_event_fingerprint,),
            ),
        )
        with self.assertRaisesRegex(ReliabilityEvidenceError, "every exact overlap"):
            estimate_reviewer_reliability(
                reliability_id="reliability:broken-lineage",
                reviewer_id=REVIEWER_ID,
                domain=domain(),
                controls=controls,
                overlaps=[broken],
                recorded_at=RECORDED_AT,
            )

    def test_output_validates_against_private_reliability_contract(self) -> None:
        schemas: dict[str, dict[str, object]] = {}
        registry = Registry()
        for path in sorted((ROOT / "packages/contracts/schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            schemas[schema["$id"]] = schema
            registry = registry.with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
        validator = Draft202012Validator(
            schemas["urn:butterflylens:schema:reviewer-reliability:v1.0.0"],
            registry=registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(estimate()), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])

    def test_snapshot_is_private_and_never_uses_model_or_majority_truth(self) -> None:
        result = estimate()
        self.assertEqual(result["visibility"], "private")
        self.assertFalse(result["public_ranking_allowed"])
        self.assertFalse(result["model_agreement_used"])
        self.assertFalse(result["majority_agreement_alone_used"])

    def test_storage_mapping_preserves_metrics_uncertainty_and_equal_weight(self) -> None:
        estimated = reliability_storage_fields(estimate())
        self.assertEqual(estimated["weighting_state"], "shrunk_capped")
        self.assertTrue(estimated["minimum_evidence_met"])
        self.assertLess(estimated["weight_lower"], estimated["shrunk_weight"])
        self.assertGreater(estimated["weight_upper"], estimated["shrunk_weight"])
        self.assertEqual(estimated["interval_level"], 0.95)
        self.assertEqual(
            estimated["metrics"]["evidence_fingerprint"],
            estimated["evidence_fingerprint"],
        )
        self.assertFalse(estimated["metrics"]["scientific_claim_allowed"])
        self.assertRegex(estimated["reliability_fingerprint"], r"^[0-9a-f]{64}$")

        unavailable = reliability_storage_fields(estimate("insufficient_case"))
        self.assertEqual(unavailable["weighting_state"], "insufficient_evidence")
        self.assertFalse(unavailable["minimum_evidence_met"])
        self.assertEqual(unavailable["shrunk_weight"], 1.0)
        self.assertIsNone(unavailable["weight_lower"])
        self.assertIsNone(unavailable["weight_upper"])
        self.assertTrue(unavailable["blockers"])


if __name__ == "__main__":
    unittest.main()
