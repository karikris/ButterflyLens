import { useEffect, useState } from 'react'

import { ReviewLanding } from './review/ReviewLanding'
import { submittedReviewItem } from './review/reviewLandingModel'
import { HowItWorks } from './HowItWorks'
import { MoreSurface } from './MoreSurface'
import { SubmittedEvidenceMap } from './map/SubmittedEvidenceMap'
import { ContributorExperience } from './community/ContributorExperience'
import { submittedContributorImpact } from './community/contributorImpactModel'
import { PublicShell, type PrimaryRouteHash, normalizeRouteHash } from './shell/PublicShell'

function ExploreRoute() {
  return (
    <>
      <section id="explore" className="shell-intro" aria-labelledby="explore-heading">
        <div>
          <p className="eyebrow">Australia’s butterfly evidence, made inspectable</p>
          <h1 id="explore-heading">Look closer. Strengthen what we know.</h1>
          <p className="shell-intro__lede">
            Explore the submitted evidence, help verify what an image supports,
            and see every uncertainty and release boundaries along the way.
          </p>
        </div>
        <dl className="shell-intro__facts">
          <div>
            <dt>Experience</dt>
            <dd>Credential-free submitted replay</dd>
          </div>
          <div>
            <dt>Baseline</dt>
            <dd>ButterflyLens rebuilt baseline</dd>
          </div>
          <div>
            <dt>Scientific state</dt>
            <dd>Candidate evidence; release gates remain active</dd>
          </div>
        </dl>
      </section>

      <SubmittedEvidenceMap />
    </>
  )
}

export function App() {
  const [route, setRoute] = useState<PrimaryRouteHash>(
    normalizeRouteHash(window.location.hash || '#explore'),
  )

  useEffect(() => {
    const syncRoute = () => {
      setRoute(normalizeRouteHash(window.location.hash || '#explore'))
    }

    syncRoute()
    window.addEventListener('hashchange', syncRoute)
    return () => {
      window.removeEventListener('hashchange', syncRoute)
    }
  }, [])

  if (route === '#explore') {
    return (
      <PublicShell>
        <ExploreRoute />
      </PublicShell>
    )
  }

  if (route === '#verify') {
    return (
      <PublicShell>
        <ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />
      </PublicShell>
    )
  }

  if (route === '#how-it-works') {
    return (
      <PublicShell>
        <HowItWorks />
      </PublicShell>
    )
  }

  if (route === '#community') {
    return (
      <PublicShell>
        <ContributorExperience snapshot={submittedContributorImpact} />
      </PublicShell>
    )
  }

  if (route === '#about') {
    return <PublicShell>{null}</PublicShell>
  }

  return (
    <PublicShell>
      <MoreSurface monitoringUrl={import.meta.env.VITE_BUTTERFLYLENS_MONITORING_URL || null} />
    </PublicShell>
  )
}
