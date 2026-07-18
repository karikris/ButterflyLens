"""Deterministic, dignity-preserving contributor impact projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Literal, Sequence

from butterflylens.contracts.fingerprint import canonicalize_json


CONTRIBUTOR_IMPACT_SCHEMA_VERSION = "butterflylens-contributor-impact:v1.0.0"
CALCULATION_VERSION = "butterflylens-contributor-impact-calculation:v1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,239}$")
_EXPERT_ROLES = {"expert", "curator", "administrator"}


class ContributorImpactError(ValueError):
    """Raised when contribution evidence cannot support a projection."""


@dataclass(frozen=True)
class ContributorIdentity:
    reviewer_profile_id: str
    project_id: str
    role: Literal["reviewer", "expert", "curator", "administrator"]
    qualification_state: Literal["unverified", "pending", "verified", "rejected"]


@dataclass(frozen=True)
class ContributionEvent:
    event_fingerprint: str
    kind: Literal["review", "conflict_resolution"]
    media_object_id: str
    species_ids: tuple[str, ...] = ()
    region_ids: tuple[str, ...] = ()
    conflict_id: str | None = None
    control_fingerprint: str | None = None
    expert_eligible: bool = False
    effective: bool = True


def compile_contributor_impact(
    events: Sequence[ContributionEvent],
    *,
    identity: ContributorIdentity,
    calculated_at: datetime,
) -> dict[str, object]:
    """Compile exact effective-event lineage; never derive rank, pace, or authority."""

    _identifier(identity.reviewer_profile_id, "reviewer profile ID")
    _identifier(identity.project_id, "project ID")
    if calculated_at.tzinfo is None or calculated_at.utcoffset() is None:
        raise ContributorImpactError("calculated_at must be timezone-aware")

    seen_fingerprints: set[str] = set()
    effective: list[ContributionEvent] = []
    for event in events:
        _validate_event(event)
        if event.event_fingerprint in seen_fingerprints:
            raise ContributorImpactError("duplicate contribution event fingerprint")
        seen_fingerprints.add(event.event_fingerprint)
        if event.effective:
            effective.append(event)

    review_media = {
        event.media_object_id for event in effective if event.kind == "review"
    }
    conflicts = {
        event.conflict_id
        for event in effective
        if event.kind == "conflict_resolution" and event.conflict_id is not None
    }
    species = {item for event in effective for item in event.species_ids}
    regions = {item for event in effective for item in event.region_ids}
    controls = {
        event.control_fingerprint
        for event in effective
        if event.kind == "review" and event.control_fingerprint is not None
    }
    expert_role = (
        identity.role in _EXPERT_ROLES
        and identity.qualification_state == "verified"
    )
    expert_count = (
        sum(1 for event in effective if event.expert_eligible)
        if expert_role
        else None
    )
    expert_state = "available" if expert_role else "not_applicable"
    expert_reason = (
        None
        if expert_role
        else "A verified expert, curator, or administrator role is not recorded."
    )
    source_fingerprints = sorted(event.event_fingerprint for event in effective)
    evidence_preimage = {
        "schema_version": CONTRIBUTOR_IMPACT_SCHEMA_VERSION,
        "project_id": identity.project_id,
        "reviewer_profile_id": identity.reviewer_profile_id,
        "source_event_fingerprints": source_fingerprints,
    }
    source_evidence_fingerprint = hashlib.sha256(
        canonicalize_json(evidence_preimage)
    ).hexdigest()
    payload: dict[str, object] = {
        "schema_version": CONTRIBUTOR_IMPACT_SCHEMA_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "project_id": identity.project_id,
        "reviewer_profile_id": identity.reviewer_profile_id,
        "snapshot_state": "available",
        "snapshot_state_reason": None,
        "reviewed_image_count": len(review_media),
        "resolved_conflict_count": len(conflicts),
        "species_helped_count": len(species),
        "region_helped_count": len(regions),
        "control_coverage_count": len(controls),
        "expert_contribution_state": expert_state,
        "expert_contribution_count": expert_count,
        "expert_contribution_reason": expert_reason,
        "source_event_fingerprints": source_fingerprints,
        "source_evidence_fingerprint": source_evidence_fingerprint,
        "visibility": "self_only",
        "ranking_permitted": False,
        "speed_metric_permitted": False,
        "scientific_claim_allowed": False,
        "calculated_at": calculated_at.astimezone(timezone.utc).isoformat().replace(
            "+00:00", "Z"
        ),
    }
    payload["projection_fingerprint"] = hashlib.sha256(
        canonicalize_json(payload)
    ).hexdigest()
    return payload


def _validate_event(event: ContributionEvent) -> None:
    _sha256(event.event_fingerprint, "event fingerprint")
    _identifier(event.media_object_id, "media object ID")
    for field, values in (("species", event.species_ids), ("region", event.region_ids)):
        if len(values) != len(set(values)):
            raise ContributorImpactError(f"duplicate {field} ID in contribution event")
        for value in values:
            _identifier(value, f"{field} ID")
    if event.kind == "review":
        if event.conflict_id is not None:
            raise ContributorImpactError("review event cannot carry a conflict ID")
    elif event.conflict_id is None:
        raise ContributorImpactError("conflict resolution requires a conflict ID")
    else:
        _identifier(event.conflict_id, "conflict ID")
    if event.control_fingerprint is not None:
        if event.kind != "review":
            raise ContributorImpactError("only review events can carry control evidence")
        _sha256(event.control_fingerprint, "control fingerprint")


def _identifier(value: str, field: str) -> None:
    if _IDENTIFIER.fullmatch(value) is None:
        raise ContributorImpactError(f"invalid {field}")


def _sha256(value: str, field: str) -> None:
    if _SHA256.fullmatch(value) is None:
        raise ContributorImpactError(f"invalid {field}")
