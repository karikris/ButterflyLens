# ButterflyLens 9.6 — Community quality dashboard

Status: **implemented locally; no representative review snapshot exists**.

Starting SHA: `cb79bfef0adc2a11c30f09281ec504dbbf9aea1f`.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. Its active GBIF evidence-database work was not
inspected, interrupted, or copied.

## Outcome

The credential-free submitted web app now includes a community quality
dashboard. It shows the reviewed sample, decisive reviews, precision and
interval availability, aggregate reviewer agreement, species-quality
availability, source-bound reference diagnostics, all reference-health flags,
and every release blocker.

The submitted replay has zero reviewed and decisive representative-audit rows.
It therefore displays precision, confidence interval, reviewer agreement, and
species quality as unavailable. Zero is explicitly labelled as a workflow count,
not zero-percent precision. Reference coverage remains a diagnostic rather than
a human-verified identity or species-quality estimate.

The bundled projection records the physical SHA-256 of the quality manifest,
the semantic reference-bank fingerprint, the manifest timestamp, and the
user-designated `ButterflyLens rebuilt baseline`. A strict runtime parser rejects
contradictory availability, fake estimates, impossible counts, missing or
duplicate blockers, malformed hashes, model votes, and scientific-claim
authority. A Python parity suite proves that the projection remains an exact
view of the authoritative reference manifests.

## Evidence and boundaries

The TaxaLens quality UI was inspected only for fail-closed presentation
precedent. No TaxaLens source, style, fixture, snapshot, estimate, or data was
copied. GitHits remained unavailable and was not retried. Valyu was not needed
because this task introduced no new scientific method or external factual
claim; local fingerprinted manifests are authoritative.

No reviewer identity, private score, source media, protected coordinate, model
output, or private storage key is exposed. No BioMiner record, Flickr API call,
YOLOE work, BioCLIP work, model artifact, model inference, or biodiversity result
occurred. YOLOE and BioCLIP remain explicitly unfinished and visible as release
blockers.

## Verification

- Full Python suite — 374 tests and 69 subtests passed.
- Dashboard projection suite — 5 tests passed against the authoritative quality
  and reference-bank manifests.
- Web suite — 13 Vitest component/parser tests passed; TypeScript check and
  production build passed.
- Web production checks — 116 dependency licences and the exact review-media
  fingerprint verified; built bundle sizes were 0.60 kB HTML, 13.50 kB CSS, and
  215.87 kB JavaScript before gzip.
- Contract parity — passed unchanged (25 schemas, 21 valid, 21 invalid, 21
  versions, 15 vocabularies; TypeScript 7.0.2).
- Rights verification — passed for 52 tracked provider payloads.
- Licensing — passed for 337 staged/tracked files, 2 dependency manifests, and
  0 model files.
- Production dependency audit — 0 vulnerabilities.
- JSONL provenance and TaxaLens migration YAML parsed successfully; whitespace
  checking and staged secret, model-file, cache, generated-bulk, and large-file
  gates passed.
- Semantic headings, an announced unavailable-state boundary, labelled metric
  group, native lists, and native disclosure details are covered by DOM tests.
  No separate browser accessibility-engine run is claimed.

Known limitation: the dashboard truthfully cannot publish population precision,
an uncertainty interval, reviewer agreement, or species quality until a
fingerprinted representative audit and eligible overlap evidence exist.

Next safe task: Task 10.1, define the visual system without performing any
Flickr, YOLOE, or BioCLIP work.
