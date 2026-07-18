import submittedSpeciesCatalogueJson from './submittedSpeciesCatalogue.json'

export type ProviderMatchState = 'matched' | 'conflict' | 'unmatched'
export type CrosswalkStatus = 'complete' | 'partial' | 'unresolved'
export type ReferenceCoverageStatus =
  | 'provisional_decode_only'
  | 'no_automated_gate_eligible_media'
  | 'no_candidate_media'

export interface SpeciesNameAssertion {
  readonly name: string
  readonly assertionId: string
  readonly reviewState: 'source_assertion_unreviewed'
  readonly sourceProvider: string
  readonly sourceDataset?: string
  readonly trustTier?: string
  readonly queryEligible?: boolean
  readonly homonymRisk?: string
  readonly providerNameId?: string | null
}

export interface SpeciesProviderMatch {
  readonly provider: 'ala' | 'gbif' | 'inaturalist'
  readonly label: string
  readonly state: ProviderMatchState
  readonly identifier: string | null
  readonly matchedName: string | null
  readonly matchedRank: string | null
  readonly reasons: readonly string[]
}

export interface SpeciesOpenConflict {
  readonly conflictId: string
  readonly provider: string
  readonly conflictType: string
  readonly reasons: readonly string[]
  readonly resolutionStatus: 'open'
}

export interface SpeciesCatalogueEntry {
  readonly key: string
  readonly slug: string
  readonly acceptedScientificName: string
  readonly queryScientificName: string
  readonly sourceTitle: string
  readonly sourceUrl: string
  readonly sourceRetrievedAt: string
  readonly hierarchy: Readonly<
    Record<
      string,
      { readonly key: string; readonly acceptedScientificName: string }
    >
  >
  readonly englishNames: readonly SpeciesNameAssertion[]
  readonly scientificSynonyms: readonly SpeciesNameAssertion[]
  readonly crosswalk: {
    readonly status: CrosswalkStatus
    readonly queryNameNormalization: string
    readonly providers: readonly SpeciesProviderMatch[]
    readonly openConflicts: readonly SpeciesOpenConflict[]
  }
  readonly referenceCoverage: {
    readonly status: ReferenceCoverageStatus
    readonly candidateMediaCount: number
    readonly automatedGateEligibleCount: number
    readonly selectedCount: number
    readonly validDecodeCount: number
    readonly humanVerifiedCount: 0
    readonly releaseStatus: string
    readonly qualityFlags: readonly string[]
    readonly evidenceFingerprint: string
  }
}

export interface SpeciesCatalogue {
  readonly schemaVersion: 'butterflylens-public-species-catalogue:v1.0.0'
  readonly catalogueId: string
  readonly catalogueFingerprint: string
  readonly generatedAt: string
  readonly speciesCount: number
  readonly authoritativeBaseline: 'ButterflyLens rebuilt baseline'
  readonly states: {
    readonly taxonomy: 'accepted_authority_snapshot'
    readonly englishNames: 'source_assertions_unreviewed'
    readonly firstNationsNames: 'empty_no_authorized_source'
    readonly alaOccurrenceEvidence: 'withheld_pending_dataset_rights_resolution'
    readonly referenceEvidence: 'published_unfinished_models_no_human_review'
    readonly humanReview: 'absent'
    readonly yoloe: 'unfinished'
    readonly bioclip: 'unfinished'
    readonly scientificClaimAllowed: false
  }
  readonly alaOccurrenceBoundary: {
    readonly snapshotId: string
    readonly snapshotFingerprint: string
    readonly releaseState: 'blocked_pending_dataset_rights_resolution'
    readonly rightsReviewRequiredDatasetUids: readonly string[]
    readonly displayedOccurrenceCount: null
    readonly absenceInferencePermitted: false
    readonly reason: string
  }
  readonly firstNationsNameBoundary: {
    readonly approvedCount: 0
    readonly pendingCount: 0
    readonly reason: string
  }
  readonly referenceBoundary: {
    readonly status: 'published_unfinished_models_no_human_review'
    readonly humanVerifiedCount: 0
    readonly yoloeState: 'blocked_not_executed'
    readonly bioclipState: 'skipped_unfinished_by_goal_instruction'
    readonly qualityScoreComputed: false
    readonly releaseReady: false
    readonly reason: string
  }
  readonly sources: readonly {
    readonly path: string
    readonly physicalSha256: string
    readonly licence: string
    readonly attribution: string
  }[]
  readonly sourceFingerprints: Readonly<Record<string, string>>
  readonly species: readonly SpeciesCatalogueEntry[]
}

const SHA256 = /^(?:sha256:)?[0-9a-f]{64}$/u
const SPECIES_KEY = /^bltx:v1:[0-9a-f]{24}$/u
const PROVIDER_IDS = ['ala', 'gbif', 'inaturalist'] as const

