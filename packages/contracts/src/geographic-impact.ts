export const GEOGRAPHIC_IMPACT_CELL_SCHEMA_VERSION =
  'butterflylens-geographic-impact-cell:v1.0.0' as const
export const GEOGRAPHIC_IMPACT_SNAPSHOT_SCHEMA_VERSION =
  'butterflylens-geographic-impact-snapshot:v1.0.0' as const
export const GEOGRAPHIC_IMPACT_QUERY_SCHEMA_VERSION =
  'butterflylens-geographic-impact-query:v1.0.0' as const

export const EVIDENCE_COUNT_STATUSES = [
  'available',
  'unavailable',
  'withheld',
  'not_applicable',
] as const

export type EvidenceCountStatus = (typeof EVIDENCE_COUNT_STATUSES)[number]
export type SnapshotMode = 'live' | 'submitted'

export interface EvidenceCount {
  readonly status: EvidenceCountStatus
  readonly value: number | null
  readonly reason: string | null
}

export interface ImpactFlag {
  readonly status: 'available' | 'unavailable'
  readonly value: boolean | null
  readonly reason: string | null
}

export interface GeographicImpactCell {
  readonly schema_version: typeof GEOGRAPHIC_IMPACT_CELL_SCHEMA_VERSION
  readonly cell_id: string
  readonly grid: 'H3'
  readonly h3_version: string
  readonly h3_resolution: number
  readonly project_id: string
  readonly run_id: string
  readonly snapshot_mode: SnapshotMode
  readonly accepted_taxon_key: string
  readonly ala_snapshot_fingerprint: string | null
  readonly flickr_snapshot_fingerprint: string | null
  readonly provider_union_fingerprint: string | null
  readonly review_projection_fingerprint: string | null
  readonly quality_snapshot_fingerprint: string | null
  readonly counts: {
    readonly ala_baseline: EvidenceCount
    readonly flickr_candidate: EvidenceCount
    readonly yoloe_butterfly: EvidenceCount
    readonly bioclip_species_candidate: EvidenceCount
    readonly community_reviewed: EvidenceCount
    readonly human_supported: EvidenceCount
    readonly release_ready: EvidenceCount
  }
  readonly impact: {
    readonly potential_coverage_gap: ImpactFlag
    readonly human_supported_additional: ImpactFlag
    readonly release_ready_additional: ImpactFlag
  }
  readonly nearest_ala_evidence_distance: {
    readonly status: 'available' | 'unavailable' | 'not_applicable'
    readonly metres: number | null
    readonly reason: string | null
  }
  readonly latest_ala_event_date: string | null
  readonly latest_flickr_event_date: string | null
  readonly data_deficiency_state:
    | 'baseline_present'
    | 'candidate_only'
    | 'baseline_and_candidate'
    | 'no_eligible_evidence'
    | 'baseline_unavailable'
    | 'coordinates_withheld'
    | 'insufficient_precision'
  readonly public_geometry: {
    readonly status: 'available' | 'generalized' | 'withheld'
    readonly source_precision_metres: number | null
    readonly published_h3_resolution: number | null
    readonly reason: string | null
  }
  readonly evidence_fingerprints: readonly string[]
  readonly cell_fingerprint: string
  readonly scientific_claim_allowed: false
}

export interface GeographicImpactSnapshot {
  readonly schema_version: typeof GEOGRAPHIC_IMPACT_SNAPSHOT_SCHEMA_VERSION
  readonly snapshot_id: string
  readonly project_id: string
  readonly run_id: string
  readonly mode: SnapshotMode
  readonly country_code: 'AU'
  readonly status: 'available' | 'stale' | 'unavailable'
  readonly generated_at: string
  readonly last_updated_at: string
  readonly submitted_source_commit: string | null
  readonly worker_heartbeat_fingerprint: string | null
  readonly cell_schema_version: typeof GEOGRAPHIC_IMPACT_CELL_SCHEMA_VERSION
  readonly cell_count: number
  readonly cell_artifact_checksum: string
  readonly cell_artifact_fingerprint: string
  readonly query_fingerprint: string
  readonly map_projection_fingerprint: string
  readonly blockers: readonly string[]
  readonly append_only_revision: number
}

export interface GeographicImpactQuery {
  readonly schema_version: typeof GEOGRAPHIC_IMPACT_QUERY_SCHEMA_VERSION
  readonly project_id: string
  readonly accepted_taxon_keys: readonly string[]
  readonly snapshot_mode: SnapshotMode
  readonly h3_resolution: number
  readonly scope: {
    readonly kind: 'national' | 'state' | 'territory' | 'ibra' | 'lga' | 'h3'
    readonly scope_id: string
  }
  readonly event_date_from: string | null
  readonly event_date_to: string | null
  readonly evidence_maturity: readonly string[]
  readonly ala_basis_of_record: readonly string[]
  readonly review_states: readonly string[]
  readonly page_size: number
  readonly query_fingerprint: string
}
