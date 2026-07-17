"""Deterministic, planned-only scheduling for Flickr photo comment evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from math import floor
import re
from typing import Literal

from butterflylens.contracts.fingerprint import canonicalize_json

from .query_plan import FLICKR_REST_ENDPOINT


COMMENT_SCHEDULER_SCHEMA_VERSION = "butterflylens-flickr-comment-scheduler:v1.0.0"
FLICKR_COMMENTS_METHOD = "flickr.photos.comments.getList"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
Visibility = Literal["public", "private", "deleted", "unavailable"]


class CommentSchedulingError(ValueError):
    """Raised when comment scheduling could waste reserve budget or lose lineage."""


@dataclass(frozen=True)
class CommentSchedulingPolicy:
    reserve_fraction: float = 0.20
    refresh_after_hours: float = 168.0
    maximum_empty_backoff_exponent: int = 3
    full_association_score: int = 5
    review_need_weight: float = 0.55
    never_checked_weight: float = 0.15
    logical_association_weight: float = 0.15
    age_weight: float = 0.15

    def validate(self) -> None:
        if not 0 <= self.reserve_fraction <= 1:
            raise CommentSchedulingError("comment reserve fraction must be zero to one")
        if self.refresh_after_hours <= 0:
            raise CommentSchedulingError("comment refresh horizon must be positive")
        if self.maximum_empty_backoff_exponent < 0:
            raise CommentSchedulingError("empty-comment backoff exponent is invalid")
        if self.full_association_score < 1:
            raise CommentSchedulingError("association score denominator must be positive")
        weights = (
            self.review_need_weight,
            self.never_checked_weight,
            self.logical_association_weight,
            self.age_weight,
        )
        if any(weight <= 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise CommentSchedulingError("comment scheduler weights must be positive and sum to one")


@dataclass(frozen=True)
class CommentCandidate:
    photo_record_id: str
    flickr_photo_id: str
    source_record_fingerprint: str
    visibility_state: Visibility
    is_current: bool
    discovered_at: datetime
    last_comments_checked_at: datetime | None
    unresolved_review_need: float
    logical_association_count: int
    consecutive_empty_comment_checks: int


def schedule_comment_requests(
    candidates: list[CommentCandidate],
    *,
    as_of: datetime,
    available_reserve_units: int,
    policy: CommentSchedulingPolicy | None = None,
) -> dict[str, object]:
    """Plan comment requests without reserving budget or crossing a transport."""

    selected_policy = policy or CommentSchedulingPolicy()
    selected_policy.validate()
    if as_of.tzinfo != timezone.utc:
        raise CommentSchedulingError("comment scheduler as_of must use UTC")
    if (
        not isinstance(available_reserve_units, int)
        or isinstance(available_reserve_units, bool)
        or not 0 <= available_reserve_units <= 500
    ):
        raise CommentSchedulingError("available reserve units must be between zero and 500")
    photo_ids: set[str] = set()
    record_ids: set[str] = set()
    scored: list[tuple[CommentCandidate, float, datetime | None]] = []
    excluded = {"not_public_or_current": 0, "cooldown": 0}
    for candidate in candidates:
        _validate_candidate(candidate, as_of)
        if candidate.flickr_photo_id in photo_ids or candidate.photo_record_id in record_ids:
            raise CommentSchedulingError("duplicate comment scheduling candidate")
        photo_ids.add(candidate.flickr_photo_id)
        record_ids.add(candidate.photo_record_id)
        if candidate.visibility_state != "public" or not candidate.is_current:
            excluded["not_public_or_current"] += 1
            continue
        next_eligible_at = _next_eligible_at(candidate, selected_policy)
        if next_eligible_at is not None and as_of < next_eligible_at:
            excluded["cooldown"] += 1
            continue
        score = _score(candidate, as_of, selected_policy)
        scored.append((candidate, score, next_eligible_at))
    scored.sort(key=lambda row: (-row[1], row[0].flickr_photo_id))
    comment_slots = floor(available_reserve_units * selected_policy.reserve_fraction)
    selected = scored[:comment_slots]
    requests = tuple(
        _request(candidate, score, next_eligible_at)
        for candidate, score, next_eligible_at in selected
    )
    preimage = {
        "as_of": _utc_text(as_of),
        "available_reserve_units": available_reserve_units,
        "policy": asdict(selected_policy),
        "comment_slots": comment_slots,
        "request_fingerprints": [row["request_fingerprint"] for row in requests],
    }
    fingerprint = _digest(preimage)
    return {
        "schema_version": COMMENT_SCHEDULER_SCHEMA_VERSION,
        "comment_schedule_id": f"blcs:v1:{fingerprint[:24]}",
        **preimage,
        "requests": requests,
        "counts": {
            "candidates": len(candidates),
            "eligible": len(scored),
            "scheduled": len(requests),
            "comment_slots_unused": comment_slots - len(requests),
            "reserve_left_for_other_purposes": available_reserve_units - len(requests),
            **excluded,
        },
        "budget_lane": "reserve",
        "budget_purpose": "comment",
        "execution_state": "planned_not_sent",
        "comments_are_discovery_evidence_not_labels": True,
        "schedule_fingerprint": fingerprint,
    }


def _request(
    candidate: CommentCandidate, score: float, next_eligible_at: datetime | None
) -> dict[str, object]:
    parameters = {"photo_id": candidate.flickr_photo_id}
    preimage = {
        "provider": "flickr",
        "method": FLICKR_COMMENTS_METHOD,
        "endpoint": FLICKR_REST_ENDPOINT,
        "normalized_parameters": parameters,
    }
    fingerprint = _digest(preimage)
    return {
        "comment_request_id": f"blcr:v1:{fingerprint[:24]}",
        "photo_record_id": candidate.photo_record_id,
        "source_record_fingerprint": candidate.source_record_fingerprint,
        **preimage,
        "request_fingerprint": fingerprint,
        "priority_score": score,
        "last_comments_checked_at": (
            None
            if candidate.last_comments_checked_at is None
            else _utc_text(candidate.last_comments_checked_at)
        ),
        "previous_next_eligible_at": (
            None if next_eligible_at is None else _utc_text(next_eligible_at)
        ),
        "budget_units": 1,
        "budget_lane": "reserve",
        "budget_purpose": "comment",
        "execution_state": "planned_not_sent",
        "comment_text_is_taxon_label": False,
    }


def _score(
    candidate: CommentCandidate,
    as_of: datetime,
    policy: CommentSchedulingPolicy,
) -> float:
    never_checked = 1.0 if candidate.last_comments_checked_at is None else 0.0
    association_score = min(
        candidate.logical_association_count / policy.full_association_score, 1.0
    )
    anchor = candidate.last_comments_checked_at or candidate.discovered_at
    age_hours = (as_of - anchor).total_seconds() / 3600
    age_score = min(max(age_hours / policy.refresh_after_hours, 0.0), 1.0)
    return (
        candidate.unresolved_review_need * policy.review_need_weight
        + never_checked * policy.never_checked_weight
        + association_score * policy.logical_association_weight
        + age_score * policy.age_weight
    )


def _next_eligible_at(
    candidate: CommentCandidate, policy: CommentSchedulingPolicy
) -> datetime | None:
    if candidate.last_comments_checked_at is None:
        return None
    exponent = min(
        candidate.consecutive_empty_comment_checks,
        policy.maximum_empty_backoff_exponent,
    )
    return candidate.last_comments_checked_at + timedelta(
        hours=policy.refresh_after_hours * (2**exponent)
    )


def _validate_candidate(candidate: CommentCandidate, as_of: datetime) -> None:
    if _STABLE_ID.fullmatch(candidate.photo_record_id) is None:
        raise CommentSchedulingError("photo record identity is invalid")
    if not candidate.flickr_photo_id.isdigit():
        raise CommentSchedulingError("Flickr photo identity is invalid")
    if _SHA256.fullmatch(candidate.source_record_fingerprint) is None:
        raise CommentSchedulingError("photo source fingerprint is invalid")
    if candidate.visibility_state not in {"public", "private", "deleted", "unavailable"}:
        raise CommentSchedulingError("photo visibility state is invalid")
    if not isinstance(candidate.is_current, bool):
        raise CommentSchedulingError("photo current-state flag is invalid")
    if candidate.discovered_at.tzinfo != timezone.utc or candidate.discovered_at > as_of:
        raise CommentSchedulingError("photo discovery time must be historical UTC")
    if candidate.last_comments_checked_at is not None and (
        candidate.last_comments_checked_at.tzinfo != timezone.utc
        or candidate.last_comments_checked_at > as_of
        or candidate.last_comments_checked_at < candidate.discovered_at
    ):
        raise CommentSchedulingError("comment checkpoint time is invalid")
    if not 0 <= candidate.unresolved_review_need <= 1:
        raise CommentSchedulingError("unresolved review need must be zero to one")
    if candidate.logical_association_count < 1:
        raise CommentSchedulingError("comment candidate has no logical association")
    if candidate.consecutive_empty_comment_checks < 0:
        raise CommentSchedulingError("empty comment checkpoint count is invalid")


def _utc_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
