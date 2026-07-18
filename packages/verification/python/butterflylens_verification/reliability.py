"""Deterministic, private reviewer-reliability estimates.

The estimator consumes governed human control and independent-overlap evidence.
It never consumes model output or treats majority agreement as truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import math
import re
from statistics import NormalDist
from typing import Literal, Mapping, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json


SCHEMA_VERSION = "butterflylens-reviewer-reliability:v1.0.0"
METHOD = "control_calibrated_beta_binomial_v1"
POLICY_VERSION = "butterflylens-reviewer-reliability-policy:v1.0.0"
ESTIMATOR_VERSION = "butterflylens-reliability-estimator:v1.0.0"

MINIMUM_CONTROL_COUNT = 20
MINIMUM_POSITIVE_CONTROL_COUNT = 5
MINIMUM_NEGATIVE_CONTROL_COUNT = 5
MINIMUM_OVERLAP_COUNT = 10
MINIMUM_ADJUDICATED_COUNT = 5
MINIMUM_CLASS_COUNT = 10
PRIOR_ALPHA = 15.0
PRIOR_BETA = 5.0
EQUAL_WEIGHT_ACCURACY = PRIOR_ALPHA / (PRIOR_ALPHA + PRIOR_BETA)
WEIGHT_MINIMUM = 0.5
WEIGHT_MAXIMUM = 2.0
INTERVAL_LEVEL = 0.95

RatingLabel = Literal["yes", "no", "cannot_tell"]
ControlLabel = Literal["yes", "no", "cannot_tell", "cannot_view"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
_SOURCE_PROVIDERS = {
    "flickr",
    "ala",
    "gbif",
    "inaturalist",
    "wikimedia_commons",
    "community_upload",
    "butterflylens_fixture",
}
_LIFE_STAGES = {"adult", "larva", "pupa", "egg", "unknown"}
_CONTROL_EXPECTATIONS: dict[str, ControlLabel] = {
    "known_butterfly": "yes",
    "known_non_butterfly": "no",
    "ambiguous_image": "cannot_tell",
    "duplicate": "yes",
    "media_failure": "cannot_view",
    "life_stage": "yes",
}
_CONTROL_LABELS = {"yes", "no", "cannot_tell", "cannot_view"}
_RATING_LABELS = {"yes", "no", "cannot_tell"}
_VISUAL_DOMAINS = {
    "live_field",
    "pinned_specimen",
    "artwork",
    "logo",
    "tattoo",
    "partial_wing",
    "dead_or_damaged_specimen",
    "ambiguous",
    "unsuitable",
}


class ReliabilityEvidenceError(ValueError):
    """Raised when private reliability evidence is malformed or non-independent."""


@dataclass(frozen=True, slots=True)
class ReliabilityDomain:
    family_taxon_key: str
    source_provider: str
    life_stage: str
    visual_domain: str


@dataclass(frozen=True, slots=True)
class ControlAttempt:
    item_id: str
    control_kind: str
    expected_decision: ControlLabel
    actual_decision: ControlLabel
    control_fingerprint: str
    event_fingerprint: str


@dataclass(frozen=True, slots=True)
class PeerRating:
    reviewer_id: str
    label: RatingLabel
    event_fingerprint: str


@dataclass(frozen=True, slots=True)
class AdjudicatedResolution:
    adjudicator_id: str
    label: RatingLabel
    event_fingerprint: str
    source_event_fingerprints: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReviewerOverlap:
    item_id: str
    reviewer_label: RatingLabel
    reviewer_event_fingerprint: str
    peer_ratings: tuple[PeerRating, ...]
    adjudication: AdjudicatedResolution | None = None


def estimate_reviewer_reliability(
    *,
    reliability_id: str,
    reviewer_id: str,
    domain: ReliabilityDomain,
    controls: Sequence[ControlAttempt],
    overlaps: Sequence[ReviewerOverlap],
    recorded_at: str,
) -> dict[str, object]:
    """Return one contract-valid private reliability snapshot.

    Inputs are for one reviewer and one exact domain cell. The returned estimate
    is unavailable until every policy threshold passes; callers use equal weight
    in that state, while the wire contract deliberately returns no applied score.
    """

    _validate_stable_id(reliability_id, "reliability_id")
    _validate_stable_id(reviewer_id, "reviewer_id")
    _validate_domain(domain)
    _validate_timestamp(recorded_at)
    canonical_controls = _validate_controls(controls)
    canonical_overlaps = _validate_overlaps(reviewer_id, overlaps)
    control_ids = {attempt.item_id for attempt in canonical_controls}
    overlap_ids = {item.item_id for item in canonical_overlaps}
    if control_ids & overlap_ids:
        raise ReliabilityEvidenceError(
            "control and independent-overlap item sets must be disjoint"
        )
    control_events = {attempt.event_fingerprint for attempt in canonical_controls}
    overlap_events = {
        fingerprint
        for item in canonical_overlaps
        for fingerprint in _overlap_event_fingerprints(item)
    }
    if control_events & overlap_events:
        raise ReliabilityEvidenceError(
            "control and independent-overlap event sets must be disjoint"
        )

    positive = [attempt for attempt in canonical_controls if attempt.expected_decision == "yes"]
    negative = [attempt for attempt in canonical_controls if attempt.expected_decision == "no"]
    control_correct = sum(
        attempt.actual_decision == attempt.expected_decision
        for attempt in canonical_controls
    )
    true_positive = sum(attempt.actual_decision == "yes" for attempt in positive)
    true_negative = sum(attempt.actual_decision == "no" for attempt in negative)

    pair_count = 0
    agreeing_pair_count = 0
    overlap_ratings: list[tuple[RatingLabel, ...]] = []
    adjudicated = []
    adjudicated_correct = 0
    for item in canonical_overlaps:
        ratings = (item.reviewer_label,) + tuple(peer.label for peer in item.peer_ratings)
        overlap_ratings.append(ratings)
        pair_count += len(item.peer_ratings)
        agreeing_pair_count += sum(
            item.reviewer_label == peer.label for peer in item.peer_ratings
        )
        if item.adjudication is not None:
            adjudicated.append(item)
            adjudicated_correct += item.reviewer_label == item.adjudication.label

    alpha, alpha_blocker = _nominal_krippendorff_alpha(overlap_ratings)
    metric_blockers: list[str] = []
    sensitivity = None
    if len(positive) >= MINIMUM_CLASS_COUNT:
        sensitivity = true_positive / len(positive)
    else:
        metric_blockers.append("sensitivity_positive_controls_below_minimum")
    specificity = None
    if len(negative) >= MINIMUM_CLASS_COUNT:
        specificity = true_negative / len(negative)
    else:
        metric_blockers.append("specificity_negative_controls_below_minimum")
    if pair_count == 0:
        metric_blockers.append("pairwise_overlap_unavailable")
    if alpha_blocker is not None:
        metric_blockers.append(alpha_blocker)
    if not adjudicated:
        metric_blockers.append("adjudicated_overlap_unavailable")

    policy_blockers: list[str] = []
    if len(canonical_controls) < MINIMUM_CONTROL_COUNT:
        policy_blockers.append("control_attempts_below_minimum")
    if len(positive) < MINIMUM_POSITIVE_CONTROL_COUNT:
        policy_blockers.append("positive_controls_below_minimum")
    if len(negative) < MINIMUM_NEGATIVE_CONTROL_COUNT:
        policy_blockers.append("negative_controls_below_minimum")
    if len(canonical_overlaps) < MINIMUM_OVERLAP_COUNT:
        policy_blockers.append("overlap_items_below_minimum")
    if len(adjudicated) < MINIMUM_ADJUDICATED_COUNT:
        policy_blockers.append("adjudicated_overlap_below_minimum")
    policy_blockers = sorted(set(policy_blockers))

    control_accuracy = _ratio(control_correct, len(canonical_controls))
    pairwise_agreement = _ratio(agreeing_pair_count, pair_count)
    adjudicated_overlap = _ratio(adjudicated_correct, len(adjudicated))
    minimum_evidence_met = not policy_blockers

    estimate: float | None = None
    interval: dict[str, float] | None = None
    applied_weight: float | None = None
    shrinkage_fraction: float | None = None
    if minimum_evidence_met:
        successes = control_correct + adjudicated_correct
        trials = len(canonical_controls) + len(adjudicated)
        posterior_alpha = PRIOR_ALPHA + successes
        posterior_beta = PRIOR_BETA + trials - successes
        estimate = posterior_alpha / (posterior_alpha + posterior_beta)
        lower, upper = _beta_normal_interval(posterior_alpha, posterior_beta)
        interval = {
            "lower": lower,
            "upper": upper,
            "level": INTERVAL_LEVEL,
        }
        shrinkage_fraction = (PRIOR_ALPHA + PRIOR_BETA) / (
            PRIOR_ALPHA + PRIOR_BETA + trials
        )
        applied_weight = _weight_from_accuracy(estimate)

    evidence_payload = {
        "schema_version": ESTIMATOR_VERSION,
        "policy_version": POLICY_VERSION,
        "reviewer_id": reviewer_id,
        "domain": _domain_dict(domain),
        "controls": [
            {
                "item_id": item.item_id,
                "control_kind": item.control_kind,
                "expected_decision": item.expected_decision,
                "actual_decision": item.actual_decision,
                "control_fingerprint": item.control_fingerprint,
                "event_fingerprint": item.event_fingerprint,
            }
            for item in canonical_controls
        ],
        "overlaps": [_overlap_dict(item) for item in canonical_overlaps],
    }
    evidence_fingerprint = hashlib.sha256(
        canonicalize_json(evidence_payload)
    ).hexdigest()
    decisive_count = sum(
        item.actual_decision in ("yes", "no") for item in canonical_controls
    ) + sum(item.reviewer_label in ("yes", "no") for item in canonical_overlaps)

    return {
        "schema_version": SCHEMA_VERSION,
        "reliability_id": reliability_id,
        "reviewer_id": reviewer_id,
        "domain": _domain_dict(domain),
        "method": METHOD,
        "availability": "estimated" if minimum_evidence_met else "unavailable",
        "sample_count": len(canonical_controls) + len(canonical_overlaps),
        "decisive_count": decisive_count,
        "control_count": len(canonical_controls),
        "estimate": estimate,
        "interval": interval,
        "equal_weight_target": 1,
        "applied_weight": applied_weight,
        "shrinkage_fraction": shrinkage_fraction,
        "minimum_evidence": MINIMUM_CONTROL_COUNT,
        "blockers": policy_blockers,
        "metrics": {
            "control_accuracy": control_accuracy,
            "sensitivity": sensitivity,
            "specificity": specificity,
            "pairwise_agreement": pairwise_agreement,
            "krippendorff_alpha": alpha,
            "adjudicated_overlap": adjudicated_overlap,
            "positive_control_count": len(positive),
            "negative_control_count": len(negative),
            "overlap_count": len(canonical_overlaps),
            "adjudicated_count": len(adjudicated),
            "pair_count": pair_count,
            "agreement_pair_count": agreeing_pair_count,
            "metric_blockers": sorted(set(metric_blockers)),
        },
        "evidence_fingerprint": evidence_fingerprint,
        "visibility": "private",
        "public_ranking_allowed": False,
        "model_agreement_used": False,
        "majority_agreement_alone_used": False,
        "recorded_at": recorded_at,
    }


def reliability_storage_fields(snapshot: Mapping[str, object]) -> dict[str, object]:
    """Map an estimator snapshot to the governed database insert fields.

    Reviewer/profile and project foreign keys remain the caller's responsibility.
    Accuracy-interval bounds are transformed through the same monotonic capped
    weight function as the point estimate.
    """

    if (
        snapshot.get("schema_version") != SCHEMA_VERSION
        or snapshot.get("method") != METHOD
        or snapshot.get("visibility") != "private"
        or snapshot.get("public_ranking_allowed") is not False
        or snapshot.get("model_agreement_used") is not False
        or snapshot.get("majority_agreement_alone_used") is not False
    ):
        raise ReliabilityEvidenceError(
            "storage mapping requires a private, non-circular estimator snapshot"
        )
    domain = snapshot.get("domain")
    metrics = snapshot.get("metrics")
    if not isinstance(domain, Mapping) or not isinstance(metrics, Mapping):
        raise ReliabilityEvidenceError("storage mapping requires domain and metrics")
    availability = snapshot.get("availability")
    interval = snapshot.get("interval")
    if availability == "estimated":
        if not isinstance(interval, Mapping):
            raise ReliabilityEvidenceError("estimated snapshot requires an interval")
        shrunk_weight = snapshot.get("applied_weight")
        if not isinstance(shrunk_weight, (int, float)):
            raise ReliabilityEvidenceError("estimated snapshot requires a weight")
        lower = interval.get("lower")
        upper = interval.get("upper")
        level = interval.get("level")
        if not all(isinstance(value, (int, float)) for value in (lower, upper, level)):
            raise ReliabilityEvidenceError("estimated snapshot interval is malformed")
        weight_lower = _weight_from_accuracy(float(lower))
        weight_upper = _weight_from_accuracy(float(upper))
        weighting_state = "shrunk_capped"
        minimum_evidence_met = True
        blockers: list[str] = []
    elif availability == "unavailable":
        shrunk_weight = 1.0
        weight_lower = None
        weight_upper = None
        level = None
        weighting_state = "insufficient_evidence"
        minimum_evidence_met = False
        raw_blockers = snapshot.get("blockers")
        if not isinstance(raw_blockers, list) or not raw_blockers:
            raise ReliabilityEvidenceError(
                "unavailable snapshot requires minimum-evidence blockers"
            )
        blockers = [str(blocker) for blocker in raw_blockers]
    else:
        raise ReliabilityEvidenceError("storage mapping received unknown availability")

    database_metrics = {
        **dict(metrics),
        "method": METHOD,
        "visibility": "private",
        "public_ranking_allowed": False,
        "model_agreement_used": False,
        "majority_agreement_alone_used": False,
        "scientific_claim_allowed": False,
        "evidence_fingerprint": snapshot.get("evidence_fingerprint"),
    }
    recorded_at = snapshot.get("recorded_at")
    return {
        "reviewer_reliability_id": snapshot.get("reliability_id"),
        "family_taxon_key": domain.get("taxon_group"),
        "source_provider": domain.get("source_provider"),
        "life_stage": domain.get("life_stage"),
        "visual_domain": domain.get("visual_domain"),
        "weighting_state": weighting_state,
        "minimum_evidence_met": minimum_evidence_met,
        "sample_count": snapshot.get("sample_count"),
        "decisive_count": snapshot.get("decisive_count"),
        "control_count": snapshot.get("control_count"),
        "overlap_count": metrics.get("overlap_count"),
        "adjudicated_count": metrics.get("adjudicated_count"),
        "positive_control_count": metrics.get("positive_control_count"),
        "negative_control_count": metrics.get("negative_control_count"),
        "shrunk_weight": shrunk_weight,
        "weight_lower": weight_lower,
        "weight_upper": weight_upper,
        "control_accuracy": metrics.get("control_accuracy"),
        "sensitivity": metrics.get("sensitivity"),
        "specificity": metrics.get("specificity"),
        "pairwise_agreement": metrics.get("pairwise_agreement"),
        "krippendorff_alpha": metrics.get("krippendorff_alpha"),
        "adjudicated_overlap": metrics.get("adjudicated_overlap"),
        "interval_level": level,
        "metrics": database_metrics,
        "estimator_version": ESTIMATOR_VERSION,
        "policy_version": POLICY_VERSION,
        "evidence_fingerprint": snapshot.get("evidence_fingerprint"),
        "evidence_cutoff": recorded_at,
        "blockers": blockers,
        "reliability_fingerprint": hashlib.sha256(
            canonicalize_json(snapshot)
        ).hexdigest(),
        "measured_at": recorded_at,
    }


def _validate_controls(controls: Sequence[ControlAttempt]) -> list[ControlAttempt]:
    by_item: dict[str, ControlAttempt] = {}
    control_fingerprints: set[str] = set()
    event_fingerprints: set[str] = set()
    for item in controls:
        _validate_stable_id(item.item_id, "control item_id")
        expected_for_kind = _CONTROL_EXPECTATIONS.get(item.control_kind)
        if expected_for_kind is None:
            raise ReliabilityEvidenceError("control kind is outside the closed catalog")
        if item.expected_decision != expected_for_kind:
            raise ReliabilityEvidenceError(
                "control expected decision disagrees with its closed kind"
            )
        if item.actual_decision not in _CONTROL_LABELS:
            raise ReliabilityEvidenceError(
                "control actual decision is outside the closed vocabulary"
            )
        _validate_sha(item.control_fingerprint, "control fingerprint")
        _validate_sha(item.event_fingerprint, "control event fingerprint")
        if item.item_id in by_item:
            raise ReliabilityEvidenceError("control item IDs must be unique")
        if item.control_fingerprint in control_fingerprints:
            raise ReliabilityEvidenceError("control fingerprints must be unique")
        if item.event_fingerprint in event_fingerprints:
            raise ReliabilityEvidenceError("control event fingerprints must be unique")
        by_item[item.item_id] = item
        control_fingerprints.add(item.control_fingerprint)
        event_fingerprints.add(item.event_fingerprint)
    return [by_item[key] for key in sorted(by_item)]


def _validate_overlaps(
    reviewer_id: str, overlaps: Sequence[ReviewerOverlap]
) -> list[ReviewerOverlap]:
    by_item: dict[str, ReviewerOverlap] = {}
    event_fingerprints: set[str] = set()
    for item in overlaps:
        _validate_stable_id(item.item_id, "overlap item_id")
        if item.reviewer_label not in _RATING_LABELS:
            raise ReliabilityEvidenceError(
                "reviewer overlap label is outside the closed vocabulary"
            )
        _validate_sha(item.reviewer_event_fingerprint, "reviewer event fingerprint")
        if item.item_id in by_item:
            raise ReliabilityEvidenceError("overlap item IDs must be unique")
        if not item.peer_ratings:
            raise ReliabilityEvidenceError("overlap requires an independent peer rating")
        peer_ids: set[str] = set()
        source_fingerprints = {item.reviewer_event_fingerprint}
        for peer in item.peer_ratings:
            _validate_stable_id(peer.reviewer_id, "peer reviewer_id")
            if peer.label not in _RATING_LABELS:
                raise ReliabilityEvidenceError(
                    "peer overlap label is outside the closed vocabulary"
                )
            _validate_sha(peer.event_fingerprint, "peer event fingerprint")
            if peer.reviewer_id == reviewer_id or peer.reviewer_id in peer_ids:
                raise ReliabilityEvidenceError("overlap reviewers must be independent")
            if peer.event_fingerprint in source_fingerprints:
                raise ReliabilityEvidenceError("overlap event fingerprints must be unique")
            peer_ids.add(peer.reviewer_id)
            source_fingerprints.add(peer.event_fingerprint)
        if item.adjudication is not None:
            adjudication = item.adjudication
            _validate_stable_id(adjudication.adjudicator_id, "adjudicator_id")
            if adjudication.label not in _RATING_LABELS:
                raise ReliabilityEvidenceError(
                    "adjudication label is outside the closed vocabulary"
                )
            _validate_sha(adjudication.event_fingerprint, "adjudication fingerprint")
            if (
                adjudication.adjudicator_id == reviewer_id
                or adjudication.adjudicator_id in peer_ids
            ):
                raise ReliabilityEvidenceError("adjudicator must be independent")
            if len(set(adjudication.source_event_fingerprints)) != len(
                adjudication.source_event_fingerprints
            ):
                raise ReliabilityEvidenceError("adjudication source fingerprints repeat")
            for fingerprint in adjudication.source_event_fingerprints:
                _validate_sha(fingerprint, "adjudication source fingerprint")
            if set(adjudication.source_event_fingerprints) != source_fingerprints:
                raise ReliabilityEvidenceError(
                    "adjudication must cite every exact overlap event"
                )
        item_events = set(_overlap_event_fingerprints(item))
        if item_events & event_fingerprints:
            raise ReliabilityEvidenceError(
                "overlap event fingerprints must be unique across items"
            )
        event_fingerprints.update(item_events)
        by_item[item.item_id] = item
    return [by_item[key] for key in sorted(by_item)]


def _nominal_krippendorff_alpha(
    items: Sequence[tuple[RatingLabel, ...]],
) -> tuple[float | None, str | None]:
    overlap = [ratings for ratings in items if len(ratings) >= 2]
    if len(overlap) < 2:
        return None, "krippendorff_overlap_below_minimum"
    labels: tuple[RatingLabel, ...] = ("yes", "no", "cannot_tell")
    marginals = {label: 0 for label in labels}
    observed_numerator = 0.0
    coincidence_count = 0
    for ratings in overlap:
        counts = {label: ratings.count(label) for label in labels}
        count = len(ratings)
        coincidence_count += count
        for label in labels:
            marginals[label] += counts[label]
        ordered_disagreements = count * count - sum(
            counts[label] * counts[label] for label in labels
        )
        observed_numerator += ordered_disagreements / (count - 1)
    observed = observed_numerator / coincidence_count
    expected = (
        coincidence_count * coincidence_count
        - sum(marginals[label] * marginals[label] for label in labels)
    ) / (coincidence_count * (coincidence_count - 1))
    if expected <= math.ulp(1.0):
        return None, "krippendorff_label_variation_absent"
    return 1.0 - observed / expected, None


def _beta_normal_interval(alpha: float, beta: float) -> tuple[float, float]:
    total = alpha + beta
    mean = alpha / total
    variance = alpha * beta / (total * total * (total + 1.0))
    radius = NormalDist().inv_cdf(0.5 + INTERVAL_LEVEL / 2.0) * math.sqrt(variance)
    return max(0.0, mean - radius), min(1.0, mean + radius)


def _weight_from_accuracy(accuracy: float) -> float:
    raw = 1.0 + (accuracy - EQUAL_WEIGHT_ACCURACY) / (
        1.0 - EQUAL_WEIGHT_ACCURACY
    )
    return min(WEIGHT_MAXIMUM, max(WEIGHT_MINIMUM, raw))


def _overlap_dict(item: ReviewerOverlap) -> dict[str, object]:
    return {
        "item_id": item.item_id,
        "reviewer_label": item.reviewer_label,
        "reviewer_event_fingerprint": item.reviewer_event_fingerprint,
        "peer_ratings": [
            {
                "reviewer_id": peer.reviewer_id,
                "label": peer.label,
                "event_fingerprint": peer.event_fingerprint,
            }
            for peer in sorted(item.peer_ratings, key=lambda value: value.reviewer_id)
        ],
        "adjudication": None
        if item.adjudication is None
        else {
            "adjudicator_id": item.adjudication.adjudicator_id,
            "label": item.adjudication.label,
            "event_fingerprint": item.adjudication.event_fingerprint,
            "source_event_fingerprints": sorted(
                item.adjudication.source_event_fingerprints
            ),
        },
    }


def _overlap_event_fingerprints(item: ReviewerOverlap) -> tuple[str, ...]:
    fingerprints = [item.reviewer_event_fingerprint]
    fingerprints.extend(peer.event_fingerprint for peer in item.peer_ratings)
    if item.adjudication is not None:
        fingerprints.append(item.adjudication.event_fingerprint)
    return tuple(fingerprints)


def _domain_dict(domain: ReliabilityDomain) -> dict[str, str]:
    return {
        "taxon_group": domain.family_taxon_key,
        "source_provider": domain.source_provider,
        "life_stage": domain.life_stage,
        "visual_domain": domain.visual_domain,
    }


def _validate_domain(domain: ReliabilityDomain) -> None:
    _validate_stable_id(domain.family_taxon_key, "family_taxon_key")
    if domain.source_provider not in _SOURCE_PROVIDERS:
        raise ReliabilityEvidenceError("source_provider is outside the closed contract")
    if domain.life_stage not in _LIFE_STAGES:
        raise ReliabilityEvidenceError("life_stage is outside the closed contract")
    if domain.visual_domain not in _VISUAL_DOMAINS:
        raise ReliabilityEvidenceError("visual_domain is outside the closed contract")


def _validate_stable_id(value: str, field: str) -> None:
    if _STABLE_ID.fullmatch(value) is None:
        raise ReliabilityEvidenceError(f"{field} is not a stable identifier")


def _validate_sha(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise ReliabilityEvidenceError(f"{field} is not a lowercase SHA-256")


def _validate_timestamp(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ReliabilityEvidenceError("recorded_at is not RFC 3339") from error
    if parsed.tzinfo is None:
        raise ReliabilityEvidenceError("recorded_at requires a timezone")


def _ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator
