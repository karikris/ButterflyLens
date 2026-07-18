import { describe, expect, it } from 'vitest'

import submittedSpeciesCatalogueJson from './submittedSpeciesCatalogue.json'
import {
  parseSpeciesCatalogue,
  submittedSpeciesCatalogue,
} from './speciesCatalogueModel'

describe('submitted species catalogue model', () => {
  it('accepts the complete authoritative submitted projection', () => {
    expect(submittedSpeciesCatalogue.speciesCount).toBe(463)
    expect(submittedSpeciesCatalogue.species).toHaveLength(463)
    expect(submittedSpeciesCatalogue.states.scientificClaimAllowed).toBe(false)
    expect(submittedSpeciesCatalogue.states.yoloe).toBe('unfinished')
    expect(submittedSpeciesCatalogue.states.bioclip).toBe('unfinished')
  })

  it('fails closed if a missing ALA count is converted to zero', () => {
    const invalid = structuredClone(submittedSpeciesCatalogueJson) as any
    invalid.alaOccurrenceBoundary.displayedOccurrenceCount = 0
    expect(() => parseSpeciesCatalogue(invalid)).toThrow(/expected null/u)
  })

  it('rejects model or human evidence that was not run', () => {
    const invalid = structuredClone(submittedSpeciesCatalogueJson)
    invalid.species[0].referenceCoverage.humanVerifiedCount = 1
    expect(() => parseSpeciesCatalogue(invalid)).toThrow(/expected 0/u)

    const wrongState = structuredClone(submittedSpeciesCatalogueJson)
    wrongState.states.yoloe = 'complete'
    expect(() => parseSpeciesCatalogue(wrongState)).toThrow(/expected unfinished/u)
  })

  it('rejects provider identifiers that bypass an unresolved crosswalk', () => {
    const invalid = structuredClone(submittedSpeciesCatalogueJson)
    const unresolved = invalid.species.find((entry) =>
      entry.crosswalk.providers.some((provider) => provider.state !== 'matched'),
    )
    expect(unresolved).toBeDefined()
    const provider = unresolved!.crosswalk.providers.find(
      (candidate) => candidate.state !== 'matched',
    )!
    provider.identifier = 'fabricated-provider-id'
    expect(() => parseSpeciesCatalogue(invalid)).toThrow(/identifier/u)
  })
})
