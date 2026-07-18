# ButterflyLens 14.2 — Darwin Core evidence package

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`e786663cd73dac939f1592bc73f5f6854eace644`.

## Outcome

ButterflyLens now generates a deterministic Darwin Core Archive from an exact
set of governed release-ready records. `occurrence.txt` is the unique core;
Taxon, Event, Location, Identification, MeasurementOrFact, Media, Provenance,
Review, and Quality are explicit core-linked extensions. `meta.xml` maps every
field to its standard or clearly namespaced ButterflyLens term.

The package is byte-reproducible: inputs are sorted and unique, CSV formatting
is fixed, archive member timestamps and permissions are fixed, and the exact
member order ends with `evidence-manifest.json`. That manifest freezes policy,
Darwin Core guide/term versions, code SHA, row/byte counts, file checksums,
source release receipts, and the canonical package fingerprint. The offline
CLI rejects unknown fields, performs no network call, writes atomically, and
prints separate physical and semantic fingerprints.

## Scientific, privacy, and rights boundary

The typed input accepts only `release_ready_occurrence_candidate` records whose
publication and scientific-claim flags remain false. Candidate and media
rights fingerprints must match. Configured expert review must have its exact
event fingerprint, while an unconfigured gate is recorded as not configured
rather than falsely presented as expert review.

Only a valid governed public H3 cell enters Location. No latitude, longitude,
verbatim coordinate, or more precise geometry field exists in the export
mapping. Information-withheld and data-generalization statements are retained.
Review extensions contain evidence fingerprints and decisions but no reviewer
account, profile, email, or personal text. Multimedia contains public source,
licence, creator, rights-holder, attribution, and checksum evidence but no
image bytes. Optional media access requires a query-free, fragment-free,
credential-free HTTPS URL, so signed URLs fail closed.

The archive records `prepared_not_published` and `not_submitted`. No archive
from live data is committed, no occurrence has been published, and no ALA or
other provider submission has occurred.

## Standards decision

Current official TDWG terms and the normative Darwin Core Text guide define the
classes and one-core/many-extension relationship. The 2026 Darwin Core Data
Package guide was reviewed, but its reserved relational tables flatten or
relate several of the ten explicitly requested domains. The archive therefore
uses the Text/DwC-A model and does not claim DwC-DP profile conformance. Exact
sources and the standards inference are frozen in `provenance/valyu.jsonl`.

## Verification

- 545 locked Python tests pass, including eleven fixture-backed archive,
  linkage, generalized-location, review privacy, media rights, release gate,
  exact parser/CLI, checksum, determinism, and atomic-write tests.
- The one-record deterministic software fixture contains all ten domain files,
  is 7,108 bytes, has archive SHA-256
  `7229ff0d02634b5a4322082383d1a99dc0cdea1aafc4bccff2576de40a8cdd71`,
  and semantic package fingerprint
  `014428c5674369195402a756613fad7f9eea6fc632ce35027d6b7013ecfd386e`.
  These are software-fixture identities, not biodiversity or production
  performance results.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing, JSON/JSONL, workflow YAML, shell syntax, Python compilation,
  whitespace, staged scope, secret-safety, and large-file checks are completed
  immediately before commit.

## External-work boundary

GitHits remained disabled by explicit user instruction and was not called. No
Flickr API call, Flickr output import, provider submission, B2 operation,
production workflow dispatch, media copy, YOLOE work, BioCLIP work, scientific
model call, or scientific inference occurred. The user-reported Flickr fetch
remains external and active from its 50,000-image checkpoint; no partial result
was consumed.

BioMiner was inspected only through its published `CURRENT_STATE.md`
coordination record. It advanced from the task-start SHA
`882cd15422aa3796a0306a8f2c335f04a76a7482` to
`fb0ec8e9925b2ac13b946543b3f92e9481dee087` and remains active with dirty
selective-rerun, Flickr, and dynamic-pooling work. Its remaining-work ledger
still names live current-policy GBIF acquisition and durable admission, so it
provides no immutable handoff for the user-supplied GBIF archive. No active
output was copied. The rebuilt ButterflyLens ALA baseline remains
authoritative. TaxaLens remained at
`e845dd98493979f37b04dbb6538e0d7b8758ca11`; its dirty user work was untouched.

Known limitation: the exporter has deterministic fixture coverage but no live
release receipts exist in this repository. A future authorized worker must
load exact database receipts and verify the resulting package before any
submission preparation. Task 14.3 must prepare ALA metadata and validation
without submitting automatically.

Next safe task: prepare the non-submitting ALA submission bundle after this
exact commit is pushed and its GitHub Pages deployment is verified.
