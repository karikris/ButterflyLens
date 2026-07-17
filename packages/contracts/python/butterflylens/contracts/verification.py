"""Community verification wire declarations."""

from __future__ import annotations

from typing import Literal, TypedDict


VERIFICATION_CAMPAIGN_SCHEMA_VERSION = (
    "butterflylens-verification-campaign:v1.0.0"
)
VERIFICATION_ASSIGNMENT_SCHEMA_VERSION = (
    "butterflylens-verification-assignment:v1.0.0"
)
VERIFICATION_ADJUDICATION_SCHEMA_VERSION = (
    "butterflylens-verification-adjudication:v1.0.0"
)
VERIFICATION_EVENT_SCHEMA_VERSION = "butterflylens-verification-event:v1.0.0"
VERIFICATION_CONSENSUS_SCHEMA_VERSION = (
    "butterflylens-verification-consensus:v1.0.0"
)
REVIEWER_RELIABILITY_SCHEMA_VERSION = (
    "butterflylens-reviewer-reliability:v1.0.0"
)

VERIFICATION_OUTCOMES = ("yes", "no", "cant_tell", "cant_view", "skipped")
CONSENSUS_STATUSES = (
    "pending",
    "complete_agreement",
    "unresolved_disagreement",
    "uncertain_only",
    "media_failure",
    "deferred",
    "adjudicated",
)


class TaxonIdentity(TypedDict):
    accepted_taxon_key: str
    scientific_name: str
    rank: str


class VerificationCampaign(TypedDict):
    schema_version: Literal["butterflylens-verification-campaign:v1.0.0"]
    campaign_id: str
    project_id: str
    run_id: str | None
    kind: str
    status: str
    target: TaxonIdentity | None
    source_providers: list[str]
    question_fingerprint: str
    manifest_fingerprint: str
    sampling_plan: dict[str, object]
    review_requirement: dict[str, object]
    blind_policy: dict[str, object]
    public_replay: bool
    scientific_claim_allowed: Literal[False]
    created_at: str
    updated_at: str


class VerificationAssignment(TypedDict):
    schema_version: Literal["butterflylens-verification-assignment:v1.0.0"]
    assignment_id: str
    campaign_id: str
    item_id: str
    reviewer_id: str
    review_round: int
    reason: str
    status: str
    blind: bool
    independence_group_key: str
    assigned_at: str
    expires_at: str | None
    completed_at: str | None
    visibility: Literal["private"]


class VerificationAdjudication(TypedDict):
    schema_version: Literal["butterflylens-verification-adjudication:v1.0.0"]
    adjudication_id: str
    project_id: str
    campaign_id: str
    item_id: str
    adjudicator_id: str
    conflicting_reviewer_ids: list[str]
    conflicting_event_fingerprints: list[str]
    decision_event_fingerprint: str
    independence_check: Literal["passed"]
    lineage_fingerprint: str
    adjudicated_at: str
    scientific_claim_allowed: Literal[False]


class VerificationEvent(TypedDict):
    schema_version: Literal["butterflylens-verification-event:v1.0.0"]
    event_id: str
    project_id: str
    campaign_id: str
    assignment_id: str
    item_id: str
    reviewer_id: str
    review_round: int
    outcome: str
    non_target_category: str | None
    alternative_taxon: TaxonIdentity | None
    corrected_life_stage: str | None
    corrected_visual_domain: str | None
    corrected_view: str | None
    media_quality: str
    duplicate_concern: bool
    captive_or_cultivated_concern: bool
    confidence: str
    comment: str | None
    reviewed_at: str
    duration_ms: int | None
    displayed_media_sha256: str
    source_record_fingerprint: str
    question_fingerprint: str
    campaign_manifest_fingerprint: str
    supersedes_event_fingerprint: str | None
    conflicts_with_consensus_fingerprint: str | None
    scientific_claim_allowed: Literal[False]


class ConsensusLayer(TypedDict):
    status: str
    outcome: str | None
    blockers: list[str]


class VerificationConsensus(TypedDict):
    schema_version: Literal["butterflylens-verification-consensus:v1.0.0"]
    consensus_id: str
    project_id: str
    campaign_id: str
    item_id: str
    revision: int
    status: str
    required_review_count: int
    effective_review_count: int
    decisive_review_count: int
    effective_event_fingerprints: list[str]
    conflicts: list[dict[str, object]]
    adjudication_event_fingerprint: str | None
    community_evidence: ConsensusLayer
    qualified_consensus: ConsensusLayer
    release_consensus: ConsensusLayer
    reviewer_weights_applied: bool
    reliability_snapshot_fingerprint: str | None
    model_vote_included: Literal[False]
    resolved_at: str | None
    consensus_fingerprint: str


class ReviewerReliability(TypedDict):
    schema_version: Literal["butterflylens-reviewer-reliability:v1.0.0"]
    reliability_id: str
    reviewer_id: str
    domain: dict[str, str]
    method: Literal["control_calibrated_beta_binomial_v1"]
    availability: Literal["estimated", "unavailable"]
    sample_count: int
    decisive_count: int
    control_count: int
    estimate: float | None
    interval: dict[str, float] | None
    equal_weight_target: Literal[1]
    applied_weight: float | None
    shrinkage_fraction: float | None
    minimum_evidence: int
    blockers: list[str]
    evidence_fingerprint: str
    visibility: Literal["private"]
    public_ranking_allowed: Literal[False]
    model_agreement_used: Literal[False]
    majority_agreement_alone_used: Literal[False]
    recorded_at: str
