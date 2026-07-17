from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))

from butterflylens.flickr import (  # noqa: E402
    CommentCandidate,
    CommentSchedulingError,
    CommentSchedulingPolicy,
    FLICKR_COMMENTS_METHOD,
    schedule_comment_requests,
)


NOW = datetime(2026, 7, 18, 5, 0, tzinfo=timezone.utc)


def candidate(index: int, **changes: object) -> CommentCandidate:
    values: dict[str, object] = {
        "photo_record_id": f"flickr-record:{index}",
        "flickr_photo_id": str(5000 + index),
        "source_record_fingerprint": format(index + 1, "064x"),
        "visibility_state": "public",
        "is_current": True,
        "discovered_at": NOW - timedelta(days=30),
        "last_comments_checked_at": None,
        "unresolved_review_need": 0.5,
        "logical_association_count": 1,
        "consecutive_empty_comment_checks": 0,
    }
    values.update(changes)
    return CommentCandidate(**values)  # type: ignore[arg-type]


class FlickrCommentSchedulerTests(unittest.TestCase):
    def test_comment_requests_are_ranked_reserve_only_and_unsent(self) -> None:
        low = candidate(1, unresolved_review_need=0.1)
        high = candidate(2, unresolved_review_need=1.0, logical_association_count=5)
        schedule = schedule_comment_requests(
            [low, high],
            as_of=NOW,
            available_reserve_units=10,
            policy=CommentSchedulingPolicy(reserve_fraction=0.1),
        )
        self.assertEqual(schedule["counts"]["scheduled"], 1)
        request = schedule["requests"][0]
        self.assertEqual(request["normalized_parameters"], {"photo_id": high.flickr_photo_id})
        self.assertEqual(request["method"], FLICKR_COMMENTS_METHOD)
        self.assertEqual(request["budget_lane"], "reserve")
        self.assertEqual(request["budget_purpose"], "comment")
        self.assertEqual(request["execution_state"], "planned_not_sent")
        self.assertFalse(request["comment_text_is_taxon_label"])

    def test_configurable_fraction_preserves_reserve_for_other_purposes(self) -> None:
        schedule = schedule_comment_requests(
            [candidate(index) for index in range(1, 201)],
            as_of=NOW,
            available_reserve_units=500,
        )
        self.assertEqual(schedule["comment_slots"], 100)
        self.assertEqual(schedule["counts"]["scheduled"], 100)
        self.assertEqual(schedule["counts"]["reserve_left_for_other_purposes"], 400)

    def test_private_removed_stale_and_recently_checked_candidates_do_not_send(self) -> None:
        candidates = [
            candidate(1, visibility_state="private"),
            candidate(2, visibility_state="deleted", is_current=False),
            candidate(
                3,
                last_comments_checked_at=NOW - timedelta(hours=1),
            ),
        ]
        schedule = schedule_comment_requests(
            candidates,
            as_of=NOW,
            available_reserve_units=500,
        )
        self.assertEqual(schedule["counts"]["scheduled"], 0)
        self.assertEqual(schedule["counts"]["not_public_or_current"], 2)
        self.assertEqual(schedule["counts"]["cooldown"], 1)

    def test_empty_comment_checks_extend_refresh_cooldown(self) -> None:
        checked_at = NOW - timedelta(days=10)
        ordinary = candidate(1, last_comments_checked_at=checked_at)
        empty = candidate(
            2,
            last_comments_checked_at=checked_at,
            consecutive_empty_comment_checks=2,
        )
        schedule = schedule_comment_requests(
            [ordinary, empty],
            as_of=NOW,
            available_reserve_units=500,
        )
        self.assertEqual(
            {row["normalized_parameters"]["photo_id"] for row in schedule["requests"]},
            {ordinary.flickr_photo_id},
        )
        self.assertEqual(schedule["counts"]["cooldown"], 1)

    def test_duplicates_and_missing_logical_lineage_fail_closed(self) -> None:
        duplicate = deepcopy(candidate(1))
        object.__setattr__(duplicate, "photo_record_id", "flickr-record:duplicate")
        with self.assertRaisesRegex(CommentSchedulingError, "duplicate"):
            schedule_comment_requests(
                [candidate(1), duplicate],
                as_of=NOW,
                available_reserve_units=500,
            )
        with self.assertRaisesRegex(CommentSchedulingError, "no logical association"):
            schedule_comment_requests(
                [candidate(2, logical_association_count=0)],
                as_of=NOW,
                available_reserve_units=500,
            )

    def test_schedule_is_deterministic_contains_no_secret_and_has_no_transport(self) -> None:
        candidates = [candidate(index) for index in range(1, 20)]
        first = schedule_comment_requests(
            candidates,
            as_of=NOW,
            available_reserve_units=50,
        )
        second = schedule_comment_requests(
            list(reversed(candidates)),
            as_of=NOW,
            available_reserve_units=50,
        )
        self.assertEqual(first, second)
        self.assertNotIn("api_key", repr(first))
        source = (ROOT / "packages/contracts/python/butterflylens/flickr/comments.py").read_text()
        for forbidden in ("requests", "urllib", "httpx", "aiohttp"):
            self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
