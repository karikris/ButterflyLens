# ButterflyLens 15.1 — unit and contract coverage

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`8337a401d5a45e0c886772b0916a1eb3218cc691`.

## Outcome

ButterflyLens now has one executable, Git-discovered inventory gate for every
governed fingerprint vocabulary, tracked schema document, discovered versioned
policy, submitted JSON artifact, and exported submitted/live projection. A new
surface cannot silently increase an aggregate count: it fails until the
registry names positive and negative evidence and the referenced test token
exists.

The inventory covers:

- 29 current and 28 frozen legacy semantic fingerprint kinds;
- all eight allowed fingerprint parent relationships;
- 36 tracked schema documents in five exact coverage groups;
- all 25 cross-language contract schemas through 21 positive and 21 negative
  parity roots, including the four shared/aggregate schemas by reference
  reachability;
- 11 discovered versioned policies and every current source that declares
  their versions;
- twelve governed projection families, every exported submitted/projection
  symbol, and all seven submitted JSON artifacts; and
- every submitted JSON fingerprint/checksum field, accepting the governed raw
  or `sha256:` representation and explicit null where a projection truthfully
  reports unavailable evidence.

Each current and legacy fingerprint kind is constructed as a valid exact
record and then rejected after a digest mutation. Each allowed parent
relationship validates and an unknown relationship fails. JSON Schemas are
Draft 2020-12 checked; frozen ALA Parquet schema descriptors retain their own
closed descriptor semantics and named artifact tests rather than being
misrepresented as JSON Schema dialects.

Policy discovery spans tracked policy Markdown, the versioned privacy JSON,
and Python policy-version declarations. Projection discovery spans every
tracked `submitted*.json`, submitted TypeScript export, TypeScript projection
builder, and Python projection function. Registry entries must remain sorted,
non-duplicated, and backed in both test directions.

## Gap closed

The audit found one missing direct negative assertion: the worker public
offline projection already validated snapshot modes internally but no focused
test supplied a live-mode object in the submitted slot. Task 15.1 adds that
test and proves the projection rejects the mismatch before public state is
built. No production implementation needed changing.

Initial failures also documented three intentional representations rather than
normalizing them away:

- submitted fingerprints may be raw SHA-256 or prefixed `sha256:`/`urn:sha256:`;
- the OpenAI artifact registry uses physical `sha256` checksum fields; and
- frozen ALA Parquet descriptors are schema artifacts with field/invariant
  vocabularies, not JSON Schema instances.

## Scientific, privacy, and operational boundary

Named negative coverage preserves candidate-versus-occurrence, provider
assertion versus human verification, score versus probability, representative
audit versus targeted failure discovery, sensitive location, rights/removal,
submitted-versus-live, and worker-independent-site boundaries.

Submitted public JSON is checked for raw coordinate, reviewer identity, and
administrative-contact keys. This test does not claim arbitrary secret or PII
discovery; Task 15.5 remains the complete security/compliance audit.

No schema pass, fingerprint, line count, or test count is presented as
biological truth, provider rights, human review, production quality, or ALA
acceptance.

## Verification

- Eight focused Task 15.1 tests pass. They data-drive 57 version/kind pairs,
  eight valid and one invalid relationship, 36 schema documents, 11 policies,
  twelve projections, seven submitted JSON artifacts, and the worker invalid
  mode boundary.
- The complete locked Python suite passes all 564 tests in 21.6 seconds.
- Before implementation, the 556-test suite was run through Python's standard
  library trace counter. It observed every executable line reached across all
  tracked Python contract, verification, storage, OpenAI, worker, and builder
  modules exercised by that suite. The trace result is supporting audit
  evidence only and is not used as semantic completeness proof.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixtures, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing, JSON/JSONL, workflow YAML, shell syntax, Python compilation,
  whitespace, staged scope, secret-safety, model/media/archive-file, and
  large-file checks are completed immediately before commit.

## Research and external-work boundary

The task depends only on versioned local code, schemas, policy documents,
fixtures, projections, and tests. No mutable external fact was needed. Valyu is
logged not needed. GitHits remained disabled by explicit user instruction and
was not called. No external implementation was copied.

BioMiner was inspected only through Git state and its published
`docs/agents/CURRENT_STATE.md` coordination record. It advanced during this
task through active dynamic-pooling CLI validation work to
`5166cf8408331898694cfd1ab5994c075a62458b`. Its authoritative remaining-work
ledger still includes live current-policy GBIF acquisition/durable admission,
live BioCLIP/Flickr scoring, representative Flickr review, and a
sufficient-sample audit. It supplies no immutable GBIF handoff, so no active
data or partial output was copied. The rebuilt ButterflyLens ALA baseline
remains authoritative.

TaxaLens remained at
`e845dd98493979f37b04dbb6538e0d7b8758ca11`; its dirty user work was untouched.
The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, Flickr result import, Supabase or
B2 mutation, provider submission, media copy, production workflow dispatch,
YOLOE work, BioCLIP work, scientific model call, or scientific inference
occurred.

Known limitation: named-reference coverage proves registry completeness and the
full gate executes those suites, but finite fixtures cannot prove every future
input or environment. Task 15.2 must now exercise the cross-component ALA,
Flickr, worker, model-state, review, map, GPT-tool, and export integrations.

Next safe task: add Task 15.2 integration tests after this exact commit is
pushed and its Pages deployment is verified.
