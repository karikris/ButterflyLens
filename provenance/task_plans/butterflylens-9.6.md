# Task plan — ButterflyLens 9.6

Task ID: `butterflylens-9.6`

Objective: publish a credential-free community quality dashboard showing the
reviewed sample, decisive reviews, precision and interval availability,
reviewer agreement, species quality, reference-health flags, and release
blockers without manufacturing unsupported estimates.

Competition criterion improved: an inspectable public quality surface whose
numbers are bound to fingerprinted evidence and whose unavailable states are
scientifically honest.

Starting and remote SHA: `cb79bfef0adc2a11c30f09281ec504dbbf9aea1f`.

BioMiner: this presentation task does not overlap the active GBIF fingerprinted
evidence-database work, so its record and data are not inspected or copied.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Only quality-panel,
quality-overview, and fail-closed dashboard-model presentation precedent was
inspected; no code, styles, fixture, snapshot, estimate, or data was copied.

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Relevant skills: Supabase and Supabase Postgres best practices were already
applied to the underlying quality contract and append-only snapshot boundary;
this task adds no database mutation.

GitHits needed: yes. It remains unavailable and is not retried. Local
fingerprinted manifests and immutable TaxaLens precedent are sufficient.

Valyu needed: no. This task projects existing authoritative local artifacts and
does not introduce a new scientific method, external factual claim, or changing
platform rule.

Expected files: submitted dashboard projection, strict runtime parser, React
quality dashboard, accessible responsive styling, UI/parser/projection tests,
human decision record, migration provenance, tool logs, and task report.

Contracts affected: a web-local submitted dashboard projection only. Existing
cross-language verification contracts and database schemas are unchanged.

Data/rights implications: aggregate counts and artifact fingerprints only; no
reviewer identity, raw provider media, protected coordinates, private storage
keys, or model output enters the bundle.

Scientific risks: presenting zero workflow rows as zero-percent precision;
presenting reference coverage as species quality; treating targeted discovery
as representative; inventing reviewer agreement; or suppressing release
blockers.

Security/privacy risks: browser-bundled private reviewer results or source media,
mutable unverified snapshots, or public reviewer ranking.

Tests: strict parser, unavailable and representative rendering, manifest hash
and projection parity, full Python and web suites, production build, contract
parity, rights/licensing, dependency audit, provenance parsing, staged safety,
and whitespace checks.

Rollback/recovery: the dashboard and static submitted projection are isolated
web assets and can be reverted without database or evidence mutation. Source
manifests remain unchanged and authoritative.
