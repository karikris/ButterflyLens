import rawSubmittedProjection from './submittedQualityProjection.json'

export type QualityAvailability = 'estimated' | 'unavailable'

export interface QualityDashboardSnapshot {
  readonly schemaVersion: 'butterflylens-community-quality-dashboard:v1.0.0'
  readonly snapshotMode: 'submitted'
  readonly status: QualityAvailability
  readonly reviewedSample: number
  readonly decisiveReviews: number
  readonly precision: {
    readonly availability: QualityAvailability
    readonly estimate: number | null
    readonly interval: {
      readonly lower: number
      readonly upper: number
      readonly level: number
    } | null
    readonly effectiveSampleSize: number | null
    readonly reason: string | null
  }
  readonly reviewerAgreement: {
    readonly availability: QualityAvailability
    readonly pairwiseAgreement: number | null
    readonly nominalAlpha: number | null
    readonly overlappingItems: number
    readonly reason: string | null
  }
  readonly speciesQuality: {
    readonly availability: QualityAvailability
    readonly estimate: number | null
    readonly auditedSpecies: number
    readonly acceptedSpecies: number
    readonly reason: string | null
  }
  readonly referenceDiagnostics: {
    readonly acceptedSpecies: number
    readonly speciesWithValidDecodes: number
    readonly humanVerifiedSpecies: number
    readonly validDecodes: number
    readonly flags: readonly {
      readonly flagId: string
      readonly affectedSpecies: number
      readonly severity: 'blocker' | 'review' | 'unfinished'
    }[]
  }
  readonly releaseBlockers: readonly string[]
  readonly provenance: {
    readonly qualityManifestSha256: string
    readonly referenceBankFingerprint: string
    readonly qualityManifestGeneratedAt: string
    readonly qualitySnapshotFingerprint: string | null
    readonly authoritativeBaseline: 'ButterflyLens rebuilt baseline'
  }
  readonly targetedQueueSeparate: true
  readonly modelVoteIncluded: false
  readonly scientificClaimAllowed: false
}

export const submittedQualityDashboard = parseQualityDashboardSnapshot(
  rawSubmittedProjection,
)

export function parseQualityDashboardSnapshot(
  value: unknown,
): QualityDashboardSnapshot {
  if (!isRecord(value)) throw new Error('quality dashboard must be an object')
  if (
    value.schemaVersion !==
      'butterflylens-community-quality-dashboard:v1.0.0' ||
    value.snapshotMode !== 'submitted' ||
    !isAvailability(value.status)
  ) {
    throw new Error('quality dashboard version or submitted state is invalid')
  }
  const reviewedSample = nonNegativeInteger(value.reviewedSample, 'reviewedSample')
  const decisiveReviews = nonNegativeInteger(
    value.decisiveReviews,
    'decisiveReviews',
  )
  if (decisiveReviews > reviewedSample) {
    throw new Error('decisiveReviews cannot exceed reviewedSample')
  }
  assertEstimate(value.precision, 'precision')
  if (
    !isRecord(value.precision) ||
    value.status !== value.precision.availability
  ) {
    throw new Error('dashboard status must match precision availability')
  }
  if (
    value.precision.availability === 'estimated' &&
    typeof value.precision.effectiveSampleSize === 'number' &&
    value.precision.effectiveSampleSize > reviewedSample
  ) {
    throw new Error('precision effectiveSampleSize exceeds reviewedSample')
  }
  assertAgreement(value.reviewerAgreement)
  assertSpeciesQuality(value.speciesQuality)
  assertReferenceDiagnostics(value.referenceDiagnostics)
  if (
    !isRecord(value.reviewerAgreement) ||
    typeof value.reviewerAgreement.overlappingItems !== 'number' ||
    value.reviewerAgreement.overlappingItems > reviewedSample
  ) {
    throw new Error('reviewer overlap exceeds reviewedSample')
  }
  if (
    !isRecord(value.speciesQuality) ||
    !isRecord(value.referenceDiagnostics) ||
    value.speciesQuality.acceptedSpecies !==
      value.referenceDiagnostics.acceptedSpecies
  ) {
    throw new Error('species quality and reference baseline disagree')
  }
  if (
    !Array.isArray(value.releaseBlockers) ||
    value.releaseBlockers.length === 0 ||
    !value.releaseBlockers.every(nonEmptyString) ||
    new Set(value.releaseBlockers).size !== value.releaseBlockers.length
  ) {
    throw new Error('releaseBlockers must be non-empty strings')
  }
  if (!isRecord(value.provenance)) {
    throw new Error('quality dashboard provenance is missing')
  }
  for (const field of ['qualityManifestSha256', 'referenceBankFingerprint']) {
    if (!isSha256(value.provenance[field])) {
      throw new Error(`${field} must be lowercase SHA-256`)
    }
  }
  if (
    value.provenance.qualitySnapshotFingerprint !== null &&
    !isSha256(value.provenance.qualitySnapshotFingerprint)
  ) {
    throw new Error('qualitySnapshotFingerprint must be null or SHA-256')
  }
  if (
    (value.status === 'estimated') !==
    (value.provenance.qualitySnapshotFingerprint !== null)
  ) {
    throw new Error('quality snapshot fingerprint does not match availability')
  }
  if (
    value.provenance.authoritativeBaseline !== 'ButterflyLens rebuilt baseline' ||
    Number.isNaN(Date.parse(String(value.provenance.qualityManifestGeneratedAt)))
  ) {
    throw new Error('quality provenance baseline or time is invalid')
  }
  if (
    value.targetedQueueSeparate !== true ||
    value.modelVoteIncluded !== false ||
    value.scientificClaimAllowed !== false
  ) {
    throw new Error('quality dashboard violates its scientific boundary')
  }
  return value as unknown as QualityDashboardSnapshot
}

