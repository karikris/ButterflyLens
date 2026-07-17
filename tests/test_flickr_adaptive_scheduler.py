from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    AustraliaLaneGate,
    SchedulerPolicy,
    SchedulingCandidate,
    SchedulingError,
    allocate_schedule,
    score_candidate,
)


NOW = datetime(2026, 7, 18, 0, 0, tzinfo=timezone.utc)


def candidate(index: int, *, lane: str = "australia_known", **changes: object) -> SchedulingCandidate:
    values: dict[str, object] = {
        "candidate_id": f"candidate:{index:03d}",
        "partition_fingerprint": format(index + 1, "064x"),
        "lane": lane,
        "tier": 5 if lane == "global_out_of_range" else 1,
        "unique_media_per_call": 50.0,
        "geotagged_media_per_call": 40.0,
        "butterfly_positive_yield": 0.2,
        "baseline_coverage_gap": 0.2,
        "species_coverage_need": 0.2,
        "review_capacity": 0.2,
        "reference_readiness": 0.2,
        "last_queried_at": NOW - timedelta(hours=12),
        "unexplored_date_partition": False,
        "calls_observed": 5,
        "consecutive_low_yield_windows": 0,
    }
    values.update(changes)
    return SchedulingCandidate(**values)  # type: ignore[arg-type]


class FlickrAdaptiveSchedulerTests(unittest.TestCase):
    def test_every_required_factor_changes_priority(self) -> None:
        base = candidate(1)
        base_score = float(score_candidate(base, as_of=NOW)["score"])
        mutations = {
            "unique_media_per_call": 200.0,
            "geotagged_media_per_call": 200.0,
            "butterfly_positive_yield": 0.9,
            "baseline_coverage_gap": 0.9,
            "species_coverage_need": 0.9,
            "review_capacity": 0.9,
            "reference_readiness": 0.9,
            "last_queried_at": NOW - timedelta(days=8),
            "unexplored_date_partition": True,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                changed = deepcopy(base)
                object.__setattr__(changed, field, value)
                self.assertGreater(float(score_candidate(changed, as_of=NOW)["score"]), base_score)

    def test_unfinished_model_metrics_are_missing_not_zero(self) -> None:
        unknown = candidate(
            2,
            butterfly_positive_yield=None,
            reference_readiness=None,
        )
        scored = score_candidate(unknown, as_of=NOW)
        self.assertEqual(
            scored["missing_components"],
            ["butterfly_positive_yield", "reference_readiness"],
        )
        self.assertGreater(scored["observed_weight"], 0)
        self.assertGreater(float(scored["score"]), 0)

    def test_low_yield_candidates_cool_then_stop(self) -> None:
        low = candidate(
            3,
            unique_media_per_call=1.0,
            butterfly_positive_yield=None,
            calls_observed=12,
            consecutive_low_yield_windows=1,
            last_queried_at=NOW - timedelta(hours=2),
        )
        cooled = score_candidate(low, as_of=NOW)
        self.assertEqual(cooled["state"], "cooldown_low_yield")
        self.assertEqual(cooled["score"], 0.0)
        stopped = deepcopy(low)
        object.__setattr__(stopped, "consecutive_low_yield_windows", 3)
        self.assertEqual(score_candidate(stopped, as_of=NOW)["state"], "stopped_low_yield")
        expired = score_candidate(low, as_of=NOW + timedelta(hours=60))
        self.assertEqual(expired["state"], "eligible")

    def test_tier5_share_is_locked_then_reserved_after_australia_gates(self) -> None:
        candidates = [candidate(index) for index in range(1, 13)] + [
            candidate(index, lane="global_out_of_range") for index in range(20, 25)
        ]
        policy = SchedulerPolicy(tier5_reserve_fraction=0.2)
        locked = allocate_schedule(
            candidates,
            as_of=NOW,
            normal_budget=10,
            australia_gate=AustraliaLaneGate(0.79, 0.9, 10),
            policy=policy,
        )
        self.assertFalse(locked["tier5_unlocked"])
        self.assertEqual(locked["counts"]["scheduled_tier5"], 0)
        self.assertEqual(locked["counts"]["scheduled_australia"], 10)
        unlocked = allocate_schedule(
            candidates,
            as_of=NOW,
            normal_budget=10,
            australia_gate=AustraliaLaneGate(0.8, 0.7, 10),
            policy=policy,
        )
        self.assertTrue(unlocked["tier5_unlocked"])
        self.assertEqual(unlocked["counts"]["scheduled_tier5"], 2)
        self.assertEqual(unlocked["counts"]["scheduled_australia"], 8)
        self.assertEqual(unlocked["execution_state"], "planned_not_sent")

    def test_unused_tier5_reserve_is_not_silently_reallocated(self) -> None:
        only_australia = [candidate(index) for index in range(1, 20)]
        schedule = allocate_schedule(
            only_australia,
            as_of=NOW,
            normal_budget=10,
            australia_gate=AustraliaLaneGate(1.0, 1.0, 10),
            policy=SchedulerPolicy(tier5_reserve_fraction=0.2),
        )
        self.assertEqual(schedule["counts"]["scheduled_australia"], 8)
        self.assertEqual(schedule["counts"]["tier5_reserved_unused"], 2)
        self.assertEqual(schedule["counts"]["budget_unused"], 2)

    def test_duplicate_physical_candidate_and_invalid_lane_tier_fail_closed(self) -> None:
        duplicate = deepcopy(candidate(1))
        object.__setattr__(duplicate, "candidate_id", "candidate:duplicate")
        with self.assertRaisesRegex(SchedulingError, "duplicate physical"):
            allocate_schedule(
                [candidate(1), duplicate],
                as_of=NOW,
                normal_budget=10,
                australia_gate=AustraliaLaneGate(0, 0, 1),
            )
        invalid = candidate(30, lane="global_out_of_range", tier=1)
        with self.assertRaisesRegex(SchedulingError, "tier 5"):
            score_candidate(invalid, as_of=NOW)


if __name__ == "__main__":
    unittest.main()
