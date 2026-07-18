# ButterflyLens 18.6 — representative live analyst recorder

Status: **credentialed recorder complete; the live GPT-5.6 evaluation, overall
ButterflyLens goal, and public release remain unfinished**.

Starting and remote SHA:
`6a316b6f08cfe9e90d2f814d998cbd7c4974e227`.

Subtask commit:

- `8b7ed09f05aff3fe116ae8ecd5a04391fbe7a7a4` — explicit-opt-in,
  resumable recorder for the frozen 48-case analyst evaluation.

Ending and remote SHAs: pending the containing Task 18.6 closeout commit and
non-force task push.

## Outcome

`scripts/run_openai_live_evaluation.ts` now supplies the missing operator path
between the frozen representative suite and the existing independent grader.
It imports the exact production `runAnalyst` loop and deterministic Submitted
tool executor, so the model prompt, request policy, strict schemas, citation
checks, tool budgets, and scientific grounding boundary cannot diverge into a
second evaluation-only implementation.

The command requires `--confirm-live`, an unused output path, a checkpoint
path, `OPENAI_API_KEY`, and a private evaluation subject in the process
environment. It hashes the subject before any request. Neither secret is
accepted on the command line, written to a trace/checkpoint, or printed.

Every completed case is atomically checkpointed with its actual selected tool
name, arguments, deterministic output, final structured response, exact suite
fingerprint, model `gpt-5.6-sol`, reasoning effort `xhigh`, and cumulative
Responses request count. Resume accepts only an integrity-checked exact prefix
of the same 48-case suite and does not repeat checkpointed cases.

The generated trace schema now permits zero tool calls structurally. This does
not weaken evaluation: the independent grader still requires exactly one
correct tool call and rejects zero, wrong, or multiple calls. The change lets a
refusal, transport failure, or unsafe no-tool answer remain observable instead
of being discarded before grading.

## Verification

- The complete Python repository suite passes all 662 tests in 32.252 seconds.
- All 49 Deno Edge tests pass, including three new recorder tests.
- The synthetic recorder test interrupts after one durable case, resumes the
  remaining 47, observes exactly 96 local response-loop steps, and records zero
  model and network calls.
- The altered-checkpoint test fails on its complete semantic fingerprint.
- The CLI rejects execution without the explicit `--confirm-live` switch.
- Deno formatting passes for 24 files. The recorder and all four Edge entry
  points type-check against the pinned Deno configuration and OpenAI SDK.
- The 72 focused OpenAI, replay, tool, contract-coverage, and release-security
  tests pass.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 635 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 611 tracked text files, and 12 explicitly
  inventoried external-network boundary files. `release_ready=false` remains
  binding.
- The current completion audit still validates at 80 satisfied criteria with
  `goal_complete=false`.
- Generated-schema byte identity, JSON/JSONL parsing, Python compilation,
  whitespace, secret scanning, and staged-scope checks pass.

## Current external contracts

The OpenAI Developer Docs MCP confirms that `gpt-5.6-sol` is the current Sol
snapshot and supports Responses, Structured Outputs, and function calling.
The official strict-mode guide retains the all-fields-required and
`additionalProperties: false` requirements used by ButterflyLens. No request
or prompt-policy change was needed.

The user-requested project-scoped Supabase MCP OAuth browser window was
launched. The callback timed out without approval, so no OAuth token, project
read, secret read, function call, database query, or project mutation occurred.
The current Supabase changelog documents a successful OAuth token status change
from HTTP 201 to HTTP 200. This attempt timed out before token exchange, so no
client-compatibility claim is derived from it.

GitHits remained unavailable and was not called. Headroom was used for the
large source goal, agent pack, and staged-diff review under receipts
`898dbe5ec3520d1425bf5d0f`, `2352c8911e640d981278d8bc`, and
`cbdf7babef53b3ba32b06404`.

## Binding unfinished work

No OpenAI Responses request or model output was produced. The checked-in
offline evaluation therefore remains `live_model_state=not_run`; criteria 73
and 81 are not upgraded. A later operator must deliberately provide the secure
environment, accept the bounded cost, run all 48 cases, grade the exact trace,
inspect any failures without silently retrying them away, and obtain the
required human review before a live result can be committed or displayed.

BioMiner is still fetching Flickr metadata only. This non-overlapping task did
not inspect, copy, or count its mutable record and made no Flickr API call.
YOLOE and BioCLIP remain unfinished by user instruction. No provider, B2,
Supabase project, image-generation, video-generation, or public-release action
occurred.

The existing demonstration packet is now known to contain stale pre-map shot
wording. The next safe local task is to refresh that packet against the
immutable Submitted ALA map while the completed Flickr handoff and live-model
credentials remain unavailable.
