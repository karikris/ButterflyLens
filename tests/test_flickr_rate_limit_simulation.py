from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    BudgetDecisionError,
    FlickrHourlyBudget,
)


WINDOW = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)
CREDENTIAL_FINGERPRINT = "c" * 64
OTHER_CREDENTIAL_FINGERPRINT = "d" * 64


def ledger(window_start: datetime = WINDOW) -> FlickrHourlyBudget:
    return FlickrHourlyBudget(
        project_id="butterflylens-rate-limit-simulation",
        credential_fingerprint=CREDENTIAL_FINGERPRINT,
        window_start=window_start,
    )


def reserve(
    budget: FlickrHourlyBudget,
    index: int,
    *,
    lane: str,
    purpose: str,
    method: str,
    outcome: str = "consumed",
    at: datetime | None = None,
    credential_fingerprint: str = CREDENTIAL_FINGERPRINT,
) -> None:
    request_id = f"simulation:{lane}:{index}"
    budget.reserve(
        request_id=request_id,
        method=method,
        purpose=purpose,
        lane=lane,
        credential_fingerprint=credential_fingerprint,
        reserved_at=at or budget.window_start + timedelta(minutes=30),
    )
    budget.settle(request_id, outcome)


class FlickrRateLimitSimulationTests(unittest.TestCase):
    def test_full_mixed_method_hour_stops_at_3500_and_leaves_100_unused(self) -> None:
        budget = ledger()
        normal_methods = (
            "flickr.photos.search",
            "flickr.photos.getInfo",
            "flickr.photos.getSizes",
        )
        reserve_work = (
            ("retry", "flickr.photos.search"),
            ("comment", "flickr.photos.comments.getList"),
            ("manual", "flickr.photos.getInfo"),
            ("judge", "flickr.photos.getSizes"),
            ("accounting_reconciliation", "flickr.test.echo"),
        )
        for index in range(3000):
            reserve(
                budget,
                index,
                lane="normal",
                purpose="discovery",
                method=normal_methods[index % len(normal_methods)],
            )
        for index in range(500):
            purpose, method = reserve_work[index % len(reserve_work)]
            reserve(
                budget,
                index,
                lane="reserve",
                purpose=purpose,
                method=method,
            )

        self.assertEqual(budget.normal_committed, 3000)
        self.assertEqual(budget.reserve_committed, 500)
        self.assertEqual(budget.total_committed, 3500)
        self.assertEqual(budget.envelope_remaining, 0)
        self.assertEqual(
            budget.policy.provider_ceiling - budget.total_committed,
            budget.policy.hard_safety_remainder,
        )
        with self.assertRaisesRegex(BudgetDecisionError, "hourly envelope exhausted"):
            reserve(
                budget,
                9999,
                lane="reserve",
                purpose="retry",
                method="flickr.photos.search",
            )

    def test_synthetic_429_chain_and_comments_share_the_same_reserve(self) -> None:
        budget = ledger()
        reserve(
            budget,
            0,
            lane="normal",
            purpose="discovery",
            method="flickr.photos.search",
        )
        for attempt in range(1, 4):
            reserve(
                budget,
                attempt,
                lane="reserve",
                purpose="retry",
                method="flickr.photos.search",
            )
        for index in range(100, 200):
            reserve(
                budget,
                index,
                lane="reserve",
                purpose="comment",
                method="flickr.photos.comments.getList",
            )

        self.assertEqual(budget.normal_committed, 1)
        self.assertEqual(budget.reserve_committed, 103)
        self.assertEqual(budget.reserve_remaining, 397)
        self.assertEqual(budget.total_committed, 104)

    def test_reserve_exhaustion_blocks_retry_comment_and_manual_work(self) -> None:
        budget = ledger()
        for index in range(500):
            purpose = "retry" if index % 2 == 0 else "comment"
            method = (
                "flickr.photos.search"
                if purpose == "retry"
                else "flickr.photos.comments.getList"
            )
            reserve(
                budget,
                index,
                lane="reserve",
                purpose=purpose,
                method=method,
            )

        for index, purpose, method in (
            (501, "retry", "flickr.photos.search"),
            (502, "comment", "flickr.photos.comments.getList"),
            (503, "manual", "flickr.photos.getInfo"),
        ):
            with self.subTest(purpose=purpose):
                with self.assertRaisesRegex(BudgetDecisionError, "reserve lane exhausted"):
                    reserve(
                        budget,
                        index,
                        lane="reserve",
                        purpose=purpose,
                        method=method,
                    )
        self.assertEqual(budget.reserve_committed, 500)

    def test_uncertain_send_freezes_every_method_and_lane(self) -> None:
        budget = ledger()
        reserve(
            budget,
            0,
            lane="normal",
            purpose="discovery",
            method="flickr.photos.search",
            outcome="uncertain",
        )
        for index, lane, purpose, method in (
            (1, "normal", "discovery", "flickr.photos.getInfo"),
            (2, "reserve", "retry", "flickr.photos.search"),
            (3, "reserve", "comment", "flickr.photos.comments.getList"),
        ):
            with self.subTest(lane=lane, purpose=purpose):
                with self.assertRaisesRegex(BudgetDecisionError, "window is frozen"):
                    reserve(
                        budget,
                        index,
                        lane=lane,
                        purpose=purpose,
                        method=method,
                    )
        self.assertEqual(budget.total_committed, 1)

    def test_clock_hour_rollover_requires_a_fresh_ledger(self) -> None:
        first = ledger()
        reserve(
            first,
            0,
            lane="normal",
            purpose="discovery",
            method="flickr.photos.search",
            at=WINDOW + timedelta(minutes=59, seconds=59),
        )
        with self.assertRaisesRegex(BudgetDecisionError, "outside its UTC clock hour"):
            reserve(
                first,
                1,
                lane="normal",
                purpose="discovery",
                method="flickr.photos.search",
                at=WINDOW + timedelta(hours=1),
            )

        second = ledger(WINDOW + timedelta(hours=1))
        self.assertEqual(second.total_committed, 0)
        reserve(
            second,
            0,
            lane="normal",
            purpose="discovery",
            method="flickr.photos.search",
            at=WINDOW + timedelta(hours=1),
        )
        self.assertEqual(first.total_committed, 1)
        self.assertEqual(second.total_committed, 1)

    def test_key_rotation_cannot_create_capacity_inside_the_hour(self) -> None:
        budget = ledger()
        with self.assertRaisesRegex(BudgetDecisionError, "multi-key accounting is forbidden"):
            reserve(
                budget,
                0,
                lane="normal",
                purpose="discovery",
                method="flickr.photos.search",
                credential_fingerprint=OTHER_CREDENTIAL_FINGERPRINT,
            )
        self.assertEqual(budget.total_committed, 0)


if __name__ == "__main__":
    unittest.main()
