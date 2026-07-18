import submittedOperationsJson from './submittedOperationsSnapshot.json'
import { describe, expect, it } from 'vitest'

import {
  buildOperationsProjection,
  buildSafeOperationsProjection,
  parseLiveOperationsObservation,
  parseSubmittedOperationsSnapshot,
} from './operationsModel'

const NOW = new Date('2026-07-18T08:30:00Z')
const LIVE_ARTIFACT = {
  snapshotId: 'live:committed:41',
  mode: 'live',
  artifactFingerprint: 'a'.repeat(64),
  generatedAt: '2026-07-18T08:20:00Z',
  sourceCommit: 'b'.repeat(40),
  label: 'Committed live catalogue',
  href: '#species',
  speciesCount: 463,
} as const

function observation(heartbeatObservedAt: string | null) {
  return {
    schemaVersion: 'butterflylens-public-worker-observation:v1.0.0',
    observedAt: '2026-07-18T08:29:30Z',
    heartbeatObservedAt,
    workerState: heartbeatObservedAt === null ? null : 'idle',
    committedLiveSnapshot: LIVE_ARTIFACT,
  }
}

describe('worker-independent operations model', () => {
  it('parses the exact immutable snapshot and preserves its release gates', () => {
    const snapshot = parseSubmittedOperationsSnapshot(submittedOperationsJson)
    expect(snapshot.site).toEqual({
      available: true,
      committedDataQueryable: true,
      workerRequired: false,
    })
    expect(snapshot.submittedSnapshot.speciesCount).toBe(463)
    expect(snapshot.map.occurrenceLayerVisible).toBe(false)
    expect(snapshot.map.absenceInferencePermitted).toBe(false)
    expect(snapshot.review.available).toBe(true)
  })

  it('uses a fresh heartbeat without making it the data authority', () => {
    const projection = buildOperationsProjection(
      submittedOperationsJson,
      observation('2026-07-18T08:28:00Z'),
      NOW,
    )
    expect(projection.workerStatus).toBe('online')
    expect(projection.currentSnapshot).toEqual(LIVE_ARTIFACT)
    expect(projection.submittedSnapshot.mode).toBe('submitted')
    expect(projection.committedDataQueryable).toBe(true)
  })

  it('shows a stale observed heartbeat as offline and retains committed live data', () => {
    const projection = buildOperationsProjection(
      submittedOperationsJson,
      observation('2026-07-18T08:00:00Z'),
      NOW,
    )
    expect(projection.workerStatus).toBe('offline')
    expect(projection.liveIsStale).toBe(true)
    expect(projection.currentSnapshot).toEqual(LIVE_ARTIFACT)
    expect(projection.siteAvailable).toBe(true)
  })

  it('does not infer offline when a heartbeat was never observed', () => {
    const projection = buildOperationsProjection(
      submittedOperationsJson,
      observation(null),
      NOW,
    )
    expect(projection.workerStatus).toBe('unavailable')
    expect(projection.currentSnapshot).toEqual(LIVE_ARTIFACT)
    expect(projection.liveIsStale).toBe(true)
  })

  it('rejects future observations and falls back to the submitted snapshot', () => {
    const future = {
      ...observation('2026-07-18T08:31:00Z'),
      observedAt: '2026-07-18T08:31:00Z',
    }
    expect(() =>
      buildOperationsProjection(submittedOperationsJson, future, NOW),
    ).toThrow(/future/)
    const safe = buildSafeOperationsProjection(submittedOperationsJson, future, NOW)
    expect(safe.workerStatus).toBe('unavailable')
    expect(safe.currentSnapshot.mode).toBe('submitted')
  })

  it('rejects extra public fields instead of accepting ambiguous status', () => {
    expect(() =>
      parseLiveOperationsObservation({
        ...observation('2026-07-18T08:28:00Z'),
        queueContents: ['private'],
      }),
    ).toThrow(/exact public shape/)
    expect(() =>
      parseSubmittedOperationsSnapshot({
        ...submittedOperationsJson,
        liveUrl: 'https://example.invalid',
      }),
    ).toThrow(/exact public shape/)
  })

  it('rejects internally inconsistent heartbeat and observation times', () => {
    expect(() =>
      parseLiveOperationsObservation({
        ...observation('2026-07-18T08:28:00Z'),
        workerState: null,
      }),
    ).toThrow(/supplied together/)
    expect(() =>
      buildOperationsProjection(
        submittedOperationsJson,
        {
          ...observation('2026-07-18T08:28:00Z'),
          observedAt: '2026-07-18T08:27:00Z',
        },
        NOW,
      ),
    ).toThrow(/postdate/)
  })
})
