# BioMiner integration audit

BioMiner is ButterflyLens's read-only research-engine upstream. This audit
records what is present at one immutable commit; it does not convert upstream
tests, examples, or historical reports into ButterflyLens results.

## Audited snapshot

| Field | Evidence |
| --- | --- |
| Repository | `karikris/BioMiner` |
| Commit | `d71bceabf75748a25df39d0025e8da907f295f8c` |
| Commit subject | `feat(evaluation): define reference-bank statistical audit` |
| Commit time | `2026-07-17T23:49:22+10:00` |
| Branch observed | `main` |
| Source licence | MIT |
| Audit time | `2026-07-17T13:54:06Z` |
| Focused verification | `192 passed in 5.51s` |

The working tree was dirty at audit time. The untracked paths were
`config/papilio_demoleus_flickr_estimator.sh2`,
`config/papilio_demoleus_multilingual_keywords.json`, `docs/superpowers/`,
`duplicate_query_terms_skipped`, `logs/`, and `query_terms_added`. They are not
part of this audit. Every source finding below came from `git show`, `git grep`,
or `git ls-tree` against the full commit SHA.

No live provider call, model download, model inference, Apple MPS execution, or
scientific result was performed for this audit.

## Capability findings

Maturity labels mean:

- **implemented and offline-tested**: committed executable code and focused
  deterministic tests exist;
- **partial**: useful committed implementation exists, but the named
  end-to-end capability has an important missing boundary;
- **contract-only**: the state, DAG, or policy is committed, but no complete
  executor or measured run was found;
- **absent**: no committed implementation was found.

### 1. Adaptive GBIF reference admission — implemented and offline-tested

BioMiner has an explicit default mode,
`adaptive_gbif_fast_start`, plus `human_verified_strict` and
`human_verified_flagged_only`. The committed implementation includes:

- typed admission policy and semantic fingerprinting in
  `src/biominer/references/admission.py`;
- deterministic GBIF eligibility and admission compilation in
  `admission_eligibility.py` and `admission_compiler.py`;
- a separate `ready_provisional` state and fail-closed permit surface in
  `readiness.py`;
- a conditional adaptive stage graph in `src/biominer/run/adaptive_workflow.py`;
- a reference-bank quality policy in
  `src/biominer/evaluation/reference_bank_audit.py`.

The only approved meaning of an automatically admitted row is **GBIF
provider-asserted provisional support**. It is not human verified, ground truth,
calibration truth, a final-test label, or a released occurrence record. A final
Flickr row remains gated on decisive human review.

The focused tests validated the default CLI/config contract, adaptive DAG,
GBIF adapter, reference audit policy, and target-verification metrics. They do
not prove that a live adaptive production run has completed.

### 2. ALA, GBIF, and iNaturalist references — partial

GBIF and iNaturalist have committed reference adapters, schemas, fixtures, and
offline tests:

- `src/biominer/references/gbif.py`;
- `src/biominer/references/inaturalist.py`;
- `tests/fixtures/references/gbif_occurrence_search_v1.json`;
- `tests/fixtures/references/inaturalist_observation_search_v1.json`.

The CLI's dry-run test explicitly asserts that `ala` is not a reference source.
No committed ALA or biocache reference adapter was found. ButterflyLens must
therefore own ALA baseline acquisition, snapshot identity, provider assertions,
sensitive-data handling, and comparison semantics. It must not label ALA data
as a BioMiner reference capability.

### 3. Flickr query planning — implemented and offline-tested

`src/biominer/flickr_fetch/query_planner.py` provides deterministic typed
queries, separate `text` and `tags` fields, logical-query identities, 4,000-row
access-window handling, 500-row normal pages, 250-row geographic pages, and
fixed upload-date slice utilities. Registry definitions are filtered by both
`enabled` and `query_eligible`, then ordered by search priority and stable
identity.

`src/biominer/flickr_fetch/workload.py` preserves one canonical photo while
retaining every distinct source/photo/query association. This supports the
required invariant: deduplicate physical work, not discovery evidence.

Important limitation: loading registry query definitions does not itself apply
the `start_date`, `end_date`, or `slice_days` arguments; broad fixed-slice
seeding is a separate planner path. Consumers must inspect the produced query
artifact rather than infer slicing from function arguments. No live Flickr call
or coverage claim was made here.

