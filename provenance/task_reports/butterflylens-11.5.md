# ButterflyLens 11.5 — Representative analyst evaluations

Status: **deterministic evaluation boundary implemented and verified; live
GPT-5.6 evaluation not run**.

Starting SHA:
`69a102cc31253e7d3eb84c91d92de2a0c266b7c8`.

## Outcome

ButterflyLens now has 48 unique analyst evaluation questions: four cases in
each of map impact, ALA/Flickr comparison, species maturity, occurrence
overclaim, reviewer reliability, representative versus targeted review, worker
unavailability, missing references, licence restrictions, First Nations name
governance, model-memory taxon IDs, and fabricated metrics. All fourteen
deterministic tools are represented.

Each case pins one smallest-sufficient expected tool call, exact arguments,
required evidence facts/states, deterministic result status and fingerprint,
complete artifact citation IDs, an expected live response state, and prohibited
claim classes. The suite, offline result, and optional complete trace each use
strict Draft 2020-12 contracts and RFC 8785 SHA-256 fingerprints.

The no-network grader replays every recorded tool call against the checksum-
pinned evidence toolbox and checks exact model/effort, complete ordered case
coverage, tool selection, arguments, output, response schema, citations,
unavailable-state abstention, budget, privacy/scientific-language prohibitions,
and metric/taxon-ID provenance. A CLI grades supplied traces but cannot invoke
OpenAI.

## Truthful evaluation state

`packages/openai/agent_evaluation.json` reports 48/48 deterministic oracle
passes, zero model and network calls, and a passing submitted-replay boundary.
It does not report a model benchmark. Live final-answer accuracy,
tool-selection accuracy, and unsupported-claim rate are null because no
GPT-5.6 output exists. Synthetic trace fixtures exercise only the grader and
remain explicitly `model_invoked: false`.

This separation follows the frozen Task 11.1 official evaluation guidance
loaded through the OpenAI documentation skill. No current external contract
changed, so no new documentation lookup was needed.

## Verification

- 456 locked Python tests passed; 22 focused evaluation/OpenAI requirements
  tests cover strict generation, all 48 oracle calls, category/dimension/tool
  coverage, immutable source commits, truthful null live metrics, full synthetic
  grader coverage, CLI execution, and adversarial failures.
- The grader rejects the wrong tool, imprecise/altered output, modified
  citations, direct claims from unavailable evidence, fabricated metrics,
  invented taxon IDs and cultural names, inferred worker state or licence
  permission, trace tampering, and false live provenance.
- All 26 frozen Deno Edge tests, Deno type check, and ten-file format check pass.
- All 67 Vitest tests, web typecheck, production build, 116-package dependency
  report, and review-media verifier pass. The unchanged client bundle remains
  1,468.09 kB (222.76 kB gzip), with the existing chunk-size warning and no new
  performance claim.
- The uv lock and eight installed-package compatibility checks pass. Rights
  verification covers 52 tracked provider payloads; licence verification covers
  441 tracked files and reports zero model files.

## Limitations and parallel work

Passing deterministic and synthetic-grader checks is necessary application
evidence, not proof of nondeterministic model behaviour or complete semantic
correctness. A later credentialed, bounded, recorded GPT-5.6 run plus human
review is required before changing the prompt/model/effort or reporting live
agent accuracy.

No OpenAI, Supabase, Flickr, provider, database, YOLOE, or BioCLIP call ran.
BioMiner advanced to `990640e1f1a27da1c459f54eaa43c55736846500` and remains
active/dirty with live GBIF acquisition/durable admission still outstanding;
no partial output was read or copied. Task 10.4 remains unfinished while the
user-reported Flickr fetch runs. GitHits remained disabled by user instruction.
