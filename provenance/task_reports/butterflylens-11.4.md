# ButterflyLens 11.4 — Credential-free analyst replay

Status: **implemented and locally verified; no model invocation or live call**.

Starting SHA:
`efcf45890d6da5e958f4d46240d3e8c00be8e68b`.

## Outcome

The submitted Ask ButterflyLens surface now replays three exact judge
questions with no login, API key, Supabase account, worker, model, or network
dependency. Each case stores the deterministic Task 11.2 tool name, exact
arguments, complete validated tool-result envelope, and a project-authored
structured evidence rendering. It is not represented as GPT-5.6 output.

The browser strictly parses the catalogue and recomputes RFC 8785 SHA-256 over
every stored result, complete trace, and catalogue before displaying evidence.
The response citations must exactly match citations in the stored tool outputs,
and the response tool inventory must exactly match its trace. Structural or
fingerprint changes, unknown questions, and conversation history fail closed;
there is no fallback to live inference.

The UI labels the mode `Replayed`, exposes the stored tool name, call ID,
arguments, output status, summary, and fingerprint, and says that no model was
invoked. The authenticated Task 11.3 live client remains a separately injected
mode and the server function was not changed.

## Verification

- 442 locked Python unit tests passed, including 15 focused replay and OpenAI
  requirements tests.
- The replay generator produced byte-identical schema and catalogue files;
  strict Draft 2020-12 validation and deterministic tool re-invocation passed.
- 67 Vitest tests passed, including no-fetch, exact-question, citation/trace,
  structural-tamper, fingerprint-tamper, and replay UI tests.
- Web TypeScript checking and production build passed; the generated client
  bundle measured 1,468.09 kB (222.76 kB gzip), with the existing Vite
  chunk-size warning retained and no performance claim made.
- The exact 26 frozen Deno Edge tests, Edge type check, and ten-file format
  check passed through the cached `npx --no-install deno` executable.
- Rights verification passed for 52 tracked provider payloads. Licence
  verification passed for 424 tracked files and reported zero model files; the
  web dependency report verified 116 packages.

## Evidence and limitations

No OpenAI Responses request, GPT-5.6 output, Supabase request, Flickr API call,
provider lookup, database operation, YOLOE run, or BioCLIP run occurred. The
three replay responses are deterministic project-authored renderings of stored
tool evidence. Questions outside the exact catalogue are unavailable, and the
replay deliberately does not simulate multi-turn conversation.

BioMiner was observed at
`6b22bf3b8c2dc6cc46bbe19d29756f1a2b0ada61`, with active dirty dynamic-pooling
and BioCLIP work. Its authoritative state still lists live GBIF acquisition and
durable admission as unfinished, so no GBIF or partial Flickr artifact was read
or copied. Task 10.4 remains unfinished while the user-reported Flickr fetch
runs. GitHits remained disabled by user instruction.
