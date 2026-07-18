import { describe, expect, it } from 'vitest'

import {
  parseContributorImpactSnapshot,
  submittedContributorImpact,
} from './contributorImpactModel'

function availableSnapshot() {
  return {
    ...submittedContributorImpact,
    snapshotMode: 'live',
    snapshotState: 'available',
    snapshotStateReason: null,
    metrics: Object.fromEntries(
      Object.entries(submittedContributorImpact.metrics).map(([key], index) => [
        key,
        { state: 'available', value: index + 1, reason: null },
      ]),
    ),
    sourceEvidenceFingerprint: 'a'.repeat(64),
    projectionFingerprint: 'b'.repeat(64),
    calculatedAt: '2026-07-18T05:30:00Z',
  }
}

describe('contributor impact parser', () => {
  it('keeps the submitted replay unavailable rather than inventing zeros', () => {
    expect(submittedContributorImpact.snapshotState).toBe('unavailable')
    expect(
      Object.values(submittedContributorImpact.metrics).every(
        (metric) => metric.value === null,
      ),
    ).toBe(true)
  })

  it('accepts a complete evidence-backed private snapshot', () => {
    const parsed = parseContributorImpactSnapshot(availableSnapshot())
    expect(parsed.metrics.reviewedImages.value).toBe(1)
    expect(parsed.visibility).toBe('self_only')
  })

  it('rejects rankings, speed metrics, and scientific authority', () => {
    for (const change of [
      { rankingPermitted: true },
      { speedMetricPermitted: true },
      { scientificClaimAllowed: true },
    ]) {
      expect(() =>
        parseContributorImpactSnapshot({ ...availableSnapshot(), ...change }),
      ).toThrow('cannot rank, time, or create authority')
    }
  })

  it('rejects unexpected fields and fake unavailable totals', () => {
    expect(() =>
      parseContributorImpactSnapshot({ ...submittedContributorImpact, rank: 1 }),
    ).toThrow('exact public shape')
    expect(() =>
      parseContributorImpactSnapshot({
        ...submittedContributorImpact,
        metrics: {
          ...submittedContributorImpact.metrics,
          reviewedImages: { state: 'available', value: 0, reason: null },
        },
      }),
    ).toThrow('withhold every total')
  })
})
