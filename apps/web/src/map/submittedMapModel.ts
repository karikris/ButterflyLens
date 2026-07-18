import rawSubmittedMap from './submittedMapSnapshot.json'

export type MapScopeKind = 'state' | 'ibra' | 'lga' | 'h3'
export type MapLayerStatus = 'available' | 'unavailable'

export interface SubmittedMapRecord {
  readonly recordId: string
  readonly recordFingerprint: string
  readonly taxonKey: string | null
  readonly providerScientificName: string | null
  readonly dataResourceUid: string
  readonly dataResourceName: string
  readonly basisOfRecord: string | null
  readonly eventYear: number | null
  readonly publiclyGeneralised: boolean
  readonly sourceReference: string
  readonly evidenceLabel: string
}

export interface SubmittedMapCell {
  readonly cellId: string
  readonly count: number
  readonly center: readonly [number, number]
  readonly polygon: readonly (readonly [number, number])[]
  readonly latestEventYear: number | null
  readonly publiclyGeneralisedCount: number
  readonly evidenceFingerprint: string
  readonly cellFingerprint: string
  readonly records: readonly SubmittedMapRecord[]
}

export interface SubmittedMapScope {
  readonly scopeId: string
  readonly label: string
  readonly count: number
  readonly matchedTaxonCount: number
  readonly unmatchedTaxonAssertionCount: number
  readonly uniqueTaxonCount: number
  readonly latestEventYear: number | null
  readonly publiclyGeneralisedCount: number
  readonly evidenceFingerprint: string
  readonly summaryFingerprint: string
}

export interface SubmittedMapSnapshot {
  readonly schemaVersion: 'butterflylens-submitted-map-browser-snapshot/v1'
  readonly snapshotId: string
  readonly snapshotFingerprint: string
  readonly mode: 'submitted'
  readonly generatedAt: string
  readonly sourceCommit: string
  readonly projectId: string
  readonly runId: string
  readonly acceptedTaxonKey: string
  readonly source: {
    readonly provider: 'Atlas of Living Australia'
    readonly snapshotId: string
    readonly snapshotFingerprint: string
    readonly attribution: string
    readonly notice: string
  }
  readonly counts: {
    readonly authoritativeBaselineSelected: number
    readonly rightsScreenedSelected: number
    readonly rightsExcludedSelected: number
    readonly mapEligible: number
    readonly rightsExcludedMapEligible: number
    readonly mapCells: number
  }
  readonly layers: Readonly<
    Record<
      'alaBaseline' | 'flickrCandidate' | 'communityReviewed' | 'releaseReady',
      {
        readonly status: MapLayerStatus
        readonly label: string
        readonly visualEncoding: string
        readonly reason: string | null
      }
    >
  >
  readonly rights: {
    readonly state: 'public_projection_available_with_flagged_datasets_excluded'
    readonly legalConclusion: false
    readonly excludedDatasets: readonly {
      readonly dataResourceUid: string
      readonly dataResourceName: string
      readonly selectedRecordCount: number
      readonly spatiallyEligibleRecordCount: number
      readonly reviewState: 'blocked_pending_citation_rights_resolution'
      readonly datasetFingerprint: string
    }[]
  }
  readonly policies: {
    readonly occurrenceCoordinatesPublished: false
    readonly boundaryGeometryCopied: false
    readonly absenceInferencePermitted: false
    readonly scientificClaimAllowed: false
    readonly lgaQualification: string
  }
  readonly cells: readonly SubmittedMapCell[]
  readonly scopes: Readonly<Record<MapScopeKind, readonly SubmittedMapScope[]>>
}

const SHA256 = /^[0-9a-f]{64}$/u
const GIT_SHA = /^[0-9a-f]{40}$/u
const H3 = /^[0-9a-f]{15}$/u
const TAXON_KEY = /^bltx:v1:[0-9a-f]{24}$/u
const BLOCKED_DATASETS = new Set(['dr1097', 'dr30019', 'dr635'])
const LAYER_KEYS = [
  'alaBaseline',
  'flickrCandidate',
  'communityReviewed',
  'releaseReady',
] as const
const SCOPE_KEYS = ['state', 'ibra', 'lga', 'h3'] as const

