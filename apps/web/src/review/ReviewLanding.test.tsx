import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ReviewLanding } from './ReviewLanding'
import type { ReviewDisclosure } from './blindReviewModel'
import {
  submittedReviewItem,
  type ReviewLandingItem,
} from './reviewLandingModel'

describe('review-first landing experience', () => {
  it('shows every required review control and keeps evidence claims gated', () => {
    render(<ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />)

    expect(
      screen.getByRole('heading', {
        name: 'One careful look can strengthen the record.',
      }),
    ).toBeInTheDocument()
    expect(screen.getByText('image awaiting review')).toBeInTheDocument()
    expect(
      screen.getByRole('img', { name: 'Rights-cleared butterfly review fixture' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Image by Jeevan Jose/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Wikimedia Commons source' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CC BY-SA 4.0' })).toHaveAttribute(
      'href',
      'https://creativecommons.org/licenses/by-sa/4.0/',
    )

    for (const decision of ['Yes', 'No', 'Can’t tell']) {
      expect(screen.getByRole('button', { name: decision })).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: 'Can’t view' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled()
    expect(screen.getByRole('textbox', { name: /Comment/ })).toBeEnabled()
    expect(screen.getByRole('textbox', { name: /Alternative taxon/ })).toBeDisabled()
    expect(screen.getByRole('heading', { name: 'Australia' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Draft review' })).toBeInTheDocument()

    expect(
      screen.getByText(/model labels, model scores.*are hidden/i),
    ).toBeInTheDocument()
    expect(screen.queryByRole('meter')).not.toBeInTheDocument()
    expect(screen.getByText('Majority vote')).toBeInTheDocument()
    expect(screen.queryByText(/majority says/i)).not.toBeInTheDocument()
    expect(screen.getByText(/does not submit or claim a stored review/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', {
        name: 'Lock draft decision and reveal permitted context',
      }),
    ).toBeDisabled()
  })

  it('updates the visible contribution without claiming persistence', () => {
    render(<ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />)

    fireEvent.click(screen.getByRole('button', { name: 'Can’t view' }))
    fireEvent.change(screen.getByRole('textbox', { name: /Comment/ }), {
      target: { value: 'Media failed to open.' },
    })

    expect(screen.getAllByText('Can’t view')).toHaveLength(2)
    expect(screen.getAllByText('Media failed to open.')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Can’t view' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('permits alternative taxa only for a qualified reviewer', () => {
    render(<ReviewLanding item={submittedReviewItem} qualifiedReviewer />)

    const alternative = screen.getByRole('textbox', { name: /Alternative taxon/ })
    expect(alternative).toBeEnabled()
    fireEvent.change(alternative, { target: { value: 'Papilionidae' } })
    expect(screen.getByText('Papilionidae')).toBeInTheDocument()
  })

  it('enables scientific choices only after verified media is displayed', () => {
    render(<ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />)

    const image = screen.getByRole('img', {
      name: 'Rights-cleared butterfly review fixture',
    })
    expect(screen.getByRole('button', { name: 'Yes' })).toBeDisabled()
    fireEvent.load(image)
    expect(screen.getByRole('button', { name: 'Yes' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'No' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Can’t tell' })).toBeEnabled()
  })

  it('fails closed when review media is unavailable', () => {
    const unavailableItem: ReviewLandingItem = {
      ...submittedReviewItem,
      itemId: 'unavailable-review-item',
      media: {
        state: 'unavailable',
        reason: 'The integrity-checked media is unavailable.',
      },
    }
    render(<ReviewLanding item={unavailableItem} qualifiedReviewer={false} />)

    expect(
      screen.getByRole('img', { name: 'Review image unavailable' }),
    ).toBeInTheDocument()
    for (const decision of ['Yes', 'No', 'Can’t tell']) {
      expect(screen.getByRole('button', { name: decision })).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: 'Can’t view' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Skip' })).toBeEnabled()
  })

  it('reveals allowlisted context only after locking a decision', () => {
    const disclosure: ReviewDisclosure = {
      state: 'available',
      reason: 'Synthetic post-decision context for the component test.',
      modelLabel: 'sentinel-model-label',
      modelScoreBand: 'sentinel-score-band',
      flickrQueryTerm: 'sentinel-query-term',
      sourceCommentExcerpt: 'sentinel-source-comment',
      peerSummary: { decisive: 3, yes: 2, no: 1, uncertain: 0 },
      scientificClaimAllowed: false,
    }
    render(
      <ReviewLanding
        item={submittedReviewItem}
        qualifiedReviewer={false}
        disclosure={disclosure}
      />,
    )

    for (const hiddenValue of [
      'sentinel-model-label',
      'sentinel-score-band',
      'sentinel-query-term',
      'sentinel-source-comment',
    ]) {
      expect(screen.queryByText(hiddenValue)).not.toBeInTheDocument()
    }

    const image = screen.getByRole('img', {
      name: 'Rights-cleared butterfly review fixture',
    })
    fireEvent.load(image)
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    fireEvent.click(
      screen.getByRole('button', {
        name: 'Lock draft decision and reveal permitted context',
      }),
    )

    for (const revealedValue of [
      'sentinel-model-label',
      'sentinel-score-band',
      'sentinel-query-term',
      'sentinel-source-comment',
    ]) {
      expect(screen.getByText(revealedValue)).toBeInTheDocument()
    }
    expect(screen.getByText(/3 decisive · 2 yes · 1 no · 0 uncertain/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Wikimedia Commons source' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'No' })).toBeDisabled()
    expect(screen.getByRole('textbox', { name: /Comment/ })).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: 'Start a new blind draft' }))
    expect(screen.queryByText('sentinel-model-label')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Yes' })).toBeEnabled()
  })
})
