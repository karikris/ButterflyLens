# ButterflyLens Task 16.1 plan

Task: Freeze submitted snapshot.

Commit: `data(submission): freeze ButterflyLens snapshot`

Starting SHA: `0e07f175fa07650e90606ca07b2286807010f1de`

## Objective and judging criterion

Create one canonical immutable Submitted manifest that a judge can resolve to
the exact ALA baseline, deterministic Flickr query plan, Australian butterfly
pack, worker implementation contract, model maturity, review state, map counts,
and source Git/content SHAs without credentials, a worker, or mutable provider
state.

## Files and contracts

- Add a deterministic offline freeze/check command that reads every input from
  one committed ButterflyLens source tree and computes a canonical snapshot
  fingerprint.
- Add the versioned `data/submission/v1/submitted_snapshot.json` manifest.
- Add exact tests for physical hashes, Git objects, Flickr plan replay, worker
  and model non-claims, review non-persistence, map rights withholding, and
  canonical immutability.
- Record the Task 15.5 commit/push/Pages receipt and Task 16.1 provenance.

## Data, rights, and scientific boundary

- The rebuilt ButterflyLens ALA baseline remains authoritative. Its exact
  counts are recorded, while its public occurrence layer remains withheld on
  the three unresolved dataset-rights records.
- The Flickr plan is rebuilt from the committed Australian pack and recorded
  as `planned_not_sent`; building and checking the snapshot performs no Flickr
  API call. The active external fetch and its partial image count are excluded.
- YOLOE and BioCLIP retain null model/checkpoint versions and their required
  unfinished states. A Git tree and contract version identify the worker
  implementation; no live worker identity or heartbeat is invented.
- The review fixture is rights-cleared, but the review surface is local-draft
  only. Stored reviews, decisive reviews, consensus, and human-verified media
  remain zero; absent public map counts remain null rather than fabricated
  zeroes.
- BioMiner remains active without a complete immutable ButterflyLens handoff;
  no partial GBIF, Flickr, or model artifact is copied. GitHits remains disabled
  and is not called.

## Verification

- Deterministic snapshot rebuild and tamper rejection.
- Exact ALA, pack, Flickr, worker, model, review, map, and source-SHA tests.
- Full Python, web, browser, Deno, parity, rights, licensing, security,
  generated-file, large-file, secret, and whitespace gates.
- Exact commit, push, remote SHA, Pages deployment, and served replay check.
