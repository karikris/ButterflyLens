# ButterflyLens Task 15.3 plan

Task: E2E tests.

Commit: `test(e2e): cover community journey`

## Objective

Add one credential-free judge-journey test that renders the submitted
application and follows all eight required steps in order: landing, review,
map, species, live pipeline, GPT replay, quality, and evidence export.

## Files and contracts

- Add a Vitest/jsdom journey under `apps/web/src` so it exercises the real
  assembled `App` rather than isolated mocks.
- Use the rights-cleared submitted review fixture, accepted species catalogue,
  submitted operations/map snapshot, stored analyst replay, submitted quality
  projection, and governed Darwin Core/ALA policy links.
- Add no new provider client, credential, model, snapshot, or data artifact.

## Tests and judging criterion

- Verify the route is usable without login, worker, model, or network access.
- Perform a blind local review draft and prove it does not fabricate a stored
  review or public map update.
- Inspect the exact accepted species, worker-independent pipeline, stored GPT
  trace, unavailable quality metrics, and export preparation boundary.
- Run the focused journey, complete web suite/build, and full repository gates.

## Risks and rights

- A component E2E test is not a real-browser or visual claim; Task 15.4 owns
  Chromium, Firefox, WebKit, viewport, contrast, and visual coverage.
- The submitted review fixture retains its exact Wikimedia Commons attribution.
- Export remains policy/preparation inspection because no release-ready public
  occurrence archive exists; the test must not invent a download.
- BioMiner's Phase 14 handoff work is active. The first TaxaLens exporter commit
  contains implementation/tests but no complete ButterflyLens data handoff, so
  no partial artifact is copied.
- GitHits remains disabled, Flickr remains external, and YOLOE/BioCLIP remain
  unfinished and unexecuted.
