# ButterflyLens Build Week Delta

This is the final evidence-backed account of work created in ButterflyLens
after the immutable baseline in [`BUILD_WEEK_BASELINE.md`](BUILD_WEEK_BASELINE.md).
It separates new repository work from upstream precedents and reports unfinished
work as unfinished.

## Audit status and boundary

| Field | Exact state |
| --- | --- |
| Repository created | `2026-07-17T13:25:55Z` |
| First commit | `db0657fd432b698c167d559328a57b0befef6664` |
| First-commit contents | `.gitignore`, `README.md`, `provenance/githits.jsonl` only |
| Audited through | `8ebbd37a7169d1b0a38e1f6fb6a3e0aac39bbb97` (Task 17.4) |
| Audited tree | `5054e8e11aed89b0ce1517f788a033546d158090` |
| Non-merge commits | 120 |
| First commit to audit boundary | 581 files changed, 175,782 insertions, 10 deletions |
| Branch and remote | `main`; audit-boundary SHA verified on `origin/main` |

Task 17.5 fixes its audit input at the preceding pushed commit. A Git commit
cannot embed its own full SHA without self-reference, so the exact containing
finalization commit is verified from remote `main` after push and reported in
the Task 17.5 handoff rather than invented inside that commit.

## Baseline versus pre-finalization state

| Area | First commit | Task 17.4 audit boundary |
| --- | --- | --- |
| Product | README title and scope only | Public evidence-first web application, frozen Submitted experience, review and quality surfaces, and fail-closed Live/analyst states |
| Taxonomy | none | Versioned Australian butterfly pack with 463 accepted species and sourced identifier/name governance |
| Occurrence evidence | none | Rebuilt ButterflyLens-owned ALA baseline: 236,897 selected rows, 230,027 spatially eligible rows, and 23,744 aggregate rows; public occurrence display withheld pending rights resolution |
| Flickr | none | 1,876 deterministic query definitions, 1,754 deduplicated physical requests, and an audited worker contract; no request in this goal and no completed-result import |
| Reference evidence | none | Metadata linkage, rights/admission evidence, 2,906 valid decodes, explicit readiness, zero human-verified species, and no committed source-image collection |
| Models | none | Worker and artifact contracts plus truthful unavailable states; YOLOE and BioCLIP unfinished and skipped |
| Community quality | none | Database contracts, independent review/adjudication/reliability/consensus/representative-audit logic, and deterministic unavailable projections; no live review evidence |
| OpenAI analyst | none | Bounded tool and replay contracts, offline evaluation fixtures, and credential-free Submitted replay; live model not invoked or deployed |
| Delivery | none | GitHub Pages application, release/security/rights/licensing gates, evidence export contracts, judge guide, 2:48 production script, ten-slide deck, and Devpost copy |

These are repository artifacts and measured local or public build properties.
They are not claims that the blocked data, model, community, provider, or human
release gates have passed.

## New ButterflyLens work

The 120 audited commits created the following ButterflyLens-owned work:

1. Governance and contracts: the AGPL-3.0-only software decision, provider and
   media-rights policies, evidence-maturity vocabulary, cross-language schemas,
   semantic fingerprints, append-only provenance, security boundaries, and
   release gates.
2. Taxonomy and national baseline: reproducible taxonomy/name/crosswalk packs;
   an independently rebuilt, authoritative ButterflyLens ALA occurrence and H3
   baseline; source manifests; row lineage; generalisation; and rights-aware
   withholding.
3. Discovery and reference planning: deterministic Flickr vocabulary, logical
   associations, physical-request deduplication, budgets and checkpoint
   contracts; metadata-only reference linkage; automated rights/admission
   evidence; and explicit readiness diagnostics. Search terms remain discovery
   hypotheses, never species labels or occurrence records.
4. Storage and workers: Supabase/Postgres migrations, row-level security,
   private reviewer evidence, append-only review events, bounded worker
   identity/lease/heartbeat/command/event contracts, B2-compatible object
   manifests, and fail-closed artifact admission. Local contracts and tests do
   not claim live Supabase, B2, M5, or provider execution.
5. Community and quality: blinded independent assignment, conflict and expert
   adjudication, private evidence-bound reliability, layered consensus,
   representative sampling and grouped intervals, geographic-impact contracts,
   and public projections that remain unavailable when evidence is absent.
6. Product and accessibility: an original Australian field/editorial design
   system, public shell, evidence map and non-WebGL fallback, species/reference
   views, review flow, contributor and quality surfaces, worker status, analyst
   replay, responsive layouts, keyboard and forced-colour support, and reduced
   motion.
7. Analyst, export, and delivery: bounded read-only analyst tools, stored replay
   provenance, model-free Submitted evaluation, export/removal contracts,
   deployment and rollback workflows, reproducible snapshot, judge route,
   production-ready video packet, pitch deck, and submission copy.

## Imported and adapted components

The migration manifests are the authority for upstream influence:

| Upstream | Immutable origins | Component records | Integration boundary |
| --- | --- | --- | --- |
| BioMiner | `d71bceabf75748a25df39d0025e8da907f295f8c` | 15 | Nine artifact contracts, two adapters, one application-boundary contract, one status-only record, and two ButterflyLens-original records. BioMiner code, generated data, media, models, and active working-tree output were not copied. |
| TaxaLens | `95f9081567d6c96abdc5b5614d7e401d15ad4f03`; `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc` | 17 | Interface/shared-contract precedents were reimplemented as ButterflyLens-owned adapters. The only byte-copied upstream asset is the attributed CC BY-SA 4.0 Wikimedia review fixture `taxalens-wikimedia-review-fixture-47248e36944c`. |

