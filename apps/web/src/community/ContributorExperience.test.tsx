import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ContributorExperience } from './ContributorExperience'
import {
  parseContributorImpactSnapshot,
  submittedContributorImpact,
} from './contributorImpactModel'

describe('contributor experience', () => {
  it('celebrates every required evidence contribution without fabricated totals', () => {
    render(<ContributorExperience snapshot={submittedContributorImpact} />)

    expect(screen.getByRole('heading', { name: 'Careful work leaves a meaningful trace.' })).toBeInTheDocument()
    for (const label of [
      'Reviewed images', 'Resolved conflicts', 'Species helped', 'Regions helped',
      'Control coverage', 'Expert contribution',
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByText(/No contribution totals are claimed/)).toBeInTheDocument()
    expect(
      screen.getAllByText('—', { selector: '.contributor-metrics strong' }),
    ).toHaveLength(6)
  })

  it('renders evidence-backed counts without a speed ranking', () => {
    const snapshot = parseContributorImpactSnapshot({
      ...submittedContributorImpact,
      snapshotMode: 'live',
      snapshotState: 'available',
      snapshotStateReason: null,
      metrics: {
        reviewedImages: { state: 'available', value: 128, reason: null },
        resolvedConflicts: { state: 'available', value: 4, reason: null },
        speciesHelped: { state: 'available', value: 19, reason: null },
        regionsHelped: { state: 'available', value: 7, reason: null },
        controlCoverage: { state: 'available', value: 12, reason: null },
        expertContribution: { state: 'available', value: 5, reason: null },
      },
      sourceEvidenceFingerprint: 'a'.repeat(64),
      projectionFingerprint: 'b'.repeat(64),
      calculatedAt: '2026-07-18T05:30:00Z',
    })
    render(<ContributorExperience snapshot={snapshot} />)

    for (const value of ['128', '4', '19', '7', '12', '5']) {
      expect(screen.getByText(value)).toBeInTheDocument()
    }
    expect(screen.getByText('Evidence, not speed.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText(/fastest|position|ranked #/i)).not.toBeInTheDocument()
  })
})
