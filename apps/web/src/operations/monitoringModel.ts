import submittedMonitoringJson from './submittedMonitoringSnapshot.json'

const SCHEMA_VERSION = 'butterflylens-public-monitoring:v1.0.0' as const
const SHA256 = /^[0-9a-f]{64}$/
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/
const STATES = new Set(['available', 'submitted', 'unavailable', 'unfinished', 'degraded'])
const WORKER_STATES = new Set([
  'starting',
  'idle',
  'leased',
  'running',
  'paused',
  'draining',
  'degraded',
])
const MODEL_STATES = new Set(['ready', 'unfinished', 'unavailable', 'failed'])

export type MonitoringState =
  | 'available'
  | 'submitted'
  | 'unavailable'
  | 'unfinished'
  | 'degraded'

export interface PublicMonitoringSnapshot {
  readonly schemaVersion: typeof SCHEMA_VERSION
  readonly snapshotMode: 'submitted' | 'live'
  readonly observedAt: string
  readonly heartbeat: {
    readonly state: MonitoringState
    readonly observedAt: string | null
    readonly workerState: string | null
    readonly reason: string
  }
  readonly apiBudget: {
    readonly state: MonitoringState
    readonly limit: number | null
    readonly used: number | null
    readonly remaining: number | null
    readonly resetsAt: string | null
    readonly reason: string
  }
  readonly stageHealth: {
    readonly state: MonitoringState
    readonly currentStage: string | null
    readonly stageState: string | null
    readonly healthyCount: number | null
    readonly failedCount: number | null
    readonly reason: string
  }
  readonly queue: {
    readonly state: MonitoringState
    readonly depth: number | null
    readonly capacity: number | null
    readonly reason: string
  }
  readonly failures: {
    readonly state: MonitoringState
    readonly count: number | null
    readonly reason: string
  }
  readonly lastArtifact: {
    readonly state: MonitoringState
    readonly fingerprint: string | null
    readonly committedAt: string | null
    readonly reason: string
  }
  readonly lastMapRefresh: {
    readonly state: MonitoringState
    readonly fingerprint: string | null
    readonly refreshedAt: string | null
    readonly reason: string
  }
  readonly models: {
    readonly state: MonitoringState
    readonly yoloe: string
    readonly bioclip: string
    readonly reason: string
  }
  readonly resources: {
    readonly state: MonitoringState
    readonly freeDiskBytes: number | null
    readonly processRssBytes: number | null
    readonly memoryCapacityBytes: number | null
    readonly mpsAllocatedBytes: number | null
    readonly mpsReservedBytes: number | null
    readonly reason: string
  }
  readonly scientificClaimAllowed: false
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function exact(value: Record<string, unknown>, keys: readonly string[], label: string) {
  if (JSON.stringify(Object.keys(value).sort()) !== JSON.stringify([...keys].sort())) {
    throw new Error(`${label} must have the exact public shape`)
  }
}

function text(value: unknown, label: string) {
  if (typeof value !== 'string' || value.length === 0 || value.length > 512) {
    throw new Error(`${label} must be a bounded non-empty string`)
  }
  return value
}

function utc(value: unknown, label: string) {
  const candidate = text(value, label)
  if (!UTC.test(candidate)) throw new Error(`${label} must be canonical UTC`)
  const parsed = new Date(candidate)
  if (Number.isNaN(parsed.getTime())) throw new Error(`${label} must be canonical UTC`)
  const normalized = parsed.toISOString()
  if (candidate !== normalized && candidate !== normalized.replace('.000Z', 'Z')) {
    throw new Error(`${label} must be canonical UTC`)
  }
  return candidate
}

function nullableUtc(value: unknown, label: string) {
  return value === null ? null : utc(value, label)
}

function state(value: unknown, label: string): MonitoringState {
  if (typeof value !== 'string' || !STATES.has(value)) {
    throw new Error(`${label} state is invalid`)
  }
  return value as MonitoringState
}

function count(value: unknown, label: string) {
  if (!Number.isSafeInteger(value) || Number(value) < 0) {
    throw new Error(`${label} must be a non-negative safe integer`)
  }
  return Number(value)
}

function nullableCount(value: unknown, label: string) {
  return value === null ? null : count(value, label)
}

function reason(value: Record<string, unknown>, label: string) {
  return text(value.reason, `${label} reason`)
}

function requireAllNull(values: readonly unknown[], label: string) {
  if (values.some((value) => value !== null)) {
    throw new Error(`${label} unavailable values must remain null`)
  }
}

function requireAllPresent(values: readonly unknown[], label: string) {
  if (values.some((value) => value === null)) {
    throw new Error(`${label} available values must be complete`)
  }
}

function parseHeartbeat(value: unknown, mode: 'submitted' | 'live') {
  if (!isRecord(value)) throw new Error('heartbeat monitoring must be an object')
  exact(value, ['state', 'observedAt', 'workerState', 'reason'], 'heartbeat monitoring')
  const metricState = state(value.state, 'heartbeat')
  const observedAt = nullableUtc(value.observedAt, 'heartbeat observation time')
  const workerState = value.workerState === null ? null : text(value.workerState, 'worker state')
  if (workerState !== null && !WORKER_STATES.has(workerState)) {
    throw new Error('worker state is invalid')
  }
  if ((observedAt === null) !== (workerState === null)) {
    throw new Error('heartbeat time and worker state must be supplied together')
  }
  if (metricState === 'unavailable') requireAllNull([observedAt, workerState], 'heartbeat')
  if (mode === 'submitted' && metricState !== 'unavailable') {
    throw new Error('submitted monitoring cannot claim a live heartbeat')
  }
  if (mode === 'live' && !['available', 'degraded', 'unavailable'].includes(metricState)) {
    throw new Error('live heartbeat state is invalid')
  }
  return { state: metricState, observedAt, workerState, reason: reason(value, 'heartbeat') }
}

function parseApiBudget(value: unknown) {
  if (!isRecord(value)) throw new Error('API budget must be an object')
  exact(value, ['state', 'limit', 'used', 'remaining', 'resetsAt', 'reason'], 'API budget')
  const metricState = state(value.state, 'API budget')
  const limit = nullableCount(value.limit, 'API budget limit')
  const used = nullableCount(value.used, 'API budget used')
  const remaining = nullableCount(value.remaining, 'API budget remaining')
  const resetsAt = nullableUtc(value.resetsAt, 'API budget reset time')
  if (metricState === 'unavailable') {
    requireAllNull([limit, used, remaining, resetsAt], 'API budget')
  } else {
    requireAllPresent([limit, used, remaining], 'API budget')
    if (Number(used) + Number(remaining) !== limit) {
      throw new Error('API budget used and remaining must equal its limit')
    }
  }
  return { state: metricState, limit, used, remaining, resetsAt, reason: reason(value, 'API budget') }
}

function parseStageHealth(value: unknown) {
  if (!isRecord(value)) throw new Error('stage health must be an object')
  exact(
    value,
    ['state', 'currentStage', 'stageState', 'healthyCount', 'failedCount', 'reason'],
    'stage health',
  )
  const metricState = state(value.state, 'stage health')
  const currentStage = value.currentStage === null ? null : text(value.currentStage, 'current stage')
  const stageState = value.stageState === null ? null : text(value.stageState, 'stage state')
  const healthyCount = nullableCount(value.healthyCount, 'healthy stage count')
  const failedCount = nullableCount(value.failedCount, 'failed stage count')
  if (metricState === 'unavailable') {
    requireAllNull([currentStage, stageState, healthyCount, failedCount], 'stage health')
  } else {
    requireAllPresent([healthyCount, failedCount], 'stage health')
    if ((currentStage === null) !== (stageState === null)) {
      throw new Error('current stage and stage state must be supplied together')
    }
  }
  return {
    state: metricState,
    currentStage,
    stageState,
    healthyCount,
    failedCount,
    reason: reason(value, 'stage health'),
  }
}

function parseQueue(value: unknown) {
  if (!isRecord(value)) throw new Error('queue monitoring must be an object')
  exact(value, ['state', 'depth', 'capacity', 'reason'], 'queue monitoring')
  const metricState = state(value.state, 'queue')
  const depth = nullableCount(value.depth, 'queue depth')
  const capacity = nullableCount(value.capacity, 'queue capacity')
  if (metricState === 'unavailable') requireAllNull([depth, capacity], 'queue')
  else {
    requireAllPresent([depth, capacity], 'queue')
    if (Number(depth) > Number(capacity)) throw new Error('queue depth exceeds capacity')
  }
  return { state: metricState, depth, capacity, reason: reason(value, 'queue') }
}

function parseFailures(value: unknown) {
  if (!isRecord(value)) throw new Error('failure monitoring must be an object')
  exact(value, ['state', 'count', 'reason'], 'failure monitoring')
  const metricState = state(value.state, 'failures')
  const failureCount = nullableCount(value.count, 'failure count')
  if (metricState === 'unavailable') requireAllNull([failureCount], 'failures')
  else requireAllPresent([failureCount], 'failures')
  return { state: metricState, count: failureCount, reason: reason(value, 'failures') }
}

function parseArtifact(value: unknown, label: 'last artifact' | 'last map refresh') {
  if (!isRecord(value)) throw new Error(`${label} must be an object`)
  const timeKey = label === 'last artifact' ? 'committedAt' : 'refreshedAt'
  exact(value, ['state', 'fingerprint', timeKey, 'reason'], label)
  const metricState = state(value.state, label)
  const fingerprint = value.fingerprint === null ? null : text(value.fingerprint, `${label} fingerprint`)
  const observed = nullableUtc(value[timeKey], `${label} time`)
  if (fingerprint !== null && !SHA256.test(fingerprint)) throw new Error(`${label} fingerprint is invalid`)
  if (metricState === 'unavailable') requireAllNull([fingerprint, observed], label)
  else requireAllPresent([fingerprint, observed], label)
  return { state: metricState, fingerprint, observed, reason: reason(value, label) }
}

function parseModels(value: unknown) {
  if (!isRecord(value)) throw new Error('model monitoring must be an object')
  exact(value, ['state', 'yoloe', 'bioclip', 'reason'], 'model monitoring')
  const metricState = state(value.state, 'models')
  const yoloe = text(value.yoloe, 'YOLOE state')
  const bioclip = text(value.bioclip, 'BioCLIP state')
  if (!MODEL_STATES.has(yoloe) || !MODEL_STATES.has(bioclip)) {
    throw new Error('model component state is invalid')
  }
  if (metricState === 'unfinished' && (yoloe !== 'unfinished' || bioclip !== 'unfinished')) {
    throw new Error('unfinished model monitoring must retain both unfinished states')
  }
  return { state: metricState, yoloe, bioclip, reason: reason(value, 'models') }
}

function parseResources(value: unknown) {
  if (!isRecord(value)) throw new Error('resource monitoring must be an object')
  const keys = [
    'state',
    'freeDiskBytes',
    'processRssBytes',
    'memoryCapacityBytes',
    'mpsAllocatedBytes',
    'mpsReservedBytes',
    'reason',
  ]
  exact(value, keys, 'resource monitoring')
  const metricState = state(value.state, 'resources')
  const resources = {
    freeDiskBytes: nullableCount(value.freeDiskBytes, 'free disk bytes'),
    processRssBytes: nullableCount(value.processRssBytes, 'process RSS bytes'),
    memoryCapacityBytes: nullableCount(value.memoryCapacityBytes, 'memory capacity bytes'),
    mpsAllocatedBytes: nullableCount(value.mpsAllocatedBytes, 'MPS allocated bytes'),
    mpsReservedBytes: nullableCount(value.mpsReservedBytes, 'MPS reserved bytes'),
  }
  if (metricState === 'unavailable') requireAllNull(Object.values(resources), 'resources')
  else requireAllPresent(
    [resources.freeDiskBytes, resources.processRssBytes, resources.memoryCapacityBytes],
    'resources',
  )
  return { state: metricState, ...resources, reason: reason(value, 'resources') }
}

export function parsePublicMonitoringSnapshot(value: unknown): PublicMonitoringSnapshot {
  if (!isRecord(value)) throw new Error('monitoring snapshot must be an object')
  exact(
    value,
    [
      'schemaVersion',
      'snapshotMode',
      'observedAt',
      'heartbeat',
      'apiBudget',
      'stageHealth',
      'queue',
      'failures',
      'lastArtifact',
      'lastMapRefresh',
      'models',
      'resources',
      'scientificClaimAllowed',
    ],
    'monitoring snapshot',
  )
  if (value.schemaVersion !== SCHEMA_VERSION) throw new Error('monitoring version is invalid')
  if (value.snapshotMode !== 'submitted' && value.snapshotMode !== 'live') {
    throw new Error('monitoring snapshot mode is invalid')
  }
  if (value.scientificClaimAllowed !== false) {
    throw new Error('monitoring cannot authorize a scientific claim')
  }
  const mode = value.snapshotMode
  const observedAt = utc(value.observedAt, 'monitoring observation time')
  const heartbeat = parseHeartbeat(value.heartbeat, mode)
  const apiBudget = parseApiBudget(value.apiBudget)
  const stageHealth = parseStageHealth(value.stageHealth)
  const queue = parseQueue(value.queue)
  const failures = parseFailures(value.failures)
  const lastArtifact = parseArtifact(value.lastArtifact, 'last artifact')
  const lastMap = parseArtifact(value.lastMapRefresh, 'last map refresh')
  const models = parseModels(value.models)
  const resources = parseResources(value.resources)
  if (mode === 'submitted') {
    if (
      heartbeat.state !== 'unavailable' ||
      apiBudget.state !== 'unavailable' ||
      stageHealth.state !== 'unavailable' ||
      queue.state !== 'unavailable' ||
      failures.state !== 'unavailable' ||
      lastArtifact.state !== 'submitted' ||
      lastMap.state !== 'submitted' ||
      models.state !== 'unfinished' ||
      resources.state !== 'unavailable'
    ) {
      throw new Error('submitted monitoring states are invalid')
    }
  }
  const envelopeTime = Date.parse(observedAt)
  for (const [candidate, label] of [
    [heartbeat.observedAt, 'heartbeat'],
    [lastArtifact.observed, 'last artifact'],
    [lastMap.observed, 'last map refresh'],
  ] as const) {
    if (candidate !== null && Date.parse(candidate) > envelopeTime) {
      throw new Error(`${label} cannot postdate the monitoring snapshot`)
    }
  }
  return {
    schemaVersion: SCHEMA_VERSION,
    snapshotMode: mode,
    observedAt,
    heartbeat,
    apiBudget,
    stageHealth,
    queue,
    failures,
    lastArtifact: {
      state: lastArtifact.state,
      fingerprint: lastArtifact.fingerprint,
      committedAt: lastArtifact.observed,
      reason: lastArtifact.reason,
    },
    lastMapRefresh: {
      state: lastMap.state,
      fingerprint: lastMap.fingerprint,
      refreshedAt: lastMap.observed,
      reason: lastMap.reason,
    },
    models,
    resources,
    scientificClaimAllowed: false,
  }
}

export const submittedMonitoringSnapshot = parsePublicMonitoringSnapshot(
  submittedMonitoringJson,
)
