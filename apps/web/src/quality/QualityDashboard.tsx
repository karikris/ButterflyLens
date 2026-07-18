import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import type { QualityDashboardSnapshot } from './qualityDashboardModel'

export function QualityDashboard({
  snapshot,
}: {
  readonly snapshot: QualityDashboardSnapshot
}) {
  const qualityAvailable = snapshot.precision.availability === 'estimated'
  return (
    <section
      id="quality-dashboard"
      className="quality-dashboard"
      aria-labelledby="quality-dashboard-heading"
    >
      <header className="quality-dashboard__intro">
        <div>
          <p className="eyebrow">Community quality</p>
          <h2 id="quality-dashboard-heading">Evidence strength, without guesswork.</h2>
          <p>
            Counts describe completed work. Population quality appears only
            after a fingerprinted representative audit preserves its sampling
            probabilities, strata, and owner/observation groups.
          </p>
        </div>
        <StateBadge
          state={snapshot.status === 'estimated' ? 'verified' : 'unavailable'}
        >
          {snapshot.status === 'estimated'
            ? 'Representative estimate available'
            : 'Representative estimate unavailable'}
        </StateBadge>
      </header>

      {!qualityAvailable ? (
        <EvidenceNotice
          className="quality-evidence-notice"
          title="No population estimate is shown"
          tone="caution"
          announce
        >
          {snapshot.precision.reason}{' '}
          {snapshot.reviewedSample === 0
            ? 'Zero reviewed records is a workflow count—not 0% precision.'
            : 'The reviewed-record count is workflow evidence, not a precision estimate.'}
        </EvidenceNotice>
      ) : null}

      <div className="quality-metrics" aria-label="Quality summary">
        <QualityMetric
          label="Reviewed sample"
          value={formatInteger(snapshot.reviewedSample)}
          detail="Representative audit records"
        />
        <QualityMetric
          label="Decisive reviews"
          value={formatInteger(snapshot.decisiveReviews)}
          detail="Supported or not supported"
        />
        <QualityMetric
          label="Precision estimate"
          value={formatProbability(snapshot.precision.estimate)}
          detail={
            qualityAvailable
              ? 'Hájek inverse-probability estimate'
              : 'Representative audit required'
          }
          state={snapshot.precision.availability}
        />
        <QualityMetric
          label="Confidence interval"
          value={formatInterval(snapshot.precision.interval)}
          detail={
            snapshot.precision.interval === null
              ? 'Grouped bootstrap unavailable'
              : `${formatProbability(snapshot.precision.interval.level)} grouped bootstrap`
          }
          state={snapshot.precision.availability}
        />
        <QualityMetric
          label="Reviewer agreement"
          value={formatProbability(snapshot.reviewerAgreement.pairwiseAgreement)}
          detail={
            snapshot.reviewerAgreement.availability === 'estimated'
              ? `${snapshot.reviewerAgreement.overlappingItems} overlapping items`
              : snapshot.reviewerAgreement.reason ?? 'Unavailable'
          }
          state={snapshot.reviewerAgreement.availability}
        />
        <QualityMetric
          label="Species quality"
          value={formatProbability(snapshot.speciesQuality.estimate)}
          detail={
            snapshot.speciesQuality.availability === 'estimated'
              ? `${snapshot.speciesQuality.auditedSpecies} audited species`
              : snapshot.speciesQuality.reason ?? 'Unavailable'
          }
          state={snapshot.speciesQuality.availability}
        />
      </div>

      <div className="quality-detail-grid">
        <section className="quality-panel" aria-labelledby="species-diagnostics-heading">
          <div>
            <p className="eyebrow">Species quality</p>
            <h3 id="species-diagnostics-heading">Reference diagnostics</h3>
            <p>
              These are coverage and workflow diagnostics, not human-verified
              identities or a representative species-quality estimate.
            </p>
          </div>
          <dl className="quality-facts">
            <QualityFact
              label="Accepted species"
              value={snapshot.referenceDiagnostics.acceptedSpecies}
            />
            <QualityFact
              label="Species with valid decodes"
              value={snapshot.referenceDiagnostics.speciesWithValidDecodes}
            />
            <QualityFact
              label="Human-verified species"
              value={snapshot.referenceDiagnostics.humanVerifiedSpecies}
            />
            <QualityFact
              label="Valid decoded images"
              value={snapshot.referenceDiagnostics.validDecodes}
            />
          </dl>
        </section>

        <section className="quality-panel" aria-labelledby="release-blockers-heading">
          <div>
            <p className="eyebrow">Release boundary</p>
            <h3 id="release-blockers-heading">Release blockers</h3>
            <p>
              The dashboard reports blockers; it cannot waive rights,
              provenance, review, quality, expert, or authorization gates.
            </p>
          </div>
          <ul className="quality-blockers">
            {snapshot.releaseBlockers.map((blocker) => (
              <li key={blocker}>{humanizeIdentifier(blocker)}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="reference-health" aria-labelledby="reference-health-heading">
        <header>
          <div>
            <p className="eyebrow">Reference health</p>
            <h3 id="reference-health-heading">Flags remain visible</h3>
          </div>
          <p>{snapshot.referenceDiagnostics.flags.length} active flag types</p>
        </header>
        <ul>
          {snapshot.referenceDiagnostics.flags.map((flag) => (
            <li key={flag.flagId} data-severity={flag.severity}>
              <span>{humanizeIdentifier(flag.flagId)}</span>
              <strong>{formatInteger(flag.affectedSpecies)}</strong>
              <small>affected species · {flag.severity}</small>
            </li>
          ))}
        </ul>
      </section>

      <details className="quality-provenance">
        <summary>Evidence, method, and provenance</summary>
        <p>
          Targeted failure discovery remains separate from representative
          estimation. Model votes are excluded. YOLOE and BioCLIP are unfinished.
        </p>
        <dl>
          <QualityFact
            label="Quality manifest"
            value={snapshot.provenance.qualityManifestSha256}
            code
          />
          <QualityFact
            label="Reference bank"
            value={snapshot.provenance.referenceBankFingerprint}
            code
          />
          <QualityFact
            label="Quality snapshot"
            value={snapshot.provenance.qualitySnapshotFingerprint ?? 'Unavailable'}
            code={snapshot.provenance.qualitySnapshotFingerprint !== null}
          />
          <QualityFact
            label="Authoritative baseline"
            value={snapshot.provenance.authoritativeBaseline}
          />
        </dl>
      </details>
    </section>
  )
}

function QualityMetric({
  detail,
  label,
  state = 'estimated',
  value,
}: {
  readonly detail: string
  readonly label: string
  readonly state?: 'estimated' | 'unavailable'
  readonly value: string
}) {
  return (
    <article data-state={state}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  )
}

function QualityFact({
  code = false,
  label,
  value,
}: {
  readonly code?: boolean
  readonly label: string
  readonly value: number | string
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{code ? <code>{value}</code> : value}</dd>
    </div>
  )
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('en-AU').format(value)
}

function formatProbability(value: number | null): string {
  return value === null
    ? 'Unavailable'
    : new Intl.NumberFormat('en-AU', {
        style: 'percent',
        maximumFractionDigits: 1,
      }).format(value)
}

function formatInterval(
  interval: { readonly lower: number; readonly upper: number } | null,
): string {
  return interval === null
    ? 'Unavailable'
    : `${formatProbability(interval.lower)} – ${formatProbability(interval.upper)}`
}

function humanizeIdentifier(value: string): string {
  const acronyms: Readonly<Record<string, string>> = {
    bioclip: 'BioCLIP',
    yoloe: 'YOLOE',
  }
  const words = value.split('_').map((word) => acronyms[word] ?? word)
  const label = words.join(' ')
  return `${label.charAt(0).toUpperCase()}${label.slice(1)}`
}
