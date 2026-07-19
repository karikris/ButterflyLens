# ButterflyLens 11.1 — Current OpenAI requirements

Status: **verified and frozen; no OpenAI runtime or live model call added**.

Starting SHA: `e83cdd2711f7b22415b60c1c4e0c7eeef1f7ec38`.

## Outcome

The repository now has a versioned machine-readable implementation policy and
a cited human guide for Tasks 11.2–11.5. Current official OpenAI documentation
was used to verify the explicit `bounded-model` model, direct Responses API,
strict function calling, strict final Structured Outputs, server-only secret,
privacy-preserving safety identifier, `store: false`, response-state handling,
and agent-evaluation boundaries.

The user-required `xhigh` effort is frozen as the first baseline, not assumed
optimal. Model, effort, prompt, budget, and architecture changes require the
same representative evaluation set. The implementation remains one bounded
analyst over deterministic read-only local tools; no Agents SDK, built-in tool,
remote MCP, multi-agent runtime, browser OpenAI access, or response persistence
is currently justified.

## Evidence and safety contract

Factual output must be grounded only in the current deterministic tool run.
Each claim requires an allowlisted artifact citation with artifact ID,
repository, exact commit, path, and fingerprint. Missing evidence is
`unavailable`, not zero. Conflicts and inferences remain labelled, and the
model cannot invent biodiversity facts, identifiers, metrics, rights, worker
state, reviewer state, or publication status from memory.

The request and application budgets are finite: at most eight model tool calls,
six continuation loops, 1,800 output tokens, ten seconds per local tool, and
one transient retry. Budget exhaustion, refusal, incomplete details, invalid
schemas, failed tools, and failed/cancelled responses are explicit states.
Live inference and stored replay remain distinct and visibly labelled.

No API key, SDK dependency, server route, prompt implementation, tool
implementation, model output, live trace, database change, or OpenAI API call
was introduced in this task.

## Verification

- Seven focused requirements contract tests passed.
- The full locked Python suite passed: 407 tests.
- The focused system-Python test passed because it has no third-party imports.
  Broader bare-system discovery was non-representative because that interpreter
  lacks the locked `rfc8785` and `pyarrow` dependencies; the required `uv
  run --locked` suite passed completely.
- Every current external source in the machine policy is allowlisted to the
  official `developers.openai.com` domain and is linked from the human guide.
- Rights verification passed for 52 tracked provider payloads.
- Licence verification passed for 394 tracked files, two dependency manifests,
  and zero model files.
- JSON and JSONL provenance validation, staged secret/model/media checks,
  whitespace checks, exact commit subject, and non-force push verification are
  release gates.

## Parallel and deferred work

The supplied GBIF Parquet handoff remains deferred behind active BioMiner work.
The user-reported Flickr fetch remains active, so Task 10.4 remains unfinished
and no partial outputs were inspected. Flickr API, GitHits, YOLOE, and BioCLIP
were not called or run.
