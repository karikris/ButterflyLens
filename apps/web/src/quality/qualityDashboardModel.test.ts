import { describe, expect, it } from 'vitest'

import {
  parseQualityDashboardSnapshot,
  submittedQualityDashboard,
} from './qualityDashboardModel'

describe('quality dashboard snapshot parser', () => {
  it('rejects a decisive count above the reviewed sample', () => {
    const value = { ...submittedQualityDashboard, decisiveReviews: 1 }

    expect(() => parseQualityDashboardSnapshot(value)).toThrow(
      'decisiveReviews cannot exceed reviewedSample',
    )
  })

  it('rejects an unavailable snapshot carrying a fake precision', () => {
    const value = {
      ...submittedQualityDashboard,
      precision: { ...submittedQualityDashboard.precision, estimate: 0 },
    }

    expect(() => parseQualityDashboardSnapshot(value)).toThrow(
      'unavailable state must withhold estimates',
    )
  })

  it('rejects dashboard status that contradicts estimate availability', () => {
    const value = { ...submittedQualityDashboard, status: 'estimated' }

    expect(() => parseQualityDashboardSnapshot(value)).toThrow(
      'dashboard status must match precision availability',
    )
  })

  it('rejects model votes and scientific claim authority', () => {
    const modelVote = { ...submittedQualityDashboard, modelVoteIncluded: true }
    expect(() => parseQualityDashboardSnapshot(modelVote)).toThrow(
      'violates its scientific boundary',
    )

    const scientificClaim = {
      ...submittedQualityDashboard,
      scientificClaimAllowed: true,
    }
    expect(() => parseQualityDashboardSnapshot(scientificClaim)).toThrow(
      'violates its scientific boundary',
    )
  })
})
