# Task plan — ButterflyLens 13.3

Task ID: `butterflylens-13.3`

Objective: prevent public map and release projections from exposing a sensitive
butterfly location beyond the explicit ALA/Flickr provider permission and the
versioned taxon-policy resolution, with unknown or incomplete evidence withheld.

Competition criterion improved: security, scientific integrity, evidence
traceability, and public trust.

Starting and remote SHA:
`e806924312cc7d5415643513eda87d2f4fc683e5`.

Task 13.2 deployment evidence: GitHub Pages run `29640377421` successfully
deployed the exact starting SHA and the served bundle exposes the canonical
community-safeguards link.

BioMiner boundary: the formal task inspection observed committed SHA
`4c38a10012e596b7591945da70821732a0602775`; it advanced during implementation
and remained dirty and active. Its published current-state record still lists
live current-policy GBIF acquisition and durable-media admission as unfinished.
Read only that record, copy no active output, and defer the supplied GBIF
archive handoff until BioMiner publishes an immutable completion.

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11` with pre-existing user work;
no component is imported.

Relevant agent files: root `AGENTS.md`, `SCIENCE_AND_DATA.md`,
`GIT_AND_PROVENANCE.md`, `TOOLS.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skills: Supabase and Supabase Postgres best practices, applied to the
RLS, fixed-search-path helper, immutable ledgers, FK indexes, and least-privilege
grants. No live Supabase mutation is authorized or attempted.

GitHits: disabled by explicit user instruction; do not call it. Use governed
local schemas and original implementation.

Current external evidence: official ALA sensitive-service/authentication docs
and official Flickr geo-accuracy, geo-permission, and privacy guidance. Browse
documentation only; make no Flickr API call.

Files expected: canonical sensitive-location policy, Python planning contract,
Supabase migration, pgTAP/static tests, public policy link, README, task
plan/report, and provenance logs.

Contracts affected: provider location constraint, public-location decision,
map/release RLS, H3-only release cell, service-only append boundary, and exact
policy/provider/target fingerprint lineage.

Data and rights implications: preserve only ALA public processed coordinates
upstream; retain Flickr geo permission and accuracy as private evidence; write
no source coordinates to the new database ledgers; never infer an H3 level from
a Flickr accuracy value without a versioned mapping.

Scientific risk: generalisation can be mistaken for taxon verification or
absence evidence. Keep `scientific_claim_allowed = false`, preserve maturity,
and state that empty cells do not prove absence.

Security/privacy risk: provider-public status alone, unrelated provider
snapshots, a stale policy, duplicate lineage, a too-fine H3 cell, or a small
aggregate could leak a protected location. Validate the exact target and source
fingerprints, use the strictest ceiling, and fail closed through public RLS.

Tests: deterministic planner cases, authoritative ALA 375-row coarse-only
proof, static database/RLS checks, 44-assertion pgTAP contract, PostgreSQL and
PL/pgSQL parsing, all Python/web/Deno gates, rights/licensing, JSON/JSONL,
whitespace, secret/scope checks, and Pages deployment verification.

Rollback: revert this task as one commit. Existing public map/release rows then
return to the earlier visibility-only RLS boundary, so rollback must be treated
as a security regression rather than an operational workaround.