### 4. Geographic artifacts — implemented and offline-tested

Committed artifacts and builders cover:

- GBIF taxon spread and occurrence evidence;
- taxon geographic summary and QA findings;
- normalized Flickr geography;
- H3 density-component clusters and per-photo assignments;
- explicit `no_geo` and `unassigned_geo` fallback clusters;
- regional candidate-species evidence.

Key committed versions include `flickr-geography-v1.0.0`,
`flickr-geo-clusters-v1.1.0`, and `flickr-geo-assignments-v1.1.0`. Cluster rows
include `candidate_distribution_only=true`; absence from a region is not
evidence of biological absence, and a cluster does not verify identity.

### 5. YOLOE-26 routing — implemented adapter; runtime not bundled

`src/biominer/detection/yoloe26_detector.py` implements prompt validation,
checkpoint validation, direct and persistent sidecar execution, normalized
detection candidates, and prompt-set fingerprints. Routing distinguishes adult
butterfly, possible adult, caterpillar, pupa, pinned specimen, moth-like,
artifact, and no-relevant-organism evidence. YOLOE is a domain/quality router,
not a species verifier.

Target-aware full-frame routing is covered by
`tests/test_full_frame_yoloe_routing.py`, including an assertion that the path
does not create spatial crops. However, the general production orchestrator
still declares `PRODUCTION_VISUAL_MODE = "detector_crop"`, and the M5 profile
retains crop settings. ButterflyLens must not infer that every BioMiner
production path is already full-frame.

No checkpoint is committed. The required Ultralytics/YOLOE runtime is external
and remains subject to the AGPL/commercial licensing gate documented in
`THIRD_PARTY_LICENSES.md`.

### 6. BioCLIP 2.5 — implemented adapter and artifact pipeline; weights not bundled

BioMiner has a persistent BioCLIP worker, taxonomy text-embedding cache,
reference embeddings, route-separated prototypes, target-aware fusion,
candidate-set scoring, and raw-evidence outputs. Reference embeddings use
schema `reference-embeddings-v3.0.0`; their publication manifest uses
`biominer-artifact-manifest-v1`.

The implementation binds outputs to model, model-weight, preprocessing,
input-content, support-row, reference-bank, admission-policy, and artifact
fingerprints. Raw cosine similarity, prototype margins, SVM output, and nearest
reference values remain non-probabilistic evidence. BioCLIP weights are not
committed and were not loaded during this audit.

### 7. Apple MPS persistent worker — implemented and offline-tested; not host-verified

`src/biominer/bioclip/bioclip_worker.py` supports `auto`, `cuda`, `mps`, and
`cpu`; its `--persistent` protocol loads the model once and serves repeated
JSON requests. It records MPS current, driver, recommended maximum, and peak
memory values when the runtime exposes them. The
`config/vision_profiles/mac_m5pro_64gb.json` profile requests one detector
worker, one BioCLIP worker, bounded preprocessing workers, and explicit batch
sizes.

The focused worker and batching tests passed, but the audit host is Linux.
There is no evidence here of an actual M5 run, MPS throughput, peak memory, or
safe production batch size. Those values remain unavailable until measured on
the target machine.

### 8. Fingerprints and artifact identity — implemented and broadly applied

`src/biominer/common/semantic_hash.py` defines a versioned canonical binary
encoding and full SHA-256 semantic fingerprint for JSON-like data, dates, and
timezone-aware datetimes. Tests cover deterministic mapping order, sequence
order, types, finite floats, and invalid inputs.

The contract is applied across run/work identities, query definitions,
geographic configurations, media content, YOLOE prompts and checkpoints,
visual transformations, model weights, preprocessing, reference support,
embeddings, prototypes, classifiers, calibrators, and score dependencies.
Physical file SHA-256 and semantic fingerprints are distinct. ButterflyLens
can reuse the concept, but cross-language parity must be proved before it treats
Python and TypeScript fingerprints as interchangeable.

### 8a. Parquet handoff — adapted contract; no source copied

