import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

import { chromium } from '@playwright/test'

const sourceCommit = process.env.BUTTERFLYLENS_CAPTURE_COMMIT
const capturedAt = process.env.BUTTERFLYLENS_CAPTURED_AT
const outputDirectory = process.env.BUTTERFLYLENS_CAPTURE_OUTPUT
const baseUrl = process.env.BUTTERFLYLENS_CAPTURE_URL ?? 'http://127.0.0.1:4173/'

if (!/^[0-9a-f]{40}$/.test(sourceCommit ?? '')) {
  throw new Error('BUTTERFLYLENS_CAPTURE_COMMIT must be an exact Git SHA.')
}
if (
  typeof capturedAt !== 'string' ||
  new Date(capturedAt).toISOString() !== capturedAt
) {
  throw new Error('BUTTERFLYLENS_CAPTURED_AT must be a normalized ISO instant.')
}
if (typeof outputDirectory !== 'string' || outputDirectory.trim() === '') {
  throw new Error('BUTTERFLYLENS_CAPTURE_OUTPUT is required.')
}

const captureRoot = path.resolve(outputDirectory)
const applicationOrigin = new URL(baseUrl).origin
const configurations = [
  capture('explore-desktop-1440x900', 'explore', 1440, 900, {
    scrollToFragment: false,
  }),
  capture('explore-desktop-1280x720', 'explore', 1280, 720, {
    scrollToFragment: false,
  }),
  capture('explore-mobile-390x844', 'explore', 390, 844, {
    hasTouch: true,
    isMobile: true,
    scrollToFragment: false,
  }),
  capture('explore-reduced-motion-1280x720', 'explore', 1280, 720, {
    reducedMotion: 'reduce',
    scrollToFragment: false,
  }),
  capture('explore-forced-colors-1280x720', 'explore', 1280, 720, {
    forcedColors: 'active',
    scrollToFragment: false,
  }),
  capture('map-desktop-1280x720', 'live', 1280, 720),
  capture('verify-desktop-1280x720', 'verify', 1280, 720),
  capture('species-desktop-1280x720', 'species', 1280, 720),
  capture('operations-desktop-1280x720', 'operations', 1280, 720),
  capture('quality-desktop-1280x720', 'quality', 1280, 720),
  capture('community-desktop-1280x720', 'contributors', 1280, 720),
]

await mkdir(captureRoot, { recursive: true })
const browser = await chromium.launch({ headless: true })
const browserVersion = browser.version()
const screenshots = []

try {
  for (const configuration of configurations) {
    const context = await browser.newContext({
      colorScheme: 'light',
      locale: 'en-AU',
      serviceWorkers: 'block',
      timezoneId: 'Australia/Sydney',
      viewport: configuration.viewport,
      screen: configuration.viewport,
      deviceScaleFactor: 1,
      hasTouch: configuration.hasTouch,
      isMobile: configuration.isMobile,
      reducedMotion: configuration.reducedMotion,
      forcedColors: configuration.forcedColors,
    })
    const page = await context.newPage()
    const externalRequests = []
    await page.route('**/*', async (route) => {
      const requestUrl = new URL(route.request().url())
      if (requestUrl.origin !== applicationOrigin) {
        externalRequests.push(route.request().url())
        await route.abort('blockedbyclient')
        return
      }
      await route.continue()
    })
    const targetUrl = configuration.scrollToFragment
      ? `${baseUrl}#${configuration.fragment}`
      : baseUrl
    await page.goto(targetUrl, {
      waitUntil: 'networkidle',
    })
    await page.evaluate(async () => document.fonts.ready)
    if (configuration.scrollToFragment) {
      await page.locator('html').evaluate((element) => {
        element.style.scrollBehavior = 'auto'
      })
      await page.locator(`#${configuration.fragment}`).evaluate((element) =>
        element.scrollIntoView({ block: 'start', inline: 'nearest' }),
      )
    }
    await page.waitForTimeout(100)
    if (externalRequests.length > 0) {
      throw new Error(
        `${configuration.name} attempted external requests: ${externalRequests.join(', ')}`,
      )
    }
    const filename = `${configuration.name}.png`
    const destination = path.join(captureRoot, filename)
    await page.screenshot({
      path: destination,
      animations: 'disabled',
      caret: 'hide',
      fullPage: false,
    })
    const bytes = await readFile(destination)
    screenshots.push({
      filename,
      fragment: configuration.fragment,
      capturePosition: configuration.scrollToFragment
        ? 'fragment-start'
        : 'document-start',
      viewport: configuration.viewport,
      pixelSize: configuration.viewport,
      hasTouch: configuration.hasTouch,
      isMobile: configuration.isMobile,
      reducedMotion: configuration.reducedMotion,
      forcedColors: configuration.forcedColors,
      byteCount: bytes.byteLength,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      externalRequestCount: 0,
    })
    await context.close()
  }
} finally {
  await browser.close()
}

const manifest = {
  schemaVersion: 'butterflylens-redesign-baseline-captures/v1',
  sourceCommit,
  capturedAt,
  baseUrl,
  applicationOrigin,
  browser: 'chromium',
  browserVersion,
  playwrightVersion: '1.61.1',
  locale: 'en-AU',
  timezoneId: 'Australia/Sydney',
  colorScheme: 'light',
  serviceWorkers: 'blocked',
  externalNetworkPolicy: 'all non-application origins aborted',
  screenshots,
}
await writeFile(
  path.join(captureRoot, 'manifest.json'),
  `${JSON.stringify(manifest, null, 2)}\n`,
  'utf8',
)

function capture(name, fragment, width, height, options = {}) {
  return Object.freeze({
    name,
    fragment,
    viewport: Object.freeze({ width, height }),
    hasTouch: options.hasTouch ?? false,
    isMobile: options.isMobile ?? false,
    reducedMotion: options.reducedMotion ?? 'no-preference',
    forcedColors: options.forcedColors ?? 'none',
    scrollToFragment: options.scrollToFragment ?? true,
  })
}
