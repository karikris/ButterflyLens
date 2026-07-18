# ButterflyLens 18.1 — fingerprinted GBIF occurrence evidence

Status: **complete as an internal, rights-blocked GBIF evidence pack; overall
product/data release remains unfinished**.

Starting SHA: `51e3dc3d84978432b3b1991a5a375a581684b64d`.

Receipt subtask commit:
`1bc592be40b1d9814189d54f360fdfb3ac4b466b`.

Builder subtask commit:
`0c7a80edbd8b10176f8f9d20b2c5d5579d759d95`.

Ending SHA: pending the containing publication commit.

Remote SHA: pending the required task push.

BioMiner SHA inspected for coordination:
`19fd744b1104c09dde75367bafb6b531ef4239a4`. BioMiner remained active on
Flickr metadata and supplied no complete immutable GBIF handoff. No partial
BioMiner file was copied.

## Outcome

The operator-supplied GBIF download `0004170-260715120105164` is now an exact,
deterministic Parquet evidence pack. The source citation is:

> GBIF.org (18 July 2026) GBIF Occurrence Download
> https://doi.org/10.15468/dl.7uut3k

The 261,743,165-byte DWCA passed ZIP integrity validation and has SHA-256
`7807622f6c2539ac536cb5f06d17087da3ecdd83b13a0dec54764e3800ff8f2b`.
It remains outside Git. The receipt freezes the official SUCCEEDED status,
country `AU`, Catalogue of Life Papilionoidea key `5G9`, 571,755 records, 126
datasets, DOI, creation/retention dates, HTTP identity, citation, download-level
CC BY-NC 4.0 licence, core member hashes, and the 126-dataset rights
distribution.

The checked-in evidence pack contains:

- `gbif_occurrences.parquet`: 571,755 rows, 55 columns, 75,916,747 bytes,
  SHA-256
  `971125b2c0cbba1a2f4d2e9f11ddc0b4149efbb3cabb8661364d36610e963cdc`;
- `gbif_multimedia.parquet`: 542,052 metadata-only rows, 20 columns,
  54,211,863 bytes, SHA-256
  `32e4e1464301ac6fc37226e36f70995c4d36860caa87057962c0da146f76fb08`;
  and
- `gbif_datasets.parquet`: 126 citation/rights rows, 15 columns, 31,274 bytes,
  SHA-256
  `632e2335044cf3c7b02369258ad1edf61d448a764c25e24222bfa306c95828a8`.

Every occurrence and multimedia row has an exact selected-source-field
fingerprint and an archive/download/row-bound evidence fingerprint. Dataset
rows bind exact EML metadata, citation, rights statement, selected count, and
member hash. The evidence-pack semantic fingerprint is
`5b65a156af3d45f21bf026661d5f9740c04a02c278c7d496f80563294325143b`.

## Evidence and rights state

Occurrence licences are retained exactly: 314,575 CC BY-NC 4.0, 195,361 CC BY
4.0, and 61,819 CC0 rows. Dataset rights comprise 76 CC BY 4.0, 28 CC BY-NC
4.0, and 22 CC0 records. Multimedia metadata has 475,437 supplied licence
values and 66,615 missing values across 256 distinct supplied strings. No
blanket compatibility is inferred.

The occurrence projection retains 18,317 rows with information-withheld text,
564 rows with generalisation text, coordinate uncertainty, exact GBIF issue
codes, and 70 rows marked with geospatial issues. Coordinates are only GBIF's
processed public values; the builder never reconstructs or increases
precision.

All nine GBIF data/schema artifacts have exact rights-manifest entries with
`processing_allowed=true`, `display_allowed=false`, and
`redistribution_allowed=false`. This is an internal evidence database, not a
public occurrence layer or media bank. The screen is conservative engineering
evidence, not a legal determination.

The independently rebuilt ButterflyLens ALA baseline remains authoritative.
The root pack records GBIF as complementary occurrence comparison,
provenance, taxonomy-reconciliation, and future keyword/reference evidence.
The Submitted catalogue and analyst registry continue to read their exact
historical Git objects rather than silently absorbing this later pack change.

## Builder and reproducibility

`scripts/build_gbif_evidence.py` has three explicit commands:

- `acquire` is the only network-enabled path and verifies byte count, archive
  hash, safe ZIP members, CRCs, member hashes, row counts, and dataset XML
  inventory before accepting a download;
- `build` is offline and produces stable ZSTD Parquet files, closed schemas,
  physical/logical manifests, and release-blocking policy state; and
- `publish` deterministically updates the root pack and data-rights manifests.

Default tests create a two-occurrence, two-media, one-dataset DWCA fixture and
prove byte-identical rebuilds without provider access. Tampered archives,
authority replacement, unsafe rights drift, and network use fail closed. A
full real-archive dry build and the publication build each completed in about
27 seconds.

## Verification

- All 635 Python tests pass in 22.25 seconds with the repository package roots
  configured. This includes 15 focused GBIF receipt/builder/published-pack
  tests plus deterministic replay, tamper, authority, rights, schema, physical,
  logical, sensitivity, and size gates.
- An initial full command omitted the repository package roots and separately
  exposed historical-test drift: Task 17.5 tests read mutable append-only
  ledgers, and Submitted catalogue tests compared a pinned snapshot to the new
  live pack. The corrected tests read their exact Task 17.5 and Submitted Git
  objects; the configured full rerun passed. No data artifact was changed to
  satisfy those historical assertions.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  TypeScript, the 119-package dependency-licence report, review-media checksum,
  and production build pass. The unchanged 1,496.87 kB script retains the
  existing non-blocking chunk-size warning.
- Rights verification passes for 62 tracked provider/data/media payloads.
  Licensing passes for 602 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 580 tracked text files, and 11 explicit network
  boundary files while retaining `release_ready=false`.
- All tracked JSON and provenance JSONL parse; tracked Python compiles; staged
  whitespace is clean. The final staged large-file gate passes across 22 files; the
  largest is 75,916,747 bytes, below GitHub's 100 MB per-file limit.

## Parallel work and excluded actions

BioMiner is still fetching Flickr metadata. No partial Flickr count, query
output, checkpoint, GBIF fixture, or report was inspected as completed or
copied. No Flickr API call or media-byte download occurred in ButterflyLens.

GitHits remained unavailable and disabled and was not called. YOLOE and
BioCLIP remain explicitly unfinished and skipped. No live GPT, M5 worker,
Supabase, B2, model, community-write, external submission, video, provider, or
public-release mutation occurred.

## Remaining blockers

The broader goal and release are not complete. BioMiner's Flickr metadata fetch
still needs a complete immutable handoff before admission. Flickr rights and
display gates, source-media decisions, YOLOE/BioCLIP and M5 work, live analyst
evidence, community review/quality evidence, provider-rights resolution, final
video/submission, and explicit human approval remain unfinished. GBIF presence
does not prove current biological presence, missing records do not prove
absence, and provider taxonomy does not identify a butterfly for ButterflyLens.
