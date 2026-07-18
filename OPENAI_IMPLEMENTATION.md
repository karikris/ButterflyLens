# OpenAI analyst implementation requirements

Verified against current official OpenAI documentation on 18 July 2026. This
document governs Tasks 11.2–11.5. The machine-readable source is
`packages/openai/implementation-requirements.v1.json`.

## Verified decision

Use the direct Responses API with explicit model `gpt-5.6-sol`. OpenAI's current
model guide identifies Sol as the flagship GPT-5.6 model and says the
`gpt-5.6` alias routes to it. The explicit slug is retained for replay and model
provenance. The user-required `xhigh` effort is the first baseline; it may be
changed only after representative ButterflyLens evals show a better measured
trade-off. [Model guidance](https://developers.openai.com/api/docs/guides/latest-model)
and [upgrade guidance](https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol).

ButterflyLens is one bounded evidence analyst with deterministic local tools,
so the direct Responses API is sufficient. Do not add Agents SDK, multi-agent,
Programmatic Tool Calling, hosted tools, remote MCP, file search, or web search
without a later measured requirement. The Responses API is OpenAI's current
recommended surface for reasoning, tool use, structured outputs, and multi-turn
workflows. [Responses migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)
and [deployment checklist](https://developers.openai.com/api/docs/guides/deployment-checklist).

## Server and request boundary

- Use the official JavaScript SDK only in a trusted server runtime. Pin the
  exact SDK version and dependency notices when Task 11.3 adds it.
- Read `OPENAI_API_KEY` from the server environment or a key-management service.
  Never return it, persist it in Supabase, include it in a browser bundle, or
  accept it from browser input. OpenAI explicitly classifies API keys as secrets
  and prohibits client-side exposure. [API authentication](https://developers.openai.com/api/reference/overview#authentication).
- Send `model: "gpt-5.6-sol"`, `reasoning: { effort: "xhigh", context:
  "current_turn" }`, `store: false`, `parallel_tool_calls: false`,
  `max_tool_calls: 8`, `max_output_tokens: 1800`, and `tool_choice: "auto"`.
  The application independently enforces six continuation loops, ten seconds
  per tool, and one retry for a transient tool failure. Budget exhaustion is a
  labelled incomplete answer, never an unbounded retry.
- Send a stable privacy-preserving `safety_identifier`: SHA-256 of the permanent
  Auth identity for signed-in users, or of a stable random session identifier
  for a logged-out replay. Never send email, public name, raw Auth UUID, or IP.
  [Safety identifiers](https://developers.openai.com/api/docs/guides/safety-best-practices#implement-safety-identifiers).
- `store: false` is mandatory. The current Responses default retains application
  state, while OpenAI documents up to 30-day default response application-state
  retention. ButterflyLens therefore manages its own governed transcript/replay
  state and does not rely on OpenAI response storage. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

If a future multi-turn design needs persisted reasoning, preserve all returned
output items and encrypted reasoning content exactly. Do not enable it by
default; `current_turn` avoids stale reasoning and simplifies credential-free
replay.

## Tool and output contracts

Every Task 11.2 function is read-only and deterministic. It accepts IDs and
scope selectors, then returns bounded evidence packets. The server validates
arguments before dispatch, validates output before returning it to the model,
and preserves `call_id` on `function_call_output`.

Every function definition uses `strict: true`. Each object sets
`additionalProperties: false`; every property is required; optional values are
required nullable fields. Apply the same rules recursively. OpenAI recommends
strict function calling and documents those exact schema requirements.
[Strict function calling](https://developers.openai.com/api/docs/guides/function-calling#strict-mode).

The final analyst message uses strict Structured Outputs through `text.format`,
not JSON mode. Function schemas structure calls; the separate final schema
structures the user-visible answer. Parse every output item and explicitly
handle refusal, incomplete details, failed/cancelled status, function calls,
and the final message. A safety refusal may not match the ordinary answer
schema and is a first-class UI state. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Evidence-grounded answer boundary

The model is not a butterfly identification source. It may synthesize only
facts returned by the deterministic tools. Every factual claim carries one or
more allowlisted citations containing artifact ID, repository, exact commit,
path, and fingerprint. The server rejects missing or mismatched citations.

The prompt and schema must require the analyst to:

- state `unavailable`, not zero or no, when evidence is absent;
- preserve source conflicts and distinguish direct facts from inference;
- never invent taxon/provider IDs, names, metrics, worker state, review state,
  quality, rights, geographic presence, or release status from model memory;
- never treat model text as consensus, expert review, quality, or publication;
- keep private reviewer/control fields and sensitive coordinates withheld;
- cite only artifacts returned in the current tool run; and
- return a bounded incomplete result when the evidence or tool budget is
  insufficient.

The prompt should be short and outcome-first, with explicit success, evidence,
permission, tool-routing, stopping, and output rules. Remove repeated
instructions only after the same eval set passes. [GPT-5.6 prompting guidance](https://developers.openai.com/api/docs/guides/prompt-guidance-gpt-5p6).

## Live, replay, and evaluation

Live inference and stored judge replay are distinct states. A replay contains
the exact stored request policy, tool calls, tool outputs, citations, final
structured result, model slug, and checksums. It is labelled `replayed`; it
never claims a live model call. If no key exists, only replay is available.

Task 11.5 must include at least 40 representative cases and evaluate more than
final prose: tool selection, argument precision, schema adherence, citations,
unsupported-claim refusal, missing-evidence abstention, privacy, budget use,
and replay labels. Start with deterministic tools and stored traces; use live
model or Evals API claims only when those calls actually ran. OpenAI recommends
evaluating where nondeterminism enters, including tool selection/arguments, and
moving from trace inspection to repeatable datasets/eval runs.
[Evaluation best practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)
and [agent evaluations](https://developers.openai.com/api/docs/guides/agent-evals).

## Current repository gap

At this task boundary ButterflyLens has no OpenAI SDK dependency, API route,
runtime key, analyst prompt, function tool implementation, live trace, live
model output, or agent evaluation result. `supabase/config.toml` contains only
the upstream local-development environment placeholder. The third-party audit
approves the official SDK's Apache-2.0 licence conditionally but requires the
later implementation to pin and audit its exact dependency tree.

No live OpenAI API call occurred during this requirements-verification task.

Task 11.2 may now implement deterministic tools without any OpenAI transport.
Task 11.3 may add the server route only after those tool contracts are stable.
