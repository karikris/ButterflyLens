# ButterflyLens 10.3 — Australian butterfly species pages

Status: **implemented locally; authoritative projection and public boundaries
verified**.

Starting SHA: `9128a2757ad3dbab35df92aa610cae76894181ca`.

## Outcome

The scheduled Species preview is now a searchable, family-filtered catalogue of
all 463 accepted species in the frozen Australian Faunal Directory hierarchy.
Selecting an entry opens a complete profile with accepted placement, sourced
English names and scientific synonyms, conservative ALA/GBIF/iNaturalist
crosswalk states, unresolved conflicts, provisional reference diagnostics, and
fingerprinted provenance.

The catalogue is generated deterministically from checksum-verified local
artifacts. Its semantic fingerprint is
`sha256:083ed290418938e1c32ee75cad5dea6d81153f529ab1c40acbb64f52beccba06`;
the checked-in JSON file SHA-256 is
`6d774e68abd6f29affb5dcfc220d0c5e4759e74c434f0f720f655e19f9a5d6f9`.
The parser fails closed on altered authority, evidence, count, provider-ID, and
unfinished-model states.

One existing rights-cleared Wikimedia Commons review fixture appears only on
the provider-labelled *Papilio (Princeps) demoleus* profile. Its caption says it
is not representative and not identity verification. Every other species uses
an explicit unavailable-media state; no image is invented or fetched.

## Scientific, cultural, and rights boundaries

- The rebuilt ButterflyLens baseline is authoritative for this goal.
- English names remain `source_assertion_unreviewed`; provider IDs exist only
  for exact matched states, and open conflicts remain unresolved.
- The First Nations language-name state remains
  `empty_no_authorized_source`, explicitly without an absence inference.
- ALA species occurrence counts are withheld while `dr1097`, `dr30019`, and
  `dr635` remain under dataset-rights review. A missing count is not biological
  absence.
- Reference counts are provider-asserted workflow diagnostics, not identities,
  occurrence records, quality scores, or scientific claims. Human-verified
  media remain zero.
- YOLOE and BioCLIP remain visibly unfinished. Neither model was loaded or run.

## BioMiner and supplied GBIF archive

The supplied GBIF DWCA download `0004170-260715120105164` (571,755 Australian
Papilionoidea records; citation `GBIF.org (18 July 2026) GBIF Occurrence
Download`, DOI `10.15468/dl.7uut3k`) overlaps BioMiner's active fingerprinted
evidence-database work. BioMiner's root instructions and current agent record
were inspected; its active work was observed at
`b372ce18d6be62c1b66025b700d5c4e4a884428c`.

Per the user's coordination rule, this task did not start a duplicate download,
conversion, or Parquet build and did not touch BioMiner's dirty working tree.
The completed published BioMiner artifact will be rechecked at the next task
boundary and copied into ButterflyLens when safe. This species release does not
claim that the new GBIF occurrence archive has been imported.

## Verification

- Full Python suite — 388 tests passed.
- Focused source, shell, and visual suite — 14 tests passed under the project
  Python environment; the system-pytest portability run passed 13 and skipped
  only the PyArrow rebuild that it cannot import.
- Web suite — 30 Vitest component and parser tests passed; TypeScript check and
  production build passed.
- Production bundle — 0.60 kB HTML, 30.81 kB CSS, and 1,406.50 kB JavaScript
  before gzip; JavaScript is 209.75 kB after gzip. Vite reports its standard
  raw-chunk size advisory because the full submitted catalogue ships locally.
- Build verification checked 116 dependency licences and the exact unchanged
  review-media fingerprint.
- Repository rights and licensing verification passed (52 tracked provider
  payloads and 352 tracked files); the production dependency audit found zero
  vulnerabilities.
- Visual tests cover palette contrast, focus, forced colours, reduced motion,
  responsive rules, and prohibit gradients or scientific-image filters across
  the new stylesheet.
- Catalogue tests cover deterministic reconstruction, source and catalogue
  fingerprints, species coverage, identifier/name conservatism, the cultural
  name gate, the ALA rights boundary, and unfinished human/model evidence.

No standalone browser screenshot or accessibility-engine run is claimed because
no browser runtime is installed. No Flickr API, GitHits, YOLOE, BioCLIP, or
scientific model call occurred.

Next safe action: publish Task 10.3, then recheck BioMiner for the GBIF Parquet
handoff before beginning Task 10.4.
