import submittedOperationsJson from './submittedOperationsSnapshot.json'

const OPERATIONS_SCHEMA_VERSION = 'butterflylens-public-operations:v1.0.0' as const
const OBSERVATION_SCHEMA_VERSION =
  'butterflylens-public-worker-observation:v1.0.0' as const
const SHA256 = /^[0-9a-f]{64}$/
const GIT_SHA = /^[0-9a-f]{40}$/
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/
const HASH_ROUTE = /^#[a-z][a-z-]*$/

export type WorkerAvailability = 'online' | 'offline' | 'unavailable'

export interface OperationsArtifact {
  readonly snapshotId: string
  readonly mode: 'submitted' | 'live'
  readonly artifactFingerprint: string
  readonly generatedAt: string
  readonly sourceCommit: string
  readonly label: string
  readonly href: string
  readonly speciesCount: number
}

export interface LiveOperationsObservation {
  readonly schemaVersion: typeof OBSERVATION_SCHEMA_VERSION
  readonly observedAt: string
  readonly heartbeatObservedAt: string | null
  readonly workerState:
    | 'starting'
    | 'idle'
    | 'leased'
    | 'running'
    | 'paused'
    | 'draining'
    | 'degraded'
    | null
  readonly committedLiveSnapshot: OperationsArtifact | null
}

export interface SubmittedOperationsSnapshot {
  readonly schemaVersion: typeof OPERATIONS_SCHEMA_VERSION
  readonly generatedAt: string
  readonly site: {
    readonly available: true
    readonly committedDataQueryable: true
    readonly workerRequired: false
  }
  readonly workerFallback: {
    readonly status: 'unavailable'
    readonly heartbeatObservedAt: null
    readonly reason: string
  }
  readonly submittedSnapshot: OperationsArtifact & { readonly mode: 'submitted' }
  readonly map: {
    readonly snapshotId: string
    readonly artifactFingerprint: string
    readonly generatedAt: string
    readonly sourceCommit: string
    readonly scopeLabel: 'Australia'
    readonly renderState: 'scope_only_occurrences_withheld'
    readonly releaseState: 'blocked_pending_dataset_rights_resolution'
    readonly occurrenceLayerVisible: false
    readonly absenceInferencePermitted: false
    readonly reason: string
  }
  readonly review: {
    readonly available: true
    readonly itemId: string
    readonly mediaSha256: string
    readonly sourceCommit: string
    readonly href: '#verify'
    readonly reason: string
  }
}

