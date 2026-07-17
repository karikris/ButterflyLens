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

Task 2.4.3 applies a conservative automated gate to all 24,329 media rows. It
requires an exact accepted-taxon crosswalk, no observation or media mirror
conflict, `cc0` or `cc-by` media rights, complete required attribution, no
import exclusion, and an approved HTTPS provider host. The current host lane
is limited to iNaturalist's open-data object store. Compatible GBIF licences
are recorded, but GBIF downloads remain blocked until each relevant media host
has an approved policy.

The gate finds 22,378 eligible metadata rows and blocks 1,951. A deterministic
diversity plan selects at most one image per observation, 20 per species, and
50 per observer across the bank. It selects 2,910 candidates spanning 237
species; 86 species reach the cap. Every selected label remains an unreviewed
provider assertion. Downloaded source objects live only in the ignored local
cache; Git receives checksums, decode evidence, gate decisions, and manifests,
not the source-image collection.

Pinned BioMiner downloaded this selection in a resumable run. Of 2,910
outcomes, 2,906 decoded locally and four were quarantined after permanent HTTP
404 responses. The report records zero retries, 391 checkpoint resumes, 2,905
unique content SHA-256 values, and 1,127,087,982 content-addressed source bytes.
The valid inventory contains 2,903 JPEG and three PNG objects. A repeated
content identity remains attached to both source records; byte/perceptual
duplicate resolution is a separate gate. Failed rows retain their stable media
identity and quarantine reason but no invented checksum or dimensions.

Task 2.4.4 records zero executed YOLOE routes. All 2,906 valid decodes are
`blocked_not_executed`: the pinned router accepts GBIF rows, the current
admitted lane contains iNaturalist rows, the audited runtime is absent, and no
verified checkpoint is available. The four failed downloads retain their
separate media blocker. BioMiner commit
`c7eaa9bf3696a25a0c8229837819dccec4fb9d66` was inspected but not adopted: its
committed report says the live GBIF support bank remains pending and no
copyable live artifact or active build was found. No Flickr API call was made.

Task 2.4.5 is also explicitly unfinished for this goal. BioCLIP was not loaded,
no weights or checkpoint were acquired, and zero embeddings, support rows, or
species prototypes were produced. The checked-in status record preserves that
skip decision so downstream diagnostics cannot mistake missing model evidence
for negative biological evidence.

Task 2.4.6 publishes one evidence-only diagnostic for each of the 463 accepted
species. Valid provisional decodes cover 237 species; 126 have no imported
candidate media and 100 have candidates but no automated-gate-eligible media.
Every row remains blocked from release, zero rows are human verified, and the
missing YOLOE and BioCLIP dimensions are explicit flags. No quality score,
accuracy estimate, model inference, source-image byte, or absence claim is
created.

Task 2.4.7 closes the tracked reference inventory with bank fingerprint
`6f23e1ec04d0297797439973aea98d9b45bc989ce9ec61db35064824621bdc3d`.
The manifest covers 20 child artifacts and binds their byte checksums, schemas,
row counts, origin, policy, unfinished states, and release blockers. It is a
provisional evidence-pack receipt, not a verified reference-bank release.

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

Rebuild the deterministic admission plan without network access:

```bash
uv run python scripts/build_reference_admission.py plan \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --observations data/packs/australian_butterflies/v1/references/v1/imported/reference_observations.parquet \
  --media data/packs/australian_butterflies/v1/references/v1/imported/reference_media_candidates.parquet \
  --observation-mirrors data/packs/australian_butterflies/v1/references/v1/deduplicated/reference_observation_mirror_groups.parquet \
  --media-duplicates data/packs/australian_butterflies/v1/references/v1/deduplicated/reference_media_duplicate_candidates.parquet \
  --import-manifest data/packs/australian_butterflies/v1/references/v1/reference_import_manifest.json \
  --decisions-output data/packs/australian_butterflies/v1/references/v1/gated/reference_media_gate_decisions.parquet \
  --selections-output data/packs/australian_butterflies/v1/references/v1/gated/reference_download_selections.parquet \
  --manifest-output data/packs/australian_butterflies/v1/references/v1/reference_gate_plan_manifest.json \
  --generated-at 2026-07-17T20:15:00Z
```

