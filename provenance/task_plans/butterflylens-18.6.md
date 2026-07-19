# Task 18.6 plan — record representative live analyst evaluations

Task ID: `butterflylens-18.6`

Objective: add the missing explicit-opt-in, resumable recorder for the existing
48-case Bounded model analyst suite so a later credentialed run can produce an exact
schema-valid trace for the fail-closed grader without exposing secrets or
silently repeating completed cases.

Competition criteria improved: 73, meaningful Bounded model runtime evidence, and 81,
representative agent evaluation. This task makes the credentialed run possible
and verifiable; it does not claim either criterion is satisfied until a real
complete trace runs, grades successfully, and receives the required review.

Starting and remote SHA:
`6a316b6f08cfe9e90d2f814d998cbd7c4974e227`.

BioMiner boundary: this task does not overlap BioMiner's active Flickr metadata
fetch. No BioMiner worktree, mutable record, partial output, or Flickr API will
be inspected, copied, or called.

TaxaLens boundary: no upstream integration is needed. ButterflyLens's committed
Responses loop, deterministic submitted tools, evaluation suite, schemas, and
grader are authoritative.

Agent files read: root `AGENTS.md`, `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Skills used:

- Headroom to inspect the exact source goal under receipt
  `898dbe5ec3520d1425bf5d0f` and the updated agent pack under receipt
  `2352c8911e640d981278d8bc`;
- OpenAI docs to verify the current `bounded-model`, Responses API, strict
  function-calling, Structured Outputs, and `/v1/responses` contract;
- Supabase to launch the user-requested project-scoped MCP OAuth flow. OAuth is
  read-only setup for this task; no project mutation is authorised or planned.

GitHits: unavailable and disabled by direct user instruction for the rest of
the goal. No call will be made; the exact disabled status will be recorded.

External documentation: current official OpenAI documentation confirms that
`bounded-model` supports the Responses API, structured outputs, and function
calling. Strict tools require every property and
`additionalProperties: false`. Supabase's current changelog records the remote
MCP OAuth flow and the June 2026 successful-token response change from HTTP 201
to HTTP 200; the current Codex client accepts the standard successful 2xx flow.

## Subtask 18.6.1 — add the live trace recorder

- Add a Deno command that requires an explicit live-call confirmation,
  `OPENAI_API_KEY` in the process environment, a private evaluation subject,
  an output path, and a checkpoint path.
- Run every frozen suite question through the same `runAnalyst` implementation
  and submitted deterministic tool executor used by the authenticated Edge
  boundary.
- Record the actual model-selected tool names, arguments, deterministic outputs,
  final structured response, response-call count, model ID, reasoning effort,
  and exact suite fingerprint.
- Checkpoint atomically after every case, validate and resume only a strict
  prefix of the current suite, and never repeat a checkpointed case.
- Keep the raw API key and private safety subject out of output, checkpoints,
  logs, and command arguments. Retain `store: false` and the bounded response
  and tool budgets from the production analyst.
- Permit a zero-tool case in the trace transport schema so refusal, API failure,
  or unsafe no-tool behavior can be recorded honestly and then rejected by the
  grader rather than disappearing before evaluation.

Expected files: `scripts/run_openai_live_evaluation.ts`, generated
`packages/openai/analyst-live-eval-trace.schema.json`,
`scripts/build_openai_evaluations.py`, `packages/openai/README.md`,
`OPENAI_IMPLEMENTATION.md`, Deno/Python tests, and provenance ledgers.

Contracts affected: live evaluation trace transport only. The production
analyst response schema, deterministic tools, submitted replay, offline result,
model slug, reasoning effort, and scientific evidence rules remain unchanged.

Security/privacy: the runner is local/operator-only, makes no browser key
available, hashes the private subject before any request, uses `store: false`,
prints no model content, and writes only caller-selected trace/checkpoint paths.
No connected Supabase secret will be read into the repository.

Scientific risk: a recorded trace is model-behavior evidence, not butterfly
identity, community review, scientific consensus, or release authority. A
trace is not a passing evaluation until the independent grader validates all
48 cases.

Tests:

- generated-schema byte identity and zero-tool mutation coverage;
- fake-transport full 48-case recording with exact tool traces and fingerprints;
- checkpoint interruption/resume without repeated cases;
- confirmation, environment, path, suite, checkpoint, and output overwrite
  fail-closed checks;
- existing analyst, evaluation, replay, contract, and release-security tests;
- Deno type/format checks, Python compilation, JSON/JSONL parsing, rights,
  licensing, secret/large-file security, and `git diff --check`.

Commit: `feat(openai): record resumable live analyst evaluations`.

## Task closeout

- Run the full offline repository gate without provider or OpenAI calls.
- Record exact tests, official sources, disabled GitHits, model usage, commit
  receipt, remaining live-run/human-review blocker, and the next safe action.
- Push `main` once without force and verify the exact remote SHA.

Commit: `docs(provenance): close live evaluation recorder task`.
