# ButterflyLens 12.4 — Incident and fallback behavior

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`e605864a786bf6897135ba968b320c86c87b967f`.

## Outcome

The worker package now exposes a closed, deterministic incident planner for all
eight required scenarios: M5 sleep, network outage, Flickr outage, B2 outage,
Supabase outage, model crash, corrupted checkpoint, and rate-limit exhaustion.
Every plan names the affected boundary, immediate stage pause, blocked actions,
checkpoint treatment, exact evidence required before resume, current monitoring
state, and a canonical SHA-256 plan fingerprint.

Planning is deliberately side-effect free. It executes no retry, provider call,
storage write, database mutation, checkpoint change, model load, or recovery.
Every incident retains local sources and the append-only committed-work journal,
keeps the submitted snapshot and last committed artifact queryable, forbids
duplicate work, and permanently denies scientific authority. The model-crash
case is a policy simulation with model execution false; YOLOE and BioCLIP remain
unfinished.

## Required incident behavior

- M5 sleep pauses all worker stages and requires a fresh fenced lease plus
  checkpoint verification after wake. The public offline projection continues
  serving the submitted and last committed artifacts.
- Network outage pauses all outbound stages and blocks immediate retry until a
  bounded scheduler-driven health probe after backoff.
- Flickr outage pauses Flickr stages, blocks requests, unbounded retry, and
  credential rotation, and requires both provider recovery and available
  governed budget.
- B2 outage pauses artifact commit/publication, blocks ambiguous write retry and
  local-source deletion, and requires a durable write acknowledgement.
- Supabase outage pauses remote control/telemetry persistence, blocks fabricated
  acknowledgements, and keeps local append-only journals and the static site
  authoritative.
- Model crash pauses model stages and blocks model execution, evidence
  publication, and fallback identity claims until an operator verifies the
  runtime and checkpoint.
- Corrupted checkpoint fails checksum verification, is marked for quarantine
  without deletion, and permits only affected uncommitted work to rebuild from
  verified inputs. Separately journalled committed work remains reusable.
- Rate-limit exhaustion blocks Flickr calls, credential rotation, budget-lane
  bypass, and early retry until a new UTC window and fresh budget ledger exist.

## Checkpoint boundary

The checkpoint verifier opens a regular file without following symlinks, checks
a 256-MiB default ceiling before and during streaming, hashes it incrementally,
and returns a fingerprinted verification receipt only on an exact SHA-256 match.
Missing, unsafe, oversized, symlinked, or mismatching files fail closed. It does
not write, move, quarantine, or delete the file.

## Verification

- 486 locked Python tests pass. Ten new resilience tests exercise all eight
  incidents, exact vocabulary and deterministic fingerprints, input closure,
  M5 public-site continuity, checkpoint byte/symlink/checksum rejection,
  committed-work reuse, and the absence of provider/storage/database/model
  clients. Nineteen adjacent restart, durable-media, and Flickr budget tests
  also pass as a focused gate.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the `/ButterflyLens/` production build, dependency audit, review
  media checksum, and Pages base-path check pass. The unchanged bundle retains
  its existing chunk-size warning.
- Rights verification covers 52 tracked provider payloads. Repository licensing
  reports zero model files. JSON/JSONL, workflow YAML, shell syntax, whitespace,
  and release gates pass.

## External and parallel-work boundary

No Flickr API call, synthetic HTTP request to Flickr, B2 action, Supabase call,
production workflow dispatch, model load, YOLOE execution, BioCLIP execution, or
scientific inference occurred. GitHits remained disabled and was not called.

BioMiner remains active at published SHA
`079c4d846fd434d1d10973c66662ff2ca6fab53b`. Its published current-state ledger
still lists live GBIF acquisition and durable-media admission as remaining and
provides no immutable GBIF handoff. No partial output or live counter was read
or copied. The GBIF Parquet import remains deferred. The user-reported Flickr
fetch remains external and active from its 50,000-image checkpoint; no partial
Flickr output was consumed.
