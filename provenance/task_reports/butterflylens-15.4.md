# ButterflyLens 15.4 — browser and visual testing

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`8df760669d9c0214c602309de49ddbfdde2b3ed5`.

## Outcome

ButterflyLens now has a pinned Playwright 1.61.1 public-experience matrix
against the built production application. The matrix runs Chromium, Firefox,
and WebKit at 1280×720; mobile Chromium at 390×844; Chromium with reduced
motion; Chromium with forced colours active; and Chromium after WebGL context
creation is forced to return `null`.

Every browser project loads only the local production-preview origin and fails
if an external request occurs. It verifies the submitted landing state,
scientific hypothesis language, withheld occurrence layer, unavailable worker
state, analyst and quality sections, governed export link, exact navigation,
and absence of page-level horizontal overflow or console/page errors. Mobile
also checks its exact viewport and 44-pixel navigation targets. The emulation
projects prove their media queries and reduced-motion scroll behavior. The
no-WebGL project proves both WebGL context types are unavailable and that the
application renders without a canvas dependency.

Vitest explicitly excludes `e2e/**`, keeping component tests and Playwright
tests in their intended runners. The package lock and dependency licence report
record `@playwright/test`, `playwright`, and `playwright-core` at the exact
1.61.1 release.

## Visual baselines

Three reviewed first-viewport PNG baselines are committed:

- Chromium desktop, 1280×720, 99,687 bytes;
- mobile Chromium, 390×844, 67,546 bytes;
- forced-colour Chromium, 1280×720, 80,620 bytes.

The captures contain the project-owned landing UI only. They stop before the
review experience, so no new derivative of the attributed review photograph
is committed. Screenshot comparison disables animation, hides the caret, and
permits at most a one-percent pixel difference. Playwright and all browser
revisions are pinned because baselines remain operating-system and browser
version sensitive.

## Browser verification

- Playwright 1.61.1: all 10 browser/visual tests pass in 5.5 seconds on the
  non-update regression run.
- Browser revisions: Chrome for Testing/headless shell 149.0.7827.55
  (Chromium 1228), Firefox 151.0 (1532), and WebKit 26.5 (2311).
- The Ubuntu 26.04 WSL host did not have Playwright's system browser libraries
  installed and `sudo` required an unavailable interactive password. Exact
  Ubuntu `libnspr4`, `libnss3`, `libasound2t64`, `libgles2`, and
  `gstreamer1.0-libav` packages were therefore extracted into an untracked
  user cache and supplied through `LD_LIBRARY_PATH`; host validation alone was
  skipped. All three engines then launched and executed the tests. Normal
  hosts and CI should use Playwright's documented browser/dependency install.
- The initial emulation configuration used direct project keys, which this
  runner treated as unset. Moving `reducedMotion` and `forcedColors` into
  Playwright `contextOptions` made both browser media-query assertions pass.

## Repository verification

- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  typecheck, the 119-package dependency audit, media checksum, and production
  build pass. The existing chunk-size warning is unchanged and non-blocking.
- The complete locked Python suite passes all 572 tests in 20.9 seconds.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixtures, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting with cached Deno 2.9.3.
- Rights, licensing, JSON/JSONL, whitespace, staged-scope, secret, generated
  file, model/media, and large-file gates are completed immediately before the
  commit.

The first raw Python discovery command omitted the local package root and
therefore reported one import error after 562 executed tests. The corrected
documented `PYTHONPATH=packages/contracts/python` run passed all 572 tests. The
first aggregate Vitest run exposed the Playwright-file collection conflict;
the runner separation above fixed it and the complete web gate passed.

## Research and external-work boundary

Current official Playwright guidance was used for multi-browser projects,
pinned browser installation, browser context emulation, and screenshot
comparisons. GitHits remained disabled by explicit user instruction and was
not called. No external implementation was copied.

BioMiner remains at
`5635dfcc9f6a0019cd00bb56fcc02ad5e2b48053`, with the intermediate TaxaLens
pooling exporter committed and active uncommitted quality/handoff follow-on
work. It still has no complete immutable ButterflyLens data handoff, so no
partial artifact was copied. The rebuilt ButterflyLens ALA baseline remains
authoritative.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, Flickr result inspection or
import, Supabase or B2 mutation, provider submission, live GPT call, YOLOE
work, BioCLIP work, scientific model call, scientific inference, or third-party
media copy occurred.

Next safe task: enforce the Task 15.5 security and release gates after this
exact task commit is pushed and its Pages deployment is verified.
