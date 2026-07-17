# Codex Collaboration Record

ButterflyLens is being created with OpenAI Codex under the product and scientific requirements supplied by Kris Kari. This record explains what is machine-authored, what is human-directed, and which runtime facts have direct evidence.

## Primary session

| Field | Value |
| --- | --- |
| Codex thread ID | `019f7038-92ae-7021-8318-53ca97648404` |
| Requested primary model | `gpt-5.6-sol` |
| Requested reasoning effort | `xhigh` |
| Reasoning mode trailer | `standard` |
| Human product owner | Kris Kari |
| Repository start | `2026-07-17T13:25:55Z` |

The thread ID is read directly from the execution environment. The model and reasoning values are the required configuration in the supplied build contract. This repository does not claim a separately observed runtime model identifier because the execution environment has not exposed one beyond that contract.

## Collaboration rules

- Codex may create files, run tests, commit directly to `main`, and push only as authorized by the build contract.
- Every numbered subtask receives a focused conventional commit after targeted checks.
- Every task is pushed once its subtasks are complete; push and remote SHAs are appended to provenance.
- BioMiner and TaxaLens remain upstream repositories. Their working trees are read-only for ButterflyLens work.
- Imported components require immutable source SHAs and migration-manifest entries.
- Metrics, model results, human review, data availability, provider access, and deployment status are reported only from inspected evidence.
- Scientific language distinguishes ALA baseline occurrence evidence, Flickr discovery candidates, review maturity, and release gates.
- `AGENTS.md` is intentionally ignored following Kris Kari’s explicit instruction on `2026-07-17`.

## Research provenance

GitHits was invoked before Task 0.1. The single request remained pending without a result and was terminated after multiple polling windows. Per the build contract, the service is marked unavailable and is not repeatedly called. Official documentation, public repository documentation, and local committed upstream state are used as fallbacks. No GitHits solution ID or repository result is invented.

## Human review

Human instructions and human review attestations are different evidence. Product decisions supplied in the build contract and subsequent chat messages are recorded as decisions. Post-change review is recorded only when a human explicitly performs or confirms it. An empty attestation ledger therefore does not imply review.

