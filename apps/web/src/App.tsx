import { ReviewLanding } from './review/ReviewLanding'
import { submittedReviewItem } from './review/reviewLandingModel'
import { QualityDashboard } from './quality/QualityDashboard'
import { submittedQualityDashboard } from './quality/qualityDashboardModel'
import { PublicShell } from './shell/PublicShell'
import { SpeciesDirectory } from './species/SpeciesDirectory'
import { FlickrDisplayBoundary } from './flickr/FlickrDisplayBoundary'
import { ContributorExperience } from './community/ContributorExperience'
import { submittedContributorImpact } from './community/contributorImpactModel'
import { AskButterflyLens } from './analyst/AskButterflyLens'
import { OperationsDashboard } from './operations/OperationsDashboard'

export function App() {
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
      <ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />
      <SpeciesDirectory />
      <OperationsDashboard />
      <FlickrDisplayBoundary />
      <QualityDashboard snapshot={submittedQualityDashboard} />
      <ContributorExperience snapshot={submittedContributorImpact} />
      <AskButterflyLens />
    </PublicShell>
  )
}
