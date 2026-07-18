# Task plan — ButterflyLens 11.4

Task ID: `butterflylens-11.4`

Objective: add a credential-free judge replay that loads stored deterministic
tool calls and outputs, preserves exact artifact citations, is visibly labelled
replayed, and never simulates or claims live GPT-5.6 inference.

Starting and remote SHA:
`efcf45890d6da5e958f4d46240d3e8c00be8e68b`.

OpenAI boundary: retain the frozen Task 11.1 policy and Task 11.3 live route
unchanged. The replay performs zero Responses calls, zero network calls, and
zero runtime tool calls. It does not claim that `gpt-5.6-sol` authored a stored
answer when no such invocation occurred.

Artifact: generate a strict versioned replay catalogue from the Python authority
for the Task 11.2 evidence tools. Store exact arguments and complete validated
tool-result envelopes for three judge questions: species evidence, national
ALA/Flickr comparability, and next reference-review priorities. Fingerprint each
trace and the complete catalogue with RFC 8785 SHA-256.

Grounding: replay response claims may only cite exact citations present in their
stored tool outputs. Generated tests re-invoke the deterministic tools and
require byte-identical arguments/results, strict schema validity, exact source
commit, zero model/network calls, response-to-trace tool parity, unique IDs, and
catalogue/trace fingerprints. Missing or altered replay questions fail closed.

Public experience: the submitted Ask surface defaults to the stored replay
client, labels every answer `Replayed`, says no model or tool was invoked, and
offers only the three stored questions. An injected authenticated live client
remains separately labelled `Live`; replay mode never falls through to it.

Verification: deterministic generator replay, strict Python schema tests,
browser catalogue parser/tamper/no-fetch/component tests, web typecheck/build,
full Python suite, existing Deno tests/type check, rights/licensing, provenance,
staged secret/model/media/large-file gates, exact commit, and non-force push.

Parallel state: BioMiner remains active and dirty without an immutable GBIF
handoff. Task 10.4 remains deferred while the user-reported Flickr fetch runs.
Do not call Flickr or GitHits, read partial BioMiner output, or run YOLOE/BioCLIP.

Rollback: remove the replay generator, schema/catalogue, parser/client/UI replay
mode, tests, documentation, and task provenance. The live Edge Function remains
unchanged and no external state requires rollback.

## Result

Implemented the three exact stored questions, complete tool-result envelopes,
strict generated schema, result/trace/catalogue fingerprints, browser verifier,
single-turn fail-closed client, visible trace, and distinct replay UI. The live
Edge Function is unchanged. No OpenAI, Supabase, Flickr, model, or provider call
was made.

Verification passed: 442 locked Python tests; 15 focused replay/requirements
tests; 26 frozen Deno Edge tests plus type and format checks; 67 Vitest tests;
web typecheck and production build; 116-package web licence report; 52-provider
rights verification; 424-file licence verification with zero model files; and
byte-identical schema/catalogue regeneration. Browser E2E and a live model run
were not performed or claimed.

BioMiner was observed at
`6b22bf3b8c2dc6cc46bbe19d29756f1a2b0ada61`, dirty on active dynamic-pooling
and BioCLIP work. Its current-state ledger still lists live GBIF acquisition and
durable admission as unfinished, so no partial artifact was read or copied.
