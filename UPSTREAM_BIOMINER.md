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
