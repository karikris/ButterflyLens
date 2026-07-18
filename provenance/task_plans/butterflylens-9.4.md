# Task plan — ButterflyLens 9.4

Task ID: `butterflylens-9.4`

Objective: define and calculate append-only community, qualified, and release
consensus layers without allowing weights or models to erase human conflict.

Competition criterion improved: inspectable community evidence, defensible
qualified review, and fail-closed release governance.

Starting SHA: `34fc90a1a2af6d030abdaecd68fe5b07845fc67e`

Remote main SHA: `34fc90a1a2af6d030abdaecd68fe5b07845fc67e`

BioMiner: no consensus overlap, so its active record and data are not inspected
or copied. The last non-overlap status observation was
`e1d12a73ff1e0b98e40a513f37b6330bb25a4aa6`.

TaxaLens immutable source SHA inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Its dirty working tree is not
used.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skills: Supabase and Supabase Postgres best practices. The same current
official Supabase RLS, explicit privilege, fixed-search-path, and Data API
guidance verified for Task 9.3 remains applicable.

GitHits needed: yes. The service remains unavailable after the recorded attempt
and is not retried; local contracts and immutable TaxaLens precedent are used
without copying source.

Valyu needed: yes for current Supabase security behavior. Valyu remains
unavailable; current official Supabase documentation is the fallback.

Expected files: a versioned consensus policy and Python projection, expanded
wire-layer summaries, deterministic tests, append-only consensus migration,
updated integration fixtures, pgTAP contract, and provenance.

Contracts affected: `butterflylens-verification-consensus:v1.0.0` gains an exact
policy version, per-layer methods/counts/totals/dissent/event lineage, and six
explicit release gates.

Data/rights implications: no provider record, source media, or biological label
is acquired. Release calculation consumes booleans from governed upstream
rights/provenance evidence and cannot create that evidence.

Scientific risks: weighted or raw majority as truth; hiding minority dissent;
counting Can't tell, Can't view, or Skip as decisive; cross-reviewer correction;
self-adjudication; releasing unresolved conflicts; or implying release-ready is
published occurrence.

Security/privacy risks: public individual reliability, browser consensus writes,
mutable snapshots, unsafe security-definer lookup, or unversioned client state.

Tests: layer separation, equal-weight fallback, weighted-disagreement blocking,
exact adjudication, supersession, release-gate consistency, order/fingerprint
stability, contract validation, storage rows, migration policy, pgTAP definition,
full Python/web/type/build, rights/licensing/provenance/safety, and
`git diff --check`.

Rollback/recovery: code and policy are new and revertible before deployment.
After migration deployment, consensus revisions remain append-only and any
correction requires a forward migration/new snapshot rather than deletion.