Existing BioMiner or TaxaLens capability is not counted as new merely because a
contract or interface precedent informed ButterflyLens. Every origin is pinned;
uncommitted upstream files are excluded.

BioMiner's concurrent GBIF/Flickr work did not present a completed immutable
ButterflyLens handoff at this boundary. The operator-supplied GBIF occurrence
download `0004170-260715120105164.zip` (571,755 Australian Papilionoidea
records; DOI `10.15468/dl.7uut3k`) is recorded as a decision, but was not copied,
fingerprinted, converted to Parquet, or admitted here. The separate external
Flickr fetch was reported active at 50,000 unique images; no partial result was
inspected or copied and no Flickr API call was made by this goal.

## Codex activity and task evidence

- One primary Codex session was used:
  `019f7038-92ae-7021-8318-53ca97648404`.
- The same identifier is the recorded `/feedback` Session ID. The available API
  surface did not expose slash-command invocation, so no feedback opening or
  submission is claimed.
- At the audit boundary, all 120 Git commits have commit receipts; 77 task-level
  push receipts record non-force publication; this patch brings the task-report
  corpus to 65 reports and the task-plan corpus to 39 plans.
- No supporting model or subagent was used. Codex performed repository work and
  verification; it did not provide scientific identities, community decisions,
  expert adjudication, provider rights, or human approval.
- Headroom was used to compress the large provenance corpus before exact local
  queries. Task-specific receipts are
  `504a09159e203964093d4131`, `7621abd7c83707de1ab1f539`, and
  `6f5fcc419eaba18612635562`; identifiers and counts were checked against source
  files rather than inferred from compression.

The machine-readable session receipt is
[`provenance/sessions/019f7038-92ae-7021-8318-53ca97648404.json`](provenance/sessions/019f7038-92ae-7021-8318-53ca97648404.json).

## GPT-5.6 runtime boundary

The model-usage ledger contains 105 activity records through Task 17.5. Every
record names the same session, requested model `gpt-5.6-sol`, requested effort
`xhigh`, and `runtime_model_identity_observed: false`. These records document
the required Codex configuration; they do not independently prove the runtime
model identity.

The application's analyst is a separate bounded target. Its Submitted answers
are project-authored, fingerprinted stored replays with zero model calls and
zero network calls. The 48-case offline suite tests deterministic contracts and
replay behaviour, not live GPT-5.6 answer quality. No live GPT-5.6 evaluation or
production analyst deployment is claimed.

## Human decisions and review

`HUMAN_DECISIONS.md` contains 15 dated decision sections, including repository
creation, exact commit/push workflow, authoritative rebuilt ALA baseline,
parallel BioMiner/Flickr boundaries, disabled GitHits, skipped YOLOE/BioCLIP,
the supplied GBIF archive, public evidence language, and the Supabase OAuth
authorization boundary.

Human direction is not post-change review. The review-attestation ledger has
zero attestations. Kris Kari has not yet attested final scientific wording,
rights presentation, product state, competition materials, public video, or
submission approval. OAuth authorization, deployment, tests, and Codex checks
do not substitute for human approval.

## Test and deployment evidence

The last complete pre-finalization release gate at Task 17.4 measured:

- 610 Python tests;
- 92 Vitest tests plus three standalone Node tests;
- 45 cached Deno Edge tests and all four Edge entry-point type checks;
- 10 Playwright checks across desktop engines, mobile, reduced motion, forced
  colours, and no WebGL;
- Python/TypeScript parity across 25 schemas;
- 563 text files in the release-security scan, 582 repository files in the
  licensing scan, and 53 rights-manifest entries; and
- GitHub Pages run `29649504728`, which built the exact Task 17.4 SHA in 17
  seconds and deployed it in 12 seconds.

The Task 17.5 finalization gate measured 620 Python tests plus 229 subtests, the
unchanged 92 Vitest plus three Node tests, 45 Deno tests, 10 Playwright checks,
and the same 25-schema parity inventory. Snapshot, security, rights, licensing,
type-check, format, build, and provenance checks also passed; the final staged
security and licensing scans covered 567 text files and 586 repository files,
while rights retained 53 manifest entries. Passing tests establish the checked
software, artifact, and documentation invariants only; they do not make absent
evidence available.

## Incomplete and excluded work

The frozen Submitted snapshot has `release_ready: false`. The following remain
unfinished or outside this goal:

- completed immutable BioMiner GBIF and Flickr handoffs, including conversion
  of the supplied GBIF download to authoritative Parquet;
- all Flickr API work in this goal and all partial external fetch output;
- YOLOE detection/routing and BioCLIP embeddings, prototypes, or scores;
- live Apple M5 Pro worker execution and observed throughput;
- live Supabase/B2 data operation, production secrets, and operator smoke test;
- live GPT-5.6 evaluation and production analyst deployment;
- real community reviews, expert adjudications, reliability estimates,
  representative quality estimates, released impact cells, and public
  occurrence evidence;
- final recorded/narrated human-approved public YouTube video, Devpost mutation,
  and competition submission; and
- post-change human review, provider-rights resolution, and overall release
  approval.

GitHits remains unavailable and disabled by direct instruction. No GitHits,
Flickr, scientific-model, live analyst, external submission, Supabase, or B2
call is represented as completed by this finalization.

## Delta accounting rule

A ButterflyLens change counts as new only when its commit, scope, origin,
verification, and task publication are recorded. Adapted work must retain its
immutable repository SHA and source path. Copied bytes require rights evidence.
Planned, simulated, unavailable, externally active, unreviewed, or blocked work
never becomes measured merely because a schema, fixture, UI, or test exists.
