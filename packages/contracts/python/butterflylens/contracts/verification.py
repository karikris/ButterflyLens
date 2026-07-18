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
QUALITY_SNAPSHOT_SCHEMA_VERSION = "butterflylens-quality-snapshot:v1.0.0"

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
    method: str
    status: str
    outcome: str | None
    eligible_review_count: int
    decisive_review_count: int
    support_count: int
    oppose_count: int
    support_total: float
    oppose_total: float
    uncertain_count: int
    media_failure_count: int
    deferred_count: int
    dissent_count: int
    event_fingerprints: list[str]
    blockers: list[str]


class VerificationConsensus(TypedDict):
    schema_version: Literal["butterflylens-verification-consensus:v1.0.0"]
    policy_version: Literal["butterflylens-layered-consensus-policy:v1.0.0"]
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
    release_gates: dict[str, bool]
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
    metrics: dict[str, object]
    evidence_fingerprint: str
    visibility: Literal["private"]
    public_ranking_allowed: Literal[False]
    model_agreement_used: Literal[False]
    majority_agreement_alone_used: Literal[False]
    recorded_at: str


class QualityStratumSummary(TypedDict):
    stratum_id: str
    population_count: int | None
    population_weight: float | None
    sample_count: int
    decisive_count: int
    supported_count: int
    failure_count: int
    analysis_weight: float | None
    precision_estimate: float | None
    resampling_group_count: int


class QualitySnapshot(TypedDict):
    schema_version: Literal["butterflylens-quality-snapshot:v1.0.0"]
    policy_version: Literal["butterflylens-representative-audit-policy:v1.0.0"]
    estimator_version: Literal["butterflylens-dataset-quality-estimator:v1.0.0"]
    quality_snapshot_id: str
    project_id: str
    run_id: str
    audit_kind: Literal["representative_audit", "targeted_failure_discovery"]
    availability: Literal["estimated", "unavailable"]
    sampling_plan_id: str
    sampling_frame_fingerprint: str
    sampling_design: str
    representative: bool
    blind: bool
    inclusion_probability_method: str | None
    interval_method: Literal["stratified_owner_observation_group_bootstrap_v1"]
    audit_records: list[dict[str, object]]
    audit_evidence_fingerprint: str
    sampling_strata: list[QualityStratumSummary]
    grouping_keys: list[str]
    reviewed_sample: int
    decisive_reviews: int
    supported_count: int
    failure_count: int
    unresolved_count: int
    precision_estimate: float | None
    interval: dict[str, object] | None
    effective_sample_size: float | None
    bootstrap_replicates: int
    bootstrap_seed_fingerprint: str
    resampling_group_count: int
    blockers: list[str]
    population_estimate_allowed: bool
    targeted_queue_separate: Literal[True]
    model_vote_included: Literal[False]
    scientific_claim_allowed: Literal[False]
    generated_at: str
    snapshot_fingerprint: str
