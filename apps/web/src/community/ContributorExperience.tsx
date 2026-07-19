import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import type {
  ContributionMetric,
  ContributorImpactSnapshot,
} from './contributorImpactModel'

const metricDetails = [
  ['reviewedImages', 'Reviewed images', 'Unique images with an effective stored review'],
  ['resolvedConflicts', 'Resolved conflicts', 'Independent adjudications with retained dissent'],
  ['speciesHelped', 'Species helped', 'Accepted species touched by governed event lineage'],
  ['regionsHelped', 'Regions helped', 'Distinct generalised public regions touched'],
  ['controlCoverage', 'Control coverage', 'Aggregate governed checks; identities stay private'],
  ['expertContribution', 'Expert contribution', 'Work completed under a verified expert role'],
] as const

export function ContributorExperience({
  snapshot,
}: {
  readonly snapshot: ContributorImpactSnapshot
}) {
  const available = snapshot.snapshotState === 'available'
  return (
    <section id="community" className="contributor-experience" aria-labelledby="community-heading">
      <header className="contributor-experience__intro">
        <div>
          <p className="eyebrow">Your evidence contribution</p>
          <h2 id="community-heading">Careful work leaves a meaningful trace.</h2>
          <p>
            Celebrate the records, species, and places your evidence work has
            strengthened—without turning community science into a race.
          </p>
        </div>
        <StateBadge state={available ? 'verified' : 'unavailable'}>
          {available ? 'Private contribution snapshot' : 'Contribution snapshot unavailable'}
        </StateBadge>
      </header>

      {!available ? (
        <EvidenceNotice title="No contribution totals are claimed" tone="caution">
          {snapshot.snapshotStateReason}
        </EvidenceNotice>
      ) : null}

      <div className="contributor-metrics" aria-label="Contribution summary">
        {metricDetails.map(([key, label, detail]) => (
          <ContributionCard
            key={key}
            label={label}
            detail={detail}
            metric={snapshot.metrics[key]}
          />
        ))}
      </div>

      <div className="contributor-principles">
        <section aria-labelledby="recognition-heading">
          <p className="eyebrow">Recognition policy</p>
          <h3 id="recognition-heading">Evidence, not speed.</h3>
          <p>
            There are no speed rankings, streak pressure, public leaderboards,
            or reviewer comparisons. Taking time and abstaining when evidence
            is weak are valuable scientific behaviours.
          </p>
        </section>
        <section aria-labelledby="privacy-heading">
          <p className="eyebrow">Privacy and authority</p>
          <h3 id="privacy-heading">Private to the contributor.</h3>
          <p>
            Totals are self-visible by default. Control identities, expected
            answers, Auth IDs, reliability weights, and exact sensitive places
            are never exposed here. Recognition cannot approve a record.
          </p>
        </section>
      </div>
    </section>
  )
}

function ContributionCard({
  detail,
  label,
  metric,
}: {
  readonly detail: string
  readonly label: string
  readonly metric: ContributionMetric
}) {
  return (
    <article data-state={metric.state}>
      <span>{label}</span>
      <strong>{metric.value === null ? '—' : new Intl.NumberFormat('en-AU').format(metric.value)}</strong>
      <small>{metric.reason ?? detail}</small>
    </article>
  )
}
