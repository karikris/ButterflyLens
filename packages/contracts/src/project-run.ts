export const PROJECT_SCHEMA_VERSION = 'butterflylens-project:v1.0.0' as const
export const RUN_SCHEMA_VERSION = 'butterflylens-run:v1.0.0' as const

export const PROJECT_STATUSES = [
  'draft',
  'active',
  'paused',
  'archived',
] as const

export type ProjectStatus = (typeof PROJECT_STATUSES)[number]

export interface ButterflyLensProject {
  readonly schema_version: typeof PROJECT_SCHEMA_VERSION
  readonly project_id: string
  readonly slug: string
  readonly name: string
  readonly description: string
  readonly status: ProjectStatus
  readonly geographic_scope: {
    readonly country_code: 'AU'
    readonly boundary_id: string
    readonly boundary_version: string
    readonly boundary_sha256: string
    readonly sensitive_coordinate_policy_version: string
  }
  readonly taxon_scope: {
    readonly root_taxon_keys: readonly string[]
    readonly taxonomy_fingerprint: string
  }
  readonly discovery_scope: {
    readonly search_plan_fingerprint: string
    readonly public_discovery_claim: 'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.'
  }
  readonly data_policy_version: string
  readonly consent_policy_version: string
  readonly created_at: string
  readonly updated_at: string
}

export const RUN_KINDS = [
  'taxonomy_pack',
  'ala_baseline',
  'reference_bank',
  'flickr_discovery',
  'vision_pipeline',
  'geographic_impact',
  'quality_snapshot',
  'release_export',
  'full_pipeline',
] as const

export const RUN_MODES = ['live', 'submitted', 'replay'] as const

export const RUN_STATUSES = [
  'queued',
  'leased',
  'running',
  'paused',
  'cancelling',
  'cancelled',
  'succeeded',
  'failed',
] as const

export const PIPELINE_STAGE_IDS = [
  'taxonomy',
  'names',
  'ala_baseline',
  'reference_admission',
  'flickr_plan',
  'flickr_fetch',
  'media',
  'yoloe',
  'bioclip',
  'scoring',
  'review',
  'geographic_impact',
  'quality',
  'release',
  'export',
] as const

export type RunKind = (typeof RUN_KINDS)[number]
export type RunMode = (typeof RUN_MODES)[number]
export type RunStatus = (typeof RUN_STATUSES)[number]
export type PipelineStageId = (typeof PIPELINE_STAGE_IDS)[number]

export interface RunStage {
  readonly stage_id: PipelineStageId
  readonly status:
    | 'pending'
    | 'blocked'
    | 'running'
    | 'paused'
    | 'succeeded'
    | 'failed'
    | 'cancelled'
    | 'unavailable'
  readonly started_at: string | null
  readonly finished_at: string | null
  readonly checkpoint_fingerprint: string | null
  readonly records_processed: number
  readonly records_total: number | null
}

export interface RunArtifact {
  readonly artifact_id: string
  readonly kind: string
  readonly object_key: string
  readonly sha256: string
  readonly byte_count: number
  readonly schema_version: string
  readonly semantic_fingerprint: string
}

export interface ButterflyLensRun {
  readonly schema_version: typeof RUN_SCHEMA_VERSION
  readonly run_id: string
  readonly project_id: string
  readonly run_kind: RunKind
  readonly mode: RunMode
  readonly status: RunStatus
  readonly requested_by: {
    readonly actor_type: 'system' | 'account' | 'operator'
    readonly actor_id: string | null
  }
  readonly requested_at: string
  readonly started_at: string | null
  readonly finished_at: string | null
  readonly updated_at: string
  readonly engine: {
    readonly repository: string
    readonly commit: string
    readonly interface_version: string
    readonly command: string
  }
  readonly input_fingerprints: readonly string[]
  readonly stages: readonly RunStage[]
  readonly artifacts: readonly RunArtifact[]
  readonly error: {
    readonly code: string
    readonly message: string
    readonly retryable: boolean
    readonly stage_id: string | null
  } | null
  readonly revision: number
}
