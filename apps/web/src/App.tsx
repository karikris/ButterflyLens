import { ReviewLanding } from './review/ReviewLanding'
import { submittedReviewItem } from './review/reviewLandingModel'
import { PublicShell } from './shell/PublicShell'
import { HowItWorks } from './HowItWorks'
import { MoreSurface } from './MoreSurface'
import { SubmittedEvidenceMap } from './map/SubmittedEvidenceMap'
import { ContributorExperience } from './community/ContributorExperience'
import { submittedContributorImpact } from './community/contributorImpactModel'

export function App() {
  const monitoringUrl = import.meta.env.VITE_BUTTERFLYLENS_MONITORING_URL || null
  return (
    <PublicShell>
      <section id="explore" className="shell-intro" aria-labelledby="explore-heading">
        <div>
          <p className="eyebrow">Australia’s butterfly evidence, made inspectable</p>
          <h1 id="explore-heading">Look closer. Strengthen what we know.</h1>
          <p className="shell-intro__lede">
            Explore the submitted evidence, help verify what an image supports,
            and see every uncertainty and release boundary along the way.
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
      <ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />
      <HowItWorks />
      <ContributorExperience snapshot={submittedContributorImpact} />
      <MoreSurface monitoringUrl={monitoringUrl} />
    </PublicShell>
  )
}
