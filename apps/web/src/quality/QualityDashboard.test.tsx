import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { QualityDashboard } from './QualityDashboard'
import {
  submittedQualityDashboard,
  type QualityDashboardSnapshot,
} from './qualityDashboardModel'

describe('community quality dashboard', () => {
  it('shows every requested field and withholds unsupported estimates', () => {
    render(<QualityDashboard snapshot={submittedQualityDashboard} />)

    expect(
      screen.getByRole('heading', { name: 'Evidence strength, without guesswork.' }),
    ).toBeVisible()
    expect(metric('Reviewed sample')).toHaveTextContent('0')
    expect(metric('Decisive reviews')).toHaveTextContent('0')
    expect(metric('Precision estimate')).toHaveTextContent('Unavailable')
    expect(metric('Confidence interval')).toHaveTextContent('Unavailable')
    expect(metric('Reviewer agreement')).toHaveTextContent('Unavailable')
    expect(metric('Species quality')).toHaveTextContent('Unavailable')
    expect(screen.getByText(/workflow count—not 0% precision/i)).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Flags remain visible' })).toBeVisible()
    expect(screen.getByText('Human review absent')).toBeVisible()
    expect(screen.getAllByText('YOLOE unfinished')).toHaveLength(2)
    expect(screen.getAllByText('BioCLIP unfinished')).toHaveLength(2)
    expect(screen.getByRole('heading', { name: 'Release blockers' })).toBeVisible()
    expect(screen.getByText('Human reference review absent')).toBeVisible()
    expect(screen.queryByRole('meter')).not.toBeInTheDocument()
  })

  it('publishes exact source fingerprints and the authoritative baseline', () => {
    render(<QualityDashboard snapshot={submittedQualityDashboard} />)

    screen.getByText('Evidence, method, and provenance').click()
    expect(
      screen.getByText(
        '4cfc41de9908dbe7f0997e5dc59fd964606d3127d5af24e660868eabc7367d91',
      ),
    ).toBeVisible()
    expect(
      screen.getByText(
        '6f23e1ec04d0297797439973aea98d9b45bc989ce9ec61db35064824621bdc3d',
      ),
    ).toBeVisible()
    expect(screen.getByText('ButterflyLens rebuilt baseline')).toBeVisible()
    expect(screen.getByText(/model votes are excluded/i)).toBeVisible()
  })

  it('formats an attached representative estimate without changing its labels', () => {
    const estimated: QualityDashboardSnapshot = {
      ...submittedQualityDashboard,
      status: 'estimated',
      reviewedSample: 80,
      decisiveReviews: 72,
      precision: {
        availability: 'estimated',
        estimate: 0.825,
        interval: { lower: 0.75, upper: 0.89, level: 0.95 },
        effectiveSampleSize: 58.4,
        reason: null,
      },
      reviewerAgreement: {
        availability: 'estimated',
        pairwiseAgreement: 0.78,
        nominalAlpha: 0.67,
        overlappingItems: 32,
        reason: null,
      },
      speciesQuality: {
        availability: 'estimated',
        estimate: 0.76,
        auditedSpecies: 20,
        acceptedSpecies: 463,
        reason: null,
      },
      provenance: {
        ...submittedQualityDashboard.provenance,
        qualitySnapshotFingerprint: 'a'.repeat(64),
      },
    }
    render(<QualityDashboard snapshot={estimated} />)

    expect(metric('Reviewed sample')).toHaveTextContent('80')
    expect(metric('Decisive reviews')).toHaveTextContent('72')
    expect(metric('Precision estimate')).toHaveTextContent('82.5%')
    expect(metric('Confidence interval')).toHaveTextContent('75% – 89%')
    expect(metric('Reviewer agreement')).toHaveTextContent('78%')
    expect(metric('Species quality')).toHaveTextContent('76%')
  })
})

function metric(label: string): HTMLElement {
  const summary = screen.getByLabelText('Quality summary')
  const article = within(summary).getByText(label).closest('article')
  expect(article).not.toBeNull()
  return article!
}
