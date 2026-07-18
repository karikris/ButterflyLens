# ButterflyLens 12.3 — Operational monitoring

Status: **implemented and locally verified; Pages publication pending the task
commit**.

Starting SHA:
`5432772619bceebd9f5a4762993c53e84abd4de7`.

## Outcome

The operations surface now shows all nine required signals: worker heartbeat,
API budget, stage health, queue depth, failure count, last artifact, last map
refresh, model state, and disk/memory state. The bundled submitted snapshot is
complete even without live services. Unknown metrics remain `null` and render
as unavailable rather than zero. The 463-species catalogue and rebuilt ALA map
fingerprints remain visible. YOLOE and BioCLIP are explicitly unfinished, and
the monitoring contract cannot authorize a scientific claim.

The optional browser transport accepts only credential-free HTTPS, omits
credentials, cache, and referrer, aborts after a bounded timeout, enforces a
32-KiB response ceiling, strictly parses an exact versioned shape, and refreshes
sequentially at a bounded interval. A missing URL, HTTP failure, timeout,
malformed response, or invalid telemetry preserves the last valid snapshot and
all worker-independent Task 12.2 content.

## Storage and service boundary

The new `operational_monitoring_snapshots` table is a typed, append-only,
service-write projection. It stores aggregate counters and immutable artifact
fingerprints, with database constraints for exact states, nullable-unavailable
shapes, safe integers, budget arithmetic, queue capacity, time envelopes,
project/run lineage, model unfinished state, and the permanent false scientific
claim flag. It has RLS, indexed foreign keys, no browser privileges or policies,
and mutation-rejection triggers. Worker identity, raw heartbeat JSON, queue
items, error messages, coordinates, storage keys, credentials, and URLs are not
columns.

`operations-status` is the sole credential-free read boundary. Its Supabase
wrapper uses `auth: none` and the function config alone uses `verify_jwt =
false`. It reads the configured logical project through the server client,
allows only `GET` plus an exact-origin preflight, rejects query input, returns
fixed sanitized errors, and applies no-store, no-referrer, content-type,
content-security, and origin headers. The Pages workflow takes only the
non-secret optional endpoint variable; no Supabase or B2 credential enters the
browser.

## Verification

- 476 locked Python tests pass, including seven operational-monitoring and all
  existing deployment, worker-independence, rights, scientific-boundary, RLS,
  and pgTAP-plan checks.
- 18 Vitest files pass with 91 tests, including submitted/live rendering,
  optional endpoint success, endpoint failure retention, exact parser
  invariants, byte limits, credential omission, URL policy, and refresh bounds.
  Three standalone Node licence-boundary tests also pass.
- All 45 frozen Deno Edge tests pass. Four Edge entry points type-check and all
  22 function files pass formatting.
- The `/ButterflyLens/` production build, 116-package dependency audit, review
  media checksum, Pages base-path check, 52-provider rights verification,
  repository licence verification, JSON/JSONL, workflow YAML, shell syntax,
  and whitespace gates pass.
- The client bundle is 1,495.91 kB (229.64 kB gzip) and retains the existing
  chunk-size warning; no bundle-performance improvement is claimed.
- The database suite defines 33 matching pgTAP assertions. Runtime execution
  was unavailable because no local Postgres server or Docker socket is
  accessible; this limitation is not represented as a pass.

## Deployment and parallel work

Supabase OAuth is authorized for project `ujfsrohgsrmssmfqgdsp`, but the MCP
tools remain unavailable to this unreloaded client. No Supabase migration,
function deployment, B2 action, or production-services workflow was dispatched.
Until an operator supplies `BUTTERFLYLENS_PUBLIC_PROJECT_ID`, deploys the
function, and configures `BUTTERFLYLENS_MONITORING_URL`, Pages truthfully uses
the submitted fallback.

BioMiner was rechecked through its published `CURRENT_STATE.md` and storage
handoff documentation only at SHA
`079c4d846fd434d1d10973c66662ff2ca6fab53b`. Its worktree remains active, its
authoritative remaining-work ledger still lists live current-policy GBIF
acquisition and durable-media admission, and it exposes no immutable GBIF
handoff. No active output or live counter was inspected or copied. The supplied
GBIF archive remains queued for authoritative Parquet admission after that
handoff. The user-reported Flickr fetch remains external and active from its
50,000-image checkpoint; ButterflyLens made no Flickr call or partial-data
import. GitHits remained disabled and was not called. No YOLOE or BioCLIP work
was performed.
