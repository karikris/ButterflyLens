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

## Engineering instructions

These are the tracked engineering instructions for core ButterflyLens work. They remain binding even though the repository-local `AGENTS.md` path is ignored.

### Models and evidence

- Use the requested `gpt-5.6-sol` model with `xhigh` reasoning effort for core work when that configuration is available. If runtime identity is not exposed, record the limitation; never invent model metadata.
- Run GitHits before every numbered task and subtask. If one attempt establishes that it is unavailable, record the failed attempt, use official documentation and committed local upstreams, and do not repeatedly retry or invent results.
- Fingerprint every material input, semantic contract, source response, media object, model artifact, review event, map projection, quality snapshot, release candidate, and export at the layer where it becomes evidence.
- Raw model similarity is raw model evidence, never a calibrated probability unless an independent calibrator exists and is versioned.
- Tests and manifests prove only what they directly cover. No planned, simulated, unavailable, or unreviewed value may be reported as measured.

### Version control

- Work directly on `main`; do not create feature branches or pull requests unless Kris Kari changes that instruction.
- Before each task, verify `main`, status, local SHA, and a fast-forward-only pull from `origin/main`.
- Give each numbered subtask one focused conventional commit after targeted checks, then push once at task completion.
- Never force-push. Stop on remote divergence and preserve local commits.
- Include the required AI, session, scope, origin, GitHits, human-decision, human-review, and test trailers without fabricating evidence.

### Scientific and provider safeguards

- Treat social-media search results as hypotheses, not biodiversity records.
- Use the mandatory ButterflyLens evidence-maturity language and block prohibited occurrence, range, absence, exhaustiveness, model-confidence, and quality claims.
- Preserve the physical-request/logical-association distinction; a search term is never a species label.
- Verify software licences, provider terms, media rights, attribution, boundary rights, and downstream compatibility before release.
- Do not upload Flickr, ALA, GBIF, or iNaturalist images to Hugging Face by default.
- Protect sensitive coordinates and retain provider generalization, uncertainty, quality assertions, licences, and removal state.

### Product quality

- Design and test to WCAG 2.2 AA, including keyboard access, text alternatives, reduced motion, contrast, mobile layouts, and non-WebGL fallback.
- Apply least-privilege authorization, row-level security on exposed data, server-side secrets, append-only review events, and auditable moderation.
- Separate representative statistical audit from targeted failure discovery. Preserve inclusion probabilities, grouping, interval methods, and effective sample size.
- Keep reviewer reliability private, domain-specific, uncertainty-aware, shrunk toward equal weight, and independent of model agreement or majority agreement alone.

## Research provenance

GitHits was invoked before Task 0.1. The single request remained pending without a result and was terminated after multiple polling windows. Per the build contract, the service is marked unavailable and is not repeatedly called. Official documentation, public repository documentation, and local committed upstream state are used as fallbacks. No GitHits solution ID or repository result is invented.

## Human review

Human instructions and human review attestations are different evidence. Product decisions supplied in the build contract and subsequent chat messages are recorded as decisions. Post-change review is recorded only when a human explicitly performs or confirms it. An empty attestation ledger therefore does not imply review.
