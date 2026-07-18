# ButterflyLens 12.2 — Website independent of M5

Status: **implemented and locally verified; Pages publication pending the task
commit**.

Starting SHA:
`68fdc1c4dd45a245f40a2ea28d9640a0c560de3e`.

## Outcome

The public Live placeholder is now a complete operations surface backed by an
immutable JSON snapshot in the static bundle. Its current artifact is the
fingerprinted 463-species submitted catalogue. The map loads an accessible
Australia scope without a worker, while ALA occurrence points, coordinates,
and counts remain withheld behind the authoritative rebuilt-baseline dataset
rights gate. The rights-cleared review fixture and submitted species snapshot
remain directly linked and usable.

Worker evidence is an optional overlay, never a data authority. The exact
parser and pure reducer distinguish a fresh heartbeat, a stale observed
heartbeat, no heartbeat evidence, and malformed or future-dated evidence. A
fresh heartbeat reports online. A stale observed heartbeat reports offline but
retains the newest explicitly committed live artifact. No heartbeat reports
unavailable rather than inferring offline. An invalid response falls back to
the submitted snapshot without hiding the map, review, or other application
surfaces.

The browser performs no worker, Supabase, provider, or status polling in this
task. Future monitoring code can inject the exact public observation contract,
but it cannot select a live artifact unless the artifact is explicitly marked
committed, fully fingerprinted, and internally time-consistent.

## Verification

- 469 locked Python tests passed. Five new cross-artifact tests prove the site
  remains available without a worker, the snapshot matches the submitted
  catalogue, the map matches the rebuilt ALA snapshot and its release block,
  the review media SHA-256 matches, and the operations surface contains no
  polling/worker execution path.
- 16 Vitest files pass with 77 component and model tests, including fresh,
  stale/offline, absent, malformed, future, and internally inconsistent live
  observations. Three standalone Node licence tests also pass.
- All 39 frozen Edge tests, three entry-point type checks, and the 19-file Deno
  format check pass.
- Web typecheck, the `/ButterflyLens/` production build, 116-package dependency
  audit, and review-media verifier pass. The client bundle is 1,480.96 kB
  (226.00 kB gzip) and retains the existing chunk-size warning; no performance
  improvement is claimed.
- The uv lock, frozen environment, eight-package compatibility check, rights,
  repository licensing, JSON/JSONL, whitespace, and secret/scope gates pass.

## Deployment and parallel work

The existing public site at `https://karikris.github.io/ButterflyLens/` was
healthy at the starting SHA through successful GitHub Actions run
`29637562893`. The Task 12.2 push will trigger the same pinned workflow, after
which the served HTML and operations content are verified over HTTPS.

BioMiner is still active and dirty at published SHA
`c462c848c9e9cb18c4efc86fa22bbae01af05a3b`. Its published record still lists
live GBIF acquisition/durable admission as unfinished and exposes no immutable
handoff; no partial output was read or copied. The supplied GBIF download stays
queued for authoritative Parquet admission after that handoff. The user-reported
Flickr fetch remains active from its 50,000-image checkpoint; ButterflyLens made
no Flickr call and consumed no partial output. GitHits remained disabled.
YOLOE and BioCLIP remain explicitly unfinished and were not run.

Supabase MCP OAuth remains authorized but unavailable to this unreloaded
client. No Supabase/B2 service workflow was dispatched and no live infrastructure
state changed during this task.
