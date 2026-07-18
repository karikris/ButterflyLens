import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import {
  buildSafeOperationsProjection,
  submittedOperationsSnapshot,
  type LiveOperationsObservation,
} from './operationsModel'

const WORKER_BADGE = {
  online: { state: 'verified', label: 'Worker online' },
  offline: { state: 'caution', label: 'Worker offline' },
  unavailable: { state: 'unavailable', label: 'Worker status unavailable' },
} as const

export function OperationsDashboard({
  liveObservation = null,
  now = new Date(),
}: {
  readonly liveObservation?: LiveOperationsObservation | unknown | null
  readonly now?: Date
}) {
  const projection = buildSafeOperationsProjection(
    submittedOperationsSnapshot,
    liveObservation,
    now,
  )
  const workerBadge = WORKER_BADGE[projection.workerStatus]
  const map = submittedOperationsSnapshot.map
  const review = submittedOperationsSnapshot.review

  return (
    <section className="operations-dashboard" id="live" aria-labelledby="live-heading">
      <header className="operations-dashboard__header">
        <div>
          <p className="eyebrow">Pipeline observatory</p>
          <h2 id="live-heading">Live when available. Committed when not.</h2>
          <p>
            The map, review route, and submitted snapshot load from this static
            build. A worker heartbeat can add status, but never gates the site.
          </p>
        </div>
        <div className="operations-dashboard__worker" aria-live="polite">
          <StateBadge state={workerBadge.state}>{workerBadge.label}</StateBadge>
          <p>{projection.reason}</p>
        </div>
      </header>

      <EvidenceNotice title="Worker-independent evidence">
        {projection.currentSnapshot.mode === 'live'
          ? 'The newest explicitly committed live artifact is selected; the submitted snapshot remains linked below.'
          : 'No committed live replacement is attached, so the immutable submitted snapshot remains current.'}
      </EvidenceNotice>

      <div className="operations-dashboard__grid">
        <article className="operations-map" aria-labelledby="operations-map-heading">
          <div className="operations-card__heading">
            <div>
              <p className="eyebrow">Committed map</p>
              <h3 id="operations-map-heading">{map.scopeLabel} scope</h3>
            </div>
            <StateBadge state="submitted">Map shell loaded</StateBadge>
          </div>
          <svg
            className="operations-map__figure"
            viewBox="0 0 420 260"
            role="img"
            aria-label="Submitted Australia map scope; occurrence layer withheld"
          >
            <rect x="1" y="1" width="418" height="258" rx="18" />
            <path d="M96 63l54-28 71 6 37 22 63 2 39 37-18 47-42 18-17 47-63 17-33-27-58-4-35-31-39-20 14-42z" />
            <circle cx="304" cy="207" r="10" />
            <path className="operations-map__withheld" d="M61 226h298" />
          </svg>
          <div className="operations-map__boundary">
            <StateBadge state="caution">Occurrence layer withheld</StateBadge>
            <p>{map.reason}</p>
          </div>
          <p className="operations-card__provenance">
            Snapshot <code>{map.snapshotId}</code> · fingerprint{' '}
            <code>{map.artifactFingerprint.slice(0, 12)}…</code>
          </p>
        </article>

        <article className="operations-snapshot" aria-labelledby="snapshot-heading">
          <div className="operations-card__heading">
            <div>
              <p className="eyebrow">Current public artifact</p>
              <h3 id="snapshot-heading">{projection.currentSnapshot.label}</h3>
            </div>
            <StateBadge state="verified">Committed</StateBadge>
          </div>
          <dl>
            <div>
              <dt>Mode</dt>
              <dd>{projection.currentSnapshot.mode}</dd>
            </div>
            <div>
              <dt>Species</dt>
              <dd>{projection.currentSnapshot.speciesCount.toLocaleString('en-AU')}</dd>
            </div>
            <div>
              <dt>Generated</dt>
              <dd>{projection.currentSnapshot.generatedAt}</dd>
            </div>
            <div>
              <dt>Fingerprint</dt>
              <dd>
                <code>{projection.currentSnapshot.artifactFingerprint.slice(0, 16)}…</code>
              </dd>
            </div>
          </dl>
          <a className="operations-link" href={projection.currentSnapshot.href}>
            Open committed species snapshot
          </a>
        </article>
      </div>

      <ul className="operations-surfaces" aria-label="Worker-independent surfaces">
        <li>
          <StateBadge state="verified">Available</StateBadge>
          <div>
            <strong>Map shell</strong>
            <span>Australia scope loads without a worker; restricted layers stay withheld.</span>
          </div>
        </li>
        <li>
          <StateBadge state="verified">Available</StateBadge>
          <div>
            <strong>Review route</strong>
            <span>{review.reason}</span>
            <a href={review.href}>Open submitted review</a>
          </div>
        </li>
        <li>
          <StateBadge state="submitted">Always bundled</StateBadge>
          <div>
            <strong>Submitted snapshot</strong>
            <span>
              The submitted catalogue stays available even when live services fail.
            </span>
            <a href={projection.submittedSnapshot.href}>Open submitted snapshot</a>
          </div>
        </li>
      </ul>
    </section>
  )
}
