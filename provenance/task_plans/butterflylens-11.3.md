# Task plan — ButterflyLens 11.3

Task ID: `butterflylens-11.3`

Objective: add the authenticated server-side Ask ButterflyLens experience using
the exact frozen Bounded model Responses API policy and the fourteen deterministic
Task 11.2 evidence tools.

Starting and remote SHA:
`5d93cf0aab9fe911b1b9d1d3979ef172f75b3d84`.

Skills: OpenAI Docs governs current model/Responses/strict-output behavior;
Supabase governs the Edge Function, auth, CORS, secrets, dependency, and local
verification boundary. The Supabase MCP OAuth grant is complete but unavailable
to this already-running client until reload, so current official Supabase
changelog and docs are the fallback. GitHits remains disabled and is not called.

Architecture: an authenticated Supabase Edge Function owns the official OpenAI
JavaScript SDK and `OPENAI_API_KEY`. The static React browser may hold only a
Supabase publishable key and user session token; it never receives or accepts an
OpenAI key. The function performs no database or service-role operation.

OpenAI policy: explicit `bounded-model`, `xhigh`, `current_turn`, Responses API,
`store: false`, no built-in tools, no remote MCP, `parallel_tool_calls: false`,
eight total tool calls, six response loops, 1,800 output tokens, ten-second tool
timeout, one transient tool retry, finite overall deadline, no implicit SDK
retry, and a SHA-256 privacy-preserving Auth safety identifier.

Grounding: invoke only the exact fourteen strict local functions. Preserve
function call IDs and all response output items. The final strict Structured
Output contains scalar claims and exact artifact citations. Server validation
rejects unknown tools, malformed arguments/results, fabricated citations,
uncited claims, unknown tool-use declarations, malformed/refused/incomplete
responses, and budget overruns. The prompt forbids species/provider IDs, map
counts, rights, quality, reviewer/worker state, or release claims from memory.

Supabase security: use the current platform JWT gate plus `@supabase/server`
authenticated-user wrapper, wrapper-owned CORS, method/body limits, no-store
headers, sanitized errors, and exact dependency pins/lock. Do not log questions,
user IDs, tool outputs, model responses, secrets, or raw provider/reviewer data.

Public experience: replace the scheduled Ask preview with an accessible bounded
chat surface and strict response parser. Live invocation is injected through a
client that accepts a Supabase URL, publishable key, and session-token provider;
the committed submitted replay has no session or live call and states this
honestly. Task 11.4 will add credential-free stored replay without simulating
live inference.

Verification: pure fake-client Responses-loop tests, all fourteen Edge tool
calls, structured-output/citation/refusal/incomplete/budget/privacy cases, Deno
type check and frozen lock, React parser/component/accessibility tests, web
typecheck/build, full Python suite, dependency audit/licence evidence, rights,
provenance JSONL, staged secret/model/media checks, exact commit, and non-force
push. No live OpenAI, Supabase project, Flickr, provider, YOLOE, or BioCLIP call.

Rollback: remove the Edge Function/shared analyst runtime, web analyst surface,
exact dependency lock/evidence, tests, and task provenance. No live state or
secret is changed.
