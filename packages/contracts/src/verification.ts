export const VERIFICATION_CAMPAIGN_SCHEMA_VERSION =
  'butterflylens-verification-campaign:v1.0.0' as const
export const VERIFICATION_ASSIGNMENT_SCHEMA_VERSION =
  'butterflylens-verification-assignment:v1.0.0' as const
export const VERIFICATION_ADJUDICATION_SCHEMA_VERSION =
  'butterflylens-verification-adjudication:v1.0.0' as const
export const VERIFICATION_EVENT_SCHEMA_VERSION =
  'butterflylens-verification-event:v1.0.0' as const
export const VERIFICATION_CONSENSUS_SCHEMA_VERSION =
  'butterflylens-verification-consensus:v1.0.0' as const
export const REVIEWER_RELIABILITY_SCHEMA_VERSION =
  'butterflylens-reviewer-reliability:v1.0.0' as const

export const VERIFICATION_OUTCOMES = [
  'yes',
  'no',
  'cant_tell',
  'cant_view',
  'skipped',
] as const

export const CONSENSUS_STATUSES = [
  'pending',
  'complete_agreement',
  'unresolved_disagreement',
  'uncertain_only',
  'media_failure',
  'deferred',
  'adjudicated',
] as const

export type VerificationOutcome = (typeof VERIFICATION_OUTCOMES)[number]
export type ConsensusStatus = (typeof CONSENSUS_STATUSES)[number]

export interface TaxonIdentity {
  readonly accepted_taxon_key: string
  readonly scientific_name: string
  readonly rank:
    | 'superfamily'
    | 'family'
    | 'subfamily'
    | 'tribe'
    | 'genus'
    | 'species'
    | 'subspecies'
    | 'other'
}

export interface VerificationCampaign {
  readonly schema_version: typeof VERIFICATION_CAMPAIGN_SCHEMA_VERSION
  readonly campaign_id: string
  readonly project_id: string
  readonly run_id: string | null
  readonly kind:
    | 'flickr_target_verification'
    | 'reference_identity_verification'
    | 'reference_route_verification'
    | 'adjudication'
    | 'quality_control'
  readonly status: 'draft' | 'ready' | 'active' | 'paused' | 'complete' | 'archived'
  readonly target: TaxonIdentity | null
  readonly source_providers: readonly string[]
  readonly question_fingerprint: string
  readonly manifest_fingerprint: string
  readonly sampling_plan: {
    readonly plan_id: string
    readonly purpose: string
    readonly design: string
    readonly representative: boolean
    readonly blind: boolean
    readonly inclusion_probabilities_recorded: boolean
    readonly grouping_keys: readonly string[]
    readonly strata: readonly {
      readonly stratum_id: string
      readonly label: string
      readonly population_count: number | null
      readonly target_sample_count: number | null
      readonly population_weight: number | null
    }[]
    readonly quality_estimation_eligible: boolean
    readonly quality_estimation_blockers: readonly string[]
  }
  readonly review_requirement: {
    readonly required_independent_reviewers: number
    readonly second_review_policy: string
    readonly adjudication_required_on_conflict: boolean
    readonly expert_gate_required_for_release: boolean
  }
  readonly blind_policy: {
    readonly enabled: boolean
    readonly hidden_fields: readonly string[]
  }
  readonly public_replay: boolean
  readonly scientific_claim_allowed: false
  readonly created_at: string
  readonly updated_at: string
}

export interface VerificationAssignment {
  readonly schema_version: typeof VERIFICATION_ASSIGNMENT_SCHEMA_VERSION
  readonly assignment_id: string
  readonly campaign_id: string
  readonly item_id: string
  readonly reviewer_id: string
  readonly review_round: number
  readonly reason: 'ordinary' | 'conflict' | 'potential_gap' | 'reference' | 'control' | 'adjudication'
  readonly status: 'assigned' | 'opened' | 'completed' | 'expired' | 'withdrawn'
  readonly blind: boolean
  readonly independence_group_key: string
  readonly assigned_at: string
  readonly expires_at: string | null
  readonly completed_at: string | null
  readonly visibility: 'private'
}

export interface VerificationAdjudication {
  readonly schema_version: typeof VERIFICATION_ADJUDICATION_SCHEMA_VERSION
  readonly adjudication_id: string
  readonly project_id: string
  readonly campaign_id: string
  readonly item_id: string
  readonly adjudicator_id: string
  readonly conflicting_reviewer_ids: readonly string[]
  readonly conflicting_event_fingerprints: readonly string[]
  readonly decision_event_fingerprint: string
  readonly independence_check: 'passed'
  readonly lineage_fingerprint: string
  readonly adjudicated_at: string
  readonly scientific_claim_allowed: false
}