export function parseSubmittedMapSnapshot(value: unknown): SubmittedMapSnapshot {
  const map = record(value, 'map snapshot')
  exact(map.schemaVersion, 'butterflylens-submitted-map-browser-snapshot/v1')
  exact(map.mode, 'submitted')
  matches(map.sourceCommit, GIT_SHA, 'sourceCommit')
  matches(map.acceptedTaxonKey, TAXON_KEY, 'acceptedTaxonKey')
  matches(map.snapshotFingerprint, SHA256, 'snapshotFingerprint')
  for (const field of ['snapshotId', 'generatedAt', 'projectId', 'runId']) {
    nonEmpty(map[field], field)
  }

  const source = record(map.source, 'source')
  exact(source.provider, 'Atlas of Living Australia')
  matches(source.snapshotFingerprint, SHA256, 'source.snapshotFingerprint')
  for (const field of ['snapshotId', 'attribution', 'notice']) {
    nonEmpty(source[field], `source.${field}`)
  }

  const counts = record(map.counts, 'counts')
  for (const field of [
    'authoritativeBaselineSelected',
    'rightsScreenedSelected',
    'rightsExcludedSelected',
    'mapEligible',
    'rightsExcludedMapEligible',
    'mapCells',
  ]) {
    nonNegativeInteger(counts[field], `counts.${field}`)
  }
  if (
    Number(counts.rightsScreenedSelected) + Number(counts.rightsExcludedSelected) !==
      Number(counts.authoritativeBaselineSelected) ||
    Number(counts.mapEligible) + Number(counts.rightsExcludedMapEligible) !== 230_027
  ) {
    throw new Error('map count boundary does not reconcile')
  }

  const layers = record(map.layers, 'layers')
  for (const key of LAYER_KEYS) {
    const layer = record(layers[key], `layers.${key}`)
    if (!['available', 'unavailable'].includes(String(layer.status))) {
      throw new Error(`layers.${key}.status is invalid`)
    }
    nonEmpty(layer.label, `layers.${key}.label`)
    nonEmpty(layer.visualEncoding, `layers.${key}.visualEncoding`)
    if (layer.status === 'available') {
      if (layer.reason !== null) throw new Error(`available ${key} layer has a reason`)
    } else {
      nonEmpty(layer.reason, `layers.${key}.reason`)
    }
  }
  if (
    record(layers.alaBaseline, 'layers.alaBaseline').status !== 'available' ||
    LAYER_KEYS.slice(1).some(
      (key) => record(layers[key], `layers.${key}`).status !== 'unavailable',
    )
  ) {
    throw new Error('submitted map layer availability is invalid')
  }

  const rights = record(map.rights, 'rights')
  exact(rights.state, 'public_projection_available_with_flagged_datasets_excluded')
  exact(rights.legalConclusion, false)
  if (!Array.isArray(rights.excludedDatasets) || rights.excludedDatasets.length !== 3) {
    throw new Error('submitted map must retain three rights exclusions')
  }
  const observedBlocked = new Set<string>()
  let excludedSelected = 0
  let excludedSpatial = 0
  for (const value of rights.excludedDatasets) {
    const dataset = record(value, 'excluded dataset')
    observedBlocked.add(nonEmpty(dataset.dataResourceUid, 'dataResourceUid'))
    nonEmpty(dataset.dataResourceName, 'dataResourceName')
    matches(dataset.datasetFingerprint, SHA256, 'datasetFingerprint')
    exact(dataset.reviewState, 'blocked_pending_citation_rights_resolution')
    excludedSelected += nonNegativeInteger(
      dataset.selectedRecordCount,
      'selectedRecordCount',
    )
    excludedSpatial += nonNegativeInteger(
      dataset.spatiallyEligibleRecordCount,
      'spatiallyEligibleRecordCount',
    )
  }
  if (
    observedBlocked.size !== BLOCKED_DATASETS.size ||
    [...BLOCKED_DATASETS].some((uid) => !observedBlocked.has(uid)) ||
    excludedSelected !== counts.rightsExcludedSelected ||
    excludedSpatial !== counts.rightsExcludedMapEligible
  ) {
    throw new Error('rights exclusions do not reconcile')
  }

  const policies = record(map.policies, 'policies')
  for (const field of [
    'occurrenceCoordinatesPublished',
    'boundaryGeometryCopied',
    'absenceInferencePermitted',
    'scientificClaimAllowed',
  ]) {
    exact(policies[field], false)
  }
  nonEmpty(policies.lgaQualification, 'policies.lgaQualification')

  if (!Array.isArray(map.cells) || map.cells.length !== counts.mapCells) {
    throw new Error('map cell count does not match')
  }
  const cellIds = new Set<string>()
  let cellCount = 0
  for (const value of map.cells) {
    const cell = validateCell(value)
    if (cellIds.has(cell.cellId)) throw new Error('map cell is duplicated')
    cellIds.add(cell.cellId)
    cellCount += cell.count
  }
  if (cellCount !== counts.mapEligible) {
    throw new Error('map cells do not reconcile with eligible count')
  }

  const scopes = record(map.scopes, 'scopes')
  for (const key of SCOPE_KEYS) {
    if (!Array.isArray(scopes[key]) || scopes[key].length === 0) {
      throw new Error(`scopes.${key} must be a non-empty array`)
    }
    const ids = new Set<string>()
    for (const value of scopes[key]) {
      const scope = validateScope(value)
      if (ids.has(scope.scopeId)) throw new Error(`scopes.${key} is duplicated`)
      ids.add(scope.scopeId)
      if (key === 'h3' && !cellIds.has(scope.label)) {
        throw new Error('H3 scope has no matching map cell')
      }
    }
  }
  if ((scopes.h3 as unknown[]).length !== map.cells.length) {
    throw new Error('H3 scope and map-cell counts differ')
  }
  return value as SubmittedMapSnapshot
}

