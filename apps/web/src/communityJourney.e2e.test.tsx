import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'


describe('credential-free community judge journey', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('covers landing, review, map, species, pipeline, quality, and export', async () => {
    const network = vi.fn(() => {
      throw new Error('the submitted judge journey must not use fetch')
    })
    vi.stubGlobal('fetch', network)

    render(<App />)

    window.location.hash = '#explore'
    fireEvent(window, new HashChangeEvent('hashchange'))

    // 1. Open the landing page.
    expect(
      screen.getByRole('heading', {
        level: 1,
        name: 'Look closer. Strengthen what we know.',
      }),
    ).toBeVisible()
    const landing = within(requiredElement('#explore'))
    expect(landing.getByText('Credential-free submitted replay')).toBeVisible()
    expect(landing.getByText('ButterflyLens rebuilt baseline')).toBeVisible()
    expect(screen.getByText('Submitted replay')).toBeVisible()

    const map = within(requiredElement('.submitted-map'))
    expect(map.getByText('Map-eligible baseline')).toBeVisible()
    expect(map.getByText('213,310')).toBeVisible()
    expect(map.getByText('630')).toBeVisible()

    // 2. Review an integrity-checked image as a local blind draft.
    window.location.hash = '#verify'
    fireEvent(window, new HashChangeEvent('hashchange'))

    const review = requiredElement('#verify')
    const reviewView = within(review)
    const image = reviewView.getByRole('img', {
      name: 'Rights-cleared butterfly review fixture',
    })
    expect(reviewView.getByRole('button', { name: 'Can’t tell' })).toBeDisabled()
    fireEvent.load(image)
    fireEvent.click(reviewView.getByRole('button', { name: 'Can’t tell' }))
    fireEvent.change(reviewView.getByRole('textbox', { name: /Comment/ }), {
      target: { value: 'Visible evidence is insufficient for a decisive answer.' },
    })
    fireEvent.click(
      reviewView.getByRole('button', {
        name: 'Lock draft decision and reveal permitted context',
      }),
    )
    expect(
      reviewView.getByRole('heading', { name: 'Permitted context revealed' }),
    ).toBeVisible()
    expect(reviewView.getByText(/draft decision is now locked locally/i)).toBeVisible()
    expect(
      reviewView.getByText(/does not submit or claim a stored review/i),
    ).toBeVisible()
    expect(
      reviewView.getByRole('link', { name: 'Wikimedia Commons source' }),
    ).toBeVisible()

    // 3. Map outcome on Explore remains committed and rights-restricted.
    window.location.hash = '#explore'
    fireEvent(window, new HashChangeEvent('hashchange'))

    const returnMap = within(requiredElement('.submitted-map'))
    expect(returnMap.getByText('Map-eligible baseline')).toBeVisible()
    expect(returnMap.getByText('213,310')).toBeVisible()
    expect(returnMap.getByText('630')).toBeVisible()

    // 4. Inspect species, operations, and quality from the specialist surface.
    window.location.hash = '#species'
    fireEvent(window, new HashChangeEvent('hashchange'))

    const species = requiredElement('#species')
    const speciesView = within(species)
    fireEvent.change(
      speciesView.getByRole('searchbox', { name: 'Search species' }),
      { target: { value: 'Acraea andromacha' } },
    )
    expect(speciesView.getByText('1 species shown')).toBeVisible()
    fireEvent.click(
      speciesView.getByRole('button', {
        name: /Open species page for .*Acraea andromacha/u,
      }),
    )
    expect(
      speciesView.getByRole('heading', { name: 'Acraea andromacha' }),
    ).toBeVisible()
    expect(
      speciesView.getByRole('heading', {
        name: 'What the submitted artifacts support',
      }),
    ).toBeVisible()
    const verifiedMedia = speciesView.getByText('Human-verified media').closest('div')
    expect(verifiedMedia).not.toBeNull()
    expect(verifiedMedia).toHaveTextContent('0')
    expect(speciesView.getByText(/YOLOE and BioCLIP are unfinished/)).toBeVisible()

    const operations = requiredElement('#operations')
    const operationsView = within(operations)
    expect(
      operationsView.getByRole('img', {
        name: 'Submitted Australia evidence summary; public aggregate layer available',
      }),
    ).toBeVisible()
    expect(operationsView.getByText('Aggregate layer available')).toBeVisible()
    const lastMapRefresh = operationsView.getByText('Last map refresh').closest('li')
    expect(lastMapRefresh).not.toBeNull()
    expect(lastMapRefresh).toHaveTextContent('submitted')
    expect(lastMapRefresh).toHaveTextContent('2026-07-19T00:00:00Z')
    expect(lastMapRefresh).toHaveTextContent(/213,310 map-eligible rows/i)

    expect(operationsView.getByText('Worker status unavailable')).toBeVisible()
    expect(operationsView.getByText('Submitted fallback')).toBeVisible()
    expect(operationsView.getByText('Aggregate map committed')).toBeVisible()
    expect(operationsView.getByText(/YOLOE unfinished · BioCLIP unfinished/)).toBeVisible()
    expect(
      operationsView.getByRole('link', { name: 'Open committed species snapshot' }),
    ).toHaveAttribute('href', '#species')

    const quality = requiredElement('#quality')
    const qualityView = within(quality)
    expect(
      qualityView.getByRole('heading', {
        name: 'Evidence strength, without guesswork.',
      }),
    ).toBeVisible()
    expect(metric(qualityView, 'Reviewed sample')).toHaveTextContent('0')
    expect(metric(qualityView, 'Precision estimate')).toHaveTextContent('Unavailable')
    expect(qualityView.getByText(/workflow count—not 0% precision/i)).toBeVisible()
    fireEvent.click(qualityView.getByText('Evidence, method, and provenance'))
    expect(qualityView.getByText('ButterflyLens rebuilt baseline')).toBeVisible()
    expect(qualityView.getByText(/model votes are excluded/i)).toBeVisible()

    // 5. Inspect governed evidence-export paths; no public archive is invented.
    const footer = requiredElement('#about')
    const footerView = within(footer)
    expect(footerView.getByRole('link', { name: 'Darwin Core export' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/DARWIN_CORE_EXPORT.md',
    )
    expect(
      footerView.getByRole('link', { name: 'ALA contribution preparation' }),
    ).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/ALA_CONTRIBUTION.md',
    )
    expect(screen.queryByRole('link', { name: /download.*export/i })).not.toBeInTheDocument()
    expect(screen.getByText('Search results are hypotheses—not biodiversity records.')).toBeVisible()
    expect(network).not.toHaveBeenCalled()
  })
})

function requiredElement(selector: string): HTMLElement {
  const element = document.querySelector(selector)
  expect(element).toBeInstanceOf(HTMLElement)
  return element as HTMLElement
}

function metric(
  view: ReturnType<typeof within>,
  label: string,
): HTMLElement {
  const summary = view.getByLabelText('Quality summary')
  const article = within(summary).getByText(label).closest('article')
  expect(article).not.toBeNull()
  return article as HTMLElement
}
