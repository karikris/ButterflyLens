# Codex Collaboration Record

ButterflyLens was built with OpenAI Codex under the product and scientific
requirements supplied by Kris Kari. This record explains what is
machine-authored, what is human-directed, and which runtime facts have direct
evidence.

## Primary session

| Field | Value |
| --- | --- |
| Codex thread ID | `019f7038-92ae-7021-8318-53ca97648404` |
| Requested primary model | `bounded-model` |
| Requested reasoning effort | `xhigh` |
| Reasoning mode trailer | `standard` |
| Human product owner | Kris Kari |
| Repository start | `2026-07-17T13:25:55Z` |

The thread ID is read directly from the execution environment. The model and reasoning values are the required configuration in the supplied build contract. This repository does not claim a separately observed runtime model identifier because the execution environment has not exposed one beyond that contract.

## Final session and activity receipt

The non-secret primary environment identifier is also the recorded `/feedback`
Session ID:

```text
019f7038-92ae-7021-8318-53ca97648404
```

The API tool surface used for this work does not expose slash-command
invocation. The identifier is therefore recorded without claiming `/feedback`
was opened or submitted. The machine-readable
[session receipt](provenance/sessions/019f7038-92ae-7021-8318-53ca97648404.json)
preserves that boundary.

At the Task 17.5 audit boundary:

| Evidence | Exact state |
| --- | --- |
| Audited Git range | `db0657fd432b698c167d559328a57b0befef6664` through `8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97` |
| Pre-finalization commits | 120 non-merge commits |
| Commit receipts / task push receipts | 120 / 77 |
| Model-usage activity records | 105, including Task 17.5 |
| Session IDs in model ledger | 105 records use the one ID above |
| Requested model / effort | 105 × `bounded-model` / `xhigh` |
| Runtime model identity observed | 0 records; all 105 are `false` |
| Supporting models or subagents | none |
| Human post-change attestations | 0 |

The exact Task 17.5 commit cannot embed its own full Git SHA without
self-reference. Its parent/audit input is fixed above; the containing commit and
remote `main` SHA are verified after push.

## Authorship and responsibility

Kris Kari supplied the product goal, competition specification, scientific and
governance constraints, exact winning line, authoritative-source decisions,
parallel-work boundaries, and commit/push instructions. These are human
decisions, not human review attestations.

Codex authored or adapted the ButterflyLens repository code, contracts,
database migrations, data builders, application, deterministic fixtures, tests,
policies, release gates, documentation, and append-only provenance under those
instructions. Codex also ran the documented local and public verification
steps. It did not supply butterfly identities, provider rights, community
reviews, expert decisions, scientific ground truth, live-worker observations,
or human approval.

The application-level Bounded model analyst is a separate bounded runtime target. The
Submitted experience contains project-authored, fingerprinted stored replays
with zero model and network calls. No live Bounded model evaluation or production
analyst deployment is claimed.

The user required exact commit subjects. That explicit instruction took
precedence over the repository's longer trailer template; the append-only
commit, model, tool, plan, and task-report ledgers carry the corresponding
machine-readable provenance without inventing human review.

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

- Use the requested `bounded-model` model with `xhigh` reasoning effort for core work when that configuration is available. If runtime identity is not exposed, record the limitation; never invent model metadata.
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

The final attestation ledger remains empty. Kris Kari still needs to review and
approve the product state, scientific wording, media/rights presentation,
competition copy, final video, and external submission. OAuth authorization,
user directions, test success, Codex verification, and public deployment do not
substitute for that approval.