function assertEstimate(value: unknown, field: string): void {
  if (!isRecord(value) || !isAvailability(value.availability)) {
    throw new Error(`${field} availability is invalid`)
  }
  if (value.availability === 'unavailable') {
    if (
      value.estimate !== null ||
      value.interval !== null ||
      value.effectiveSampleSize !== null ||
      !nonEmptyString(value.reason)
    ) {
      throw new Error(`${field} unavailable state must withhold estimates`)
    }
    return
  }
  if (!isRecord(value.interval)) throw new Error(`${field}.interval is missing`)
  const lower = probability(value.interval.lower, `${field}.interval.lower`)
  const upper = probability(value.interval.upper, `${field}.interval.upper`)
  const level = probability(value.interval.level, `${field}.interval.level`)
  const estimate = probability(value.estimate, `${field}.estimate`)
  if (
    lower > upper ||
    estimate < lower ||
    estimate > upper ||
    level <= 0 ||
    level >= 1
  ) {
    throw new Error(`${field}.interval bounds or level are invalid`)
  }
  if (
    typeof value.effectiveSampleSize !== 'number' ||
    !Number.isFinite(value.effectiveSampleSize) ||
    value.effectiveSampleSize <= 0 ||
    value.reason !== null
  ) {
    throw new Error(`${field} estimated state is incomplete`)
  }
}

function assertAgreement(value: unknown): void {
  if (!isRecord(value) || !isAvailability(value.availability)) {
    throw new Error('reviewerAgreement availability is invalid')
  }
  const overlappingItems = nonNegativeInteger(
    value.overlappingItems,
    'reviewerAgreement.overlappingItems',
  )
  if (value.availability === 'unavailable') {
    if (
      value.pairwiseAgreement !== null ||
      value.nominalAlpha !== null ||
      !nonEmptyString(value.reason)
    ) {
      throw new Error('unavailable reviewer agreement must withhold coefficients')
    }
    return
  }
  if (overlappingItems === 0) {
    throw new Error('estimated reviewer agreement needs overlapping items')
  }
  probability(value.pairwiseAgreement, 'reviewerAgreement.pairwiseAgreement')
  if (
    typeof value.nominalAlpha !== 'number' ||
    !Number.isFinite(value.nominalAlpha) ||
    value.nominalAlpha < -1 ||
    value.nominalAlpha > 1 ||
    value.reason !== null
  ) {
    throw new Error('estimated reviewer agreement is invalid')
  }
}

function assertSpeciesQuality(value: unknown): void {
  if (!isRecord(value) || !isAvailability(value.availability)) {
    throw new Error('speciesQuality availability is invalid')
  }
  const audited = nonNegativeInteger(value.auditedSpecies, 'auditedSpecies')
  const accepted = nonNegativeInteger(value.acceptedSpecies, 'acceptedSpecies')
  if (audited > accepted) throw new Error('auditedSpecies exceeds acceptedSpecies')
  if (value.availability === 'unavailable') {
    if (value.estimate !== null || !nonEmptyString(value.reason)) {
      throw new Error('unavailable species quality must withhold its estimate')
    }
    return
  }
  if (audited === 0) {
    throw new Error('estimated species quality needs audited species')
  }
  probability(value.estimate, 'speciesQuality.estimate')
  if (value.reason !== null) throw new Error('estimated species quality has a blocker')
}

function assertReferenceDiagnostics(value: unknown): void {
  if (!isRecord(value) || !Array.isArray(value.flags)) {
    throw new Error('reference diagnostics are invalid')
  }
  const acceptedSpecies = nonNegativeInteger(
    value.acceptedSpecies,
    'referenceDiagnostics.acceptedSpecies',
  )
  const speciesWithValidDecodes = nonNegativeInteger(
    value.speciesWithValidDecodes,
    'referenceDiagnostics.speciesWithValidDecodes',
  )
  const humanVerifiedSpecies = nonNegativeInteger(
    value.humanVerifiedSpecies,
    'referenceDiagnostics.humanVerifiedSpecies',
  )
  nonNegativeInteger(value.validDecodes, 'referenceDiagnostics.validDecodes')
  if (
    speciesWithValidDecodes > acceptedSpecies ||
    humanVerifiedSpecies > acceptedSpecies
  ) {
    throw new Error('reference diagnostic species counts exceed acceptedSpecies')
  }
  const flagIds = new Set<string>()
  for (const flag of value.flags) {
    if (
      !isRecord(flag) ||
      !nonEmptyString(flag.flagId) ||
      !['blocker', 'review', 'unfinished'].includes(String(flag.severity))
    ) {
      throw new Error('reference health flag is invalid')
    }
    const affectedSpecies = nonNegativeInteger(
      flag.affectedSpecies,
      'flag.affectedSpecies',
    )
    if (affectedSpecies > acceptedSpecies || flagIds.has(flag.flagId as string)) {
      throw new Error('reference health flag count or identity is invalid')
    }
    flagIds.add(flag.flagId as string)
  }
}

function probability(value: unknown, field: string): number {
  if (
    typeof value !== 'number' ||
    !Number.isFinite(value) ||
    value < 0 ||
    value > 1
  ) {
    throw new Error(`${field} must be a probability`)
  }
  return value
}

function nonNegativeInteger(value: unknown, field: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) {
    throw new Error(`${field} must be a non-negative integer`)
  }
  return value
}

function nonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim() !== ''
}

function isAvailability(value: unknown): value is QualityAvailability {
  return value === 'estimated' || value === 'unavailable'
}

function isSha256(value: unknown): value is string {
  return typeof value === 'string' && /^[0-9a-f]{64}$/u.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}
