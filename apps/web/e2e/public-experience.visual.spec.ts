import { expect, test } from '@playwright/test'


test('matches the submitted landing viewport', async ({ page }) => {
  await page.goto('/', { waitUntil: 'networkidle' })
  await page.evaluate(async () => document.fonts.ready)
  await expect(
    page.getByRole('heading', {
      level: 1,
      name: 'Look closer. Strengthen what we know.',
    }),
  ).toBeVisible()
  await expect(page).toHaveScreenshot('submitted-landing.png', {
    fullPage: false,
  })
})
