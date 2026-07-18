"""Deterministic fail-closed occurrence release-readiness decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
from typing import Literal, Sequence

from .fingerprint import canonicalize_json


OCCURRENCE_RELEASE_POLICY_VERSION = "butterflylens-occurrence-release:v1.0.0"
OCCURRENCE_RELEASE_DECISION_SCHEMA_VERSION = (
    "butterflylens-occurrence-release-decision:v1.0.0"
)
RELEASE_GATE_NAMES = (
    "coordinate_date_validity",
    "duplicate_independence",
    "evidence_packet_complete",
    "expert_review_when_configured",
    "human_supported_identity",
    "no_unresolved_conflict",
    "qualified_consensus",
    "quality_threshold",
    "rights_provenance",
)

ReleaseGateName = Literal[
    "coordinate_date_validity",
    "duplicate_independence",
    "evidence_packet_complete",
    "expert_review_when_configured",
    "human_supported_identity",
    "no_unresolved_conflict",
    "qualified_consensus",
    "quality_threshold",
    "rights_provenance",
]
ReleaseState = Literal["blocked", "release_ready_occurrence_candidate"]

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_BLOCKER = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")


def _require_fingerprint(value: str, field: str) -> None:
    if not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")


@dataclass(frozen=True, slots=True)
class ReleaseGateEvidence:
    """One independently evidenced release gate."""

    gate_name: ReleaseGateName
    passed: bool
    evidence_fingerprints: tuple[str, ...]
    blocker_code: str | None

    def __post_init__(self) -> None:
        if self.gate_name not in RELEASE_GATE_NAMES:
            raise ValueError("unsupported occurrence release gate")
        if not isinstance(self.passed, bool):
            raise ValueError("release gate passed must be boolean")
        if tuple(sorted(set(self.evidence_fingerprints))) != self.evidence_fingerprints:
            raise ValueError("gate evidence fingerprints must be sorted and unique")
        for fingerprint in self.evidence_fingerprints:
            _require_fingerprint(fingerprint, "gate evidence fingerprint")
        if self.passed:
            if not self.evidence_fingerprints:
                raise ValueError("a passed release gate requires evidence")
            if self.blocker_code is not None:
                raise ValueError("a passed release gate cannot have a blocker")
        elif self.blocker_code is None or not _BLOCKER.fullmatch(self.blocker_code):
            raise ValueError("a failed release gate requires a stable blocker code")


@dataclass(frozen=True, slots=True)
class OccurrenceReleaseDecision:
    schema_version: str
    policy_version: str
    release_state: ReleaseState
    gate_results: tuple[ReleaseGateEvidence, ...]
    blocker_codes: tuple[str, ...]
    evidence_fingerprints: tuple[str, ...]
    decision_fingerprint: str
    published_occurrence: Literal[False] = False
    scientific_claim_allowed: Literal[False] = False

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        gate_payloads: list[dict[str, object]] = []
        for gate in self.gate_results:
            gate_payload = asdict(gate)
            gate_payload["evidence_fingerprints"] = list(gate.evidence_fingerprints)
            gate_payloads.append(gate_payload)
        payload["gate_results"] = gate_payloads
        payload["blocker_codes"] = list(self.blocker_codes)
        payload["evidence_fingerprints"] = list(self.evidence_fingerprints)
        return payload


def plan_occurrence_release(
    gates: Sequence[ReleaseGateEvidence],
    *,
    policy_version: str = OCCURRENCE_RELEASE_POLICY_VERSION,
) -> OccurrenceReleaseDecision:
    """Return release-ready only when every closed, evidenced gate passes."""

    if policy_version != OCCURRENCE_RELEASE_POLICY_VERSION:
        raise ValueError("unsupported occurrence release policy version")
    ordered = tuple(sorted(gates, key=lambda gate: gate.gate_name))
    names = tuple(gate.gate_name for gate in ordered)
    if names != RELEASE_GATE_NAMES:
        missing = sorted(set(RELEASE_GATE_NAMES) - set(names))
        extra = sorted(set(names) - set(RELEASE_GATE_NAMES))
        raise ValueError(f"release gates must be exact; missing={missing}, extra={extra}")
    if len(set(names)) != len(names):
        raise ValueError("release gates must be unique")

    blockers = tuple(sorted(gate.blocker_code for gate in ordered if not gate.passed))
    fingerprints = tuple(
        sorted(
            {
                fingerprint
                for gate in ordered
                for fingerprint in gate.evidence_fingerprints
            }
        )
    )
    release_state: ReleaseState = (
        "release_ready_occurrence_candidate" if not blockers else "blocked"
    )
    gate_payloads = []
    for gate in ordered:
        payload = asdict(gate)
        payload["evidence_fingerprints"] = list(gate.evidence_fingerprints)
        gate_payloads.append(payload)
    preimage = {
        "schema_version": OCCURRENCE_RELEASE_DECISION_SCHEMA_VERSION,
        "policy_version": policy_version,
        "release_state": release_state,
        "gate_results": gate_payloads,
        "blocker_codes": list(blockers),
        "evidence_fingerprints": list(fingerprints),
        "published_occurrence": False,
        "scientific_claim_allowed": False,
    }
    decision_fingerprint = hashlib.sha256(canonicalize_json(preimage)).hexdigest()
    return OccurrenceReleaseDecision(
        schema_version=OCCURRENCE_RELEASE_DECISION_SCHEMA_VERSION,
        policy_version=policy_version,
        release_state=release_state,
        gate_results=ordered,
        blocker_codes=blockers,
        evidence_fingerprints=fingerprints,
        decision_fingerprint=decision_fingerprint,
    )
