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
    ConsensusAdjudication,
    ConsensusEvidenceError,
    ConsensusReview,
    ReleaseGates,
    ReliabilityDomain,
    calculate_layered_consensus,
    consensus_storage_rows,
)


PROJECT_ID = "project:butterflies"
CAMPAIGN_ID = "campaign:layered"
ITEM_ID = "item:one"
DOMAIN = ReliabilityDomain(
    family_taxon_key="family:papilionidae",
    source_provider="flickr",
    life_stage="adult",
    visual_domain="live_field",
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def review(
    index: int,
    reviewer_id: str,
    outcome: str,
    *,
    qualified: bool = True,
    supersedes: str | None = None,
) -> ConsensusReview:
    return ConsensusReview(
        project_id=PROJECT_ID,
        campaign_id=CAMPAIGN_ID,
        item_id=ITEM_ID,
        reviewer_id=reviewer_id,
        event_fingerprint=digest(f"review:{index}"),
        outcome=outcome,
        qualified=qualified,
        reviewed_at=f"2026-07-18T03:{index:02d}:00Z",
        supersedes_event_fingerprint=supersedes,
    )


def reliability(reviewer_id: str, weight: float) -> dict[str, object]:
    return {
        "schema_version": "butterflylens-reviewer-reliability:v1.0.0",
        "reliability_id": f"reliability:{reviewer_id.split(':')[-1]}",
        "reviewer_id": reviewer_id,
        "domain": {
            "taxon_group": DOMAIN.family_taxon_key,
            "source_provider": DOMAIN.source_provider,
            "life_stage": DOMAIN.life_stage,
            "visual_domain": DOMAIN.visual_domain,
        },
        "method": "control_calibrated_beta_binomial_v1",
        "availability": "estimated",
        "blockers": [],
        "applied_weight": weight,
        "evidence_fingerprint": digest(f"reliability:{reviewer_id}"),
        "visibility": "private",
        "public_ranking_allowed": False,
        "model_agreement_used": False,
        "majority_agreement_alone_used": False,
        "recorded_at": "2026-07-18T02:30:00Z",
    }


def calculate(
    events: list[ConsensusReview],
    *,
    snapshots: dict[str, dict[str, object]] | None = None,
    adjudication: ConsensusAdjudication | None = None,
    gates: ReleaseGates | None = None,
) -> dict[str, object]:
    return calculate_layered_consensus(
        consensus_id="consensus:layered",
        project_id=PROJECT_ID,
        campaign_id=CAMPAIGN_ID,
        item_id=ITEM_ID,
        revision=1,
        required_review_count=2,
        events=events,
        domain=DOMAIN,
        reliability_snapshots=snapshots or {},
        adjudication=adjudication,
        release_gates=gates or ReleaseGates(),
    )


class LayeredConsensusTests(unittest.TestCase):
    def test_unweighted_community_and_weighted_qualified_layers_are_separate(self) -> None:
        events = [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "yes")]
        result = calculate(
            events,
            snapshots={"reviewer:one": reliability("reviewer:one", 1.2)},
        )
        community = result["community_evidence"]
        qualified = result["qualified_consensus"]
        self.assertEqual(result["status"], "complete_agreement")
        self.assertEqual(community["method"], "unweighted_human_counts_v1")
        self.assertEqual(community["support_count"], 2)
        self.assertEqual(community["support_total"], 2)
        self.assertEqual(qualified["method"], "qualified_reliability_weighted_v1")
        self.assertAlmostEqual(qualified["support_total"], 2.2)
        self.assertTrue(result["reviewer_weights_applied"])
        self.assertRegex(result["reliability_snapshot_fingerprint"], r"^[0-9a-f]{64}$")
        self.assertEqual(result["release_consensus"]["outcome"], "not_release_ready")
        self.assertEqual(result["release_consensus"]["support_total"], 2)

    def test_equal_weight_fallback_is_explicit_when_reliability_is_missing(self) -> None:
        result = calculate(
            [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "yes")]
        )
        self.assertFalse(result["reviewer_weights_applied"])
        self.assertIsNone(result["reliability_snapshot_fingerprint"])
        self.assertEqual(
            result["qualified_consensus"]["method"],
            "qualified_equal_weight_v1",
        )
        self.assertEqual(result["qualified_consensus"]["support_total"], 2)

    def test_weighted_majority_never_erases_disagreement_or_dissent(self) -> None:
        events = [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "no")]
        result = calculate(
            events,
            snapshots={
                "reviewer:one": reliability("reviewer:one", 2.0),
                "reviewer:two": reliability("reviewer:two", 0.5),
            },
        )
        self.assertEqual(result["status"], "unresolved_disagreement")
        self.assertEqual(result["community_evidence"]["status"], "blocked")
        self.assertEqual(result["qualified_consensus"]["status"], "blocked")
        self.assertEqual(result["qualified_consensus"]["support_total"], 2.0)
        self.assertEqual(result["qualified_consensus"]["oppose_total"], 0.5)
        self.assertEqual(result["qualified_consensus"]["support_count"], 1)
        self.assertEqual(result["qualified_consensus"]["oppose_count"], 1)
        self.assertEqual(result["qualified_consensus"]["dissent_count"], 1)
        self.assertEqual(
            result["conflicts"][0]["event_fingerprints"],
            sorted(event.event_fingerprint for event in events),
        )
        with self.assertRaisesRegex(ConsensusEvidenceError, "contradicts"):
            calculate(
                events,
                gates=ReleaseGates(True, True, True, True, True, True),
            )

    def test_independent_exact_adjudication_resolves_only_later_layers(self) -> None:
        events = [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "no")]
        adjudication = ConsensusAdjudication(
            adjudicator_id="reviewer:expert",
            event_fingerprint=digest("adjudication"),
            outcome="yes",
            source_event_fingerprints=tuple(
                event.event_fingerprint for event in reversed(events)
            ),
            adjudicated_at="2026-07-18T03:10:00Z",
            qualified=True,
        )
        passed = ReleaseGates(True, True, True, True, True, True)
        result = calculate(events, adjudication=adjudication, gates=passed)
        self.assertEqual(result["status"], "adjudicated")
        self.assertEqual(result["community_evidence"]["status"], "blocked")
        self.assertIn(
            "source_dissent_retained_after_adjudication",
            result["community_evidence"]["blockers"],
        )
        self.assertEqual(result["qualified_consensus"]["method"], "qualified_adjudication_v1")
        self.assertEqual(result["qualified_consensus"]["outcome"], "supported")
        self.assertEqual(result["qualified_consensus"]["dissent_count"], 1)
        self.assertEqual(result["release_consensus"]["outcome"], "release_ready")
        self.assertEqual(result["adjudication_event_fingerprint"], digest("adjudication"))

    def test_superseded_review_is_not_effective_but_remains_caller_ledger_evidence(self) -> None:
        original = review(1, "reviewer:one", "no")
        correction = review(
            2,
            "reviewer:one",
            "yes",
            supersedes=original.event_fingerprint,
        )
        second = review(3, "reviewer:two", "yes")
        result = calculate([correction, second, original])
        self.assertEqual(result["status"], "complete_agreement")
        self.assertNotIn(
            original.event_fingerprint,
            result["effective_event_fingerprints"],
        )
        self.assertEqual(result["effective_review_count"], 2)

    def test_adjudication_independence_and_exact_lineage_fail_closed(self) -> None:
        events = [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "no")]
        self_adjudication = ConsensusAdjudication(
            adjudicator_id="reviewer:one",
            event_fingerprint=digest("self-adjudication"),
            outcome="yes",
            source_event_fingerprints=tuple(event.event_fingerprint for event in events),
            adjudicated_at="2026-07-18T03:10:00Z",
            qualified=True,
        )
        with self.assertRaisesRegex(ConsensusEvidenceError, "independent"):
            calculate(events, adjudication=self_adjudication)
        broken = ConsensusAdjudication(
            adjudicator_id="reviewer:expert",
            event_fingerprint=digest("broken-adjudication"),
            outcome="yes",
            source_event_fingerprints=(events[0].event_fingerprint,),
            adjudicated_at="2026-07-18T03:10:00Z",
            qualified=True,
        )
        with self.assertRaisesRegex(ConsensusEvidenceError, "every exact"):
            calculate(events, adjudication=broken)

    def test_output_is_order_stable_contract_valid_and_storage_ready(self) -> None:
        events = [review(1, "reviewer:one", "yes"), review(2, "reviewer:two", "yes")]
        snapshots = {"reviewer:one": reliability("reviewer:one", 1.2)}
        forward = calculate(events, snapshots=snapshots)
        reverse = calculate(list(reversed(events)), snapshots=snapshots)
        self.assertEqual(forward, reverse)

        registry = Registry()
        schemas: dict[str, dict[str, object]] = {}
        for path in sorted((ROOT / "packages/contracts/schemas").glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            schemas[schema["$id"]] = schema
            registry = registry.with_resource(
                schema["$id"], Resource.from_contents(schema)
            )
        validator = Draft202012Validator(
            schemas["urn:butterflylens:schema:verification-consensus:v1.0.0"],
            registry=registry,
            format_checker=FormatChecker(),
        )
        errors = sorted(validator.iter_errors(forward), key=lambda error: list(error.path))
        self.assertEqual([], [error.message for error in errors])

        rows = consensus_storage_rows(forward)
        self.assertEqual([row["consensus_layer"] for row in rows], [
            "community_evidence",
            "qualified_consensus",
            "release_consensus",
        ])
        self.assertFalse(rows[0]["reviewer_weights_applied"])
        self.assertTrue(rows[1]["reviewer_weights_applied"])
        self.assertFalse(rows[2]["reviewer_weights_applied"])
        for row in rows:
            self.assertRegex(row["consensus_fingerprint"], r"^[0-9a-f]{64}$")
            self.assertFalse(row["layer_summary"]["model_vote_included"])
            self.assertFalse(row["layer_summary"]["scientific_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
