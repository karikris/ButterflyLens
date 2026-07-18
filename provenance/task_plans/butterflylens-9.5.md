# Task plan — ButterflyLens 9.5

Task ID: `butterflylens-9.5`

Objective: estimate dataset precision from a defensible representative audit
while keeping targeted failure discovery structurally separate.

Competition criterion improved: inspectable population-quality evidence with
design-aware weighting, dependence-aware uncertainty, and fail-closed storage.

Starting and remote SHA: `b774a993adca9320063dc9244a09465527e25172`.

BioMiner: this statistical audit task does not overlap its active GBIF evidence
database work, so its record and data are not inspected or copied. The last
non-overlap observation remains
`e1d12a73ff1e0b98e40a513f37b6330bb25a4aa6`.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Its dirty working tree is not
used. Only the target-precision interface and tests were inspected; no code,
fixture, record, estimate, or data was copied.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skills: Supabase and Supabase Postgres best practices, for fixed search
paths, least privileges, RLS preservation, foreign-key indexing, serialized
append-only revisions, explicit constraints, and timestamped migrations.

GitHits needed: yes. It remains unavailable and is not retried. Local contracts
and immutable TaxaLens precedent are sufficient.

Valyu needed: yes. It remains unavailable; primary statistical publications
and current official Supabase documentation are the fallback.

Expected files: a deterministic Python estimator, representative-audit policy,
wire contract and declaration parity, estimator and policy tests, append-only
quality migration, updated integration fixtures, pgTAP schema contract, and
provenance.

Statistical risks: treating targeted cases as representative; ignoring unequal
inclusion probabilities, strata, or repeated owners/observations; reporting an
independent-row interval for dependent evidence; overstating Kish ESS; missing
strata; or substituting zero for unavailable evidence.

Security/privacy risks: browser publication, mutable latest-row estimates,
stored bootstrap secrets, unsafe security-definer lookup, or unindexed
supersession.

Tests: point estimate, effective sample size, grouped interval, order and seed
stability, targeted separation, malformed/missing evidence, cross-stratum
groups, contract parity, database admission invariants, pgTAP definition, full
Python/web/type/build, rights/licensing/provenance/safety, and whitespace.

Rollback/recovery: application code and policy are revertible before database
deployment. After deployment, corrections are forward-only snapshots linked by
serialized revisions; existing evidence is never deleted or overwritten.
