import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { SpeciesDirectory } from './SpeciesDirectory'
import { submittedSpeciesCatalogue } from './speciesCatalogueModel'

describe('Australian butterfly species pages', () => {
  it('opens the photographic submitted species page with honest boundaries', () => {
    render(<SpeciesDirectory />)

    expect(
      screen.getByRole('heading', { name: 'Meet the accepted butterfly catalogue.' }),
    ).toBeVisible()
    expect(screen.getByText('463 accepted species')).toBeVisible()
    expect(
      screen.getByRole('heading', { name: 'Papilio (Princeps) demoleus' }),
    ).toBeVisible()
    expect(
      screen.getByRole('img', {
        name: /Wikimedia Commons source labels it Papilio demoleus/u,
      }),
    ).toBeVisible()
    expect(screen.getByText(/not representative and not identity verification/i)).toBeVisible()
    expect(screen.getByText(/occurrence counts are withheld/i)).toBeVisible()
    expect(screen.getByText(/YOLOE and BioCLIP are unfinished/i)).toBeVisible()
    expect(fact('Human-verified media')).toHaveTextContent('0')
  })

  it('searches all 463 pages by scientific and source-reported English names', () => {
    render(<SpeciesDirectory />)

    const search = screen.getByRole('searchbox', { name: 'Search species' })
    fireEvent.change(search, { target: { value: 'ptunarra' } })
    expect(screen.getByText('1 species shown')).toBeVisible()
    expect(
      screen.getByRole('button', { name: /Oreixenica ptunarra/u }),
    ).toBeVisible()

    fireEvent.change(search, { target: { value: 'glasswing butterfly' } })
    expect(screen.getByText(/species shown/u)).toBeVisible()
    expect(screen.getByRole('button', { name: /Glasswing, Acraea andromacha/u })).toBeVisible()
    expect(screen.getByText('Glasswing Butterfly')).toBeVisible()
  })

  it('opens a selected page without promoting unavailable photography', () => {
    render(<SpeciesDirectory />)

    const search = screen.getByRole('searchbox', { name: 'Search species' })
    fireEvent.change(search, { target: { value: 'Oreixenica ptunarra' } })
    fireEvent.click(screen.getByRole('button', { name: /Oreixenica ptunarra/u }))

    expect(
      screen.getByRole('heading', { name: 'Oreixenica ptunarra' }),
    ).toBeVisible()
    expect(
      screen.getByRole('img', { name: /No public species photograph/u }),
    ).toBeVisible()
    expect(screen.getByText(/Missing media is a data gap/i)).toBeVisible()
  })

  it('exposes unresolved provider evidence instead of fabricating identifiers', () => {
    const conflicted = submittedSpeciesCatalogue.species.find(
      (species) => species.crosswalk.openConflicts.length > 0,
    )
    expect(conflicted).toBeDefined()
    render(<SpeciesDirectory />)

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search species' }), {
      target: { value: conflicted!.acceptedScientificName },
    })
    fireEvent.click(
      screen.getByRole('button', {
        name: new RegExp(escapeRegex(conflicted!.acceptedScientificName), 'u'),
      }),
    )

    expect(screen.getByText(/No automatic resolution is permitted/u)).toBeVisible()
    const table = screen.getByRole('table', {
      name: 'Provider relationships for this accepted taxon',
    })
    expect(within(table).getByText('Conflict')).toBeVisible()
  })

  it('keeps the empty First Nations name state culturally explicit', () => {
    render(<SpeciesDirectory />)
    expect(
      screen.getByText(/not evidence that no First Nations names exist/u),
    ).toBeVisible()
  })
})

function fact(label: string): HTMLElement {
  return screen.getByText(label).closest('div')!
}

function escapeRegex(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/gu, '\\$&')
}