export interface VerificationEvent {
  readonly schema_version: typeof VERIFICATION_EVENT_SCHEMA_VERSION
  readonly event_id: string
  readonly project_id: string
  readonly campaign_id: string
  readonly assignment_id: string
  readonly item_id: string
  readonly reviewer_id: string
  readonly review_round: number
  readonly outcome: VerificationOutcome
  readonly non_target_category: string | null
  readonly alternative_taxon: TaxonIdentity | null
  readonly corrected_life_stage: string | null
  readonly corrected_visual_domain: string | null
  readonly corrected_view: string | null
  readonly media_quality: 'high' | 'medium' | 'low' | 'unusable' | 'unknown'
  readonly duplicate_concern: boolean
  readonly captive_or_cultivated_concern: boolean
  readonly confidence: 'high' | 'medium' | 'low' | 'unknown'
  readonly comment: string | null
  readonly reviewed_at: string
  readonly duration_ms: number | null
  readonly displayed_media_sha256: string
  readonly source_record_fingerprint: string
  readonly question_fingerprint: string
  readonly campaign_manifest_fingerprint: string
  readonly supersedes_event_fingerprint: string | null
  readonly conflicts_with_consensus_fingerprint: string | null
  readonly scientific_claim_allowed: false
}

export interface ConsensusLayer {
  readonly status: 'pending' | 'available' | 'blocked' | 'unavailable'
  readonly outcome:
    | 'supported'
    | 'not_supported'
    | 'uncertain'
    | 'media_failure'
    | 'deferred'
    | 'release_ready'
    | 'not_release_ready'
    | null
  readonly blockers: readonly string[]
}

export interface VerificationConsensus {
  readonly schema_version: typeof VERIFICATION_CONSENSUS_SCHEMA_VERSION
  readonly consensus_id: string
  readonly project_id: string
  readonly campaign_id: string
  readonly item_id: string
  readonly revision: number
  readonly status: ConsensusStatus
  readonly required_review_count: number
  readonly effective_review_count: number
  readonly decisive_review_count: number
  readonly effective_event_fingerprints: readonly string[]
  readonly conflicts: readonly {
    readonly field: string
    readonly event_fingerprints: readonly string[]
  }[]
  readonly adjudication_event_fingerprint: string | null
  readonly community_evidence: ConsensusLayer
  readonly qualified_consensus: ConsensusLayer
  readonly release_consensus: ConsensusLayer
  readonly reviewer_weights_applied: boolean
  readonly reliability_snapshot_fingerprint: string | null
  readonly model_vote_included: false
  readonly resolved_at: string | null
  readonly consensus_fingerprint: string
}

export interface ReviewerReliability {
  readonly schema_version: typeof REVIEWER_RELIABILITY_SCHEMA_VERSION
  readonly reliability_id: string
  readonly reviewer_id: string
  readonly domain: {
    readonly taxon_group: string
    readonly source_provider: string
    readonly life_stage: string
    readonly visual_domain: string
  }
  readonly method: 'control_calibrated_beta_binomial_v1'
  readonly availability: 'estimated' | 'unavailable'
  readonly sample_count: number
  readonly decisive_count: number
  readonly control_count: number
  readonly estimate: number | null
  readonly interval: { readonly lower: number; readonly upper: number; readonly level: number } | null
  readonly equal_weight_target: 1
  readonly applied_weight: number | null
  readonly shrinkage_fraction: number | null
  readonly minimum_evidence: number
  readonly blockers: readonly string[]
  readonly metrics: {
    readonly control_accuracy: number | null
    readonly sensitivity: number | null
    readonly specificity: number | null
    readonly pairwise_agreement: number | null
    readonly krippendorff_alpha: number | null
    readonly adjudicated_overlap: number | null
    readonly positive_control_count: number
    readonly negative_control_count: number
    readonly overlap_count: number
    readonly adjudicated_count: number
    readonly pair_count: number
    readonly agreement_pair_count: number
    readonly metric_blockers: readonly string[]
  }
  readonly evidence_fingerprint: string
  readonly visibility: 'private'
  readonly public_ranking_allowed: false
  readonly model_agreement_used: false
  readonly majority_agreement_alone_used: false
  readonly recorded_at: string
}
