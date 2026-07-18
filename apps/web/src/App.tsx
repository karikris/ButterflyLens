import { StateBadge } from './design-system/EvidencePrimitives'
import { ReviewLanding } from './review/ReviewLanding'
import { submittedReviewItem } from './review/reviewLandingModel'
import { QualityDashboard } from './quality/QualityDashboard'
import { submittedQualityDashboard } from './quality/qualityDashboardModel'

export function App() {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#review-workspace">
        Skip to review
      </a>
      <header className="site-header">
        <a className="brand" href="/" aria-label="ButterflyLens home">
          <span className="brand-mark" aria-hidden="true">
            BL
          </span>
          <span>
            <strong>ButterflyLens</strong>
            <small>Australian butterfly evidence</small>
          </span>
        </a>
        <StateBadge state="submitted">Submitted replay</StateBadge>
      </header>
      <main id="review-workspace">
        <ReviewLanding item={submittedReviewItem} qualifiedReviewer={false} />
        <QualityDashboard snapshot={submittedQualityDashboard} />
      </main>
      <footer className="site-footer">
        <p>Search results are hypotheses—not biodiversity records.</p>
        <p>Built for independent community review.</p>
      </footer>
    </div>
  )
}
