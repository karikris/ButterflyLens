import { useEffect, useMemo, useState } from 'react'

import { EvidenceNotice, StateBadge } from '../design-system/EvidencePrimitives'
import { submittedMapSnapshot } from '../map/submittedMapModel'
import {
  buildSafeOperationsProjection,
  submittedOperationsSnapshot,
  type LiveOperationsObservation,
} from './operationsModel'
import {
  submittedMonitoringSnapshot,
  type MonitoringState,
  type PublicMonitoringSnapshot,
} from './monitoringModel'
import { loadMonitoringSnapshot } from './monitoringTransport'

const WORKER_BADGE = {
  online: { state: 'verified', label: 'Worker online' },
  offline: { state: 'caution', label: 'Worker offline' },
  unavailable: { state: 'unavailable', label: 'Worker status unavailable' },
} as const

const MONITORING_BADGE = {
  available: 'verified',
  submitted: 'submitted',
  unavailable: 'unavailable',
  unfinished: 'unfinished',
  degraded: 'caution',
} as const

function liveObservationFromMonitoring(
  snapshot: PublicMonitoringSnapshot,
): LiveOperationsObservation | null {
  if (snapshot.snapshotMode !== 'live') return null
  return {
    schemaVersion: 'butterflylens-public-worker-observation:v1.0.0',
    observedAt: snapshot.observedAt,
    heartbeatObservedAt: snapshot.heartbeat.observedAt,
    workerState: snapshot.heartbeat.workerState as LiveOperationsObservation['workerState'],
    committedLiveSnapshot: null,
  }
}

function useMonitoringSnapshot(
  initial: PublicMonitoringSnapshot,
  endpoint: string | null,
  refreshMs: number,
) {
  const [snapshot, setSnapshot] = useState(initial)
  useEffect(() => setSnapshot(initial), [initial])
  useEffect(() => {
    if (endpoint === null) return
    let active = true
    let refreshTimer: ReturnType<typeof setTimeout> | undefined
    const refresh = async () => {
      try {
        const next = await loadMonitoringSnapshot(endpoint)
        if (active) setSnapshot(next)
      } catch {
        // Keep the last valid snapshot. Live monitoring never gates static content.
      } finally {
        if (active) refreshTimer = setTimeout(refresh, refreshMs)
      }
    }
    void refresh()
    return () => {
      active = false
      if (refreshTimer !== undefined) clearTimeout(refreshTimer)
    }
  }, [endpoint, refreshMs])
  return snapshot
}

export function validateMonitoringRefreshMs(value: number) {
  if (!Number.isInteger(value) || value < 5_000 || value > 300_000) {
    throw new Error('monitoring refresh interval is invalid')
  }
  return value
}

function MetricCard({
  detail,
  label,
  reason,
  state,
  value,
}: {
  readonly detail?: string
  readonly label: string
  readonly reason: string
  readonly state: MonitoringState
  readonly value: string
}) {
  return (
    <li className="monitoring-card">
      <div className="monitoring-card__heading">
        <span>{label}</span>
        <StateBadge state={MONITORING_BADGE[state]}>{state}</StateBadge>
      </div>
      <strong>{value}</strong>
      {detail ? <span>{detail}</span> : null}
      <p>{reason}</p>
    </li>
  )
}

function formatBytes(value: number | null) {
  if (value === null) return 'Unavailable'
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
  let scaled = value
  let unit = 0
  while (scaled >= 1024 && unit < units.length - 1) {
    scaled /= 1024
    unit += 1
  }
  return `${scaled.toLocaleString('en-AU', { maximumFractionDigits: 1 })} ${units[unit]}`
}

