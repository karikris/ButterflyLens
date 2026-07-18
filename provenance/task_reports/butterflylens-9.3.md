# ButterflyLens 9.3 — Reviewer reliability estimates

Status: **implemented locally; database integration gate unavailable in this
environment**.

Starting SHA: `77d9ab117440e6d10550805d4aa14267a42ed181`

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. BioMiner remains active on unrelated work; no BioMiner
record or data was inspected or copied.

## Outcome

The deterministic estimator measures control accuracy, sensitivity and
specificity where each relevant class has enough evidence, target-versus-peer
pairwise agreement, nominal Krippendorff alpha, and exact-lineage adjudicated
overlap for one family × source provider × life stage × visual-domain cell.

Policy eligibility requires 20 controls, at least 5 positive and 5 negative
controls, 10 independent overlap items, and 5 independently adjudicated
overlaps. Eligible estimates use the predeclared `Beta(15, 5)` prior, a 95%
posterior normal-approximation interval, shrinkage toward the equal-weight
accuracy of 0.75, and a monotonic weight capped to 0.5–2.0. Sparse cells return
an unavailable estimate and persist the equal weight of 1 with explicit
blockers.

The database mapping preserves every metric and evidence fingerprint. A
fixed-search-path admission trigger enforces the exact estimator/policy
versions, thresholds, class minima, privacy flags, no-model/no-majority
boundary, metric-column parity, monotonic domain revisions, and append-only
supersession under an advisory transaction lock. Browser roles cannot write
scores; reviewers may read only their own private rows and authorized curators
retain governance access.

## Evidence and boundaries

The Supabase skills informed explicit privileges, existing RLS preservation,
fixed search paths, foreign-key indexes, and serialized append-only admission.
Current official Supabase RLS, database-function, and Data API documentation was
used because Valyu was unavailable. TaxaLens reliability precedent was
inspected from an immutable commit; no code, fixture, label, score, or reviewer
record was copied.

No public ranking, scientific claim, release decision, Flickr API call, YOLOE
work, BioCLIP work, model artifact, model inference, or biodiversity result was
produced. YOLOE and BioCLIP remain explicitly unfinished.

## Verification

- Focused reliability, storage, database, policy, and control suites — 26 tests
  passed.
- Full Python suite — 331 tests passed.
- Contract parity — passed (24 schemas, 20 valid, 20 invalid, 20 versions,
  15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check and production
  build passed.
- Web dependency report — 116 packages verified; review-media fingerprint
  passed.
- pgTAP fixture — 26 assertions defined; Docker-backed execution remains
  unavailable and is not reported as executed.
- Supabase CLI migration generation was unavailable; the timestamped migration
  follows the existing repository convention.
- Rights verification passed for 52 tracked provider payloads; licence
  verification passed for 310 tracked files, 2 dependency manifests, and 0
  model files.
- JSONL provenance, staged whitespace, secret, model-file, cache, and large-file
  gates passed.
