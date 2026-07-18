# ButterflyLens 17.5 — final Build Week provenance

Status: **provenance finalization complete at the fixed Task 17.4 audit
boundary; product/data release remains blocked**.

Starting SHA: `8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97`.

Ending SHA: pending the containing Task 17.5 commit.

Remote SHA: pending the containing Task 17.5 push.

BioMiner SHA inspected for coordination:
`0874a8b6be5eb256d0756681edf04b15fdcce310`.

TaxaLens SHA inspected for coordination:
`e845dd98493979f37b04dbb6538e0d7b8758ca11`.

## Outcome

`BUILD_WEEK_DELTA.md` now replaces the obsolete Phase 0-only summary with an
auditable Build Week account. It fixes the input at the pushed Task 17.4 commit,
quantifies 120 non-merge commits and the 581-file delta, inventories new
ButterflyLens work by phase, separates BioMiner and TaxaLens precedents from new
work, and names the one copied attributed upstream fixture.

The final collaboration record and machine-readable session receipt distinguish
four kinds of evidence that must not be collapsed:

- Kris Kari's product and execution decisions;
- Codex-authored repository work and deterministic verification;
- the requested `gpt-5.6-sol` / `xhigh` configuration, recorded 105 times but
  never separately exposed as observed runtime identity; and
- the application's uninvoked live GPT-5.6 target and model-free Submitted
  replay.

The exact non-secret `/feedback` Session ID is
`019f7038-92ae-7021-8318-53ca97648404`. The available API surface did not expose
slash-command invocation, so the receipt records the identifier while keeping
`command_invoked` and `feedback_submission_observed` false.

## Evidence accounting

At the fixed audit boundary:

- all 120 Git commits have append-only receipts;
- 77 task-level, non-force push receipts are present;
- 105 model-activity records use the same session, requested model, and effort,
  with `runtime_model_identity_observed: false` in every record;
- 130 GitHits records retain the prior unavailable/disabled history without a
  new call, and 104 Valyu records retain exact prior use/skip decisions;
- this patch produces 65 task reports and 39 task plans;
- the BioMiner manifest has 15 component records, the TaxaLens manifest has 17,
  and only one upstream asset was byte-copied; and
- `HUMAN_DECISIONS.md` has 15 sections while the human-review attestation ledger
  remains empty.

The containing commit cannot store its own full Git SHA without self-reference.
The session receipt therefore pins the parent commit, tree, remote SHA, and
hashes of stable audit inputs. The final containing SHA is verified from remote
`main` after the required push.

## Headroom-assisted audit

The Headroom skill compressed the unusually large provenance corpus before
exact local source queries were used for identifiers, counts, and hashes. The
three task-specific compression receipts are:

- core documentation and manifests: `504a09159e203964093d4131`;
- append-only JSONL ledgers: `7621abd7c83707de1ab1f539`; and
- task reports: `6f5fcc419eaba18612635562`.

At audit time, the session-wide Headroom statistics were seven compression
events, one retrieval, 404,862 input tokens, 334,533 output tokens, and 70,329
tokens saved (17.4%). Only the three receipts above were created for this task.
Compression guided corpus navigation; every published exact value was checked
against Git or the source artifact.

## Verification

- All 10 focused provenance validators pass. They cover the immutable first
  commit and audited Git range, delta facts, exact commit/push/model/tool
  counts, stable receipt hashes, migration-kind inventories, copied-asset
  rights, parallel-work exclusions, human decision/review separation, test
  evidence, and the self-reference boundary.
- All 620 locked Python tests plus 229 subtests pass in 22.18 seconds.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  TypeScript, the 119-package dependency-licence report, review-media checksum,
  and production build pass. The unchanged script remains 1,496.87 kB / 229.80
  kB gzip with the existing non-blocking chunk-size warning.
- All 45 frozen Deno Edge tests pass; the four Edge entry points type-check and
  all 22 function files pass formatting.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid roots,
  21 versions, and 15 vocabularies using TypeScript 7.0.2.
- All 10 Playwright browser and visual checks pass in 5.4 seconds across
  Chromium, Firefox, WebKit, mobile, reduced motion, forced colours, and no
  WebGL. As previously documented, untracked extracted host libraries and the
  Playwright host-validation bypass were required on this WSL host.
- The canonical Submitted snapshot reproduces exactly. Release security passes
  across 50 RLS tables, 11 security-invoker views, 60 security-definer
  functions, 563 tracked text files, and 10 network-boundary files while
  retaining `release_ready=false`. The final staged rerun expands the text scan
  to 567 files. Rights verifies 53 tracked provider payloads. Licensing verifies
  586 staged repository files, two dependency manifests, and
  zero model files.
- The first aggregate Python command used the dependency-free host interpreter
  and failed during collection; rerunning with the locked site packages passed
  the complete suite. The first browser command omitted the documented
  untracked host-library configuration; the configured full rerun passed all
  engines. Neither false start identified a repository regression.

## Rights, privacy, provenance, and parallel work

This task adds documentation, JSON metadata, YAML review state, append-only
ledger entries, and tests only. It copies no provider data, source image,
uncommitted upstream file, model artifact, reviewer identity, credential,
access token, private endpoint, or worker telemetry.

BioMiner had committed a dynamic-pooling default but still retained active
uncommitted Flickr and reporting work. No completed immutable ButterflyLens
GBIF/Flickr handoff receipt was present, so nothing partial was copied. The
operator-supplied GBIF download and DOI are recorded, but the archive has not
yet been fingerprinted or converted to the requested authoritative Parquet in
this repository. The independently rebuilt ButterflyLens ALA baseline remains
authoritative.

The external Flickr fetch reported by the operator at 50,000 unique images was
acknowledged without inspection. No Flickr API call occurred. GitHits remained
disabled and was not called. YOLOE and BioCLIP remain explicitly unfinished.
No live model, Supabase, B2, provider, video, Devpost, or submission mutation
occurred.

## Remaining release blockers

The Submitted snapshot remains `release_ready: false`. Required future human or
external work includes immutable GBIF and Flickr handoffs, GBIF Parquet
admission, provider-rights resolution, live service/operator checks, live M5
worker and analyst evidence, community review and quality evidence, final
recorded public video, competition submission, and explicit human approval.

Scientific claims allowed: exact repository history, source-manifest inventory,
requested configuration, deterministic stored-artifact counts, measured test
and deployment properties, and explicit unavailable states.

Scientific claims blocked: model accuracy or runtime identity, butterfly
identity, biological absence, Flickr completeness, human consensus, reviewer
reliability, representative quality, released geographic impact, public
occurrence evidence, or overall scientific/data release readiness.
