# ButterflyLens 9.5 — Representative dataset-quality audit

Status: **implemented locally; database integration gate unavailable in this
environment**.

Starting SHA: `b774a993adca9320063dc9244a09465527e25172`.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. Its active work was not inspected and no BioMiner data
was copied.

## Outcome

The new versioned audit policy and deterministic estimator calculate population
precision only for a blind probability audit with an immutable sampling-frame
fingerprint, exact inclusion probabilities, fully declared strata, and owner
plus observation grouping evidence.

The point estimate is a stratified Hájek weighted proportion. Population
stratum weights are explicit or derived from complete population counts.
Effective sample size is labelled as the Kish weight-inequality diagnostic, not
as a complete dependence correction. A deterministic percentile bootstrap
resamples connected owner/observation groups within strata; groups crossing a
stratum boundary invalidate the estimate. The persisted seed is a fingerprint.
The audit manifest retains exact review and consensus lineage while replacing
raw owner/observation identifiers with sampling-frame-scoped fingerprints.

Targeted failure discovery remains a separate lane. It retains reviewed,
decisive, supported, failure, and unresolved counts, but its precision estimate,
interval, and effective sample size are always null. Missing probability,
stratum, blindness, or grouping evidence similarly produces an explicit
unavailable snapshot rather than a zero substitute.

Postgres persists method versions, sampling design, uncertainty evidence,
append-only monotonic plan revisions, and exact fingerprinted payload parity. A
fixed-search-path trigger denies model votes, scientific claims, browser
writes, targeted population estimates, malformed representative estimates, and
mutation. Existing RLS reads remain in force and supersession is indexed.

## Evidence and boundaries

Primary complex-survey and clustered-bootstrap publications informed the
weight, ESS, and grouped-resampling boundaries. The Supabase skills informed
explicit privileges, fixed search paths, indexed foreign keys, advisory locks,
and RLS preservation. Current official sources were used because Valyu remained
unavailable.

No TaxaLens source or data was copied. No provider record, Flickr API call,
BioMiner record, YOLOE work, BioCLIP work, model inference, or biodiversity
result occurred. YOLOE and BioCLIP remain explicitly unfinished. The rebuilt
ButterflyLens baseline remains authoritative.

## Verification

- Focused estimator, policy, database, and storage suites — 19 tests passed.
- Full Python suite — 369 tests passed.
- Contract parity — passed (25 schemas, 21 valid, 21 invalid, 21 versions,
  15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check and production
  build passed.
- Web dependency report — 116 packages verified; review-media fingerprint
  passed.
- pgTAP fixture — 26 assertions defined; Docker-backed execution remains
  unavailable and is not reported as executed.
- Supabase CLI remains unavailable; the timestamped migration follows the
  existing repository convention.
- Rights verification passed for 52 tracked provider payloads; licensing
  passed for 329 tracked files, 2 dependency manifests, and 0 model files.
- The production dependency audit reported 0 vulnerabilities; staged secret,
  model-file, cache, generated-bulk, and large-file gates passed.
