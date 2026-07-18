import { defineConfig } from '@playwright/test'


const desktop = {
  viewport: { width: 1280, height: 720 },
  screen: { width: 1280, height: 720 },
} as const

const browserTest = '**/public-experience.browser.spec.ts'
const visualTest = '**/public-experience.visual.spec.ts'

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results/playwright',
  fullyParallel: true,
  forbidOnly: true,
  retries: 0,
  workers: 4,
  reporter: [['line']],
  expect: {
    timeout: 5_000,
    toHaveScreenshot: {
      animations: 'disabled',
      caret: 'hide',
      maxDiffPixelRatio: 0.01,
    },
  },
  use: {
    baseURL: 'http://127.0.0.1:4173',
    colorScheme: 'light',
    locale: 'en-AU',
    timezoneId: 'Australia/Sydney',
    serviceWorkers: 'block',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  webServer: {
    command: 'npm run preview -- --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
    timeout: 60_000,
  },
  projects: [
    {
      name: 'chromium-1280x720',
      testMatch: [browserTest, visualTest],
      use: { browserName: 'chromium', ...desktop },
    },
    {
      name: 'firefox-1280x720',
      testMatch: browserTest,
      use: { browserName: 'firefox', ...desktop },
    },
    {
      name: 'webkit-1280x720',
      testMatch: browserTest,
      use: { browserName: 'webkit', ...desktop },
    },
    {
      name: 'mobile-chromium',
      testMatch: [browserTest, visualTest],
      use: {
        browserName: 'chromium',
        viewport: { width: 390, height: 844 },
        screen: { width: 390, height: 844 },
        deviceScaleFactor: 1,
        hasTouch: true,
        isMobile: true,
      },
    },
    {
      name: 'reduced-motion-chromium',
      testMatch: browserTest,
      use: {
        browserName: 'chromium',
        ...desktop,
        contextOptions: { reducedMotion: 'reduce' },
      },
    },
    {
      name: 'forced-colors-chromium',
      testMatch: [browserTest, visualTest],
      use: {
        browserName: 'chromium',
        ...desktop,
        contextOptions: { forcedColors: 'active' },
      },
    },
    {
      name: 'no-webgl-chromium',
      testMatch: browserTest,
      use: { browserName: 'chromium', ...desktop },
    },
  ],
})
