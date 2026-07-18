# Task plan — ButterflyLens 10.5

Task ID: `butterflylens-10.5`

Objective: enforce the current Flickr public-display terms at the database,
server-contract, and browser-rendering boundaries without calling Flickr or
using partial BioMiner output.

Competition criterion improved: rights-respecting community-science display
with owner credit, transparent provider relationship, rapid removal, and
machine-checked fail-closed release gates.

Starting and remote SHA:
`f053c27d877fba07df841e2825618d9f705b2333`.

Task 10.4: deferred unfinished because the active user-reported 50,000-image
Flickr fetch has about 20 hours remaining and overlaps the live page.

BioMiner overlap: none for implementation. Its current record was inspected only
to confirm active work. No logs, outputs, configuration, credentials, code, or
partial artifacts are read, changed, or copied.

Relevant agent files read: ButterflyLens root `AGENTS.md` and complete
`docs/agents/`; BioMiner root `AGENTS.md` and complete current state record.

Skills used: Supabase for current migration/RLS/Data API guidance; Supabase
Postgres Best Practices for least privilege, security-invoker views, foreign-key
indexes, partial indexes, and RLS policy structure.

Current official sources inspected: Flickr API Terms, Flickr Terms, Developer
Guide API/Business/Attribution/Community pages; Supabase changelog, current RLS,
and Data API security guidance.

GitHits: disabled for the remainder of the goal by explicit user instruction. No
call is made.

Expected files: versioned machine-readable policy, Python admission contract,
service-only Supabase migration and pgTAP assertions, strict web model, public
blocked/eligible display component, responsive styles, source and component
tests, rights/human-decision updates, prior-task commit receipt, tool/model
ledgers, and task report.

Contracts affected: Flickr application approval, public display asset, cache
revalidation, owner removal, downstream removal-event, and page rendering
contracts. Discovery/query and scientific identity contracts are unchanged.

Rights/privacy controls: maximum 30 photos per page; exact source,
photographer, licence and attribution; exact non-endorsement notice; no logo,
private media or remote thumbnail; privacy disclosure and application approval;
24-hour cache/revalidation maximum; immediate removal quarantine; 24-hour owner
request deadline; append-only downstream removal actions.

Database controls: explicit grants, RLS on every new public-schema table,
curator read-only policies, service-only writes, security-invoker service
projection, no anonymous grants, no security-definer function, indexed foreign
keys/deadlines/eligible expiry, and no removal-case update/delete authority.

Tests: policy parsing, valid admission, 31-photo failure, duplicates, private and
removed media, active removal cases, attribution, source/thumbnail URLs, cache
expiry/revalidation, application approval/privacy disclosure, strict browser
parity, zero-photo submitted boundary, SQL/RLS/grant/index/trigger/view static
contracts, pgTAP plan count, full Python/web suites, build, rights/licensing,
dependency audit, provenance, staged safety, and whitespace.

Rollback/recovery: remove the new policy/component/contracts/migration and
restore the application composition. No live database migration or provider
record is applied by this task, and no Flickr image or credential is introduced.
