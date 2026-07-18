import type { ReactNode } from 'react'

import { StateBadge } from '../design-system/EvidencePrimitives'

export const primaryNavigation = [
  { label: 'Explore', href: '#explore', current: true },
  { label: 'Verify', href: '#verify' },
  { label: 'Species', href: '#species' },
  { label: 'Live', href: '#live' },
  { label: 'Quality', href: '#quality' },
  { label: 'Contributors', href: '#contributors' },
  { label: 'Ask ButterflyLens', href: '#ask-butterflylens' },
  { label: 'About', href: '#about' },
] as const

export function PublicShell({ children }: { readonly children: ReactNode }) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <header className="site-header">
        <div className="site-header__identity">
          <a className="brand" href="#explore" aria-label="ButterflyLens home">
            <span className="brand-mark" aria-hidden="true">
              BL
            </span>
            <span>
              <strong>ButterflyLens</strong>
              <small>Australian butterfly evidence</small>
            </span>
          </a>
          <StateBadge state="submitted">Submitted replay</StateBadge>
        </div>
        <nav className="primary-navigation" aria-label="Primary">
          <ul>
            {primaryNavigation.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  aria-current={'current' in item && item.current ? 'page' : undefined}
                >
                  {item.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main id="main-content" tabIndex={-1}>
        {children}
      </main>
      <footer id="about" className="site-footer" aria-labelledby="about-heading">
        <div>
          <p className="eyebrow">About ButterflyLens</p>
          <h2 id="about-heading">Evidence grows through careful community work.</h2>
        </div>
        <div className="site-footer__copy">
          <p>Search results are hypotheses—not biodiversity records.</p>
          <p>
            ButterflyLens keeps candidate discovery, human review, quality
            estimation, and scientific release as separate evidence stages.
          </p>
          <p>
            <a href="https://github.com/karikris/ButterflyLens/blob/main/PRIVACY.md">
              Community privacy policy
            </a>
            {' · '}
            <a href="https://github.com/karikris/ButterflyLens/blob/main/MODERATION.md">
              Community safeguards
            </a>
            {' · '}
            <a href="https://github.com/karikris/ButterflyLens/blob/main/SENSITIVE_LOCATIONS.md">
              Sensitive locations
            </a>
            {' · '}
            <a href="https://github.com/karikris/ButterflyLens/blob/main/MEDIA_RIGHTS.md">
              Media rights
            </a>
            {' · '}
            <a href="https://github.com/karikris/ButterflyLens/blob/main/OCCURRENCE_RELEASE.md">
              Occurrence release
            </a>
            {' · '}
            <a href="https://github.com/karikris/ButterflyLens/blob/main/DARWIN_CORE_EXPORT.md">
              Darwin Core export
            </a>
          </p>
        </div>
      </footer>
    </div>
  )
}

export function RoutePreview({
  description,
  id,
  kicker,
  title,
}: {
  readonly description: string
  readonly id: string
  readonly kicker: string
  readonly title: string
}) {
  return (
    <section className="route-preview" id={id} aria-labelledby={`${id}-heading`}>
      <div>
        <p className="eyebrow">{kicker}</p>
        <h2 id={`${id}-heading`}>{title}</h2>
      </div>
      <div>
        <StateBadge state="unfinished">Surface scheduled</StateBadge>
        <p>{description}</p>
      </div>
    </section>
  )
}
