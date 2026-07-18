import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { EvidenceNotice, StateBadge } from './EvidencePrimitives'

describe('ButterflyLens evidence primitives', () => {
  it('keeps every evidence state legible without relying on colour', () => {
    render(
      <div>
        <StateBadge state="submitted">Submitted replay</StateBadge>
        <StateBadge state="verified">Verified evidence</StateBadge>
        <StateBadge state="caution">Review required</StateBadge>
        <StateBadge state="unavailable">Estimate unavailable</StateBadge>
        <StateBadge state="unfinished">Model unfinished</StateBadge>
        <StateBadge state="critical">Release blocked</StateBadge>
      </div>,
    )

    for (const label of [
      'Submitted replay',
      'Verified evidence',
      'Review required',
      'Estimate unavailable',
      'Model unfinished',
      'Release blocked',
    ]) {
      expect(screen.getByText(label)).toBeVisible()
    }
    expect(document.querySelectorAll('[aria-hidden="true"]')).toHaveLength(6)
  })

  it('announces dynamic boundaries only when requested', () => {
    const { rerender } = render(
      <EvidenceNotice title="Independent review">
        Model context is withheld.
      </EvidenceNotice>,
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    rerender(
      <EvidenceNotice title="Quality estimate" tone="caution" announce>
        Representative evidence is unavailable.
      </EvidenceNotice>,
    )
    expect(screen.getByRole('status')).toHaveTextContent(
      'Quality estimate: Representative evidence is unavailable.',
    )
  })
})
