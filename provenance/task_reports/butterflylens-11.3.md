# ButterflyLens 11.3 — Ask ButterflyLens

Status: **implemented and locally verified; live deployment and inference not run**.

Starting SHA: `5d93cf0aab9fe911b1b9d1d3979ef172f75b3d84`.

## Outcome

ButterflyLens now has an authenticated Supabase Edge Function and accessible
public Ask ButterflyLens surface. The function owns the exact OpenAI 6.48.0
SDK and server secret; the browser contract can carry only a Supabase
publishable key and signed-in user's JWT. The committed submitted experience
injects no live client and truthfully reports that no model call was made.

The Responses loop sends explicit `bounded-model`, `xhigh`, `current_turn`,
`store: false`, serial custom tools, strict JSON Schema output, a hashed Auth
safety identifier, and no stored-response chaining. The pinned SDK confirmed
that `max_tool_calls` is not a supported Responses request field, so the
application enforces eight total tool calls itself. It also enforces six
response attempts, 1,800 output tokens, ten seconds per tool, one transient
tool retry, a 90-second overall deadline, and no implicit SDK retry.

## Grounding and security

Every non-refusal model answer requires current deterministic tool evidence.
Completed answers require at least one cited claim. Tool declarations must
exactly match executed tools, and every final citation must byte-for-byte match
an artifact citation returned during the current loop. Unknown calls,
malformed arguments, transport failures, timeouts, modified citations,
citation-free summaries, claims hidden in refusals, and exhausted budgets fail
closed into bounded structured states.

The platform `verify_jwt` gate and `@supabase/server` `auth: "user"` wrapper
both remain enabled. The pure HTTP boundary rejects non-POST, oversized,
malformed, secretless, or subjectless requests before the model runner. It
returns `no-store`/`nosniff` responses and sanitizes unexpected errors. No
service-role client, database write, remote MCP, built-in tool, log statement,
or browser OpenAI key exists.

The exact Deno pins are `openai` 6.48.0 and `@supabase/server` 1.4.0. A frozen
lock and generated licence report cover all twelve npm packages and their
registry integrities. The optional local Studio assistant uses a distinct
environment variable from the application secret.

## Verification

- Twenty-six Deno tests cover the Responses loop, all fourteen evidence tools,
  budgets, call IDs, retries, transport/tool failures, strict grounding,
  refusals, privacy hashing, HTTP limits, auth subject, secret absence, and
  sanitized errors.
- Frozen Deno resolution, format, and Edge Function type checking pass.
- Sixty-six Vitest parser, component, interaction, and shell tests pass.
- Web dependency/media audits, strict type checking, and production build pass.
- The full locked Python suite passes: 434 tests.
- Rights verification covers 52 tracked provider payloads. The staged licence
  verification covers the Deno lock and its exact twelve-package report.
- JSON/JSONL, whitespace, staged secret/model/media, exact commit subject, and
  non-force push checks remain final release gates.

## Parallel and operational state

BioMiner advanced to `9327b0af38232d9f98e276dd02df1bac34d6634e` but
remains ahead/dirty on active BioCLIP matrix-cache and Flickr estimator work.
Its current-state ledger still lists live GBIF acquisition and durable admission
as remaining; no immutable GBIF handoff exists. No partial BioMiner output was
read or copied. Task 10.4 remains unfinished while the user-reported Flickr
fetch runs. Flickr API, GitHits, YOLOE, BioCLIP, live Supabase, and live OpenAI
were not called or run.
