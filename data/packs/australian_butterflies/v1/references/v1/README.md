# Provisional reference metadata import v1

This directory contains provider-labelled candidate observations and media
metadata. It is not a human-verified reference bank and contains no downloaded
image bytes, YOLOE routes, BioCLIP embeddings, prototypes, or calibrated
probabilities.

The deterministic query plan selects the 371 accepted species that have exact
GBIF and iNaturalist identifiers in the frozen ButterflyLens crosswalk. It
issues one Australia-scoped query to each provider for each species. GBIF is
capped at three records per species. iNaturalist uses the adapter-required
200-record page size and one page per species, with place `6744` verified as
Australia. The remaining 92 accepted species are explicit identity shortfalls;
they are not searched by name.

Provider polling and normalization were executed by BioMiner at immutable
commit `d71bceabf75748a25df39d0025e8da907f295f8c`. Its typed observation and
media-candidate contracts preserve source IDs, source-record hashes, query
fingerprints, provider taxon assertions, coordinates, source links, creators,
rights holders, licences, attribution, and review/gate state. The checkpoint
archive contains all 742 completed query states and their normalized page
artifacts. It records 769 requests, including 27 bounded first retries after
iNaturalist rate-limit responses.

The frozen Task 2.3 ALA occurrence artifact remains the ALA candidate-
observation source. Its acquisition contract did not request media metadata,
so this import records zero ALA media candidates and does not infer URLs or
labels. The existing three-resource ALA downstream release block remains in
force.

Current imported metadata:

- 12,980 candidate observations: 980 GBIF and 12,000 iNaturalist;
- 24,329 candidate media rows: 1,696 GBIF and 22,633 iNaturalist;
- 12,977 exact provider taxon reconciliations and 3 conflicts;
- 22,633 iNaturalist rows allowed by the import-time `cc0`/`cc-by` filter;
- 1,651 GBIF rows awaiting the automated licence gate and 45 quarantined;
- zero downloaded images and zero human-verified media.

The Task 2.4.2 metadata linkage records 10,453 cross-provider observation
mirror groups using exact iNaturalist observation identifiers. Of those,
10,401 link two sources and 52 link ALA, GBIF, and iNaturalist. Five groups
retain conflicting ButterflyLens taxon keys and require review. It also records
93 GBIF/iNaturalist media mirror candidates using the exact iNaturalist
observation-plus-photo identity. Ninety-two have matching normalized licence
metadata; one retains a `cc-by`/`cc-by-nc` conflict.

These rows are duplicate hypotheses, not proof that media bytes or visual
content are identical. Byte checks, perceptual checks, and canonical-media
selection remain explicitly null until permitted media is acquired and passes
Task 2.4.3. Provider source records, media IDs, taxon keys, licence assertions,
and conflicts remain attached to every group.

Rebuild the query plan:

```bash
uv run python scripts/build_reference_import.py plan \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --output data/packs/australian_butterflies/v1/references/v1/reference_source_queries.json \
  --source-snapshot-version provider-live-20260718 \
  --generated-at 2026-07-17T19:33:06Z
```

Replay provider normalization from the archived checkpoints by extracting them
into a detached BioMiner worktree at the pinned SHA and rerunning `biominer
references fetch-metadata` with the checked-in plan. Network replay is not
byte-stable because provider records can change; the frozen checkpoint archive
and consolidated artifacts are the evidence for this import.

Rebuild the metadata linkage without network access:

```bash
uv run python scripts/build_reference_import.py deduplicate-metadata \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --ala-occurrences data/packs/australian_butterflies/v1/ala/ala_baseline_occurrences.parquet \
  --observations data/packs/australian_butterflies/v1/references/v1/imported/reference_observations.parquet \
  --media data/packs/australian_butterflies/v1/references/v1/imported/reference_media_candidates.parquet \
  --observation-output data/packs/australian_butterflies/v1/references/v1/deduplicated/reference_observation_mirror_groups.parquet \
  --media-output data/packs/australian_butterflies/v1/references/v1/deduplicated/reference_media_duplicate_candidates.parquet \
  --manifest data/packs/australian_butterflies/v1/references/v1/reference_deduplication_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T19:55:50Z
```
