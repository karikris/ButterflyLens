"""Adaptive, replayable Flickr discovery scoring and lane allocation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import floor
import hashlib
import re
from collections.abc import Iterable
from typing import Literal, Mapping

from butterflylens.contracts.fingerprint import canonicalize_json


ADAPTIVE_SCHEDULER_SCHEMA_VERSION = "butterflylens-flickr-adaptive-scheduler:v1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
Lane = Literal["australia_known", "global_out_of_range"]


class SchedulingError(ValueError):
    """Raised when ranking inputs or lane allocation are not auditable."""


@dataclass(frozen=True)
class SchedulerPolicy:
    unique_media_weight: float = 0.20
    geotagged_media_weight: float = 0.10
    butterfly_positive_weight: float = 0.15
    baseline_coverage_gap_weight: float = 0.15
    species_coverage_need_weight: float = 0.15
    review_capacity_weight: float = 0.05
    reference_readiness_weight: float = 0.05
    age_weight: float = 0.10
    unexplored_date_weight: float = 0.05
    full_age_score_hours: float = 168.0
    low_yield_unique_media_per_call: float = 2.0
    low_yield_butterfly_positive: float = 0.02
    low_yield_minimum_calls: int = 10
    low_yield_stop_windows: int = 3
    low_yield_cooldown_hours: float = 48.0
    australia_coverage_gate: float = 0.80
    australia_saturation_gate: float = 0.70
    tier5_reserve_fraction: float = 0.10

    def validate(self) -> None:
        weights = self.weights()
        if any(value <= 0 for value in weights.values()):
            raise SchedulingError("scheduler weights must be positive")
        if abs(sum(weights.values()) - 1.0) > 1e-9:
            raise SchedulingError("scheduler weights must sum to one")
        if self.full_age_score_hours <= 0 or self.low_yield_cooldown_hours <= 0:
            raise SchedulingError("scheduler time horizons must be positive")
        if self.low_yield_minimum_calls < 1 or self.low_yield_stop_windows < 1:
            raise SchedulingError("low-yield evidence thresholds must be positive")
        for value in (
            self.low_yield_butterfly_positive,
            self.australia_coverage_gate,
            self.australia_saturation_gate,
            self.tier5_reserve_fraction,
        ):
            if not 0 <= value <= 1:
                raise SchedulingError("scheduler fractions must be between zero and one")
        if not 0 <= self.low_yield_unique_media_per_call <= 250:
            raise SchedulingError("low-yield media threshold exceeds a geo page")

    def weights(self) -> dict[str, float]:
        return {
            "unique_media_per_call": self.unique_media_weight,
            "geotagged_media_per_call": self.geotagged_media_weight,
            "butterfly_positive_yield": self.butterfly_positive_weight,
            "baseline_coverage_gap": self.baseline_coverage_gap_weight,
            "species_coverage_need": self.species_coverage_need_weight,
            "review_capacity": self.review_capacity_weight,
            "reference_readiness": self.reference_readiness_weight,
            "age_since_last_query": self.age_weight,
            "unexplored_date_partition": self.unexplored_date_weight,
        }


@dataclass(frozen=True)
class SchedulingCandidate:
    candidate_id: str
    partition_fingerprint: str
    lane: Lane
    tier: int
    unique_media_per_call: float | None
    geotagged_media_per_call: float | None
    butterfly_positive_yield: float | None
    baseline_coverage_gap: float
    species_coverage_need: float
    review_capacity: float
    reference_readiness: float | None
    last_queried_at: datetime | None
    unexplored_date_partition: bool
    calls_observed: int
    consecutive_low_yield_windows: int


@dataclass(frozen=True)
class AustraliaLaneGate:
    baseline_coverage: float
    saturation_fraction: float
    eligible_partition_count: int


def score_candidate(
    candidate: SchedulingCandidate,
    *,
    as_of: datetime,
    policy: SchedulerPolicy | None = None,
) -> dict[str, object]:
    """Score one candidate with availability-aware, non-fabricated components."""

    selected_policy = policy or SchedulerPolicy()
    selected_policy.validate()
    _validate_candidate(candidate, as_of)
    state, next_eligible_at = _candidate_state(candidate, as_of, selected_policy)
    raw_components: dict[str, float | None] = {
        "unique_media_per_call": (
            None
            if candidate.unique_media_per_call is None
            else candidate.unique_media_per_call / 250.0
        ),
        "geotagged_media_per_call": (
            None
            if candidate.geotagged_media_per_call is None
            else candidate.geotagged_media_per_call / 250.0
        ),
        "butterfly_positive_yield": candidate.butterfly_positive_yield,
        "baseline_coverage_gap": candidate.baseline_coverage_gap,
        "species_coverage_need": candidate.species_coverage_need,
        "review_capacity": candidate.review_capacity,
        "reference_readiness": candidate.reference_readiness,
        "age_since_last_query": _age_score(
            candidate.last_queried_at, as_of, selected_policy.full_age_score_hours
        ),
        "unexplored_date_partition": 1.0 if candidate.unexplored_date_partition else 0.0,
    }
    weights = selected_policy.weights()
    observed = {key: value for key, value in raw_components.items() if value is not None}
    missing = tuple(sorted(set(raw_components) - set(observed)))
    observed_weight = sum(weights[key] for key in observed)
    if observed_weight <= 0:
        raise SchedulingError("candidate has no observed scheduling components")
    active_score = sum(float(value) * weights[key] for key, value in observed.items()) / observed_weight
    score = active_score if state == "eligible" else 0.0
    preimage = {
        "candidate_id": candidate.candidate_id,
        "partition_fingerprint": candidate.partition_fingerprint,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "policy": asdict(selected_policy),
        "components": raw_components,
        "missing_components": list(missing),
        "state": state,
        "next_eligible_at": (
            None
            if next_eligible_at is None
            else next_eligible_at.isoformat().replace("+00:00", "Z")
        ),
        "score": score,
    }
    digest = _digest(preimage)
    return {
        "schema_version": ADAPTIVE_SCHEDULER_SCHEMA_VERSION,
        "score_id": f"blfs:v1:{digest[:24]}",
        **preimage,
        "observed_weight": observed_weight,
        "score_fingerprint": digest,
    }


def allocate_schedule(
    candidates: list[SchedulingCandidate],
    *,
    as_of: datetime,
    normal_budget: int,
    australia_gate: AustraliaLaneGate,
    policy: SchedulerPolicy | None = None,
) -> dict[str, object]:
    """Allocate one-call candidates with a gated, non-reallocated Tier-5 share."""

    selected_policy = policy or SchedulerPolicy()
    selected_policy.validate()
    if not isinstance(normal_budget, int) or isinstance(normal_budget, bool) or not 1 <= normal_budget <= 3000:
        raise SchedulingError("normal scheduling budget must be between 1 and 3000")
    _validate_gate(australia_gate)
    fingerprints = [candidate.partition_fingerprint for candidate in candidates]
    if len(fingerprints) != len(set(fingerprints)):
        raise SchedulingError("duplicate physical scheduling candidate")
    scored = [
        (candidate, score_candidate(candidate, as_of=as_of, policy=selected_policy))
        for candidate in candidates
    ]
    eligible = [(candidate, score) for candidate, score in scored if score["state"] == "eligible"]
    australia = _rank(
        (item for item in eligible if item[0].lane == "australia_known")
    )
    global_out_of_range = _rank(
        (item for item in eligible if item[0].lane == "global_out_of_range")
    )
    tier5_unlocked = (
        australia_gate.eligible_partition_count > 0
        and australia_gate.baseline_coverage >= selected_policy.australia_coverage_gate
        and australia_gate.saturation_fraction >= selected_policy.australia_saturation_gate
    )
    tier5_slots = (
        floor(normal_budget * selected_policy.tier5_reserve_fraction)
        if tier5_unlocked
        else 0
    )
    australia_slots = normal_budget - tier5_slots
    selected_australia = australia[:australia_slots]
    selected_tier5 = global_out_of_range[:tier5_slots]
    scheduled_items = [*selected_australia, *selected_tier5]
    scheduled = tuple(
        {
            "schedule_rank": rank,
            "candidate_id": candidate.candidate_id,
            "partition_fingerprint": candidate.partition_fingerprint,
            "lane": candidate.lane,
            "tier": candidate.tier,
            "score": score["score"],
            "score_fingerprint": score["score_fingerprint"],
            "budget_units": 1,
        }
        for rank, (candidate, score) in enumerate(scheduled_items, 1)
    )
    preimage = {
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "normal_budget": normal_budget,
        "policy": asdict(selected_policy),
        "australia_gate": asdict(australia_gate),
        "tier5_unlocked": tier5_unlocked,
        "tier5_slots": tier5_slots,
        "scheduled_score_fingerprints": [row["score_fingerprint"] for row in scheduled],
    }
    digest = _digest(preimage)
    return {
        "schema_version": ADAPTIVE_SCHEDULER_SCHEMA_VERSION,
        "schedule_id": f"blsc:v1:{digest[:24]}",
        **preimage,
        "scheduled": scheduled,
        "counts": {
            "scheduled_total": len(scheduled),
            "scheduled_australia": len(selected_australia),
            "scheduled_tier5": len(selected_tier5),
            "tier5_reserved_unused": tier5_slots - len(selected_tier5),
            "budget_unused": normal_budget - len(scheduled),
            "cooled_or_stopped": sum(score["state"] != "eligible" for _, score in scored),
        },
        "execution_state": "planned_not_sent",
        "schedule_fingerprint": digest,
    }


def _candidate_state(
    candidate: SchedulingCandidate, as_of: datetime, policy: SchedulerPolicy
) -> tuple[str, datetime | None]:
    low_unique = (
        candidate.unique_media_per_call is not None
        and candidate.unique_media_per_call <= policy.low_yield_unique_media_per_call
    )
    low_positive = (
        candidate.butterfly_positive_yield is None
        or candidate.butterfly_positive_yield <= policy.low_yield_butterfly_positive
    )
    proven_low_yield = (
        candidate.calls_observed >= policy.low_yield_minimum_calls
        and low_unique
        and low_positive
    )
    if proven_low_yield and candidate.consecutive_low_yield_windows >= policy.low_yield_stop_windows:
        return "stopped_low_yield", None
    if proven_low_yield:
        assert candidate.last_queried_at is not None
        next_eligible = candidate.last_queried_at + timedelta(
            hours=policy.low_yield_cooldown_hours
        )
        if as_of < next_eligible:
            return "cooldown_low_yield", next_eligible
    return "eligible", None


def _validate_candidate(candidate: SchedulingCandidate, as_of: datetime) -> None:
    if as_of.tzinfo != timezone.utc:
        raise SchedulingError("scheduler as_of must use UTC")
    if not candidate.candidate_id or _SHA256.fullmatch(candidate.partition_fingerprint) is None:
        raise SchedulingError("candidate identity is invalid")
    if candidate.lane not in {"australia_known", "global_out_of_range"}:
        raise SchedulingError("candidate lane is invalid")
    if candidate.lane == "global_out_of_range" and candidate.tier != 5:
        raise SchedulingError("global out-of-range candidate must be tier 5")
    if candidate.lane == "australia_known" and candidate.tier not in {1, 2, 3, 4}:
        raise SchedulingError("Australia-known candidate tier is invalid")
    for value in (candidate.unique_media_per_call, candidate.geotagged_media_per_call):
        if value is not None and not 0 <= value <= 250:
            raise SchedulingError("per-call media yield must be between zero and 250")
    for value in (
        candidate.butterfly_positive_yield,
        candidate.baseline_coverage_gap,
        candidate.species_coverage_need,
        candidate.review_capacity,
        candidate.reference_readiness,
    ):
        if value is not None and not 0 <= value <= 1:
            raise SchedulingError("normalized scheduling metric is outside zero to one")
    if candidate.calls_observed < 0 or candidate.consecutive_low_yield_windows < 0:
        raise SchedulingError("yield evidence counts cannot be negative")
    if candidate.calls_observed > 0 and candidate.last_queried_at is None:
        raise SchedulingError("observed calls require last_queried_at")
    if candidate.last_queried_at is not None:
        if candidate.last_queried_at.tzinfo != timezone.utc:
            raise SchedulingError("last_queried_at must use UTC")
        if candidate.last_queried_at > as_of:
            raise SchedulingError("last_queried_at cannot be in the future")


def _validate_gate(gate: AustraliaLaneGate) -> None:
    if not 0 <= gate.baseline_coverage <= 1 or not 0 <= gate.saturation_fraction <= 1:
        raise SchedulingError("Australia gate metrics must be between zero and one")
    if gate.eligible_partition_count < 0:
        raise SchedulingError("Australia eligible partition count cannot be negative")


def _age_score(last_queried_at: datetime | None, as_of: datetime, horizon_hours: float) -> float:
    if last_queried_at is None:
        return 1.0
    age_hours = (as_of - last_queried_at).total_seconds() / 3600
    return min(max(age_hours / horizon_hours, 0.0), 1.0)


def _rank(
    items: Iterable[tuple[SchedulingCandidate, Mapping[str, object]]],
) -> list[tuple[SchedulingCandidate, Mapping[str, object]]]:
    return sorted(
        items,
        key=lambda item: (-float(item[1]["score"]), item[0].candidate_id),
    )


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()