export interface OperationsProjection {
  readonly workerStatus: WorkerAvailability
  readonly workerState: LiveOperationsObservation['workerState']
  readonly heartbeatObservedAt: string | null
  readonly currentSnapshot: OperationsArtifact
  readonly submittedSnapshot: OperationsArtifact
  readonly committedLiveSnapshot: OperationsArtifact | null
  readonly liveIsStale: boolean
  readonly siteAvailable: true
  readonly committedDataQueryable: true
  readonly reason: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function requireExactKeys(
  value: Record<string, unknown>,
  expected: readonly string[],
  label: string,
) {
  const actual = Object.keys(value).sort()
  const required = [...expected].sort()
  if (JSON.stringify(actual) !== JSON.stringify(required)) {
    throw new Error(`${label} must have the exact public shape`)
  }
}

function requireUtc(value: unknown, label: string): string {
  if (typeof value !== 'string' || !UTC.test(value)) {
    throw new Error(`${label} must be canonical UTC`)
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${label} must be canonical UTC`)
  }
  const normalized = parsed.toISOString()
  if (value !== normalized && value !== normalized.replace('.000Z', 'Z')) {
    throw new Error(`${label} must be canonical UTC`)
  }
  return value
}

function requireString(value: unknown, label: string): string {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    throw new Error(`${label} must be a bounded non-empty string`)
  }
  return value
}

function parseArtifact(value: unknown, expectedMode?: 'submitted' | 'live') {
  if (!isRecord(value)) throw new Error('operations artifact must be an object')
  requireExactKeys(
    value,
    [
      'snapshotId',
      'mode',
      'artifactFingerprint',
      'generatedAt',
      'sourceCommit',
      'label',
      'href',
      'speciesCount',
    ],
    'operations artifact',
  )
  const mode = value.mode
  if ((mode !== 'submitted' && mode !== 'live') || (expectedMode && mode !== expectedMode)) {
    throw new Error('operations artifact mode is invalid')
  }
  const artifactFingerprint = requireString(
    value.artifactFingerprint,
    'artifact fingerprint',
  )
  const sourceCommit = requireString(value.sourceCommit, 'source commit')
  const href = requireString(value.href, 'artifact route')
  if (!SHA256.test(artifactFingerprint) || !GIT_SHA.test(sourceCommit)) {
    throw new Error('operations artifact provenance is invalid')
  }
  if (!HASH_ROUTE.test(href)) throw new Error('operations artifact route is invalid')
  if (!Number.isInteger(value.speciesCount) || Number(value.speciesCount) < 0) {
    throw new Error('operations artifact species count is invalid')
  }
  return {
    snapshotId: requireString(value.snapshotId, 'snapshot ID'),
    mode,
    artifactFingerprint,
    generatedAt: requireUtc(value.generatedAt, 'artifact generation time'),
    sourceCommit,
    label: requireString(value.label, 'artifact label'),
    href,
    speciesCount: Number(value.speciesCount),
  } satisfies OperationsArtifact
}

export function parseSubmittedOperationsSnapshot(
  value: unknown,
): SubmittedOperationsSnapshot {
  if (!isRecord(value)) throw new Error('operations snapshot must be an object')
  requireExactKeys(
    value,
    [
      'schemaVersion',
      'generatedAt',
      'site',
      'workerFallback',
      'submittedSnapshot',
      'map',
      'review',
    ],
    'operations snapshot',
  )
  if (value.schemaVersion !== OPERATIONS_SCHEMA_VERSION) {
    throw new Error('operations snapshot version is invalid')
  }
  if (!isRecord(value.site) || !isRecord(value.workerFallback)) {
    throw new Error('operations availability boundary is invalid')
  }
  requireExactKeys(
    value.site,
    ['available', 'committedDataQueryable', 'workerRequired'],
    'site boundary',
  )
  if (
    value.site.available !== true ||
    value.site.committedDataQueryable !== true ||
    value.site.workerRequired !== false
  ) {
    throw new Error('site must remain independent of the worker')
  }
  requireExactKeys(
    value.workerFallback,
    ['status', 'heartbeatObservedAt', 'reason'],
    'worker fallback',
  )
  if (
    value.workerFallback.status !== 'unavailable' ||
    value.workerFallback.heartbeatObservedAt !== null
  ) {
    throw new Error('worker fallback cannot infer liveness')
  }
  const submittedSnapshot = parseArtifact(value.submittedSnapshot, 'submitted')

  if (!isRecord(value.map)) throw new Error('operations map must be an object')
  requireExactKeys(
    value.map,
    [
      'snapshotId',
      'artifactFingerprint',
      'generatedAt',
      'sourceCommit',
      'scopeLabel',
      'renderState',
      'releaseState',
      'occurrenceLayerVisible',
      'absenceInferencePermitted',
      'reason',
    ],
    'operations map',
  )
  if (
    value.map.scopeLabel !== 'Australia' ||
    value.map.renderState !== 'scope_only_occurrences_withheld' ||
    value.map.releaseState !== 'blocked_pending_dataset_rights_resolution' ||
    value.map.occurrenceLayerVisible !== false ||
    value.map.absenceInferencePermitted !== false
  ) {
    throw new Error('operations map rights boundary is invalid')
  }
  const mapFingerprint = requireString(value.map.artifactFingerprint, 'map fingerprint')
  const mapCommit = requireString(value.map.sourceCommit, 'map source commit')
  if (!SHA256.test(mapFingerprint) || !GIT_SHA.test(mapCommit)) {
    throw new Error('operations map provenance is invalid')
  }

  if (!isRecord(value.review)) throw new Error('operations review must be an object')
  requireExactKeys(
    value.review,
    ['available', 'itemId', 'mediaSha256', 'sourceCommit', 'href', 'reason'],
    'operations review',
  )
  const reviewSha = requireString(value.review.mediaSha256, 'review media SHA-256')
  const reviewCommit = requireString(value.review.sourceCommit, 'review source commit')
  if (
    value.review.available !== true ||
    value.review.href !== '#verify' ||
    !SHA256.test(reviewSha) ||
    !GIT_SHA.test(reviewCommit)
  ) {
    throw new Error('operations review boundary is invalid')
  }

  return {
    schemaVersion: OPERATIONS_SCHEMA_VERSION,
    generatedAt: requireUtc(value.generatedAt, 'operations generation time'),
    site: {
      available: true,
      committedDataQueryable: true,
      workerRequired: false,
    },
    workerFallback: {
      status: 'unavailable',
      heartbeatObservedAt: null,
      reason: requireString(value.workerFallback.reason, 'worker fallback reason'),
    },
    submittedSnapshot: { ...submittedSnapshot, mode: 'submitted' },
    map: {
      snapshotId: requireString(value.map.snapshotId, 'map snapshot ID'),
      artifactFingerprint: mapFingerprint,
      generatedAt: requireUtc(value.map.generatedAt, 'map generation time'),
      sourceCommit: mapCommit,
      scopeLabel: 'Australia',
      renderState: 'scope_only_occurrences_withheld',
      releaseState: 'blocked_pending_dataset_rights_resolution',
      occurrenceLayerVisible: false,
      absenceInferencePermitted: false,
      reason: requireString(value.map.reason, 'map reason'),
    },
    review: {
      available: true,
      itemId: requireString(value.review.itemId, 'review item ID'),
      mediaSha256: reviewSha,
      sourceCommit: reviewCommit,
      href: '#verify',
      reason: requireString(value.review.reason, 'review reason'),
    },
  }
}

export function parseLiveOperationsObservation(value: unknown): LiveOperationsObservation {
  if (!isRecord(value)) throw new Error('live observation must be an object')
  requireExactKeys(
    value,
    [
      'schemaVersion',
      'observedAt',
      'heartbeatObservedAt',
      'workerState',
      'committedLiveSnapshot',
    ],
    'live observation',
  )
  if (value.schemaVersion !== OBSERVATION_SCHEMA_VERSION) {
    throw new Error('live observation version is invalid')
  }
  const states = new Set([
    'starting',
    'idle',
    'leased',
    'running',
    'paused',
    'draining',
    'degraded',
  ])
  if (value.workerState !== null && !states.has(String(value.workerState))) {
    throw new Error('live worker state is invalid')
  }
  if ((value.heartbeatObservedAt === null) !== (value.workerState === null)) {
    throw new Error('live heartbeat and worker state must be supplied together')
  }
  return {
    schemaVersion: OBSERVATION_SCHEMA_VERSION,
    observedAt: requireUtc(value.observedAt, 'observation time'),
    heartbeatObservedAt:
      value.heartbeatObservedAt === null
        ? null
        : requireUtc(value.heartbeatObservedAt, 'heartbeat time'),
    workerState: value.workerState as LiveOperationsObservation['workerState'],
    committedLiveSnapshot:
      value.committedLiveSnapshot === null
        ? null
        : parseArtifact(value.committedLiveSnapshot, 'live'),
  }
}

function unavailableProjection(
  snapshot: SubmittedOperationsSnapshot,
  reason: string,
): OperationsProjection {
  return {
    workerStatus: 'unavailable',
    workerState: null,
    heartbeatObservedAt: null,
    currentSnapshot: snapshot.submittedSnapshot,
    submittedSnapshot: snapshot.submittedSnapshot,
    committedLiveSnapshot: null,
    liveIsStale: false,
    siteAvailable: true,
    committedDataQueryable: true,
    reason,
  }
}

export function buildOperationsProjection(
  snapshotValue: unknown,
  observationValue: unknown | null,
  asOf: Date,
  staleAfterMs = 300_000,
): OperationsProjection {
  const snapshot = parseSubmittedOperationsSnapshot(snapshotValue)
  if (Number.isNaN(asOf.getTime())) throw new Error('projection time is invalid')
  if (!Number.isInteger(staleAfterMs) || staleAfterMs <= 0 || staleAfterMs > 3_600_000) {
    throw new Error('stale horizon is invalid')
  }
  if (observationValue === null) {
    return unavailableProjection(snapshot, snapshot.workerFallback.reason)
  }
  const observation = parseLiveOperationsObservation(observationValue)
  const observedAt = Date.parse(observation.observedAt)
  const heartbeatAt =
    observation.heartbeatObservedAt === null
      ? null
      : Date.parse(observation.heartbeatObservedAt)
  if (observedAt > asOf.getTime() || (heartbeatAt !== null && heartbeatAt > asOf.getTime())) {
    throw new Error('live observation cannot be in the future')
  }
  if (heartbeatAt !== null && heartbeatAt > observedAt) {
    throw new Error('heartbeat cannot postdate its observation envelope')
  }
  if (
    observation.committedLiveSnapshot !== null &&
    Date.parse(observation.committedLiveSnapshot.generatedAt) > observedAt
  ) {
    throw new Error('committed snapshot cannot postdate its observation envelope')
  }
  const currentSnapshot = observation.committedLiveSnapshot ?? snapshot.submittedSnapshot
  if (heartbeatAt === null) {
    return {
      ...unavailableProjection(
        snapshot,
        'No heartbeat was supplied by the live status boundary; committed data remains available.',
      ),
      currentSnapshot,
      committedLiveSnapshot: observation.committedLiveSnapshot,
      liveIsStale: observation.committedLiveSnapshot !== null,
    }
  }
  const offline = asOf.getTime() - heartbeatAt > staleAfterMs
  return {
    workerStatus: offline ? 'offline' : 'online',
    workerState: observation.workerState,
    heartbeatObservedAt: observation.heartbeatObservedAt,
    currentSnapshot,
    submittedSnapshot: snapshot.submittedSnapshot,
    committedLiveSnapshot: observation.committedLiveSnapshot,
    liveIsStale: offline && observation.committedLiveSnapshot !== null,
    siteAvailable: true,
    committedDataQueryable: true,
    reason: offline
      ? 'The last observed heartbeat is stale. The worker is offline; the last committed data remains available.'
      : 'A fresh worker heartbeat is available. Public content still reads only committed artifacts.',
  }
}

export function buildSafeOperationsProjection(
  snapshotValue: unknown,
  observationValue: unknown | null,
  asOf: Date,
  staleAfterMs = 300_000,
): OperationsProjection {
  const snapshot = parseSubmittedOperationsSnapshot(snapshotValue)
  try {
    return buildOperationsProjection(snapshot, observationValue, asOf, staleAfterMs)
  } catch {
    return unavailableProjection(
      snapshot,
      'Live worker evidence failed strict validation. The committed submitted snapshot remains available.',
    )
  }
}

export const submittedOperationsSnapshot = parseSubmittedOperationsSnapshot(
  submittedOperationsJson,
)