export function parseSpeciesCatalogue(value: unknown): SpeciesCatalogue {
  if (!isRecord(value)) throw new Error('species catalogue must be an object')
  exact(value.schemaVersion, 'butterflylens-public-species-catalogue:v1.0.0')
  exact(value.authoritativeBaseline, 'ButterflyLens rebuilt baseline')
  nonEmpty(value.catalogueId, 'catalogueId')
  matches(value.catalogueFingerprint, SHA256, 'catalogueFingerprint')
  nonEmpty(value.generatedAt, 'generatedAt')

  const states = record(value.states, 'states')
  exact(states.taxonomy, 'accepted_authority_snapshot')
  exact(states.englishNames, 'source_assertions_unreviewed')
  exact(states.firstNationsNames, 'empty_no_authorized_source')
  exact(states.alaOccurrenceEvidence, 'withheld_pending_dataset_rights_resolution')
  exact(states.referenceEvidence, 'published_unfinished_models_no_human_review')
  exact(states.humanReview, 'absent')
  exact(states.yoloe, 'unfinished')
  exact(states.bioclip, 'unfinished')
  exact(states.scientificClaimAllowed, false)

  const ala = record(value.alaOccurrenceBoundary, 'alaOccurrenceBoundary')
  nonEmpty(ala.snapshotId, 'alaOccurrenceBoundary.snapshotId')
  matches(ala.snapshotFingerprint, SHA256, 'alaOccurrenceBoundary.snapshotFingerprint')
  exact(ala.releaseState, 'blocked_pending_dataset_rights_resolution')
  exact(ala.displayedOccurrenceCount, null)
  exact(ala.absenceInferencePermitted, false)
  nonEmpty(ala.reason, 'alaOccurrenceBoundary.reason')
  stringArray(ala.rightsReviewRequiredDatasetUids, 'rightsReviewRequiredDatasetUids', true)

  const firstNations = record(
    value.firstNationsNameBoundary,
    'firstNationsNameBoundary',
  )
  exact(firstNations.approvedCount, 0)
  exact(firstNations.pendingCount, 0)
  nonEmpty(firstNations.reason, 'firstNationsNameBoundary.reason')

  const reference = record(value.referenceBoundary, 'referenceBoundary')
  exact(reference.status, 'published_unfinished_models_no_human_review')
  exact(reference.humanVerifiedCount, 0)
  exact(reference.yoloeState, 'blocked_not_executed')
  exact(reference.bioclipState, 'skipped_unfinished_by_goal_instruction')
  exact(reference.qualityScoreComputed, false)
  exact(reference.releaseReady, false)
  nonEmpty(reference.reason, 'referenceBoundary.reason')

  if (!Array.isArray(value.sources) || value.sources.length === 0) {
    throw new Error('sources must be a non-empty array')
  }
  for (const source of value.sources) {
    const row = record(source, 'source')
    nonEmpty(row.path, 'source.path')
    matches(row.physicalSha256, SHA256, 'source.physicalSha256')
    nonEmpty(row.licence, 'source.licence')
    nonEmpty(row.attribution, 'source.attribution')
  }
  const sourceFingerprints = record(value.sourceFingerprints, 'sourceFingerprints')
  for (const [name, fingerprint] of Object.entries(sourceFingerprints)) {
    nonEmpty(name, 'source fingerprint name')
    matches(fingerprint, SHA256, `sourceFingerprints.${name}`)
  }

  const speciesCount = integer(value.speciesCount, 'speciesCount')
  if (!Array.isArray(value.species) || value.species.length !== speciesCount) {
    throw new Error('species count does not match species array')
  }
  const keys = new Set<string>()
  const slugs = new Set<string>()
  for (const species of value.species) {
    validateSpecies(species, keys, slugs)
  }
  if (speciesCount !== 463) {
    throw new Error('submitted species catalogue must contain 463 accepted species')
  }
  return value as unknown as SpeciesCatalogue
}

