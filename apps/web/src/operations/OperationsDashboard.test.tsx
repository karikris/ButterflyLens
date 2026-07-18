import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OperationsDashboard } from './OperationsDashboard'

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

describe('OperationsDashboard', () => {
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
})
