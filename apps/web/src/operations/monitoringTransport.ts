import {
  parsePublicMonitoringSnapshot,
  type PublicMonitoringSnapshot,
} from './monitoringModel'

export type MonitoringFetch = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>

export function validateMonitoringUrl(value: string) {
  if (value.length === 0 || value.length > 2_048) {
    throw new Error('monitoring URL length is invalid')
  }
  const url = new URL(value)
  if (
    url.protocol !== 'https:' ||
    url.username !== '' ||
    url.password !== '' ||
    url.hash !== ''
  ) {
    throw new Error('monitoring URL must be credential-free HTTPS')
  }
  return url.toString()
}

export async function loadMonitoringSnapshot(
  endpoint: string,
  fetcher: MonitoringFetch = fetch,
  timeoutMs = 3_000,
): Promise<PublicMonitoringSnapshot> {
  if (!Number.isInteger(timeoutMs) || timeoutMs < 250 || timeoutMs > 10_000) {
    throw new Error('monitoring timeout is invalid')
  }
  const url = validateMonitoringUrl(endpoint)
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetcher(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      credentials: 'omit',
      cache: 'no-store',
      referrerPolicy: 'no-referrer',
      signal: controller.signal,
    })
    if (!response.ok) throw new Error('monitoring endpoint is unavailable')
    const contentType = response.headers.get('content-type') ?? ''
    if (!contentType.toLowerCase().startsWith('application/json')) {
      throw new Error('monitoring response type is invalid')
    }
    const body = await response.text()
    const bodyBytes = new TextEncoder().encode(body).byteLength
    if (bodyBytes === 0 || bodyBytes > 32_768) {
      throw new Error('monitoring response size is invalid')
    }
    let decoded: unknown
    try {
      decoded = JSON.parse(body)
    } catch {
      throw new Error('monitoring response is invalid JSON')
    }
    return parsePublicMonitoringSnapshot(decoded)
  } finally {
    clearTimeout(timeout)
  }
}