function validateSpecies(
  value: unknown,
  keys: Set<string>,
  slugs: Set<string>,
): void {
  const species = record(value, 'species')
  const key = matches(species.key, SPECIES_KEY, 'species.key')
  const slug = nonEmpty(species.slug, 'species.slug')
  if (keys.has(key) || slugs.has(slug)) throw new Error('species key or slug is duplicated')
  keys.add(key)
  slugs.add(slug)
  for (const field of [
    'acceptedScientificName',
    'queryScientificName',
    'sourceTitle',
    'sourceUrl',
    'sourceRetrievedAt',
  ]) {
    nonEmpty(species[field], `species.${field}`)
  }

  const hierarchy = record(species.hierarchy, 'species.hierarchy')
  for (const rank of ['family', 'genus']) {
    const item = record(hierarchy[rank], `species.hierarchy.${rank}`)
    matches(item.key, SPECIES_KEY, `species.hierarchy.${rank}.key`)
    nonEmpty(
      item.acceptedScientificName,
      `species.hierarchy.${rank}.acceptedScientificName`,
    )
  }
  validateNames(species.englishNames, 'species.englishNames')
  validateNames(species.scientificSynonyms, 'species.scientificSynonyms')

  const crosswalk = record(species.crosswalk, 'species.crosswalk')
  if (!['complete', 'partial', 'unresolved'].includes(String(crosswalk.status))) {
    throw new Error('species.crosswalk.status is invalid')
  }
  nonEmpty(crosswalk.queryNameNormalization, 'queryNameNormalization')
  if (!Array.isArray(crosswalk.providers) || crosswalk.providers.length !== 3) {
    throw new Error('species crosswalk must contain exactly three providers')
  }
  const providers = new Set<string>()
  for (const providerValue of crosswalk.providers) {
    const provider = record(providerValue, 'provider match')
    if (!PROVIDER_IDS.includes(provider.provider as (typeof PROVIDER_IDS)[number])) {
      throw new Error('provider match has an unknown provider')
    }
    providers.add(provider.provider as string)
    if (!['matched', 'conflict', 'unmatched'].includes(String(provider.state))) {
      throw new Error('provider match state is invalid')
    }
    if ((provider.identifier !== null) !== (provider.state === 'matched')) {
      throw new Error('provider identifier must exist only for a matched provider')
    }
    if (provider.identifier !== null) nonEmpty(provider.identifier, 'provider.identifier')
    stringArray(provider.reasons, 'provider.reasons')
  }
  if (providers.size !== 3) throw new Error('provider matches are duplicated')
  if (!Array.isArray(crosswalk.openConflicts)) {
    throw new Error('openConflicts must be an array')
  }
  for (const conflictValue of crosswalk.openConflicts) {
    const conflict = record(conflictValue, 'open conflict')
    nonEmpty(conflict.conflictId, 'conflictId')
    nonEmpty(conflict.provider, 'conflict.provider')
    nonEmpty(conflict.conflictType, 'conflict.conflictType')
    exact(conflict.resolutionStatus, 'open')
    stringArray(conflict.reasons, 'conflict.reasons', true)
  }

  const coverage = record(species.referenceCoverage, 'referenceCoverage')
  if (
    ![
      'provisional_decode_only',
      'no_automated_gate_eligible_media',
      'no_candidate_media',
    ].includes(String(coverage.status))
  ) {
    throw new Error('reference coverage status is invalid')
  }
  const candidate = integer(coverage.candidateMediaCount, 'candidateMediaCount')
  const eligible = integer(
    coverage.automatedGateEligibleCount,
    'automatedGateEligibleCount',
  )
  const selected = integer(coverage.selectedCount, 'selectedCount')
  const decoded = integer(coverage.validDecodeCount, 'validDecodeCount')
  if (eligible > candidate || selected > eligible || decoded > selected) {
    throw new Error('reference coverage counts are inconsistent')
  }
  exact(coverage.humanVerifiedCount, 0)
  nonEmpty(coverage.releaseStatus, 'referenceCoverage.releaseStatus')
  matches(
    coverage.evidenceFingerprint,
    SHA256,
    'referenceCoverage.evidenceFingerprint',
  )
  stringArray(coverage.qualityFlags, 'referenceCoverage.qualityFlags', true)
}

function validateNames(value: unknown, field: string): void {
  if (!Array.isArray(value)) throw new Error(`${field} must be an array`)
  for (const item of value) {
    const name = record(item, field)
    nonEmpty(name.name, `${field}.name`)
    nonEmpty(name.assertionId, `${field}.assertionId`)
    exact(name.reviewState, 'source_assertion_unreviewed')
    nonEmpty(name.sourceProvider, `${field}.sourceProvider`)
  }
}

function record(value: unknown, field: string): Record<string, unknown> {
  if (!isRecord(value)) throw new Error(`${field} must be an object`)
  return value
}

function nonEmpty(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${field} must be a non-empty string`)
  }
  return value
}

function matches(value: unknown, pattern: RegExp, field: string): string {
  const string = nonEmpty(value, field)
  if (!pattern.test(string)) throw new Error(`${field} has an invalid format`)
  return string
}

function integer(value: unknown, field: string): number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 0) {
    throw new Error(`${field} must be a non-negative integer`)
  }
  return value
}

function exact(value: unknown, expected: unknown): void {
  if (value !== expected) throw new Error(`expected ${String(expected)}`)
}

function stringArray(value: unknown, field: string, nonEmptyArray = false): void {
  if (
    !Array.isArray(value) ||
    (nonEmptyArray && value.length === 0) ||
    value.some((item) => typeof item !== 'string' || item.trim() === '')
  ) {
    throw new Error(`${field} must be ${nonEmptyArray ? 'a non-empty' : 'an'} string array`)
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export const submittedSpeciesCatalogue = parseSpeciesCatalogue(
  submittedSpeciesCatalogueJson,
)
