import { describe, expect, it } from 'vitest'

import submittedMonitoringJson from './submittedMonitoringSnapshot.json'
import { parsePublicMonitoringSnapshot } from './monitoringModel'

export const LIVE_MONITORING = {
  ...submittedMonitoringJson,
  snapshotMode: 'live',
  observedAt: '2026-07-18T09:00:00Z',
  heartbeat: {
    state: 'available',
    observedAt: '2026-07-18T08:59:45Z',
    workerState: 'running',
    reason: 'A fresh governed heartbeat is available.',
  },
  apiBudget: {
    state: 'available',
    limit: 1000,
    used: 240,
    remaining: 760,
    resetsAt: '2026-07-19T00:00:00Z',
    reason: 'A governed aggregate request budget is available.',
  },
  stageHealth: {
    state: 'degraded',
    currentStage: 'metadata',
    stageState: 'running',
    healthyCount: 11,
    failedCount: 1,
    reason: 'One stage failure is retained for investigation.',
  },
  queue: {
    state: 'available',
    depth: 12,
    capacity: 512,
    reason: 'Aggregate queue occupancy is available.',
  },
  failures: {
    state: 'degraded',
    count: 1,
    reason: 'One terminal stage failure is recorded.',
  },
  lastArtifact: {
    ...submittedMonitoringJson.lastArtifact,
    state: 'available',
    committedAt: '2026-07-18T08:58:00Z',
  },
  lastMapRefresh: {
    ...submittedMonitoringJson.lastMapRefresh,
    state: 'available',
    refreshedAt: '2026-07-18T08:57:00Z',
  },
  resources: {
    state: 'available',
    freeDiskBytes: 500_000_000_000,
    processRssBytes: 2_000_000_000,
    memoryCapacityBytes: 32_000_000_000,
    mpsAllocatedBytes: null,
    mpsReservedBytes: null,
    reason: 'Bounded worker resource counters are available.',
  },
} as const

describe('public operational monitoring model', () => {
  it('parses the submitted fallback without turning missing values into zero', () => {
    const snapshot = parsePublicMonitoringSnapshot(submittedMonitoringJson)
    expect(snapshot.snapshotMode).toBe('submitted')
    expect(snapshot.heartbeat.state).toBe('unavailable')
    expect(snapshot.apiBudget.remaining).toBeNull()
    expect(snapshot.queue.depth).toBeNull()
    expect(snapshot.failures.count).toBeNull()
    expect(snapshot.models).toMatchObject({
      state: 'unfinished',
      yoloe: 'unfinished',
      bioclip: 'unfinished',
    })
    expect(snapshot.scientificClaimAllowed).toBe(false)
  })

  it('accepts a complete privacy-safe live snapshot', () => {
    const snapshot = parsePublicMonitoringSnapshot(LIVE_MONITORING)
    expect(snapshot.heartbeat.workerState).toBe('running')
    expect(snapshot.apiBudget.remaining).toBe(760)
    expect(snapshot.stageHealth.failedCount).toBe(1)
    expect(snapshot.queue.depth).toBe(12)
    expect(snapshot.resources.freeDiskBytes).toBe(500_000_000_000)
  })

  it('rejects unavailable metrics carrying fabricated zeroes', () => {
    expect(() =>
      parsePublicMonitoringSnapshot({
        ...submittedMonitoringJson,
        failures: { ...submittedMonitoringJson.failures, count: 0 },
      }),
    ).toThrow(/must remain null/)
  })

  it('rejects inconsistent budget and queue arithmetic', () => {
    expect(() =>
      parsePublicMonitoringSnapshot({
        ...LIVE_MONITORING,
        apiBudget: { ...LIVE_MONITORING.apiBudget, remaining: 761 },
      }),
    ).toThrow(/equal its limit/)
    expect(() =>
      parsePublicMonitoringSnapshot({
        ...LIVE_MONITORING,
        queue: { ...LIVE_MONITORING.queue, depth: 513 },
      }),
    ).toThrow(/exceeds capacity/)
  })

  it('rejects a submitted snapshot claiming live telemetry', () => {
    expect(() =>
      parsePublicMonitoringSnapshot({
        ...submittedMonitoringJson,
        apiBudget: LIVE_MONITORING.apiBudget,
      }),
    ).toThrow(/submitted monitoring states/)
  })

  it('rejects telemetry that postdates its observation envelope', () => {
    expect(() =>
      parsePublicMonitoringSnapshot({
        ...LIVE_MONITORING,
        heartbeat: {
          ...LIVE_MONITORING.heartbeat,
          observedAt: '2026-07-18T09:00:01Z',
        },
      }),
    ).toThrow(/cannot postdate/)
  })
})
