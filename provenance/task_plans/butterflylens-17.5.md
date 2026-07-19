# Task 17.5 plan — final Build Week provenance

Task ID: `butterflylens-17.5`

Objective: replace the Phase 0-only delta with an evidence-backed final Build
Week account of the new repository baseline, imported/adapted components, new
ButterflyLens work, Codex tasks, Bounded model runtime boundary, human decisions,
test evidence, and primary `/feedback` Session ID.

Competition criterion improved: transparent Build Week authorship, origin,
testing, model use, human direction, and unfinished-work disclosure.

Starting SHA: `8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97`

Remote main SHA: `8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97`

BioMiner SHA: `0874a8b6be5eb256d0756681edf04b15fdcce310`

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`

Relevant agent files read: `AGENTS.md`, `docs/agents/TOOLS.md`,
`docs/agents/GIT_AND_PROVENANCE.md`, `docs/agents/TESTING_AND_RELEASE.md`, and
`docs/agents/TASK_TEMPLATE.md`.

Relevant skill: Headroom. It compressed the large core provenance, four JSONL
ledgers, and task-report corpus before exact local queries were used for final
identifiers and counts. Preserved compression hashes:

- core documentation/manifests: `504a09159e203964093d4131`;
- append-only JSONL ledgers: `7621abd7c83707de1ab1f539`;
- task reports: `6f5fcc419eaba18612635562`.

Headroom session statistics at audit time: seven stored compression events,
one retrieval, 404,862 input tokens, 334,533 output tokens, and 70,329 tokens
saved. These session-wide statistics include earlier compression events; only
the three hashes above were created for this task.

GitHits needed: no call. It remains unavailable and disabled for the rest of
the goal by direct user instruction; the existing append-only ledger is the
audit source.

Valyu needed: no. This task reports exact local Git, file, test, session, and
provenance evidence and introduces no mutable external claim.

Files expected:

- `BUILD_WEEK_DELTA.md`
- `CODEX_COLLABORATION.md`
- `HUMAN_DECISIONS.md`
- `provenance/review_attestations.yaml`
- `provenance/sessions/019f7038-92ae-7021-8318-53ca97648404.json`
- `tests/test_build_week_provenance.py`
- Task plan/report and append-only provenance/tool logs

Contracts affected: documentation-only session receipt
`butterflylens-codex-session/v1`; no runtime, provider, data, or database
contract changes.

Data/rights implications: inventory exact origins without moving data. The
active BioMiner/Flickr work, supplied GBIF archive, public ALA occurrence layer,
source-image collections, and unfinished model outputs remain outside the
delta's completed artifacts.

Scientific risks: provenance could overcount upstream capability as new work,
equate Codex configuration with observed runtime identity, imply Bounded model authored
stored replays, call product decisions human review, or call blocked outputs
complete. The final delta must preserve every distinction.

Security/privacy risks: the session receipt may contain only the non-secret
Codex thread identifier and public repository evidence. It must exclude tokens,
credentials, private endpoints, reviewer identities, and environment dumps.

Tests: focused baseline/history/manifest/log/session/human-review/test-evidence
validators; full Python/web/Deno/browser and cross-language gates; snapshot,
security, rights, licensing, JSON/JSONL, session JSON, compilation, shell,
whitespace, staged-scope, secret, generated/binary/model, and large-file checks.

Rollback/recovery: restore the prior append-oriented summaries and remove the
session receipt/focused test. Existing immutable Git history and append-only
ledgers remain the underlying evidence.

## Patch plan

1. Fix the audit boundary at the exact Task 17.4 commit and quantify the new
   repository delta without counting the finalization commit itself.
2. Separate ButterflyLens-owned work from BioMiner/TaxaLens contracts,
   interface precedents, and the one copied attributed review fixture.
3. Record Codex activity and requested model configuration separately from the
   app's uninvoked live Bounded model target and model-free Submitted replays.
4. Add a non-secret session receipt with the exact environment-observed
   `/feedback` Session ID and explicit no-feedback-invocation boundary.
5. Preserve human decisions separately from the still-empty human-review
   attestation ledger and list every remaining release blocker.
6. Validate all cross-file counts and identities, run release gates, commit,
   push, and verify.

## Parallel-work boundary

BioMiner advanced to `0874a8b6be5eb256d0756681edf04b15fdcce310`
with a committed dynamic-pooling default while retaining uncommitted final-report
and Flickr work. No complete immutable ButterflyLens data handoff receipt was
found, so no partial GBIF, Flickr, review, model, pooling, or worker output will
be copied. YOLOE and BioCLIP remain unfinished, and no Flickr API call will be
made.
