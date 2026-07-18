# Task 18.5 plan — refresh the immutable completion boundary

Task ID: `butterflylens-18.5`

Objective: publish and enforce a second immutable 100-criterion completion
audit at the pushed Task 18.4 boundary, crediting only the map implementation
and artifacts now directly proven while retaining every Flickr, model, live
worker, live GPT-5.6, human-review, video, and release blocker.

Competition criterion improved: repository provenance and displayed-metric
proof (criteria 3–8 and 99), plus exact current evidence for map criteria 19,
61, 63–68, 72, and 96. This task does not itself satisfy a scientific or live
criterion; it corrects the authoritative completion account.

Starting and remote SHA:
`45fb5ac07dcd51852c9e92217667f3f5052868fe`.

Audited tree:
`aa93a6abf058d15c0ef80c7bde241a3355cfe024`.

Source goal SHA-256:
`898dbe5ec3520d1425bf5d0f891c49d6f7615318ed28b35b16f7513684a3fa40`.

BioMiner boundary: this audit task does not overlap BioMiner's active Flickr
metadata fetch. No BioMiner worktree, mutable record, partial output, or Flickr
API will be inspected or copied.

TaxaLens boundary: no upstream integration is needed. The fixed ButterflyLens
Git tree, exact goal criteria, existing audit, map artifacts, tests, and task
reports are authoritative.

Agent files read: root `AGENTS.md`, `docs/agents/README.md`, `TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Skill used: Headroom for the exact 57,356-byte source goal under receipt
`898dbe5ec3520d1425bf5d0f` and the agent-pack review under receipt
`68f877e2154683642274c51a`.

GitHits: unavailable and disabled by direct user instruction for the remainder
of the goal; no call will be made. The disabled status will be recorded.

Valyu: not needed. This task makes no claim based on mutable external facts and
changes no provider contract, public data interpretation, API, licence, model,
or deployment behavior.

Rights and scientific boundary: the full rebuilt ALA baseline remains
authoritative. The second audit may credit the conservative coordinate-free
public map, but must not call it biological completeness, a legal rights
conclusion, Flickr comparison, species identification, or full public release.

Security/privacy boundary: evidence paths must exist in the exact audited Git
tree. Future worktree files, unsafe paths, mutable service state, raw
coordinates, credentials, and user data cannot support a status upgrade.

## Subtask 18.5.1 — publish and enforce the current audit

- Add a deterministic builder for `completion_audit.v2.json` that derives from
  the immutable v1 inventory and applies a closed set of evidence-backed map
  status upgrades.
- Add a fixed-boundary verifier that checks the exact commit/tree, all 100
  criteria, all 46 artifact names, exact summaries, evidence membership,
  status transitions, and the derived `goal_complete=false` result.
- Update `COMPLETION_STATUS.md` to make v2 the current audit while retaining v1
  as historical evidence.
- Add mutation, schema, deterministic-generation, and release-security tests.
- Keep the completion result false unless all 100 criteria and all 46 minimum
  artifacts satisfy the original rule.

Expected result: 80 satisfied, 8 partial, 7 blocked by user instruction, and 5
blocked externally; 14 named artifacts present, 7 equivalents, 5 deferred
model artifacts, and 20 blocked externally.

Commit: `docs(provenance): refresh completion evidence boundary`.

## Task closeout

- Run both historical and current audit verifiers, mutation tests, full Python
  tests, release security, JSON/JSONL, compilation, whitespace, and staged-scope
  checks.
- Record disabled GitHits, not-needed Valyu, model usage, commit receipt, task
  report, exact remaining blockers, and next safe action.
- Push `main` once without force and verify the exact remote SHA.

Commit: `docs(provenance): close current completion audit`.
