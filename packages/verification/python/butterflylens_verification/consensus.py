"""Deterministic layered human consensus with preserved dissent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import re
from typing import Literal, Mapping, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json

from .reliability import (
    METHOD as RELIABILITY_METHOD,
    SCHEMA_VERSION as RELIABILITY_SCHEMA_VERSION,
    ReliabilityDomain,
)


SCHEMA_VERSION = "butterflylens-verification-consensus:v1.0.0"
METHOD_VERSION = "butterflylens-layered-consensus:v1.0.0"
POLICY_VERSION = "butterflylens-layered-consensus-policy:v1.0.0"

ReviewOutcome = Literal["yes", "no", "cant_tell", "cant_view", "skipped"]
DecisiveOutcome = Literal["yes", "no"]

_OUTCOMES = {"yes", "no", "cant_tell", "cant_view", "skipped"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_STABLE_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")


class ConsensusEvidenceError(ValueError):
    """Raised when consensus input is malformed, mixed, or non-independent."""


@dataclass(frozen=True, slots=True)
class ConsensusReview:
    project_id: str
    campaign_id: str
    item_id: str
    reviewer_id: str
    event_fingerprint: str
    outcome: ReviewOutcome
    qualified: bool
    reviewed_at: str
    supersedes_event_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class ConsensusAdjudication:
    adjudicator_id: str
    event_fingerprint: str
    outcome: DecisiveOutcome
    source_event_fingerprints: tuple[str, ...]
    adjudicated_at: str
    qualified: bool


@dataclass(frozen=True, slots=True)
class ReleaseGates:
    rights_passed: bool = False
    provenance_passed: bool = False
    conflict_resolved: bool = False
    quality_passed: bool = False
    expert_gate_satisfied: bool = False
    authorization_passed: bool = False


def calculate_layered_consensus(
    *,
    consensus_id: str,
    project_id: str,
    campaign_id: str,
    item_id: str,
    revision: int,
    required_review_count: int,
    events: Sequence[ConsensusReview],
    domain: ReliabilityDomain,
    reliability_snapshots: Mapping[str, Mapping[str, object]],
    adjudication: ConsensusAdjudication | None,
    release_gates: ReleaseGates,
) -> dict[str, object]:
    """Calculate unweighted, qualified, and release layers.

    Disagreement is never resolved by a majority or model vote. Reliability
    changes only the separately labelled qualified totals; exact independent
    adjudication is required to resolve conflicting decisive human events.
    """

    for value, field in (
        (consensus_id, "consensus_id"),
        (project_id, "project_id"),
        (campaign_id, "campaign_id"),
        (item_id, "item_id"),
    ):
        _validate_stable_id(value, field)
    if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
        raise ConsensusEvidenceError("revision must be a positive integer")
    if (
        isinstance(required_review_count, bool)
        or not isinstance(required_review_count, int)
        or required_review_count < 1
    ):
        raise ConsensusEvidenceError(
            "required_review_count must be a positive integer"
        )

    effective = _effective_reviews(
        events,
        project_id=project_id,
        campaign_id=campaign_id,
        item_id=item_id,
    )
    decisive = [event for event in effective if event.outcome in ("yes", "no")]
    uncertain = [event for event in effective if event.outcome == "cant_tell"]
    yes_events = [event for event in decisive if event.outcome == "yes"]
    no_events = [event for event in decisive if event.outcome == "no"]
    decisive_conflict = bool(yes_events and no_events)
    conflict_events = sorted(
        event.event_fingerprint
        for event in (
            decisive if decisive_conflict else [*decisive, *uncertain]
        )
    )
    has_uncertain_conflict = bool(uncertain and decisive)
    conflicts = []
    if decisive_conflict or has_uncertain_conflict:
        conflicts.append(
            {
                "field": "outcome",
                "event_fingerprints": conflict_events,
            }
        )

    valid_adjudication = _validate_adjudication(
        adjudication,
        effective=effective,
        conflicting_decisive=decisive if decisive_conflict else [],
    )
    status = _overall_status(
        effective=effective,
        decisive=decisive,
        uncertain=uncertain,
        decisive_conflict=decisive_conflict,
        valid_adjudication=valid_adjudication,
        required_review_count=required_review_count,
    )
    _validate_release_gates(release_gates, consensus_status=status)

    community = _community_layer(
        effective=effective,
        decisive=decisive,
        uncertain=uncertain,
        status=status,
        required_review_count=required_review_count,
    )
    qualified_events = [event for event in effective if event.qualified]
    weights, reliability_fingerprint = _qualified_weights(
        qualified_events,
        reliability_snapshots=reliability_snapshots,
        domain=domain,
    )
    qualified = _qualified_layer(
        events=qualified_events,
        weights=weights,
        weights_applied=reliability_fingerprint is not None,
        adjudication=adjudication if valid_adjudication else None,
        required_review_count=required_review_count,
    )
    reviewer_weights_applied = reliability_fingerprint is not None
    release = _release_layer(
        qualified=qualified,
        release_gates=release_gates,
    )
    resolved_at = _resolved_at(status, effective, adjudication)
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": POLICY_VERSION,
        "consensus_id": consensus_id,
        "project_id": project_id,
        "campaign_id": campaign_id,
        "item_id": item_id,
        "revision": revision,
        "status": status,
        "required_review_count": required_review_count,
        "effective_review_count": len(effective),
        "decisive_review_count": len(decisive),
        "effective_event_fingerprints": sorted(
            event.event_fingerprint for event in effective
        ),
        "conflicts": conflicts,
        "adjudication_event_fingerprint": (
            adjudication.event_fingerprint if valid_adjudication else None
        ),
        "community_evidence": community,
        "qualified_consensus": qualified,
        "release_consensus": release,
        "release_gates": _release_gate_dict(release_gates),
        "reviewer_weights_applied": reviewer_weights_applied,
        "reliability_snapshot_fingerprint": reliability_fingerprint,
        "model_vote_included": False,
        "resolved_at": resolved_at,
    }
    payload["consensus_fingerprint"] = hashlib.sha256(
        canonicalize_json(payload)
    ).hexdigest()
    return payload


def consensus_storage_rows(snapshot: Mapping[str, object]) -> list[dict[str, object]]:
    """Map one layered snapshot to three append-only database rows."""

    if (
        snapshot.get("schema_version") != SCHEMA_VERSION
        or snapshot.get("policy_version") != POLICY_VERSION
    ):
        raise ConsensusEvidenceError("storage mapping requires a consensus snapshot")
    if snapshot.get("model_vote_included") is not False:
        raise ConsensusEvidenceError("model vote cannot enter consensus storage")
    layers = (
        ("community_evidence", "community_evidence"),
        ("qualified_consensus", "qualified_consensus"),
        ("release_consensus", "release_consensus"),
    )
    rows: list[dict[str, object]] = []
    for field, database_layer in layers:
        layer = snapshot.get(field)
        if not isinstance(layer, Mapping):
            raise ConsensusEvidenceError("consensus storage layer is malformed")
        status, decision = _database_status_and_decision(layer)
        row_payload = {
            "outer_consensus_fingerprint": snapshot.get("consensus_fingerprint"),
            "layer": database_layer,
            "summary": dict(layer),
            "release_gates": snapshot.get("release_gates"),
            "adjudication_event_fingerprint": snapshot.get(
                "adjudication_event_fingerprint"
            ),
            "reliability_snapshot_fingerprint": snapshot.get(
                "reliability_snapshot_fingerprint"
            ),
        }
        row_fingerprint = hashlib.sha256(canonicalize_json(row_payload)).hexdigest()
        layer_id = f"consensus:{row_fingerprint[:32]}"
        is_qualified = database_layer == "qualified_consensus"
        rows.append(
            {
                "consensus_id": layer_id,
                "consensus_layer": database_layer,
                "status": status,
                "decision": decision,
                "method": layer.get("method"),
                "method_version": METHOD_VERSION,
                "eligible_review_count": layer.get("eligible_review_count"),
                "decisive_review_count": layer.get("decisive_review_count"),
                "qualified_review_count": (
                    layer.get("eligible_review_count") if is_qualified else 0
                ),
                "expert_gate_satisfied": (
                    snapshot.get("release_gates", {}).get(
                        "expert_gate_satisfied", False
                    )
                    if database_layer == "release_consensus"
                    and isinstance(snapshot.get("release_gates"), Mapping)
                    else False
                ),
                "minority_dissent_count": layer.get("dissent_count"),
                "review_event_fingerprints": layer.get("event_fingerprints"),
                "revision": snapshot.get("revision"),
                "adjudication_event_fingerprint": snapshot.get(
                    "adjudication_event_fingerprint"
                ),
                "reviewer_weights_applied": (
                    snapshot.get("reviewer_weights_applied") if is_qualified else False
                ),
                "reliability_snapshot_fingerprint": (
                    snapshot.get("reliability_snapshot_fingerprint")
                    if is_qualified
                    else None
                ),
                "layer_summary": {
                    **dict(layer),
                    "policy_version": snapshot.get("policy_version"),
                    "model_vote_included": False,
                    "scientific_claim_allowed": False,
                    "outer_consensus_fingerprint": snapshot.get(
                        "consensus_fingerprint"
                    ),
                    "adjudication_event_fingerprint": snapshot.get(
                        "adjudication_event_fingerprint"
                    ),
                    "release_gates": snapshot.get("release_gates"),
                },
                "consensus_fingerprint": row_fingerprint,
            }
        )
    return rows


def _effective_reviews(
    events: Sequence[ConsensusReview],
    *,
    project_id: str,
    campaign_id: str,
    item_id: str,
) -> list[ConsensusReview]:
    by_fingerprint: dict[str, ConsensusReview] = {}
    for event in events:
        for value, field in (
            (event.project_id, "event project_id"),
            (event.campaign_id, "event campaign_id"),
            (event.item_id, "event item_id"),
            (event.reviewer_id, "event reviewer_id"),
        ):
            _validate_stable_id(value, field)
        if (event.project_id, event.campaign_id, event.item_id) != (
            project_id,
            campaign_id,
            item_id,
        ):
            raise ConsensusEvidenceError("review event is outside the exact scope")
        _validate_sha(event.event_fingerprint, "review event fingerprint")
        if event.outcome not in _OUTCOMES:
            raise ConsensusEvidenceError("review outcome is outside the closed vocabulary")
        if not isinstance(event.qualified, bool):
            raise ConsensusEvidenceError("review qualification flag must be boolean")
        _validate_timestamp(event.reviewed_at, "reviewed_at")
        if event.event_fingerprint in by_fingerprint:
            raise ConsensusEvidenceError("review event fingerprints must be unique")
        by_fingerprint[event.event_fingerprint] = event

    superseded: set[str] = set()
    for event in events:
        parent_fingerprint = event.supersedes_event_fingerprint
        if parent_fingerprint is None:
            continue
        _validate_sha(parent_fingerprint, "superseded event fingerprint")
        parent = by_fingerprint.get(parent_fingerprint)
        if parent is None:
            raise ConsensusEvidenceError("superseded review event is missing")
        if parent.reviewer_id != event.reviewer_id:
            raise ConsensusEvidenceError("review correction crosses reviewer identity")
        if _parsed_timestamp(event.reviewed_at) < _parsed_timestamp(parent.reviewed_at):
            raise ConsensusEvidenceError("review correction predates its source event")
        if parent_fingerprint in superseded:
            raise ConsensusEvidenceError("review event is superseded more than once")
        superseded.add(parent_fingerprint)
        _assert_acyclic_supersession(event, by_fingerprint)

    effective = [
        event for event in events if event.event_fingerprint not in superseded
    ]
    reviewer_ids = [event.reviewer_id for event in effective]
    if len(reviewer_ids) != len(set(reviewer_ids)):
        raise ConsensusEvidenceError("reviewer has more than one effective event")
    return sorted(effective, key=lambda event: event.event_fingerprint)


def _assert_acyclic_supersession(
    event: ConsensusReview,
    by_fingerprint: Mapping[str, ConsensusReview],
) -> None:
    visited = {event.event_fingerprint}
    current = event
    while current.supersedes_event_fingerprint is not None:
        parent_fingerprint = current.supersedes_event_fingerprint
        if parent_fingerprint in visited:
            raise ConsensusEvidenceError("review supersession contains a cycle")
        visited.add(parent_fingerprint)
        current = by_fingerprint[parent_fingerprint]


def _validate_adjudication(
    adjudication: ConsensusAdjudication | None,
    *,
    effective: Sequence[ConsensusReview],
    conflicting_decisive: Sequence[ConsensusReview],
) -> bool:
    if adjudication is None:
        return False
    _validate_stable_id(adjudication.adjudicator_id, "adjudicator_id")
    _validate_sha(adjudication.event_fingerprint, "adjudication event fingerprint")
    _validate_timestamp(adjudication.adjudicated_at, "adjudicated_at")
    if adjudication.outcome not in ("yes", "no"):
        raise ConsensusEvidenceError("adjudication outcome must be decisive")
    if adjudication.qualified is not True:
        raise ConsensusEvidenceError("adjudication requires a qualified reviewer")
    if adjudication.adjudicator_id in {event.reviewer_id for event in effective}:
        raise ConsensusEvidenceError("adjudicator must be independent")
    source_fingerprints = tuple(adjudication.source_event_fingerprints)
    if len(source_fingerprints) != len(set(source_fingerprints)):
        raise ConsensusEvidenceError("adjudication source fingerprints repeat")
    if adjudication.event_fingerprint in source_fingerprints:
        raise ConsensusEvidenceError("adjudication cannot cite itself")
    for fingerprint in source_fingerprints:
        _validate_sha(fingerprint, "adjudication source fingerprint")
    expected = {event.event_fingerprint for event in conflicting_decisive}
    if not expected:
        raise ConsensusEvidenceError("adjudication requires decisive disagreement")
    if set(source_fingerprints) != expected:
        raise ConsensusEvidenceError(
            "adjudication must cite every exact conflicting decisive event"
        )
    return True


def _qualified_weights(
    events: Sequence[ConsensusReview],
    *,
    reliability_snapshots: Mapping[str, Mapping[str, object]],
    domain: ReliabilityDomain,
) -> tuple[dict[str, float], str | None]:
    weights = {event.reviewer_id: 1.0 for event in events}
    selected: list[dict[str, object]] = []
    expected_domain = {
        "taxon_group": domain.family_taxon_key,
        "source_provider": domain.source_provider,
        "life_stage": domain.life_stage,
        "visual_domain": domain.visual_domain,
    }
    for reviewer_id in sorted(weights):
        snapshot = reliability_snapshots.get(reviewer_id)
        if snapshot is None:
            continue
        if (
            snapshot.get("schema_version") != RELIABILITY_SCHEMA_VERSION
            or snapshot.get("reviewer_id") != reviewer_id
            or snapshot.get("domain") != expected_domain
            or snapshot.get("method") != RELIABILITY_METHOD
            or snapshot.get("visibility") != "private"
            or snapshot.get("public_ranking_allowed") is not False
            or snapshot.get("model_agreement_used") is not False
            or snapshot.get("majority_agreement_alone_used") is not False
        ):
            raise ConsensusEvidenceError(
                "reliability snapshot violates exact private domain policy"
            )
        availability = snapshot.get("availability")
        if availability == "unavailable":
            if snapshot.get("applied_weight") is not None:
                raise ConsensusEvidenceError(
                    "unavailable reliability snapshot cannot carry a weight"
                )
            continue
        if availability != "estimated" or snapshot.get("blockers") != []:
            raise ConsensusEvidenceError("reliability availability is malformed")
        weight = snapshot.get("applied_weight")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not 0.5 <= float(weight) <= 2.0
        ):
            raise ConsensusEvidenceError("reliability weight is outside policy")
        _validate_sha(
            str(snapshot.get("evidence_fingerprint", "")),
            "reliability evidence fingerprint",
        )
        weights[reviewer_id] = float(weight)
        selected.append(
            {
                "reviewer_id": reviewer_id,
                "reliability_id": snapshot.get("reliability_id"),
                "evidence_fingerprint": snapshot.get("evidence_fingerprint"),
                "recorded_at": snapshot.get("recorded_at"),
                "applied_weight": float(weight),
            }
        )
    if not selected:
        return weights, None
    fingerprint = hashlib.sha256(
        canonicalize_json(
            {
                "method_version": METHOD_VERSION,
                "domain": expected_domain,
                "snapshots": selected,
            }
        )
    ).hexdigest()
    return weights, fingerprint


def _community_layer(
    *,
    effective: Sequence[ConsensusReview],
    decisive: Sequence[ConsensusReview],
    uncertain: Sequence[ConsensusReview],
    status: str,
    required_review_count: int,
) -> dict[str, object]:
    blockers: list[str] = []
    layer_status = "available"
    outcome: str | None
    if status == "pending":
        layer_status = "pending"
        outcome = None
        blockers.append("decisive_reviews_below_required")
    elif status == "unresolved_disagreement":
        layer_status = "blocked"
        outcome = "uncertain"
        blockers.append("human_disagreement_requires_adjudication")
    elif status == "adjudicated":
        layer_status = "blocked"
        outcome = "uncertain"
        blockers.append("source_dissent_retained_after_adjudication")
    elif status == "uncertain_only":
        outcome = "uncertain"
    elif status == "media_failure":
        outcome = "media_failure"
    elif status == "deferred":
        layer_status = "unavailable"
        outcome = "deferred"
        blockers.append("all_effective_reviews_deferred")
    else:
        outcome = "supported" if decisive[0].outcome == "yes" else "not_supported"
    if len(decisive) < required_review_count and status == "complete_agreement":
        raise ConsensusEvidenceError("complete agreement is below the review minimum")
    return _layer_summary(
        method="unweighted_human_counts_v1",
        status=layer_status,
        outcome=outcome,
        events=effective,
        weights=None,
        blockers=blockers,
    )


def _qualified_layer(
    *,
    events: Sequence[ConsensusReview],
    weights: Mapping[str, float],
    weights_applied: bool,
    adjudication: ConsensusAdjudication | None,
    required_review_count: int,
) -> dict[str, object]:
    decisive = [event for event in events if event.outcome in ("yes", "no")]
    uncertain = [event for event in events if event.outcome == "cant_tell"]
    yes = [event for event in decisive if event.outcome == "yes"]
    no = [event for event in decisive if event.outcome == "no"]
    method = (
        "qualified_reliability_weighted_v1"
        if weights_applied
        else "qualified_equal_weight_v1"
    )
    blockers: list[str] = []
    if adjudication is not None:
        method = "qualified_adjudication_v1"
        status = "available"
        outcome = "supported" if adjudication.outcome == "yes" else "not_supported"
    elif not events:
        status = "unavailable"
        outcome = None
        blockers.append("qualified_reviews_unavailable")
    elif len(decisive) < required_review_count:
        status = "pending"
        outcome = None
        blockers.append("qualified_decisive_reviews_below_required")
    elif yes and no:
        status = "blocked"
        outcome = "uncertain"
        blockers.append("qualified_disagreement_requires_adjudication")
    elif uncertain:
        status = "blocked"
        outcome = "uncertain"
        blockers.append("qualified_uncertainty_unresolved")
    else:
        status = "available"
        outcome = "supported" if yes else "not_supported"
    return _layer_summary(
        method=method,
        status=status,
        outcome=outcome,
        events=events,
        weights=weights,
        blockers=blockers,
    )


def _release_layer(
    *,
    qualified: Mapping[str, object],
    release_gates: ReleaseGates,
) -> dict[str, object]:
    blockers = _release_blockers(release_gates)
    qualified_status = qualified.get("status")
    qualified_outcome = qualified.get("outcome")
    if qualified_status != "available":
        blockers.append("qualified_consensus_unavailable")
    if qualified_outcome == "not_supported":
        status = "available"
        outcome = "not_release_ready"
        blockers = []
    elif not blockers and qualified_outcome == "supported":
        status = "available"
        outcome = "release_ready"
    else:
        status = "blocked"
        outcome = "not_release_ready"
    return {
        **dict(qualified),
        "method": "release_gate_v1",
        "status": status,
        "outcome": outcome,
        "support_total": qualified.get("support_count", 0),
        "oppose_total": qualified.get("oppose_count", 0),
        "blockers": sorted(set(blockers)),
    }


def _layer_summary(
    *,
    method: str,
    status: str,
    outcome: str | None,
    events: Sequence[ConsensusReview],
    weights: Mapping[str, float] | None,
    blockers: Sequence[str],
) -> dict[str, object]:
    decisive = [event for event in events if event.outcome in ("yes", "no")]
    support_total = sum(
        (weights or {}).get(event.reviewer_id, 1.0)
        for event in decisive
        if event.outcome == "yes"
    )
    oppose_total = sum(
        (weights or {}).get(event.reviewer_id, 1.0)
        for event in decisive
        if event.outcome == "no"
    )
    return {
        "method": method,
        "status": status,
        "outcome": outcome,
        "eligible_review_count": len(events),
        "decisive_review_count": len(decisive),
        "support_count": sum(event.outcome == "yes" for event in decisive),
        "oppose_count": sum(event.outcome == "no" for event in decisive),
        "support_total": support_total,
        "oppose_total": oppose_total,
        "uncertain_count": sum(event.outcome == "cant_tell" for event in events),
        "media_failure_count": sum(event.outcome == "cant_view" for event in events),
        "deferred_count": sum(event.outcome == "skipped" for event in events),
        "dissent_count": min(
            sum(event.outcome == "yes" for event in decisive),
            sum(event.outcome == "no" for event in decisive),
        ),
        "event_fingerprints": sorted(event.event_fingerprint for event in events),
        "blockers": sorted(set(blockers)),
    }


def _overall_status(
    *,
    effective: Sequence[ConsensusReview],
    decisive: Sequence[ConsensusReview],
    uncertain: Sequence[ConsensusReview],
    decisive_conflict: bool,
    valid_adjudication: bool,
    required_review_count: int,
) -> str:
    if not decisive:
        if uncertain:
            return "uncertain_only"
        if any(event.outcome == "cant_view" for event in effective):
            return "media_failure"
        return "deferred"
    if decisive_conflict:
        return "adjudicated" if valid_adjudication else "unresolved_disagreement"
    if uncertain:
        return "unresolved_disagreement"
    if len(decisive) < required_review_count:
        return "pending"
    return "complete_agreement"


def _resolved_at(
    status: str,
    events: Sequence[ConsensusReview],
    adjudication: ConsensusAdjudication | None,
) -> str | None:
    if status == "adjudicated" and adjudication is not None:
        return adjudication.adjudicated_at
    if status == "complete_agreement":
        return max(
            events,
            key=lambda event: (
                _parsed_timestamp(event.reviewed_at),
                event.event_fingerprint,
            ),
        ).reviewed_at
    return None


def _release_gate_dict(gates: ReleaseGates) -> dict[str, bool]:
    return {
        "rights_passed": gates.rights_passed,
        "provenance_passed": gates.provenance_passed,
        "conflict_resolved": gates.conflict_resolved,
        "quality_passed": gates.quality_passed,
        "expert_gate_satisfied": gates.expert_gate_satisfied,
        "authorization_passed": gates.authorization_passed,
    }


def _validate_release_gates(
    gates: ReleaseGates,
    *,
    consensus_status: str,
) -> None:
    values = _release_gate_dict(gates)
    if any(not isinstance(value, bool) for value in values.values()):
        raise ConsensusEvidenceError("release gate values must be boolean")
    actually_resolved = consensus_status in ("complete_agreement", "adjudicated")
    if gates.conflict_resolved and not actually_resolved:
        raise ConsensusEvidenceError(
            "release conflict gate contradicts unresolved human evidence"
        )


def _release_blockers(gates: ReleaseGates) -> list[str]:
    return [
        blocker
        for passed, blocker in (
            (gates.rights_passed, "rights_gate_required"),
            (gates.provenance_passed, "provenance_gate_required"),
            (gates.conflict_resolved, "conflict_resolution_required"),
            (gates.quality_passed, "quality_gate_required"),
            (gates.expert_gate_satisfied, "expert_gate_required"),
            (gates.authorization_passed, "release_authorization_required"),
        )
        if not passed
    ]


def _database_status_and_decision(
    layer: Mapping[str, object],
) -> tuple[str, str | None]:
    outcome = layer.get("outcome")
    if outcome == "supported":
        return "reached", "yes"
    if outcome == "not_supported":
        return "reached", "no"
    if outcome == "uncertain" and layer.get("status") == "available":
        return "reached", "cannot_tell"
    if outcome == "media_failure":
        return "reached", "cannot_view"
    if outcome == "release_ready":
        return "reached", "yes"
    if outcome == "not_release_ready" and layer.get("status") == "available":
        return "rejected", None
    if layer.get("status") == "blocked":
        return "disputed", None
    return "insufficient", None


def _validate_stable_id(value: str, field: str) -> None:
    if _STABLE_ID.fullmatch(value) is None:
        raise ConsensusEvidenceError(f"{field} is not a stable identifier")


def _validate_sha(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise ConsensusEvidenceError(f"{field} is not a lowercase SHA-256")


def _validate_timestamp(value: str, field: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConsensusEvidenceError(f"{field} is not RFC 3339") from error
    if parsed.tzinfo is None:
        raise ConsensusEvidenceError(f"{field} requires a timezone")


def _parsed_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
