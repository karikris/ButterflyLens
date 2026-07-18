"""Fail-closed public-location decisions for sensitive butterfly evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Literal, Sequence

from .fingerprint import canonicalize_json


SENSITIVE_LOCATION_POLICY_VERSION = "butterflylens-sensitive-location-policy:v1.0.0"
PUBLIC_LOCATION_DECISION_SCHEMA_VERSION = (
    "butterflylens-public-location-decision:v1.0.0"
)

Provider = Literal["ala", "flickr"]
SensitivityState = Literal["not_sensitive", "sensitive", "unknown"]
PolicyAction = Literal["provider_resolution", "generalise", "withhold"]
PublicationState = Literal["publish", "generalised", "withheld"]
SourcePrecision = Literal["exact", "generalised", "coarse_rollup", "withheld"]
ScopeKind = Literal["australia", "state_territory", "ibra", "lga", "h3"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_H3_CELL = re.compile(r"^[0-9a-f]{15}$")
_ALA_STATES = frozenset(
    {"public_processed", "public_generalised", "withheld", "not_used"}
)
_FLICKR_STATES = frozenset({"public_geo", "nonpublic_geo", "no_geo", "not_used"})
_PUBLIC_STATES = {
    "ala": frozenset({"public_processed", "public_generalised"}),
    "flickr": frozenset({"public_geo"}),
}
_SCOPE_KINDS = frozenset({"australia", "state_territory", "ibra", "lga", "h3"})


def _require_fingerprint(value: str, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


def _digest(value: object) -> str:
    return hashlib.sha256(canonicalize_json(value)).hexdigest()


@dataclass(frozen=True, slots=True)
class ProviderLocationConstraint:
    """One provider's explicit permission and maximum public resolution.

    The contract deliberately does not infer an H3 level from ALA labels or a
    Flickr accuracy value. A versioned mapping must make that decision before
    a provider location can be used.
    """

    provider: Provider
    disclosure_state: str
    location_used_for_target: bool
    maximum_public_h3_resolution: int | None
    provider_precision: str | None
    flickr_accuracy: int | None
    resolution_mapping_version: str | None
    source_snapshot_fingerprint: str
    permission_evidence_fingerprint: str

    def __post_init__(self) -> None:
        if self.provider not in ("ala", "flickr"):
            raise ValueError("provider must be ala or flickr")
        states = _ALA_STATES if self.provider == "ala" else _FLICKR_STATES
        if self.disclosure_state not in states:
            raise ValueError(f"invalid {self.provider} disclosure state")
        _require_fingerprint(self.source_snapshot_fingerprint, "source_snapshot_fingerprint")
        _require_fingerprint(
            self.permission_evidence_fingerprint,
            "permission_evidence_fingerprint",
        )
        if self.flickr_accuracy is not None and not 1 <= self.flickr_accuracy <= 16:
            raise ValueError("flickr_accuracy must be between 1 and 16")
        if self.provider == "ala" and self.flickr_accuracy is not None:
            raise ValueError("ALA constraints cannot carry Flickr accuracy")
        if self.provider == "flickr":
            if self.disclosure_state == "public_geo" and self.flickr_accuracy is None:
                raise ValueError("public Flickr geo requires the provider accuracy")
            if self.disclosure_state != "public_geo" and self.flickr_accuracy is not None:
                raise ValueError("non-public Flickr geo cannot carry public accuracy")
        if self.disclosure_state == "not_used" and self.location_used_for_target:
            raise ValueError("not_used provider location cannot contribute to a target")
        if self.location_used_for_target:
            if self.disclosure_state not in _PUBLIC_STATES[self.provider]:
                raise ValueError("a non-public provider location cannot contribute to a target")
            if not isinstance(self.maximum_public_h3_resolution, int) or not (
                0 <= self.maximum_public_h3_resolution <= 15
            ):
                raise ValueError("used provider location requires an H3 resolution ceiling")
            if not self.provider_precision or len(self.provider_precision) > 120:
                raise ValueError("used provider location requires bounded precision evidence")
            if not self.resolution_mapping_version or len(self.resolution_mapping_version) > 120:
                raise ValueError("used provider location requires a versioned resolution mapping")
        elif self.maximum_public_h3_resolution is not None:
            raise ValueError("unused provider location cannot set a public H3 ceiling")

    @property
    def constraint_fingerprint(self) -> str:
        return _digest(
            {
                "schema_version": "butterflylens-provider-location-constraint:v1.0.0",
                **asdict(self),
            }
        )


@dataclass(frozen=True, slots=True)
class SensitiveLocationRule:
    """Versioned taxon/location policy evaluated after provider constraints."""

    sensitivity_state: SensitivityState
    action: PolicyAction
    maximum_public_h3_resolution: int | None
    allowed_scope_kinds: tuple[ScopeKind, ...]
    minimum_public_record_count: int | None
    policy_evidence_fingerprint: str
    policy_version: str = SENSITIVE_LOCATION_POLICY_VERSION

    def __post_init__(self) -> None:
        if self.policy_version != SENSITIVE_LOCATION_POLICY_VERSION:
            raise ValueError("unsupported sensitive-location policy version")
        if self.sensitivity_state not in ("not_sensitive", "sensitive", "unknown"):
            raise ValueError("invalid sensitivity_state")
        if self.action not in ("provider_resolution", "generalise", "withhold"):
            raise ValueError("invalid sensitive-location action")
        _require_fingerprint(self.policy_evidence_fingerprint, "policy_evidence_fingerprint")
        if len(set(self.allowed_scope_kinds)) != len(self.allowed_scope_kinds):
            raise ValueError("allowed_scope_kinds must be unique")
        if tuple(sorted(self.allowed_scope_kinds)) != self.allowed_scope_kinds:
            raise ValueError("allowed_scope_kinds must be sorted")
        if not set(self.allowed_scope_kinds).issubset(_SCOPE_KINDS):
            raise ValueError("allowed_scope_kinds contains an unsupported scope")
        if self.sensitivity_state == "unknown" and self.action != "withhold":
            raise ValueError("unknown sensitivity must be withheld")
        if self.sensitivity_state == "sensitive" and self.action == "provider_resolution":
            raise ValueError("sensitive taxa must be generalised or withheld")
        if self.action == "withhold":
            if self.maximum_public_h3_resolution is not None:
                raise ValueError("withheld rules cannot publish an H3 ceiling")
            if self.allowed_scope_kinds:
                raise ValueError("withheld rules cannot allow public scopes")
            if self.minimum_public_record_count is not None:
                raise ValueError("withheld rules cannot set a public count threshold")
        else:
            if not isinstance(self.maximum_public_h3_resolution, int) or not (
                0 <= self.maximum_public_h3_resolution <= 15
            ):
                raise ValueError("publishable rules require an H3 resolution ceiling")
            if not self.allowed_scope_kinds:
                raise ValueError("publishable rules require explicit allowed scopes")
            if (
                not isinstance(self.minimum_public_record_count, int)
                or self.minimum_public_record_count < 1
            ):
                raise ValueError("publishable rules require a positive count threshold")


@dataclass(frozen=True, slots=True)
class PublicLocationRequest:
    """A materialized public scope request; it contains no source coordinates."""

    scope_kind: ScopeKind
    scope_id: str
    h3_resolution: int | None
    h3_cell: str | None
    source_precision: SourcePrecision
    record_count: int

    def __post_init__(self) -> None:
        if self.scope_kind not in _SCOPE_KINDS:
            raise ValueError("unsupported public scope")
        if not self.scope_id or len(self.scope_id) > 240:
            raise ValueError("scope_id must be a bounded non-empty identifier")
        if self.source_precision not in ("exact", "generalised", "coarse_rollup", "withheld"):
            raise ValueError("invalid source_precision")
        if not isinstance(self.record_count, int) or self.record_count < 0:
            raise ValueError("record_count must be a non-negative integer")
        if self.scope_kind == "h3":
            if not isinstance(self.h3_resolution, int) or not 0 <= self.h3_resolution <= 15:
                raise ValueError("H3 scope requires a valid resolution")
            if self.h3_cell is None or not _H3_CELL.fullmatch(self.h3_cell):
                raise ValueError("H3 scope requires a lowercase 15-character cell")
        elif self.h3_resolution is not None or self.h3_cell is not None:
            raise ValueError("non-H3 scopes cannot carry an H3 cell")


@dataclass(frozen=True, slots=True)
class PublicLocationDecision:
    schema_version: str
    policy_version: str
    publication_state: PublicationState
    scope_kind: ScopeKind | None
    scope_id: str | None
    h3_resolution: int | None
    h3_cell: str | None
    source_precision: SourcePrecision | None
    effective_maximum_h3_resolution: int | None
    blocker_codes: tuple[str, ...]
    source_constraint_fingerprints: tuple[str, ...]
    policy_evidence_fingerprint: str
    decision_fingerprint: str
    scientific_claim_allowed: Literal[False] = False

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["blocker_codes"] = list(self.blocker_codes)
        payload["source_constraint_fingerprints"] = list(
            self.source_constraint_fingerprints
        )
        return payload


def plan_public_location(
    *,
    rule: SensitiveLocationRule,
    request: PublicLocationRequest,
    constraints: Sequence[ProviderLocationConstraint],
    required_providers: Sequence[Provider] = ("ala",),
) -> PublicLocationDecision:
    """Return a deterministic public scope or a coordinate-free withheld result."""

    if len(set(required_providers)) != len(required_providers):
        raise ValueError("required_providers must be unique")
    if any(provider not in ("ala", "flickr") for provider in required_providers):
        raise ValueError("required_providers contains an unsupported provider")

    ordered = sorted(constraints, key=lambda item: item.constraint_fingerprint)
    fingerprints = tuple(item.constraint_fingerprint for item in ordered)
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError("provider constraints must be unique")

    blockers: set[str] = set()
    present_providers = {item.provider for item in ordered}
    for provider in required_providers:
        if provider not in present_providers:
            blockers.add(f"missing_{provider}_provider_constraint")
    if not ordered:
        blockers.add("missing_provider_constraints")
    if rule.action == "withhold" or rule.sensitivity_state == "unknown":
        blockers.add("sensitive_location_policy_withholds")
    if request.scope_kind not in rule.allowed_scope_kinds:
        blockers.add("scope_not_permitted")
    if request.source_precision == "withheld":
        blockers.add("source_location_withheld")
    if rule.sensitivity_state == "sensitive" and request.source_precision == "exact":
        blockers.add("sensitive_exact_location_forbidden")
    if (
        rule.minimum_public_record_count is None
        or request.record_count < rule.minimum_public_record_count
    ):
        blockers.add("minimum_public_record_count_not_met")

    used = [item for item in ordered if item.location_used_for_target]
    if not used:
        blockers.add("no_permitted_provider_location_used")
    for constraint in used:
        if constraint.disclosure_state not in _PUBLIC_STATES[constraint.provider]:
            blockers.add(f"{constraint.provider}_location_not_public")
        if constraint.maximum_public_h3_resolution is None:
            blockers.add(f"{constraint.provider}_resolution_mapping_missing")

    ceilings = [
        ceiling
        for ceiling in (
            rule.maximum_public_h3_resolution,
            *(item.maximum_public_h3_resolution for item in used),
        )
        if ceiling is not None
    ]
    effective_maximum = min(ceilings) if ceilings else None
    if effective_maximum is None:
        blockers.add("public_resolution_ceiling_missing")
    if request.scope_kind == "h3" and (
        effective_maximum is None or request.h3_resolution is None
        or request.h3_resolution > effective_maximum
    ):
        blockers.add("requested_h3_resolution_exceeds_ceiling")

    blocker_codes = tuple(sorted(blockers))
    state: PublicationState
    if blocker_codes:
        state = "withheld"
    elif rule.action == "generalise" or request.source_precision in (
        "generalised",
        "coarse_rollup",
    ):
        state = "generalised"
    else:
        state = "publish"

    decision_preimage: dict[str, object] = {
        "schema_version": PUBLIC_LOCATION_DECISION_SCHEMA_VERSION,
        "policy_version": rule.policy_version,
        "publication_state": state,
        "scope_kind": request.scope_kind if state != "withheld" else None,
        "scope_id": request.scope_id if state != "withheld" else None,
        "h3_resolution": request.h3_resolution if state != "withheld" else None,
        "h3_cell": request.h3_cell if state != "withheld" else None,
        "source_precision": request.source_precision if state != "withheld" else None,
        "effective_maximum_h3_resolution": (
            effective_maximum if state != "withheld" else None
        ),
        "blocker_codes": list(blocker_codes),
        "source_constraint_fingerprints": list(fingerprints),
        "policy_evidence_fingerprint": rule.policy_evidence_fingerprint,
        "required_providers": sorted(required_providers),
        "scientific_claim_allowed": False,
    }
    return PublicLocationDecision(
        schema_version=PUBLIC_LOCATION_DECISION_SCHEMA_VERSION,
        policy_version=rule.policy_version,
        publication_state=state,
        scope_kind=request.scope_kind if state != "withheld" else None,
        scope_id=request.scope_id if state != "withheld" else None,
        h3_resolution=request.h3_resolution if state != "withheld" else None,
        h3_cell=request.h3_cell if state != "withheld" else None,
        source_precision=request.source_precision if state != "withheld" else None,
        effective_maximum_h3_resolution=(
            effective_maximum if state != "withheld" else None
        ),
        blocker_codes=blocker_codes,
        source_constraint_fingerprints=fingerprints,
        policy_evidence_fingerprint=rule.policy_evidence_fingerprint,
        decision_fingerprint=_digest(decision_preimage),
    )