Task 2.3 adopts the artifact behavior of pinned
`src/biominer/storage/parquet.py`: Zstandard compression, an explicit schema,
temporary-file replacement, and bounded row groups. ButterflyLens does not
import `biominer.*`, copy the implementation, or use the dirty upstream
worktree. Its native PyArrow adapter adds ALA-specific provider, licence,
sensitivity, quality, exact-crosswalk, and row-fingerprint fields and writes a
manifest only after the Parquet checksum is available.

The resulting artifact remains ButterflyLens-owned ALA baseline occurrence
evidence. This integration does not turn ALA into a BioMiner reference source,
does not establish human verification, and does not infer absence.

### 8b. H3 projection — adapted interface; no source copied

Task 2.3.3 follows the pinned `src/biominer/geography/cells.py` interface and
`GeographicResolutions(coarse=3, regional=5, local=7)` ordering demonstrated by
its committed tests. ButterflyLens calls the locked `h3` 4.5.0 package through
a native ALA aggregation adapter; it does not import or copy BioMiner source.

ButterflyLens adds product-specific Australia, state/territory, IBRA, LGA, and
H3 rollups, ordered source-row lineage digests, provider-context caveats, and a
strict sensitive-membership rule. Publicly generalised ALA values contribute
only to Australia, state/territory, and H3 resolution 3. No boundary geometry
is copied, a cell center is not an occurrence coordinate, and an empty cell is
not evidence of biological absence.

### 9. Statistical evaluation — implemented components; no audited live result

BioMiner has committed modules for reviewed labels, grouped splits, leakage
checks, sampling, calibration, thresholds, uncertainty, target metrics,
selective decision policy, reports, and reference-bank audit. The public
`biominer references evaluate-target-verifier` command accepts evaluation,
balanced-holdout, natural-holdout, leakage-register, bootstrap, calibration,
and threshold inputs.

The reference-bank audit can flag groups for inadequate sample, objective
shortfall, or other configured evidence. An insufficient sample must remain
unavailable. The 192-test audit includes deterministic statistical tests, but
no committed result was adopted as a ButterflyLens metric and no live pilot
claim is made.

### 10. Selective reruns — contract-only at the end-to-end boundary

BioMiner has strong prerequisites for selective work: content-addressed media,
dependency fingerprints, checkpointed embeddings, idempotent work keys, lease
validation, and an adaptive DAG containing `affected_reference_rebuild` and
`affected_record_rescore` stages.

The accepted ADR describes impact analysis, cache reuse, affected prototype
rebuilds, and affected Flickr rescoring. But the inspected commit exposes these
last two steps as conditional stage states rather than a complete, measured
revision-impact executor. Its own reference workflow baseline marks
`selective_rerun_records` unavailable and `full_rerun_work_avoided` not
instrumented. ButterflyLens must present selective reruns as planned until a
versioned impact artifact and executed work ledger prove otherwise.

## Focused verification

Run from the BioMiner working directory with bytecode and pytest cache writes
disabled:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider \
  tests/test_adaptive_cli_defaults.py \
  tests/test_adaptive_config_validation.py \
  tests/test_adaptive_run_stages.py \
  tests/test_query_planner.py \
  tests/test_flickr_workload_input.py \
  tests/test_registry_geographic_spread.py \
  tests/test_registry_geographic_summary.py \
  tests/test_flickr_geographic_clustering.py \
  tests/test_reference_gbif.py \
  tests/test_reference_inaturalist.py \
  tests/test_reference_yoloe_routing.py \
  tests/test_full_frame_yoloe_routing.py \
  tests/test_yoloe26_detector.py \
  tests/test_bioclip_worker.py \
  tests/test_bioclip_worker_batching.py \
  tests/test_semantic_hash.py \
  tests/test_reference_bank_audit.py \
  tests/test_target_verification_metrics.py
