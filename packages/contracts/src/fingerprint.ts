export const CONTENT_CHECKSUM_SCHEMA_VERSION =
  'butterflylens-content-checksum:v1.0.0' as const
export const EVIDENCE_FINGERPRINT_SCHEMA_VERSION =
  'butterflylens-evidence-fingerprint:v1.0.0' as const
export const FINGERPRINT_CANONICALIZATION = 'RFC8785-JCS' as const
export const FINGERPRINT_HASH_ALGORITHM = 'sha256' as const

export const FINGERPRINT_KINDS = [
  'project_definition',
  'run_input_set',
  'taxon_concept',
  'name_assertion',
  'query_definition',
  'physical_api_request',
  'provider_snapshot',
  'api_response',
  'source_flickr_record',
  'downloaded_image',
  'media_object',
  'perceptual_duplicate_group',
  'model_artifact',
  'preprocessing',
  'yoloe_route',
  'full_frame_visual_input',
  'bioclip_embedding',
  'reference_bank',
  'prototype',
  'candidate_score',
  'review_event',
  'consensus',
  'quality_snapshot',
  'geographic_impact_cell',
  'map_snapshot',
  'release_candidate',
  'artifact_manifest',
  'export_manifest',
] as const

export const FINGERPRINT_PARENT_RELATIONSHIPS = [
  'derived_from',
  'contains',
  'produced_by',
  'supersedes',
  'reviews',
  'aggregates',
  'compares',
  'calibrates',
] as const

export type FingerprintKind = (typeof FINGERPRINT_KINDS)[number]
export type FingerprintParentRelationship =
  (typeof FINGERPRINT_PARENT_RELATIONSHIPS)[number]

export interface ContentChecksum {
  readonly schema_version: typeof CONTENT_CHECKSUM_SCHEMA_VERSION
  readonly algorithm: typeof FINGERPRINT_HASH_ALGORITHM
  readonly digest: string
  readonly byte_count: number
  readonly media_type: string
}

export interface EvidenceFingerprintParent {
  readonly relationship: FingerprintParentRelationship
  readonly fingerprint_kind: FingerprintKind
  readonly digest: string
}

export interface EvidenceFingerprintPreimage {
  readonly fingerprint_kind: FingerprintKind
  readonly subject_id: string
  readonly payload_schema_version: string
  readonly payload: Readonly<Record<string, unknown>>
  readonly parents: readonly EvidenceFingerprintParent[]
}

export interface EvidenceFingerprint {
  readonly schema_version: typeof EVIDENCE_FINGERPRINT_SCHEMA_VERSION
  readonly hash_algorithm: typeof FINGERPRINT_HASH_ALGORITHM
  readonly canonicalization: typeof FINGERPRINT_CANONICALIZATION
  readonly preimage: EvidenceFingerprintPreimage
  readonly digest: string
  readonly recorded_at: string
}
