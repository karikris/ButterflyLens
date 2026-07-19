# Task 19.1 plan — remove the obsolete fingerprint compatibility island

Task ID: `butterflylens-19.1`

Objective: finish the repository-wide implementation uplift with one
high-confidence simplification: remove the unused evidence-fingerprint v1.0
schema, vocabulary, union types, validator branch, parity fixtures, and
compatibility-positive tests. Retain v1.1 as the only admitted fingerprint
contract and prove that v1.0 now fails closed.

Starting and remote SHA:
`b86d32334476f6497a7ac187472c2d2cb53e80a9`.

Exact upstream boundaries inspected:

- BioMiner `ae6a18509b7be48da5c6ca69ab0caacf4632cc70`;
- TaxaLens `e845dd98493979f37b04dbb6538e0d7b8758ca11`.

Neither committed upstream tree contains a v1.0 fingerprint consumer or
artifact. Their dirty worktrees are user-owned and remain untouched. BioMiner
is still fetching Flickr metadata only; this task will not wait for or copy
partial output and will make no Flickr API call. No BioMiner data is expected.

Evidence and scope:

- v1.0 was introduced at `9fd6137596613eb19d87f537e37c5be140e27122`
  and superseded by v1.1 at
  `690592cb8b2ff31da22734504b69dcda04b86c19` on 18 July 2026;
- tracked searches find v1.0 only in its own schema, declarations, fixtures,
  exports, and compatibility tests;
- no submitted artifact or runtime record uses v1.0;
- the v1.1 vocabulary is authoritative and distinguishes logical query
  associations and source responses instead of the legacy `api_response` kind.

GitHits solution `f19c0cc1-02b7-44e2-9bc6-0bff36544b17` was consulted under
strict licensing. The adopted pattern is current-only validation plus an
explicit negative test for the retired version; no source code is copied.

Headroom was used to inspect the repository inventory and implementation
surface under receipts `c616f4b972c9064f6e680cef`,
`cb010be6f1f94f4be6ed02b6`, and `a00314dbc32ea6436f5c1e83`.

## Subtask 19.1.1 — make the fingerprint contract current-only

- Delete the retired v1.0 JSON Schema.
- Remove legacy constants, vocabulary, types, validator branches, and exports
  from the TypeScript and Python contract surfaces.
- Simplify graph storage and return types to the concrete current fingerprint
  type instead of the compatibility union wrapper.
- Remove v1.0 parity roots and declaration checks; retain current positive
  coverage and add explicit schema-version rejection evidence.
- Update governed inventory counts and wording.

Scientific and data boundary: this is a wire-contract cleanup only. It changes
no taxonomy, occurrence baseline, evidence interpretation, human-review state,
model behavior, public release decision, or provider claim. The rebuilt ALA
baseline remains authoritative. YOLOE and BioCLIP work remains unfinished and
out of scope.

Security and rights boundary: validation remains strict and fail-closed. No
credentials, Flickr content, mutable upstream output, bulk data, or private
location data will be read or written.

Tests: focused fingerprint validation, contract coverage, Python/TypeScript
parity, package typecheck/build, then the repository's full offline gates,
release-security checks, JSON/JSONL validation, compilation, whitespace, and
tracked-scope checks.

Rollback: revert the focused implementation commit to restore the frozen v1.0
schema and compatibility branch if a real persisted consumer is later proven.

Commit: `refactor(contracts): remove legacy fingerprint version`.

## Task closeout

- Record GitHits, Headroom, exact upstream commits, tests, model provenance,
  and the intentionally unfinished external/model work.
- Push `main` without force and verify the remote SHA.

Commit: `docs(provenance): close implementation uplift`.