```

Result: `192 passed in 5.51s`.

This test result establishes only deterministic behavior covered by those
tests at the pinned commit. It does not establish provider availability,
licensing permission for a specific asset, model accuracy, MPS performance,
human review, scientific release readiness, or successful deployment.

## ButterflyLens application boundary

The boundary is artifact-first and pinned to the audited SHA. “Stable” here
means ButterflyLens has chosen an explicit command or artifact contract at that
commit; it is not a claim that BioMiner has published a backwards-compatibility
guarantee or package release.

### Ownership

BioMiner owns research-engine work:

- taxonomic registry and name/query compilation;
- Flickr discovery planning and physical-request deduplication;
- GBIF and iNaturalist reference acquisition;
- geographic spread, clustering, and regional candidate generation;
- reference admission, readiness, and route-separated support artifacts;
- YOLOE routing and full-frame visual-input evidence where that path is
  explicitly selected;
- BioCLIP embeddings, prototypes, classifiers, calibrators, scoring, and
  statistical evaluation.

ButterflyLens owns the Australia-wide product:

- the ALA baseline snapshot and ALA provider semantics;
- user projects, runs, accounts, consent, moderation, and review operations;
- Australian taxonomy/name overlays and First Nations governance;
- reviewer reliability and quality-estimate presentation;
- live M5 worker control, health, and product-visible job state;
- public maps, evidence cards, comparisons, exports, replay, and deployment;
- the final release gate joining provider rights, reviews, quality snapshots,
  coordinate sensitivity, and removal state.

BioMiner artifacts never acquire greater maturity when imported. In
particular, a Flickr candidate remains a candidate, GBIF provisional support
remains provider asserted, raw scores remain raw, and unavailable selective
rerun metrics remain unavailable.

### Permitted command surface

ButterflyLens may invoke only the following committed public command classes,
through a server-side worker adapter pinned to the full BioMiner SHA:

```text
biominer registry build --output-dir <dir> --registry-version <version> ...
biominer registry audit --registry-dir <dir> --report-dir <dir>
biominer registry publish --registry-dir <dir> --output-dir <dir>

biominer references <supported-command> --settings-file <json> [--dry-run]

biominer run \
  --taxon <accepted-name-or-key> \
  --rank <auto|family|genus|species> \
  --registry-dir <immutable-registry> \
  --output-prefix <local-or-s3-prefix> \
  --workflow adaptive \
  [--dry-run]
