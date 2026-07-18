import { expect, test } from '@playwright/test'


test.beforeEach(async ({ page }, testInfo) => {
  if (testInfo.project.name !== 'no-webgl-chromium') return
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function getContext(
      contextId: string,
      ...arguments_: unknown[]
    ) {
      if (/^webgl2?$/u.test(contextId)) return null
      return original.call(this, contextId, ...arguments_)
    } as typeof original
  })
})

test('renders the complete public fallback without browser or network errors', async ({
  page,
}, testInfo) => {
  const browserErrors: string[] = []
  const externalRequests: string[] = []
  page.on('pageerror', (error) => browserErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') browserErrors.push(message.text())
  })
  await page.route('**/*', async (route) => {
    const requestUrl = new URL(route.request().url())
    if (requestUrl.origin === 'http://127.0.0.1:4173') {
      await route.continue()
      return
    }
    externalRequests.push(requestUrl.href)
    await route.abort('blockedbyclient')
  })

  await page.goto('/', { waitUntil: 'networkidle' })
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Look closer. Strengthen what we know.',
    }),
  ).toBeVisible()
  await expect(page.getByText('Search results are hypotheses—not biodiversity records.')).toBeVisible()
  await expect(page.getByText('Occurrence layer withheld').first()).toBeVisible()
  await expect(page.getByText('Worker status unavailable')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Ask ButterflyLens' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Evidence strength, without guesswork.' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Darwin Core export' })).toHaveAttribute(
    'href',
    'https://github.com/karikris/ButterflyLens/blob/main/DARWIN_CORE_EXPORT.md',
  )

  const navigationLinks = page.getByRole('navigation', { name: 'Primary' }).getByRole('link')
  await expect(navigationLinks).toHaveCount(8)
  const fragments = await navigationLinks.evaluateAll((links) =>
    links.map((link) => link.getAttribute('href')),
  )
  expect(fragments).toEqual([
    '#explore',
    '#verify',
    '#species',
    '#live',
    '#quality',
    '#contributors',
    '#ask-butterflylens',
    '#about',
  ])
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBe(true)

  const viewport = page.viewportSize()
  expect(viewport).not.toBeNull()
  if (testInfo.project.name.includes('1280x720')) {
    expect(viewport).toEqual({ width: 1280, height: 720 })
  }
  if (testInfo.project.name === 'mobile-chromium') {
    expect(viewport).toEqual({ width: 390, height: 844 })
    await expect(page.getByRole('link', { name: 'Skip to main content' })).toBeAttached()
    const smallestTarget = await navigationLinks.evaluateAll((links) =>
      Math.min(...links.map((link) => link.getBoundingClientRect().height)),
    )
    expect(smallestTarget).toBeGreaterThanOrEqual(44)
  }
  if (testInfo.project.name === 'reduced-motion-chromium') {
    expect(
      await page.evaluate(() => ({
        preference: matchMedia('(prefers-reduced-motion: reduce)').matches,
        scrollBehavior: getComputedStyle(document.documentElement).scrollBehavior,
      })),
    ).toEqual({ preference: true, scrollBehavior: 'auto' })
  }
  if (testInfo.project.name === 'forced-colors-chromium') {
    expect(await page.evaluate(() => matchMedia('(forced-colors: active)').matches)).toBe(true)
    await expect(page.locator('.bl-state-badge__marker').first()).toBeVisible()
  }
  if (testInfo.project.name === 'no-webgl-chromium') {
    expect(
      await page.evaluate(() => {
        const canvas = document.createElement('canvas')
        return {
          canvasCount: document.querySelectorAll('canvas').length,
          webgl: canvas.getContext('webgl'),
          webgl2: canvas.getContext('webgl2'),
        }
      }),
    ).toEqual({ canvasCount: 0, webgl: null, webgl2: null })
  }

  expect(externalRequests).toEqual([])
  expect(browserErrors).toEqual([])
})
