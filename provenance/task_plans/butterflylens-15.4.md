# ButterflyLens Task 15.4 plan

Task: Browser and visual testing.

Commit: `test(web): validate public experience`

## Objective

Pin Playwright and validate the built submitted application in real Chromium,
Firefox, and WebKit engines, plus explicit mobile, 1280×720, reduced-motion,
forced/high-contrast, and WebGL-unavailable configurations.

## Files and contracts

- Add the exact `@playwright/test` dependency and reproducible npm scripts.
- Add a Playwright configuration with a production preview server, closed
  local origin, blocked service workers, fixed projects, bounded artifacts,
  and no external-network dependency.
- Add one cross-browser public-experience specification and selected stable
  landing-page screenshot baselines for desktop Chromium, mobile Chromium, and
  forced-colour Chromium.
- Keep screenshots limited to the first viewport so no new copy of the
  attributed review photograph is embedded in visual baselines.

## Test matrix

- Desktop Chromium, Firefox, and WebKit at 1280×720.
- Mobile Chromium at 390×844 with touch/mobile emulation.
- Chromium at 1280×720 with `prefers-reduced-motion: reduce`.
- Chromium at 1280×720 with forced colours active as the high-contrast gate.
- Chromium at 1280×720 after WebGL context creation is forced to return null.
- Every project checks navigation, scientific boundary text, map fallback,
  horizontal overflow, browser errors, and network scope.

## Risks, rights, and judging criterion

- Screenshot comparisons are host/browser-version sensitive, so Playwright and
  all browser revisions are pinned and the baselines are deliberately narrow.
- The visual viewport excludes the review image; no new third-party media
  derivative is committed.
- No provider, Flickr, GPT, Supabase, B2, model, WebGL, or worker call occurs.
- BioMiner remains active on its intermediate Phase 14 handoff, so no partial
  artifact is copied.
- GitHits remains disabled. Current official Playwright project, browser,
  emulation, and visual-comparison guidance is recorded through primary docs.