function validateCell(value: unknown): SubmittedMapCell {
  const cell = record(value, 'map cell')
  const cellId = matches(cell.cellId, H3, 'cellId')
  const count = nonNegativeInteger(cell.count, 'cell.count')
  matches(cell.evidenceFingerprint, SHA256, 'cell.evidenceFingerprint')
  matches(cell.cellFingerprint, SHA256, 'cell.cellFingerprint')
  nullableYear(cell.latestEventYear, 'cell.latestEventYear')
  nonNegativeInteger(cell.publiclyGeneralisedCount, 'publiclyGeneralisedCount')
  coordinatePair(cell.center, 'cell.center')
  if (!Array.isArray(cell.polygon) || cell.polygon.length < 6) {
    throw new Error('cell polygon must contain an H3 boundary')
  }
  for (const point of cell.polygon) coordinatePair(point, 'cell.polygon point')
  if (!Array.isArray(cell.records) || cell.records.length > 2) {
    throw new Error('cell evidence samples are invalid')
  }
  for (const value of cell.records) validateRecord(value)
  return { ...(cell as unknown as SubmittedMapCell), cellId, count }
}

function validateRecord(value: unknown): void {
  const evidence = record(value, 'map evidence record')
  nonEmpty(evidence.recordId, 'recordId')
  matches(evidence.recordFingerprint, SHA256, 'recordFingerprint')
  if (evidence.taxonKey !== null) matches(evidence.taxonKey, TAXON_KEY, 'taxonKey')
  nullableString(evidence.providerScientificName, 'providerScientificName')
  const uid = nonEmpty(evidence.dataResourceUid, 'dataResourceUid')
  if (BLOCKED_DATASETS.has(uid)) throw new Error('blocked dataset leaked into map')
  nonEmpty(evidence.dataResourceName, 'dataResourceName')
  nullableString(evidence.basisOfRecord, 'basisOfRecord')
  nullableYear(evidence.eventYear, 'eventYear')
  exact(typeof evidence.publiclyGeneralised, 'boolean')
  const reference = nonEmpty(evidence.sourceReference, 'sourceReference')
  if (!/^https?:\/\//u.test(reference)) throw new Error('sourceReference must be HTTP(S)')
  const label = nonEmpty(evidence.evidenceLabel, 'evidenceLabel')
  if (!label.includes('not human verification')) {
    throw new Error('record evidence label overstates provider authority')
  }
}

function validateScope(value: unknown): SubmittedMapScope {
  const scope = record(value, 'map scope')
  nonEmpty(scope.scopeId, 'scopeId')
  nonEmpty(scope.label, 'scope.label')
  const count = nonNegativeInteger(scope.count, 'scope.count')
  const matched = nonNegativeInteger(scope.matchedTaxonCount, 'matchedTaxonCount')
  const unmatched = nonNegativeInteger(
    scope.unmatchedTaxonAssertionCount,
    'unmatchedTaxonAssertionCount',
  )
  if (matched + unmatched !== count) throw new Error('scope counts do not reconcile')
  nonNegativeInteger(scope.uniqueTaxonCount, 'uniqueTaxonCount')
  nullableYear(scope.latestEventYear, 'scope.latestEventYear')
  nonNegativeInteger(scope.publiclyGeneralisedCount, 'publiclyGeneralisedCount')
  matches(scope.evidenceFingerprint, SHA256, 'scope.evidenceFingerprint')
  matches(scope.summaryFingerprint, SHA256, 'scope.summaryFingerprint')
  return scope as unknown as SubmittedMapScope
}

function record(value: unknown, name: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${name} must be an object`)
  }
  return value as Record<string, unknown>
}

function exact(value: unknown, expected: unknown): void {
  if (value !== expected) throw new Error(`expected ${String(expected)}`)
}

function nonEmpty(value: unknown, name: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${name} must be a non-empty string`)
  }
  return value
}

function matches(value: unknown, pattern: RegExp, name: string): string {
  const text = nonEmpty(value, name)
  if (!pattern.test(text)) throw new Error(`${name} has an invalid format`)
  return text
}

function nonNegativeInteger(value: unknown, name: string): number {
  if (!Number.isSafeInteger(value) || Number(value) < 0) {
    throw new Error(`${name} must be a non-negative integer`)
  }
  return Number(value)
}

function nullableYear(value: unknown, name: string): void {
  if (value !== null && (!Number.isInteger(value) || Number(value) < 1600 || Number(value) > 2026)) {
    throw new Error(`${name} must be a plausible year or null`)
  }
}

function nullableString(value: unknown, name: string): void {
  if (value !== null) nonEmpty(value, name)
}

function coordinatePair(value: unknown, name: string): void {
  if (
    !Array.isArray(value) ||
    value.length !== 2 ||
    typeof value[0] !== 'number' ||
    typeof value[1] !== 'number' ||
    !Number.isFinite(value[0]) ||
    !Number.isFinite(value[1]) ||
    value[0] < -180 ||
    value[0] > 180 ||
    value[1] < -90 ||
    value[1] > 90
  ) {
    throw new Error(`${name} must be a WGS84 coordinate pair`)
  }
}

export const submittedMapSnapshot = parseSubmittedMapSnapshot(rawSubmittedMap)
