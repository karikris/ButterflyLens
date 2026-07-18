import { describe, expect, it, vi } from 'vitest'

import submittedMonitoringJson from './submittedMonitoringSnapshot.json'
import {
  loadMonitoringSnapshot,
  validateMonitoringUrl,
  type MonitoringFetch,
} from './monitoringTransport'

function response(body: string, status = 200, contentType = 'application/json') {
  return new Response(body, { status, headers: { 'content-type': contentType } })
}

const LIVE_TRANSPORT_SNAPSHOT = {
  ...submittedMonitoringJson,
  snapshotMode: 'live',
} as const

describe('public monitoring transport', () => {
  it('accepts only credential-free HTTPS endpoints', () => {
    expect(validateMonitoringUrl('https://example.test/functions/v1/operations-status')).toBe(
      'https://example.test/functions/v1/operations-status',
    )
    for (const value of [
      'http://example.test/status',
      'https://user:secret@example.test/status',
      'https://example.test/status#private',
    ]) {
      expect(() => validateMonitoringUrl(value)).toThrow(/credential-free HTTPS/)
    }
  })

  it('loads an exact bounded snapshot without credentials, cache, or referrer', async () => {
    const fetcher = vi.fn<MonitoringFetch>().mockResolvedValue(
      response(JSON.stringify(LIVE_TRANSPORT_SNAPSHOT)),
    )
    const result = await loadMonitoringSnapshot(
      'https://example.test/functions/v1/operations-status',
      fetcher,
    )
    expect(result.snapshotMode).toBe('live')
    expect(fetcher).toHaveBeenCalledOnce()
    expect(fetcher.mock.calls[0]?.[1]).toMatchObject({
      method: 'GET',
      credentials: 'omit',
      cache: 'no-store',
      referrerPolicy: 'no-referrer',
    })
  })

  it('rejects errors, non-JSON bodies, and oversized responses', async () => {
    const endpoint = 'https://example.test/functions/v1/operations-status'
    await expect(
      loadMonitoringSnapshot(endpoint, async () => response('{}', 503)),
    ).rejects.toThrow(/unavailable/)
    await expect(
      loadMonitoringSnapshot(endpoint, async () => response('{}', 200, 'text/plain')),
    ).rejects.toThrow(/type/)
    await expect(
      loadMonitoringSnapshot(endpoint, async () => response('x'.repeat(32_769))),
    ).rejects.toThrow(/size/)
    await expect(
      loadMonitoringSnapshot(endpoint, async () => response('é'.repeat(16_385))),
    ).rejects.toThrow(/size/)
  })

  it('rejects timeout values outside the bounded policy', async () => {
    await expect(
      loadMonitoringSnapshot('https://example.test/status', async () => response('{}'), 10),
    ).rejects.toThrow(/timeout/)
  })
})
