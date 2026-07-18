import { describe, expect, it } from 'vitest'

import {
  parseSubmittedMapSnapshot,
  submittedMapSnapshot,
} from './submittedMapModel'

describe('submitted map model', () => {
  it('accepts the exact rights-screened submitted projection', () => {
    expect(submittedMapSnapshot.mode).toBe('submitted')
    expect(submittedMapSnapshot.counts).toEqual({
      authoritativeBaselineSelected: 236_897,
      mapCells: 630,
      mapEligible: 213_310,
      rightsExcludedMapEligible: 16_717,
      rightsExcludedSelected: 16_753,
      rightsScreenedSelected: 220_144,
    })
    expect(submittedMapSnapshot.cells).toHaveLength(630)
    expect(submittedMapSnapshot.scopes.state).toHaveLength(9)
    expect(submittedMapSnapshot.scopes.ibra).toHaveLength(87)
    expect(submittedMapSnapshot.scopes.lga).toHaveLength(532)
    expect(submittedMapSnapshot.layers.flickrCandidate.status).toBe('unavailable')
    expect(submittedMapSnapshot.policies.occurrenceCoordinatesPublished).toBe(false)
    expect(submittedMapSnapshot.policies.absenceInferencePermitted).toBe(false)
  })

  it('rejects a fabricated available Flickr layer', () => {
    const broken = structuredClone(submittedMapSnapshot) as unknown as {
      layers: {
        flickrCandidate: { status: string; reason: string | null }
      }
    }
    broken.layers.flickrCandidate.status = 'available'
    broken.layers.flickrCandidate.reason = null
    expect(() => parseSubmittedMapSnapshot(broken)).toThrow(
      'submitted map layer availability is invalid',
    )
  })

  it('rejects drifted rights totals and blocked dataset leakage', () => {
    const drifted = structuredClone(submittedMapSnapshot) as unknown as {
      counts: { rightsExcludedSelected: number }
    }
    drifted.counts.rightsExcludedSelected -= 1
    expect(() => parseSubmittedMapSnapshot(drifted)).toThrow(
      'map count boundary does not reconcile',
    )

    const leaked = structuredClone(submittedMapSnapshot) as unknown as {
      cells: { records: { dataResourceUid: string }[] }[]
    }
    leaked.cells[0].records[0].dataResourceUid = 'dr1097'
    expect(() => parseSubmittedMapSnapshot(leaked)).toThrow(
      'blocked dataset leaked into map',
    )
  })

  it('retains unavailable values as reasons rather than zeros', () => {
    for (const layer of [
      submittedMapSnapshot.layers.flickrCandidate,
      submittedMapSnapshot.layers.communityReviewed,
      submittedMapSnapshot.layers.releaseReady,
    ]) {
      expect(layer.status).toBe('unavailable')
      expect(layer.reason).toBeTruthy()
    }
    expect(submittedMapSnapshot.layers.flickrCandidate.reason).toContain(
      'still fetching Flickr metadata',
    )
  })
})
