import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { SubmittedEvidenceMap } from './SubmittedEvidenceMap'
import { submittedMapSnapshot } from './submittedMapModel'

describe('submitted evidence map', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network disabled'))))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders an offline national ALA heatmap with explicit unavailable layers', () => {
    render(<SubmittedEvidenceMap />)

    expect(
      screen.getByRole('heading', { name: 'Where the baseline has evidence' }),
    ).toBeVisible()
    expect(
      screen.getByRole('img', {
        name: 'Australia evidence heatmap with 630 H3 aggregate cells',
      }),
    ).toHaveAttribute('data-webgl', 'not-used')
    expect(screen.getByText('213,310')).toBeVisible()
    expect(screen.getByText('16,753')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Submitted' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    expect(screen.getByRole('button', { name: 'Live unavailable' })).toBeDisabled()
    expect(screen.getByRole('checkbox', { name: /ALA baseline · blue filled cells/ })).toBeChecked()
    expect(
      screen.getByRole('checkbox', { name: /Flickr candidate · amber diamonds/ }),
    ).toBeDisabled()
    expect(screen.getByText(/still fetching Flickr metadata/)).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('synchronizes an H3 table choice with evidence details without coordinates', () => {
    render(<SubmittedEvidenceMap />)
    const next = [...submittedMapSnapshot.cells].sort(
      (left, right) => right.count - left.count,
    )[1]

    fireEvent.click(screen.getByText('Open the synchronized H3 exact-count table'))
    fireEvent.click(
      screen.getByRole('button', { name: `Inspect H3 ${next.cellId}` }),
    )

    const detail = screen.getByRole('heading', { name: next.cellId }).closest('aside')
    expect(detail).not.toBeNull()
    expect(within(detail!).getByText(next.count.toLocaleString('en-AU'))).toBeVisible()
    expect(within(detail!).getByText('Unavailable—not zero')).toBeVisible()
    expect(within(detail!).getByText(/Coordinates are never included here/)).toBeVisible()
    expect(screen.getByText(`H3 ${next.cellId}: ${next.count.toLocaleString('en-AU')} ALA baseline records`)).toBeInTheDocument()
  })

  it('drills through contextual scopes with exact accessible tables', () => {
    render(<SubmittedEvidenceMap />)

    fireEvent.click(screen.getByRole('button', { name: 'IBRA v7' }))
    const ibra = submittedMapSnapshot.scopes.ibra[0]
    fireEvent.change(screen.getByRole('searchbox', { name: 'Filter IBRA v7' }), {
      target: { value: ibra.label },
    })
    expect(
      screen.getByText(`Exact IBRA v7 counts; 1 rows`),
    ).toBeVisible()
    expect(screen.getAllByText(ibra.label).length).toBeGreaterThan(0)

    fireEvent.click(screen.getByRole('button', { name: 'LGA approximation' }))
    expect(screen.getByText(/statistical approximation, not a legal boundary/)).toBeVisible()

    fireEvent.click(screen.getByRole('button', { name: 'H3 coarse cells' }))
    const largest = [...submittedMapSnapshot.scopes.h3].sort(
      (left, right) => right.count - left.count,
    )[0]
    expect(
      screen.getByRole('heading', { level: 3, name: largest.label }),
    ).toBeVisible()
    expect(
      screen.getByText('All 630 submitted H3 cells and exact ALA baseline counts'),
    ).toBeInTheDocument()
  }, 15_000)

  it('can hide the visual ALA layer while retaining the exact table', () => {
    render(<SubmittedEvidenceMap />)
    const layer = screen.getByRole('checkbox', { name: /ALA baseline · blue filled cells/ })
    fireEvent.click(layer)
    expect(layer).not.toBeChecked()
    expect(
      screen.getByText('Open the synchronized H3 exact-count table'),
    ).toBeVisible()
    expect(fetch).not.toHaveBeenCalled()
  })
})
