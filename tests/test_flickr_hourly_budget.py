from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    BudgetDecisionError,
    FlickrHourlyBudget,
    HourlyBudgetPolicy,
)


POLICY_PATH = ROOT / "packages/flickr/hourly-budget.v1.json"
DOC_PATH = ROOT / "packages/flickr/BUDGET.md"
WINDOW = datetime(2026, 7, 17, 22, tzinfo=timezone.utc)
KEY = "a" * 64


class FlickrHourlyBudgetTests(unittest.TestCase):
    def ledger(
        self, policy: HourlyBudgetPolicy | None = None
    ) -> FlickrHourlyBudget:
        return FlickrHourlyBudget(
            project_id="project:australian-butterflies",
            credential_fingerprint=KEY,
            window_start=WINDOW,
            policy=policy,
        )

    def reserve(
        self,
        ledger: FlickrHourlyBudget,
        index: int,
        *,
        lane: str = "normal",
        purpose: str = "search",
        method: str = "flickr.photos.search",
    ) -> None:
        ledger.reserve(
            request_id=f"request:{index}",
            method=method,
            purpose=purpose,
            lane=lane,
            credential_fingerprint=KEY,
            reserved_at=WINDOW + timedelta(minutes=1),
        )

    def test_required_envelope_is_exact_and_one_bucket_covers_all_methods(self) -> None:
        document = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        policy = HourlyBudgetPolicy()
        self.assertEqual(policy.provider_ceiling, 3600)
        self.assertEqual(policy.envelope, 3500)
        self.assertEqual(policy.normal_maximum, 3000)
        self.assertEqual(policy.reserve_maximum, 500)
        self.assertEqual(policy.hard_safety_remainder, 100)
        self.assertEqual(document["bucket_scope"], "all_flickr_methods")
        self.assertEqual(document["window"], "utc_clock_hour")
        self.assertEqual(document["credential_strategy"], "one_project_key_fingerprint")

    def test_normal_reserve_and_total_boundaries_fail_closed(self) -> None:
        small = HourlyBudgetPolicy(
            provider_ceiling=10,
            envelope=9,
            normal_maximum=6,
            reserve_maximum=3,
            hard_safety_remainder=1,
        )
        ledger = self.ledger(small)
        for index in range(6):
            self.reserve(ledger, index)
        with self.assertRaisesRegex(BudgetDecisionError, "normal lane exhausted"):
            self.reserve(ledger, 6)
        for index, purpose in enumerate(("retry", "comment", "judge"), 100):
            self.reserve(ledger, index, lane="reserve", purpose=purpose)
        self.assertEqual(ledger.total_committed, 9)
        self.assertEqual(ledger.envelope_remaining, 0)
        with self.assertRaisesRegex(BudgetDecisionError, "hourly envelope exhausted"):
            self.reserve(ledger, 200, lane="reserve", purpose="manual")

    def test_retry_comment_manual_and_judge_each_consume_one_shared_token(self) -> None:
        ledger = self.ledger()
        calls = (
            ("retry", "flickr.photos.search"),
            ("comment", "flickr.photos.comments.getList"),
            ("manual", "flickr.photos.getInfo"),
            ("judge", "flickr.photos.getSizes"),
        )
        for index, (purpose, method) in enumerate(calls):
            self.reserve(
                ledger,
                index,
                lane="reserve",
                purpose=purpose,
                method=method,
            )
            ledger.settle(f"request:{index}", "consumed")
        self.assertEqual(ledger.reserve_committed, 4)
        self.assertEqual(ledger.total_committed, 4)

    def test_not_sent_releases_but_uncertain_consumes_and_freezes(self) -> None:
        ledger = self.ledger()
        self.reserve(ledger, 1)
        self.assertEqual(ledger.total_committed, 1)
        ledger.settle("request:1", "not_sent")
        self.assertEqual(ledger.total_committed, 0)
        self.reserve(ledger, 2)
        ledger.settle("request:2", "uncertain")
        self.assertEqual(ledger.total_committed, 1)
        self.assertTrue(ledger.frozen)
        with self.assertRaisesRegex(BudgetDecisionError, "frozen"):
            self.reserve(ledger, 3)

    def test_multi_key_duplicate_window_and_out_of_window_attempts_reject(self) -> None:
        ledger = self.ledger()
        with self.assertRaisesRegex(BudgetDecisionError, "multi-key"):
            ledger.reserve(
                request_id="request:key-swap",
                method="flickr.photos.search",
                purpose="search",
                lane="normal",
                credential_fingerprint="b" * 64,
                reserved_at=WINDOW,
            )
        self.reserve(ledger, 1)
        with self.assertRaisesRegex(BudgetDecisionError, "duplicated"):
            self.reserve(ledger, 1)
        with self.assertRaisesRegex(BudgetDecisionError, "outside"):
            ledger.reserve(
                request_id="request:late",
                method="flickr.photos.search",
                purpose="search",
                lane="normal",
                credential_fingerprint=KEY,
                reserved_at=WINDOW + timedelta(hours=1),
            )

    def test_reserve_is_closed_and_contract_makes_no_api_call(self) -> None:
        ledger = self.ledger()
        with self.assertRaisesRegex(BudgetDecisionError, "not eligible"):
            self.reserve(ledger, 1, lane="reserve", purpose="bulk_search")
        with self.assertRaisesRegex(BudgetDecisionError, "explicit Flickr method"):
            self.reserve(ledger, 2, method="photos.search")
        docs = DOC_PATH.read_text(encoding="utf-8")
        for phrase in (
            "one project-wide token bucket",
            "leaving 100 calls unused",
            "A retry is a new attempt",
            "consume",
            "freeze",
            "performs no Flickr API call",
        ):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
