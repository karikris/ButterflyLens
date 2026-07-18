import rawSubmittedImpact from './submittedContributorImpact.json'

export type ContributionMetricState = 'available' | 'not_applicable' | 'unavailable'

export interface ContributionMetric {
  readonly state: ContributionMetricState
  readonly value: number | null
  readonly reason: string | null
}

export interface ContributorImpactSnapshot {
  readonly schemaVersion: 'butterflylens-contributor-impact-web:v1.0.0'
  readonly snapshotMode: 'submitted' | 'live'
  readonly snapshotState: 'available' | 'unavailable'
  readonly snapshotStateReason: string | null
  readonly recognitionPolicy: 'evidence_not_speed'
  readonly visibility: 'self_only'
  readonly metrics: {
    readonly reviewedImages: ContributionMetric
    readonly resolvedConflicts: ContributionMetric
    readonly speciesHelped: ContributionMetric
    readonly regionsHelped: ContributionMetric
    readonly controlCoverage: ContributionMetric
    readonly expertContribution: ContributionMetric
  }
  readonly sourceEvidenceFingerprint: string | null
  readonly projectionFingerprint: string | null
  readonly calculatedAt: string | null
  readonly rankingPermitted: false
  readonly speedMetricPermitted: false
  readonly scientificClaimAllowed: false
}

const ROOT_KEYS = new Set([
  'schemaVersion', 'snapshotMode', 'snapshotState', 'snapshotStateReason',
  'recognitionPolicy', 'visibility', 'metrics', 'sourceEvidenceFingerprint',
  'projectionFingerprint', 'calculatedAt', 'rankingPermitted',
  'speedMetricPermitted', 'scientificClaimAllowed',
])
const METRIC_KEYS = [
  'reviewedImages', 'resolvedConflicts', 'speciesHelped', 'regionsHelped',
  'controlCoverage', 'expertContribution',
] as const

export const submittedContributorImpact = parseContributorImpactSnapshot(
  rawSubmittedImpact,
)

export function parseContributorImpactSnapshot(value: unknown): ContributorImpactSnapshot {
  if (!isRecord(value) || !hasExactKeys(value, ROOT_KEYS)) {
    throw new Error('contributor impact must have the exact public shape')
  }
  if (
    value.schemaVersion !== 'butterflylens-contributor-impact-web:v1.0.0' ||
    !['submitted', 'live'].includes(String(value.snapshotMode)) ||
    !['available', 'unavailable'].includes(String(value.snapshotState)) ||
    value.recognitionPolicy !== 'evidence_not_speed' ||
    value.visibility !== 'self_only'
  ) {
    throw new Error('contributor impact version or dignity boundary is invalid')
  }
  if (
    value.rankingPermitted !== false ||
    value.speedMetricPermitted !== false ||
    value.scientificClaimAllowed !== false
  ) {
    throw new Error('contributor impact cannot rank, time, or create authority')
  }
  if (!isRecord(value.metrics) || !hasExactKeys(value.metrics, new Set(METRIC_KEYS))) {
    throw new Error('contributor impact metrics must have the exact public shape')
  }
  const metrics = value.metrics
  for (const key of METRIC_KEYS) assertMetric(metrics[key], key)
  const validatedMetrics = metrics as Record<(typeof METRIC_KEYS)[number], ContributionMetric>

  const unavailable = value.snapshotState === 'unavailable'
  if (unavailable) {
    if (
      !nonEmptyString(value.snapshotStateReason) ||
      value.sourceEvidenceFingerprint !== null ||
      value.projectionFingerprint !== null ||
      value.calculatedAt !== null ||
      METRIC_KEYS.some((key) => validatedMetrics[key].state !== 'unavailable')
    ) {
      throw new Error('unavailable contributor snapshot must withhold every total')
    }
  } else if (
    value.snapshotStateReason !== null ||
    !isSha256(value.sourceEvidenceFingerprint) ||
    !isSha256(value.projectionFingerprint) ||
    typeof value.calculatedAt !== 'string' ||
    Number.isNaN(Date.parse(value.calculatedAt)) ||
    METRIC_KEYS.slice(0, 5).some((key) => validatedMetrics[key].state !== 'available')
  ) {
    throw new Error('available contributor snapshot lacks governed evidence')
  }
  return value as unknown as ContributorImpactSnapshot
}

function assertMetric(value: unknown, field: string): asserts value is ContributionMetric {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, new Set(['state', 'value', 'reason'])) ||
    !['available', 'not_applicable', 'unavailable'].includes(String(value.state))
  ) {
    throw new Error(`${field} contribution metric is invalid`)
  }
  if (value.state === 'available') {
    if (!Number.isSafeInteger(value.value) || Number(value.value) < 0 || value.reason !== null) {
      throw new Error(`${field} available metric is incomplete`)
    }
  } else if (value.value !== null || !nonEmptyString(value.reason)) {
    throw new Error(`${field} withheld metric must have a reason`)
  }
}

function hasExactKeys(value: Record<string, unknown>, expected: Set<string>): boolean {
  const keys = Object.keys(value)
  return keys.length === expected.size && keys.every((key) => expected.has(key))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== ''
}

function isSha256(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)
}