```

The permitted `references` commands are limited to the committed producer or
validator set needed by an approved worker plan:

```text
build-geographic-spread
build-regional-competitor-evidence
cluster-flickr-metadata
materialize-flickr-workload
plan
fetch-metadata
download
build-support-embeddings
build-prototypes
train-classifier
calibrate-classifier
score-target-aware
evaluate-target-verifier
```

Prototype-finalization and prototype-only commands are not part of the
ButterflyLens production boundary. Nothing under `biominer dev` is stable
product integration. Storage/workstore doctors and handoff commands may be
used operationally, but their output is diagnostic and cannot become
scientific evidence by itself.

Before a non-dry run, the adapter must persist:

- BioMiner full SHA and dirty-state check;
- exact argv with secrets redacted;
- project/run identity and approval event;
- input artifact URIs, byte counts, SHA-256 values, schema versions, and
  semantic fingerprints;
- provider and model rights permits;
- output prefix and expected artifact contract;
- worker/device identity and retry/stop policy.

A dirty BioMiner worktree blocks execution unless the worker runs from a clean
archive or isolated environment created from the pinned commit. ButterflyLens
must never invoke a command against whatever happens to be checked out in a
developer directory.

### Permitted artifact surface

The primary handoff root is:

```text
<output-prefix>/run_id=<run-id>/
```

Its layout identity is `reference-first-run-artifacts-v1.0.0`. ButterflyLens
may ingest only artifacts listed in a verified manifest or in the allowlist
below. A path match alone is insufficient.

| Artifact | Upstream contract | ButterflyLens use |
| --- | --- | --- |
| `run_manifest.json` | integer `schema_version: 1` | stage/status projection only after contract validation |
| `registry/manifest.json` | registry-produced manifest | source snapshot and inventory root |
| `registry/taxa.parquet` | accepted taxon rows | immutable taxonomy input, not image truth |
| `registry/names.parquet` | sourced name rows | names and evidence links |
| `registry/flickr_query_definitions.parquet` | query definitions | discovery hypotheses and logical-query provenance |
| `registry/geography/taxon_geographic_spread.parquet` | versioned geographic-spread artifact | soft regional evidence |
| `registry/geography/geographic_occurrence_evidence.parquet` | versioned provider evidence | source assertions, never absence proof |
| `registry/geography/taxon_geographic_summary.parquet` | versioned summary | candidate generation and explanation |
| `registry/geography/geographic_qa_findings.parquet` | versioned QA | blocked/warning state |
| `flickr/geography/flickr_geography.parquet` | `flickr-geography-v1.0.0` | normalized candidate coordinates |
| `flickr/geography/flickr_geo_clusters.parquet` | `flickr-geo-clusters-v1.1.0` | candidate-distribution clusters |
| `flickr/geography/flickr_geo_assignments.parquet` | `flickr-geo-assignments-v1.1.0` | candidate cluster/no-geo state |
| `candidates/regional_candidate_species.parquet` | versioned regional-candidate artifact | complete candidate-set input; geography is soft |
| `references/metadata/reference_observations.parquet` | `reference-observations-v1.2.0` | provider assertions and provenance |
| `references/media/reference_media_candidates.parquet` | `reference-media-candidates-v1.0.0` | acquisition candidates, not redistribution permission |
| `references/media/reference_media_objects.parquet` | `reference-media-objects-v1.1.0` | content identity and download state |
| `references/readiness/reference_bank_readiness.json` | `reference-bank-readiness-v3.0.0` | fail-closed readiness permit |
| `references/readiness/reference_support_manifest.parquet` | `reference-support-manifest-v3.0.0` | route- and maturity-specific support rows |
| `references/embeddings/reference_embeddings.parquet` | `reference-embeddings-v3.0.0` | frozen raw embedding evidence |
| `references/embeddings/manifest.json` | `biominer-artifact-manifest-v1` | inventory, checksums, and dependencies |
| `references/prototypes/reference_prototypes.parquet` | embedded version field required | route-separated prototype evidence |
| `scores/target_aware_object_scores.parquet` | embedded version field required | raw/calibrated fields kept distinct |
| `scores/target_aware_candidate_scores.parquet` | embedded version field required | full candidate-union evidence |

Files not listed above require a new migration-manifest entry and contract
review before ingestion. Historical `examples/` and `reports/` are not product
handoffs. Model weights, downloaded media, and provider payloads are never
implicitly ingestible merely because a BioMiner manifest references them.

### Acceptance rules for every handoff

The ButterflyLens adapter must fail closed unless all applicable checks pass:

1. the producer repository and full SHA match the approved migration entry;
2. every required artifact is named in the upstream inventory;
3. byte count and SHA-256 match before parsing;
4. schema version is explicitly supported—missing or unknown is not upgraded;
5. Parquet columns and types pass a ButterflyLens-owned runtime schema;
6. semantic fingerprints recompute identically where a shared contract exists;
7. dependency fingerprints resolve to artifacts in the same verified graph;
8. row primary keys are unique and declared foreign keys resolve;
9. evidence maturity, provider, licence, review, coordinate, and removal fields
   remain attached;
10. partial, failed, blocked, stale, and awaiting-review stages remain visible;
11. no raw score is mapped into a probability field;
12. provider/media rights pass the independent ButterflyLens rights gate.

TypeScript or JSON Schema validation may confirm structure, but it cannot
substitute for Parquet checksum verification, statistical policy, source
rights, or human review.

### Integration prohibitions

- Do not import `biominer.*` from the ButterflyLens web application.
- Do not copy `src/biominer` or vendor upstream internal modules.
- Do not use a BioMiner worktree path as a production dependency.
- Do not let the browser invoke provider APIs, YOLOE, BioCLIP, or BioMiner.
- Do not accept floating branches, tags, package versions, model revisions, or
  artifact prefixes as immutable identity.
- Do not infer ALA support, all-Australia coverage, live M5 readiness, human
  verification, calibration, or release readiness from the upstream audit.
- Do not use `detector_crop` output in a target-aware ButterflyLens decision;
  require the explicit full-frame transformation and fingerprint contract.

If the pinned BioMiner SHA changes, ButterflyLens must repeat the relevant
audit, update `provenance/biominer_migration_manifest.yaml`, rerun contract
tests, and record whether each integration is unchanged, migrated, or blocked.

The command, reference-contract, run-path, and target-aware CLI boundary was
checked separately at the pinned commit: `121 passed in 8.71s`. This remains an
offline interface check, not evidence that a provider or model run completed.
