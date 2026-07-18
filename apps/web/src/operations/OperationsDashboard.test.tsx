import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import submittedMonitoringJson from './submittedMonitoringSnapshot.json'
import {
  OperationsDashboard,
  validateMonitoringRefreshMs,
} from './OperationsDashboard'
import { parsePublicMonitoringSnapshot } from './monitoringModel'

const OFFLINE_OBSERVATION = {
  schemaVersion: 'butterflylens-public-worker-observation:v1.0.0',
  observedAt: '2026-07-18T08:29:30Z',
  heartbeatObservedAt: '2026-07-18T08:00:00Z',
  workerState: 'degraded',
  committedLiveSnapshot: {
    snapshotId: 'live:committed:41',
    mode: 'live',
    artifactFingerprint: 'a'.repeat(64),
    generatedAt: '2026-07-18T08:20:00Z',
    sourceCommit: 'b'.repeat(40),
    label: 'Committed live catalogue',
    href: '#species',
    speciesCount: 463,
  },
} as const

const LIVE_MONITORING = parsePublicMonitoringSnapshot({
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
})

describe('OperationsDashboard', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders map, review, and submitted data without live worker evidence', () => {
    render(<OperationsDashboard now={new Date('2026-07-18T08:30:00Z')} />)

    expect(screen.getByText('Worker status unavailable')).toBeVisible()
    expect(screen.getByText('Map shell loaded')).toBeVisible()
    expect(
      screen.getByRole('img', {
        name: /submitted Australia map scope; occurrence layer withheld/i,
      }),
    ).toBeVisible()
    expect(screen.getByText('Review route')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Open submitted review' })).toHaveAttribute(
      'href',
      '#verify',
    )
    expect(screen.getByText('Always bundled')).toBeVisible()
    expect(screen.getByText('463')).toBeVisible()
    for (const label of [
      'Worker heartbeat',
      'API budget',
      'Stage health',
      'Queue depth',
      'Failures',
      'Last artifact',
      'Last map refresh',
      'Model state',
      'Disk / memory',
    ]) {
      expect(screen.getByText(label)).toBeVisible()
    }
    expect(screen.getByText('Submitted fallback')).toBeVisible()
    expect(screen.getByText(/YOLOE unfinished · BioCLIP unfinished/)).toBeVisible()
  })

  it('shows a stale worker as offline while keeping the committed artifact visible', () => {
    render(
      <OperationsDashboard
        liveObservation={OFFLINE_OBSERVATION}
        now={new Date('2026-07-18T08:30:00Z')}
      />,
    )

    expect(screen.getByText('Worker offline')).toBeVisible()
    expect(screen.getByText('Committed live catalogue')).toBeVisible()
    expect(screen.getByText(/last observed heartbeat is stale/i)).toBeVisible()
    expect(screen.getByText('Review route')).toBeVisible()
  })

  it('rejects malformed live evidence without hiding static surfaces', () => {
    render(
      <OperationsDashboard
        liveObservation={{ status: 'online', privateQueue: ['secret'] }}
        now={new Date('2026-07-18T08:30:00Z')}
      />,
    )

    expect(screen.getByText('Worker status unavailable')).toBeVisible()
    expect(screen.getByText(/failed strict validation/i)).toBeVisible()
    expect(screen.getByText('Map shell loaded')).toBeVisible()
    expect(screen.getByRole('link', { name: 'Open submitted snapshot' })).toBeVisible()
  })

  it('renders a validated live operational snapshot without changing the artifact', () => {
    render(
      <OperationsDashboard
        monitoringSnapshot={LIVE_MONITORING}
        now={new Date('2026-07-18T09:00:00Z')}
      />,
    )

    expect(screen.getByText('Live snapshot')).toBeVisible()
    expect(screen.getByText('Worker online')).toBeVisible()
    expect(screen.getByText('760 of 1,000 remaining')).toBeVisible()
    expect(screen.getByText('12 of 512')).toBeVisible()
    expect(screen.getByText('Submitted Australian butterfly catalogue')).toBeVisible()
  })

  it('enforces a bounded sequential monitoring refresh policy', () => {
    expect(validateMonitoringRefreshMs(30_000)).toBe(30_000)
    expect(() => validateMonitoringRefreshMs(4_999)).toThrow(/interval/)
    expect(() => validateMonitoringRefreshMs(300_001)).toThrow(/interval/)
  })

  it('loads the optional public monitor without attaching browser credentials', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(LIVE_MONITORING), {
        headers: { 'content-type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetcher)

    render(
      <OperationsDashboard
        monitoringUrl="https://example.test/functions/v1/operations-status"
        now={new Date('2026-07-18T09:00:00Z')}
      />,
    )

    expect(await screen.findByText('Live snapshot')).toBeVisible()
    expect(fetcher).toHaveBeenCalledOnce()
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({ credentials: 'omit' })
  })

  it('retains the submitted monitor when the optional endpoint fails', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('network unavailable'))
    vi.stubGlobal('fetch', fetcher)

    render(
      <OperationsDashboard
        monitoringUrl="https://example.test/functions/v1/operations-status"
        now={new Date('2026-07-18T09:00:00Z')}
      />,
    )

    await waitFor(() => expect(fetcher).toHaveBeenCalledOnce())
    expect(screen.getByText('Submitted fallback')).toBeVisible()
    expect(screen.getByText('Worker status unavailable')).toBeVisible()
    expect(screen.getByText(/YOLOE unfinished · BioCLIP unfinished/)).toBeVisible()
  })
})