export function OperationsDashboard({
  liveObservation,
  monitoringSnapshot = submittedMonitoringSnapshot,
  monitoringUrl = null,
  now = new Date(),
  refreshMs = 30_000,
}: {
  readonly liveObservation?: LiveOperationsObservation | unknown | null
  readonly monitoringSnapshot?: PublicMonitoringSnapshot
  readonly monitoringUrl?: string | null
  readonly now?: Date
  readonly refreshMs?: number
}) {
  const monitoring = useMonitoringSnapshot(
    monitoringSnapshot,
    monitoringUrl,
    validateMonitoringRefreshMs(refreshMs),
  )
  const effectiveLiveObservation = useMemo(
    () =>
      liveObservation === undefined
        ? liveObservationFromMonitoring(monitoring)
        : liveObservation,
    [liveObservation, monitoring],
  )
  const projection = buildSafeOperationsProjection(
    submittedOperationsSnapshot,
    effectiveLiveObservation,
    now,
  )
  const workerBadge = WORKER_BADGE[projection.workerStatus]
  const map = submittedMapSnapshot
  const review = submittedOperationsSnapshot.review
  const lastMapRefresh =
    monitoring.snapshotMode === 'submitted'
      ? {
          state: 'submitted' as const,
          fingerprint: map.snapshotFingerprint,
          refreshedAt: map.generatedAt,
          reason:
            'The committed rights-screened ALA projection contains 213,310 map-eligible rows across 630 coarse H3 cells.',
        }
      : monitoring.lastMapRefresh

  return (
    <section className="operations-dashboard" id="operations" aria-labelledby="operations-heading">
      <header className="operations-dashboard__header">
        <div>
          <p className="eyebrow">Pipeline observatory</p>
          <h2 id="operations-heading">Live when available. Committed when not.</h2>
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
              <h3 id="operations-map-heading">Australia scope</h3>
            </div>
            <StateBadge state="submitted">Aggregate map committed</StateBadge>
          </div>
          <svg
            className="operations-map__figure"
            viewBox="0 0 420 260"
            role="img"
            aria-label="Submitted Australia evidence summary; public aggregate layer available"
          >
            <rect x="1" y="1" width="418" height="258" rx="18" />
            <path d="M96 63l54-28 71 6 37 22 63 2 39 37-18 47-42 18-17 47-63 17-33-27-58-4-35-31-39-20 14-42z" />
            <circle cx="304" cy="207" r="10" />
          </svg>
          <div className="operations-map__boundary">
            <StateBadge state="verified">Aggregate layer available</StateBadge>
            <p>
              {map.counts.mapEligible.toLocaleString('en-AU')} rights-screened,
              map-eligible ALA rows across{' '}
              {map.counts.mapCells.toLocaleString('en-AU')} coarse H3 cells. Flickr
              remains unavailable.
            </p>
          </div>
          <p className="operations-card__provenance">
            Snapshot <code>{map.snapshotId}</code> · fingerprint{' '}
            <code>{map.snapshotFingerprint.slice(0, 12)}…</code>
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

      <section className="monitoring-panel" aria-labelledby="monitoring-heading">
        <header>
          <div>
            <p className="eyebrow">Operational monitoring</p>
            <h3 id="monitoring-heading">What the live system can prove now</h3>
          </div>
          <StateBadge state={monitoring.snapshotMode === 'live' ? 'verified' : 'submitted'}>
            {monitoring.snapshotMode === 'live' ? 'Live snapshot' : 'Submitted fallback'}
          </StateBadge>
        </header>
        <p className="monitoring-panel__boundary">
          Unavailable values stay unavailable—not zero. These operational signals
          never establish butterfly identity, occurrence, or dataset quality.
        </p>
        <ul className="monitoring-grid">
          <MetricCard
            label="Worker heartbeat"
            state={monitoring.heartbeat.state}
            value={monitoring.heartbeat.observedAt ?? 'Unavailable'}
            detail={monitoring.heartbeat.workerState ?? undefined}
            reason={monitoring.heartbeat.reason}
          />
          <MetricCard
            label="API budget"
            state={monitoring.apiBudget.state}
            value={
              monitoring.apiBudget.remaining === null || monitoring.apiBudget.limit === null
                ? 'Unavailable'
                : `${monitoring.apiBudget.remaining.toLocaleString('en-AU')} of ${monitoring.apiBudget.limit.toLocaleString('en-AU')} remaining`
            }
            detail={
              monitoring.apiBudget.resetsAt === null
                ? undefined
                : `Resets ${monitoring.apiBudget.resetsAt}`
            }
            reason={monitoring.apiBudget.reason}
          />
          <MetricCard
            label="Stage health"
            state={monitoring.stageHealth.state}
            value={monitoring.stageHealth.currentStage ?? 'Unavailable'}
            detail={
              monitoring.stageHealth.healthyCount === null ||
                monitoring.stageHealth.failedCount === null
                ? undefined
                : `${monitoring.stageHealth.healthyCount} healthy · ${monitoring.stageHealth.failedCount} failed`
            }
            reason={monitoring.stageHealth.reason}
          />
          <MetricCard
            label="Queue depth"
            state={monitoring.queue.state}
            value={
              monitoring.queue.depth === null || monitoring.queue.capacity === null
                ? 'Unavailable'
                : `${monitoring.queue.depth.toLocaleString('en-AU')} of ${monitoring.queue.capacity.toLocaleString('en-AU')}`
            }
            reason={monitoring.queue.reason}
          />
          <MetricCard
            label="Failures"
            state={monitoring.failures.state}
            value={
              monitoring.failures.count === null
                ? 'Unavailable'
                : monitoring.failures.count.toLocaleString('en-AU')
            }
            reason={monitoring.failures.reason}
          />
          <MetricCard
            label="Last artifact"
            state={monitoring.lastArtifact.state}
            value={
              monitoring.lastArtifact.fingerprint === null
                ? 'Unavailable'
                : `${monitoring.lastArtifact.fingerprint.slice(0, 12)}…`
            }
            detail={monitoring.lastArtifact.committedAt ?? undefined}
            reason={monitoring.lastArtifact.reason}
          />
          <MetricCard
            label="Last map refresh"
            state={lastMapRefresh.state}
            value={lastMapRefresh.refreshedAt ?? 'Unavailable'}
            detail={
              lastMapRefresh.fingerprint === null
                ? undefined
                : `${lastMapRefresh.fingerprint.slice(0, 12)}…`
            }
            reason={lastMapRefresh.reason}
          />
          <MetricCard
            label="Model state"
            state={monitoring.models.state}
            value={`YOLOE ${monitoring.models.yoloe} · BioCLIP ${monitoring.models.bioclip}`}
            reason={monitoring.models.reason}
          />
          <MetricCard
            label="Disk / memory"
            state={monitoring.resources.state}
            value={`Disk ${formatBytes(monitoring.resources.freeDiskBytes)}`}
            detail={`RSS ${formatBytes(monitoring.resources.processRssBytes)} · capacity ${formatBytes(monitoring.resources.memoryCapacityBytes)}`}
            reason={monitoring.resources.reason}
          />
        </ul>
      </section>
    </section>
  )
}