The network download is not claimed to be byte-replayable: provider objects
can disappear or change. Its frozen command report and media-object inventory
are the evidence for this run. Rebuild the normalized publication and root
pack state from those tracked artifacts without reading source-image bytes:

```bash
uv run python scripts/build_reference_admission.py publish \
  --plan-manifest data/packs/australian_butterflies/v1/references/v1/reference_gate_plan_manifest.json \
  --decisions data/packs/australian_butterflies/v1/references/v1/gated/reference_media_gate_decisions.parquet \
  --selections data/packs/australian_butterflies/v1/references/v1/gated/reference_download_selections.parquet \
  --media-objects data/packs/australian_butterflies/v1/references/v1/gated/reference_media_objects.parquet \
  --media-objects-output data/packs/australian_butterflies/v1/references/v1/gated/reference_media_objects.parquet \
  --download-report data/packs/australian_butterflies/v1/references/v1/reference_media_download_report.json \
  --download-report-output data/packs/australian_butterflies/v1/references/v1/reference_media_download_report.json \
  --manifest-output data/packs/australian_butterflies/v1/references/v1/reference_admission_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T20:36:03.622395Z
```

Rebuild the fail-closed YOLOE readiness ledger without model execution:

```bash
uv run python scripts/build_reference_yoloe_readiness.py \
  --selections data/packs/australian_butterflies/v1/references/v1/gated/reference_download_selections.parquet \
  --observations data/packs/australian_butterflies/v1/references/v1/imported/reference_observations.parquet \
  --media-objects data/packs/australian_butterflies/v1/references/v1/gated/reference_media_objects.parquet \
  --admission-manifest data/packs/australian_butterflies/v1/references/v1/reference_admission_manifest.json \
  --output data/packs/australian_butterflies/v1/references/v1/gated/reference_yoloe_readiness.parquet \
  --manifest-output data/packs/australian_butterflies/v1/references/v1/reference_yoloe_readiness_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T20:47:49Z
```

Rebuild the reference-quality diagnostics without model execution:

```bash
uv run python scripts/build_reference_quality_diagnostics.py \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --decisions data/packs/australian_butterflies/v1/references/v1/gated/reference_media_gate_decisions.parquet \
  --selections data/packs/australian_butterflies/v1/references/v1/gated/reference_download_selections.parquet \
  --media-objects data/packs/australian_butterflies/v1/references/v1/gated/reference_media_objects.parquet \
  --yoloe-manifest data/packs/australian_butterflies/v1/references/v1/reference_yoloe_readiness_manifest.json \
  --bioclip-status data/packs/australian_butterflies/v1/references/v1/reference_bioclip_status.json \
  --output data/packs/australian_butterflies/v1/references/v1/gated/reference_quality_diagnostics.parquet \
  --manifest-output data/packs/australian_butterflies/v1/references/v1/reference_quality_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T21:05:00Z
```

Republish the closed reference-bank inventory and root fingerprint:

```bash
uv run python scripts/publish_reference_pack.py \
  --reference-dir data/packs/australian_butterflies/v1/references/v1 \
  --admission-manifest data/packs/australian_butterflies/v1/references/v1/reference_admission_manifest.json \
  --yoloe-manifest data/packs/australian_butterflies/v1/references/v1/reference_yoloe_readiness_manifest.json \
  --bioclip-status data/packs/australian_butterflies/v1/references/v1/reference_bioclip_status.json \
  --quality-manifest data/packs/australian_butterflies/v1/references/v1/reference_quality_manifest.json \
  --output data/packs/australian_butterflies/v1/references/v1/reference_bank_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T21:12:00Z
```
