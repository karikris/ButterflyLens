export const WORKER_IDENTITY_SCHEMA_VERSION =
  'butterflylens-worker-identity:v1.0.0' as const
export const WORKER_HEARTBEAT_SCHEMA_VERSION =
  'butterflylens-worker-heartbeat:v1.0.0' as const
export const WORKER_LEASE_SCHEMA_VERSION =
  'butterflylens-worker-lease:v1.0.0' as const
export const WORKER_COMMAND_SCHEMA_VERSION =
  'butterflylens-worker-command:v1.0.0' as const
export const WORKER_EVENT_SCHEMA_VERSION =
  'butterflylens-worker-event:v1.0.0' as const

export const WORKER_COMMAND_KINDS = [
  'start_run',
  'pause_run',
  'resume_run',
  'cancel_run',
  'health_check',
  'graceful_shutdown',
] as const

export const WORKER_EVENT_KINDS = [
  'stage_started',
  'progress',
  'checkpoint_committed',
  'artifact_committed',
  'stage_succeeded',
  'stage_failed',
  'run_paused',
  'run_cancelled',
  'shutdown_started',
  'shutdown_complete',
] as const

export interface WorkerIdentity {
  readonly schema_version: typeof WORKER_IDENTITY_SCHEMA_VERSION
  readonly worker_id: string
  readonly registered_at: string
  readonly machine_profile: {
    readonly platform: 'macos' | 'linux'
    readonly architecture: 'arm64' | 'x86_64'
    readonly os_version: string
    readonly chip_label: string
    readonly cpu_core_count: number
    readonly unified_memory_bytes: number
    readonly mps_available: boolean
    readonly mps_runtime: string | null
  }
  readonly capabilities: {
    readonly supported_stage_ids: readonly string[]
    readonly max_queue_records: number
    readonly max_queue_bytes: number
    readonly rolling_prefetch_batches: number
    readonly checkpoint_format: 'parquet-manifest-v1'
    readonly graceful_shutdown_supported: true
  }
  readonly configured_models: readonly {
    readonly role: 'yoloe_router' | 'bioclip_embedder'
    readonly model_id: string
    readonly revision: string
    readonly weights_sha256: string
    readonly preprocessing_fingerprint: string
    readonly licence_status: 'approved' | 'blocked'
    readonly device: 'mps' | 'cpu'
  }[]
  readonly identity_fingerprint: string
  readonly scientific_claim_allowed: false
}

export interface WorkerHeartbeat {
  readonly schema_version: typeof WORKER_HEARTBEAT_SCHEMA_VERSION
  readonly heartbeat_id: string
  readonly worker_id: string
  readonly sequence: number
  readonly observed_at: string
  readonly state: 'starting' | 'idle' | 'leased' | 'running' | 'paused' | 'draining' | 'degraded'
  readonly project_id: string | null
  readonly run_id: string | null
  readonly lease_id: string | null
  readonly lease_revision: number | null
  readonly lease_expires_at: string | null
  readonly current_stage_id: string | null
  readonly resources: Readonly<Record<string, number | null>>
  readonly queues: readonly Readonly<Record<string, number | string>>[]
  readonly models: readonly Readonly<Record<string, unknown>>[]
  readonly cache: Readonly<Record<string, number>>
  readonly last_committed_artifact_fingerprint: string | null
  readonly last_committed_at: string | null
  readonly health_checks: readonly Readonly<Record<string, string>>[]
  readonly heartbeat_fingerprint: string
  readonly scientific_claim_allowed: false
}

export interface WorkerLease {
  readonly schema_version: typeof WORKER_LEASE_SCHEMA_VERSION
  readonly lease_id: string
  readonly project_id: string
  readonly run_id: string
  readonly stage_id: string
  readonly worker_id: string
  readonly status: 'offered' | 'active' | 'released' | 'expired' | 'revoked'
  readonly revision: number
  readonly fencing_token: string
  readonly idempotency_key: string
  readonly issued_at: string
  readonly acquired_at: string | null
  readonly renewed_at: string | null
  readonly expires_at: string
  readonly released_at: string | null
  readonly checkpoint_fingerprint: string | null
  readonly cancellation_requested: boolean
  readonly cancellation_requested_at: string | null
  readonly lease_fingerprint: string
}

export interface WorkerCommand {
  readonly schema_version: typeof WORKER_COMMAND_SCHEMA_VERSION
  readonly command_id: string
  readonly worker_id: string
  readonly project_id: string | null
  readonly run_id: string | null
  readonly lease_id: string | null
  readonly expected_lease_revision: number | null
  readonly kind: (typeof WORKER_COMMAND_KINDS)[number]
  readonly idempotency_key: string
  readonly issued_at: string
  readonly expires_at: string
  readonly requested_by: string
  readonly payload: {
    readonly stage_id: string | null
    readonly checkpoint_fingerprint: string | null
    readonly reason: string | null
  }
  readonly command_fingerprint: string
}

export interface WorkerEvent {
  readonly schema_version: typeof WORKER_EVENT_SCHEMA_VERSION
  readonly event_id: string
  readonly worker_id: string
  readonly sequence: number
  readonly project_id: string
  readonly run_id: string
  readonly lease_id: string
  readonly lease_revision: number
  readonly kind: (typeof WORKER_EVENT_KINDS)[number]
  readonly stage_id: string
  readonly occurred_at: string
  readonly records_processed: number
  readonly bytes_processed: number
  readonly checkpoint_fingerprint: string | null
  readonly artifact_fingerprint: string | null
  readonly error: {
    readonly code: string
    readonly message: string
    readonly retryable: boolean
  } | null
  readonly event_fingerprint: string
  readonly scientific_claim_allowed: false
}
