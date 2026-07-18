# Task plan — ButterflyLens 11.5

Task ID: `butterflylens-11.5`

Objective: add a versioned, deterministic GPT-5.6 analyst evaluation suite with
at least forty representative cases, a strict trace grader, an offline oracle
result, and explicit separation between tested application boundaries and
unrun live-model behaviour.

Competition criterion improved: representative agent evaluation coverage for
map impact, ALA/Flickr comparison, species maturity, occurrence-overclaim
prevention, reviewer reliability, representative versus targeted review,
worker unavailability, missing references, licence restrictions, First Nations
name governance, model-memory taxon IDs, and fabricated metrics.

Starting and remote SHA:
`69a102cc31253e7d3eb84c91d92de2a0c266b7c8`.

BioMiner: observed at
`6b22bf3b8c2dc6cc46bbe19d29756f1a2b0ada61`, dirty on active dynamic-pooling
and BioCLIP work, with live GBIF acquisition/durable admission unfinished. This
task reads no partial BioMiner data and does not overlap those active files.

Relevant instructions: root `AGENTS.md`; `docs/agents/SCIENCE_AND_DATA.md`,
`TESTING_AND_RELEASE.md`, `TOOLS.md`, `GIT_AND_PROVENANCE.md`, and
`TASK_TEMPLATE.md`; OpenAI documentation skill. Task 11.1's frozen current
official evaluation requirements remain authoritative. No new mutable external
decision exists, so Valyu is not needed. GitHits is disabled by user directive
and will not be called.

Artifacts: generate a strict 48-case suite (four cases in each of twelve
required categories), a strict result/trace schema, and
`packages/openai/agent_evaluation.json`. Each case stores the exact expected
tool and arguments, deterministic result status/fingerprint/citations,
evidence-state assertions, and claim prohibitions. Fingerprint the suite and
result with RFC 8785 SHA-256.

Grader: validate optional recorded live traces against exact model and effort,
tool budgets, expected tool/arguments, deterministic tool outputs, final schema,
artifact citations, unavailable-state handling, privacy, scientific-language
prohibitions, and metric/taxon-ID provenance. It must never call OpenAI itself.

Truth boundary: the committed offline run may pass deterministic oracle,
schema, citation, privacy-policy, replay-integrity, and grader self-tests. It
must label final-answer correctness and model tool selection as not run, set
live unsupported-claim rate to null, and never portray scripted fixtures as
GPT-5.6 output.

Tests: strict schema and byte-identical generation; all 48 deterministic tool
re-invocations; positive and adversarial synthetic trace-grader tests; exact
category/dimension coverage; replay integrity; full Python, Deno, and web gates;
rights/licensing; JSON/JSONL; staged secret/model/media/large-file gates; exact
commit and non-force push.

Rights/privacy: introduce no provider data, media, model output, credentials,
private reviewer data, sensitive coordinates, or external runtime dependency.

Rollback: remove the evaluation generator, schemas, suite/result artifacts,
tests, documentation, and provenance. Tasks 11.1–11.4 remain unchanged.

## Result

Implemented 48 unique cases with four cases in every required category and all
fourteen tools represented. Added strict suite, result, and complete-trace
schemas; RFC 8785 suite/result/trace fingerprints; exact deterministic oracle
receipts; a no-network trace-grading library and CLI; and positive/adversarial
grader self-tests. The committed result labels all live-model dimensions not
run and leaves the three live accuracy/rate metrics null.

Verification passed: 456 locked Python tests; 22 focused evaluation/OpenAI
requirements tests; 26 frozen Deno Edge tests plus type and format checks; 67
Vitest tests; web typecheck/build and 116-package licence report; uv lock and
eight-package compatibility checks; 52-provider rights verification; 430-file
441-file licence verification with zero model files; byte-identical generation; JSON,
JSONL, and whitespace gates. No browser E2E or live model run was performed or
claimed.

BioMiner advanced during the task to
`990640e1f1a27da1c459f54eaa43c55736846500` and remains active/dirty. Its
current-state record still lists live GBIF acquisition/durable admission and
live model/Flickr review work as remaining, so no partial artifact was read or
copied.
