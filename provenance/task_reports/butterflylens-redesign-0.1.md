# ButterflyLens redesign Task 0.1 — route and product-state audit

Status: **complete and pushed; runtime unchanged**.

Date: 2026-07-19

Starting ButterflyLens SHA:
`3d6486da87f32136c35e29aeed6cb6291da66a17`.

Verified subtask-batch remote SHA:
`a60617f73c082850643bc9845ea442143b7bb71c`.

Exact upstream audit boundaries:

- TaxaLens `e845dd98493979f37b04dbb6538e0d7b8758ca11`;
- BioMiner `7452e196e95cb3a91fc3f08efcb294a0d1849fd0`.

BioMiner remains in its Flickr-metadata fetch and no mutable output was read,
counted, or copied. No Flickr API call occurred. The rebuilt ButterflyLens
baseline remains authoritative. YOLOE and BioCLIP remain unfinished.

## Completed subtasks

| Subtask | Commit | Result |
| --- | --- | --- |
| 0.1.1 — inventory current public routes | `4dfebad154c47119d48ccc43f82832991c9c1bc8` | Documented the single-document fragment architecture, every public surface's data and maturity, and its keep/remove/move decision |
| 0.1.2 — audit review persistence | `23f4f068b68169161c756a4e561f01cb0e6f8787` | Traced the React draft, absent local/remote web adapters, existing authenticated RPC receipt, assignment transition, consensus, and missing map/community projection links |
| 0.1.3 — audit TaxaLens | `a60617f73c082850643bc9845ea442143b7bb71c` | Inspected the exact pinned repository, IndexedDB, notification, sync, map maturity, candidate gap, Verify workspace, reset, and incompatible direct-table Supabase adapter |

Audit reports:

- `docs/reports/butterflylens_redesign_0_1_1_route_audit.md`;
- `docs/reports/butterflylens_redesign_0_1_2_review_persistence_audit.md`;
- `docs/reports/butterflylens_redesign_0_1_3_taxalens_precedent_audit.md`.

## Frozen product decisions

- The first four public destinations will be exactly Explore, Verify, How it
  works, and Community.
- Advanced scientific, operational, governance, rights, provenance, export,
  and methods surfaces move under More with useful deep links preserved.
- Ask ButterflyLens and the runtime analyst are deliberately removed in Phase
  1 while historical immutable provenance remains untouched.
- The current Supabase append-only review and assignment transaction is
  preserved; the web app needs an offline-first repository, receipt-aware RPC
  adapter, and projection notification boundary.
- TaxaLens repository/projection/reset/map-maturity patterns are selectively
  adapted at its pinned SHA. Its direct table writes, demo data, broad research
  console, and styling are not copied.
- TaxaLens has no candidate drawer and no `BroadcastChannel` at the pinned SHA;
  those are original ButterflyLens implementation work.
- A local human review may update the current record, map overlay, set progress,
  and visitor contribution immediately. It cannot create consensus, quality,
  occurrence release, or scientific truth.

## Task gate

| Check | Result |
| --- | --- |
| Full Python suite with the documented contracts path | 670 passed in 32.847 seconds |
| Full web Vitest | 21 files, 100 tests passed |
| Web licence Node tests | 3 passed |
| Web production gate | Dependency licences 119 packages; media SHA-256 verified; TypeScript passed; Vite production build passed |
| Deno Edge suite | 49 passed |
| Deno formatting and entry-point checks | 23 files formatted; four current Edge entry points checked against the frozen lock |
| Python/TypeScript/JSON Schema parity | 24 schemas, 20 valid, 22 invalid, 20 versions, 14 vocabularies; TypeScript 7.0.2 |
| Rights | 66 tracked provider payloads passed |
| Licensing | 649 tracked files, two dependency manifests, zero model files passed |
| Release security | 50 public-RLS tables, 11 security-invoker views, 60 security-definer functions, 625 text files, 12 network-boundary files passed; `release_ready=false` |
| Fixed completion audits | Historical and current fixed-boundary audits passed; `goal_complete=false` remains binding |
| Exact pinned TaxaLens focused suite | 8 files, 33 tests passed; inspected review/impact surface has zero diff from pinned SHA |
| JSONL and whitespace | Passed |

The first Python invocation omitted the documented
`PYTHONPATH=packages/contracts/python` and therefore could not import one
contracts-backed test module. The corrected command ran all 670 tests and
passed. Contract parity likewise passed after supplying the repository's exact
pinned TypeScript compiler path. These were command-environment corrections,
not product failures.

## GitHits, platform research, and provenance

The single bounded Task 0.1 GitHits batch timed out without a solution. Per the
user's instruction, no retry occurred and GitHits is disabled for the remainder
of the goal. Each subtask records the exact query and unavailable state.

Current official Supabase database-function, JavaScript RPC, and changelog
documentation plus MDN IndexedDB and BroadcastChannel documentation informed
only the persistence audit. No external code was copied. Model usage and exact
source boundaries are recorded in `provenance/model_usage.jsonl`,
`provenance/githits.jsonl`, and `provenance/valyu.jsonl`.

## Push and worktree preservation

The three focused subtask commits were pushed directly from local `main` to
`origin/main` without force. Both local and remote returned
`a60617f73c082850643bc9845ea442143b7bb71c` immediately after the task push.

Pre-existing untracked `AGENTS.md:Zone.Identifier` and `docs/agents/` content
remain unstaged and unchanged. The next task is 0.2, the screenshot defect
matrix; it must not be treated as complete until the required viewport,
reduced-motion, and high-contrast captures exist.
