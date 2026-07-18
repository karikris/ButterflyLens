export const CLASSIFICATION_MATURITY_SCHEMA_VERSION =
  'butterflylens-classification-maturity:v1.0.0' as const

export const CLASSIFICATION_MATURITY_FIELDS = [
  'butterfly_detected',
  'species_candidate_available',
  'community_reviewed',
  'quality_estimate_available',
  'expert_reviewed',
  'release_ready',
] as const

export const CLASSIFICATION_MATURITY_STATUSES = [
  'available',
  'unavailable',
] as const

export interface ClassificationEvidenceState {
  readonly status: typeof CLASSIFICATION_MATURITY_STATUSES[number]
  readonly value: boolean | null
  readonly reason: string | null
  readonly evidence_fingerprints: readonly string[]
}

export interface ClassificationMaturity {
  readonly schema_version: typeof CLASSIFICATION_MATURITY_SCHEMA_VERSION
  readonly image_id: string
  readonly source_record_fingerprint: string
  readonly observed_at: string
  readonly maturity: Readonly<Record<
    typeof CLASSIFICATION_MATURITY_FIELDS[number],
    ClassificationEvidenceState
  >>
  readonly projection_fingerprint: string
  readonly scientific_claim_allowed: false
}
