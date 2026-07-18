# Task plan — ButterflyLens 9.3

Task ID: `butterflylens-9.3`

Objective: implement deterministic, private, domain-specific reviewer
reliability estimates with policy-bound database admission and exact evidence
lineage.

Competition criterion improved: scientifically honest community verification
quality, inspectable uncertainty, and privacy-preserving reviewer governance.

Starting SHA: `77d9ab117440e6d10550805d4aa14267a42ed181`

Remote main SHA: `77d9ab117440e6d10550805d4aa14267a42ed181`

BioMiner SHA observed: `e1d12a73ff1e0b98e40a513f37b6330bb25a4aa6`;
its active work does not overlap reviewer reliability, so no BioMiner record or
data is inspected or copied.

TaxaLens immutable source SHA inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Its current working tree is dirty
and is not used.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skills: Supabase and Supabase Postgres best practices. The Supabase CLI
is unavailable, so the migration uses the repository's timestamped convention
and is created with a patch.

GitHits needed: yes for a non-trivial estimator/database task. The service is
already recorded unavailable and is not retried; local contracts and immutable
TaxaLens precedent are used without copying code.

Valyu needed: yes for current Supabase RLS, database-function, and Data API
behavior. Valyu is unavailable; current official Supabase documentation is the
recorded fallback.

Expected files: a versioned Python estimator and storage mapping, reliability
contract metrics, deterministic fixtures/tests, an append-only Supabase
migration and pgTAP contract, an algorithm specification, and provenance.

Contracts affected: `butterflylens-reviewer-reliability:v1.0.0` gains explicit
control, agreement, alpha, adjudication, and count metrics while retaining its
private/non-circular boundary.

Data/rights implications: no source media, provider record, biological label,
or reviewer evidence is acquired. Fixtures are synthetic and fingerprinted.

Scientific risks: treating peer or majority agreement as truth, using model
agreement, reporting sparse estimates, pooling incompatible domains, hiding
uncertainty or dissent, or turning reliability into a public ranking.

Security/privacy risks: exposing individual scores, admitting client-computed
rows that bypass policy, mutable history, non-monotonic supersession, browser
write privileges, or unsafe security-definer search paths.

Tests: deterministic metric/interval fixtures, malformed and non-independent
evidence rejection, storage mapping, JSON Schema parity, static migration
policy tests, pgTAP definition, full Python/web/type/build gates, rights,
licensing, provenance JSONL, secret/model/large-file scans, and
`git diff --check`.

Rollback/recovery: the migration is append-only and the estimator is a new
package. Reverting the focused commit removes the feature before deployment;
after deployment, a forward migration is required because snapshots must not be
deleted or rewritten.
