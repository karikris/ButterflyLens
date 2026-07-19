import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { App } from '../App'
import { PublicShell, primaryNavigation } from './PublicShell'

describe('public application shell', () => {
  it('publishes the exact primary navigation once and in order', () => {
    render(
      <PublicShell>
        <p>Test content</p>
      </PublicShell>,
    )

    const navigation = screen.getByRole('navigation', { name: 'Primary' })
    const links = within(navigation).getAllByRole('link')
    expect(links.map((link) => link.textContent)).toEqual(
      primaryNavigation.map((item) => item.label),
    )
    expect(links.map((link) => link.getAttribute('href'))).toEqual(
      primaryNavigation.map((item) => item.href),
    )
    expect(links[0]).toHaveAttribute('aria-current', 'page')
  })

  it('updates aria-current from the current hash', () => {
    window.location.hash = '#verify'
    render(
      <PublicShell>
        <p>Test content</p>
      </PublicShell>,
    )
    fireEvent(window, new HashChangeEvent('hashchange'))

    const navigation = screen.getByRole('navigation', { name: 'Primary' })
    const links = within(navigation).getAllByRole('link')
    expect(links[1]).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Explore' })).not.toHaveAttribute('aria-current')
  })

  it('provides one skip target and the expected page landmarks', () => {
    render(
      <PublicShell>
        <p>Test content</p>
      </PublicShell>,
    )

    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveAttribute('id', 'main-content')
    expect(screen.getByRole('contentinfo')).toHaveAttribute('id', 'about')
    expect(screen.getByRole('link', { name: 'Community privacy policy' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/PRIVACY.md',
    )
    expect(screen.getByRole('link', { name: 'Community safeguards' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/MODERATION.md',
    )
    expect(screen.getByRole('link', { name: 'Sensitive locations' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/SENSITIVE_LOCATIONS.md',
    )
    expect(screen.getByRole('link', { name: 'Media rights' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/MEDIA_RIGHTS.md',
    )
    expect(screen.getByRole('link', { name: 'Occurrence release' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/OCCURRENCE_RELEASE.md',
    )
    expect(screen.getByRole('link', { name: 'Darwin Core export' })).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/DARWIN_CORE_EXPORT.md',
    )
    expect(
      screen.getByRole('link', { name: 'ALA contribution preparation' }),
    ).toHaveAttribute(
      'href',
      'https://github.com/karikris/ButterflyLens/blob/main/ALA_CONTRIBUTION.md',
    )
  })

  it('shows the route root for each primary navigation hash', () => {
    render(<App />)

    const navigation = screen.getByRole('navigation', { name: 'Primary' })
    for (const link of within(navigation).getAllByRole('link')) {
      const href = link.getAttribute('href')
      expect(href).toMatch(/^#[a-z-]+$/u)
      window.location.hash = href
      fireEvent(window, new HashChangeEvent('hashchange'))

      if (href === '#about') {
        expect(screen.getByRole('contentinfo')).toHaveAttribute('id', 'about')
        expect(document.querySelector(href)).toBeInTheDocument()
      } else {
        expect(document.querySelector(href)).toBeInTheDocument()
      }
    }
    window.location.hash = '#explore'
    fireEvent(window, new HashChangeEvent('hashchange'))
    expect(screen.getByRole('heading', { level: 1, name: 'Look closer. Strengthen what we know.' })).toBeInTheDocument()
  })
})
