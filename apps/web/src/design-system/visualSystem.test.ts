import { describe, expect, it } from 'vitest'

import visualSystem from './visualSystem.json'

describe('ButterflyLens visual-system contract', () => {
  it('locks the requested design principles and responsive targets', () => {
    expect(visualSystem.schemaVersion).toBe('butterflylens-visual-system:v1.0.0')
    expect(visualSystem.browserThemeColor).toBe(
      visualSystem.palette['bl-eucalypt-850'],
    )
    expect(visualSystem.principles).toEqual([
      'photographic',
      'distinctly_australian',
      'scientific_editorial',
      'optimistic_evidence_disciplined',
      'no_generic_gradient',
      'no_admin_template',
    ])
    expect(visualSystem.accessibility.responsiveViewports).toEqual([
      { width: 1280, height: 720, label: 'desktop_judge_replay' },
      { width: 390, height: 844, label: 'mobile_portrait' },
    ])
    expect(visualSystem.photography.pixelAlterationAllowed).toBe(false)
  })

  it('keeps every declared normal-text pair above WCAG AA contrast', () => {
    for (const [foreground, background] of visualSystem.normalTextContrastPairs) {
      expect(
        contrast(
          paletteColour(foreground),
          paletteColour(background),
        ),
      ).toBeGreaterThanOrEqual(
        visualSystem.accessibility.normalTextMinimumContrast,
      )
    }
  })

  it('declares textual states and generous interaction boundaries', () => {
    expect(visualSystem.evidenceStates).toEqual([
      'submitted',
      'verified',
      'caution',
      'unavailable',
      'unfinished',
      'critical',
    ])
    expect(visualSystem.accessibility.minimumTargetCssPixels).toBeGreaterThanOrEqual(24)
    expect(visualSystem.accessibility.minimumViewportCssPixels).toBe(320)
    expect(visualSystem.accessibility.focusOutlineCssPixels).toBeGreaterThanOrEqual(2)
    expect(visualSystem.accessibility.forcedColours).toBe(true)
    expect(visualSystem.accessibility.reducedMotion).toBe(true)
  })
})

function paletteColour(name: string): string {
  const colour = visualSystem.palette[name as keyof typeof visualSystem.palette]
  if (colour === undefined) throw new Error(`missing palette colour ${name}`)
  return colour
}

function contrast(first: string, second: string): number {
  const [lighter, darker] = [luminance(first), luminance(second)].sort(
    (left, right) => right - left,
  )
  return (lighter + 0.05) / (darker + 0.05)
}

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((offset) => {
    const value = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255
    return value <= 0.04045
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * channels[0]! + 0.7152 * channels[1]! + 0.0722 * channels[2]!
}
