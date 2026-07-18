# ButterflyLens 13.3 — Sensitive butterfly location controls

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`e806924312cc7d5415643513eda87d2f4fc683e5`.

## Outcome

ButterflyLens now fails closed before a map or release location becomes
public. A deterministic Python contract combines a versioned taxon-sensitive
location rule with exact ALA/Flickr provider constraints. Unknown sensitivity,
missing provider evidence, missing permission-to-H3 mapping, excessive H3
resolution, disallowed scope, exact sensitive source precision, or a count
below the explicit policy threshold produces a coordinate-free `withheld`
decision.

The planner sorts provider fingerprints, applies the strictest taxon/provider
resolution ceiling, emits only a pre-materialized named scope or H3 cell, and
fingerprints the complete decision. It does not contain a hardcoded Flickr
accuracy-to-H3 conversion and every output has
`scientific_claim_allowed = false`.

## Database and public-read boundary

The Supabase migration adds private, append-only provider-constraint and
publication-receipt ledgers. They contain snapshot, permission, mapping,
policy, target, and semantic fingerprints but no occurrence latitude or
longitude columns. Only the service role can append. Project curators and
administrators may inspect evidence through RLS; community and anonymous roles
cannot write it, and anonymous users cannot inspect the private ledgers.

The receipt trigger validates the exact project/species/target fingerprint,
current project policy version, sorted unique source lineage, exact ALA and
applicable Flickr snapshot, pre-materialized target scope, count bound, and
minimum of every used provider ceiling and the taxon-policy ceiling. It rejects
a used location from an unrelated snapshot. Sensitive targets can be
generalised or withheld, never published with exact source precision. Release
locations use closed H3 cell identifiers and require geographic-impact lineage.

The existing anonymous map and release RLS policies now call a fixed-query,
empty-search-path security-definer helper. A row that is nominally public,
approved, or exported remains invisible until one validated `publish` or
`generalised` receipt exists. Receipts and constraints reject updates and
deletes even for a role accidentally granted broader privileges later.

## Authoritative ALA and Flickr boundaries

The rebuilt ButterflyLens ALA baseline remains authoritative. Its frozen
aggregation manifest and Parquet tests prove that all 375 publicly generalised
rows contribute only to Australia, state/territory, and H3 resolution 3, with
zero membership in IBRA, LGA, H3 resolution 5, or H3 resolution 7 aggregates.
The policy preserves that materialized precedent without assuming it applies to
a later snapshot.

Current official ALA documentation says its sensitive service applies supplied
generalisations and that protected/private reads require authentication.
Current official Flickr documentation separates geo visibility permission from
photo visibility and records accuracy on a 1-to-16 scale. ButterflyLens stores
accuracy as evidence only; both public geo permission and a reviewed versioned
mapping are required before Flickr location use. Exact sources and inferences
are recorded in `provenance/valyu.jsonl`.

## Verification

- 515 locked Python tests pass, including twelve new sensitive-location planner,
  database, policy, deterministic-fingerprint, and authoritative ALA tests.
- The complete migration passes PostgreSQL parsing as 33 statements. All three
  PL/pgSQL trigger functions independently pass the PL/pgSQL parser.
- The 44-assertion pgTAP contract covers schema, RLS, privileges, indexes,
  triggers, fixed-search-path functions, public receipt policies, and absence
  of source-coordinate columns. Runtime pgTAP is unavailable because the local
  Docker socket is not accessible and no PostgreSQL server is listening; this
  is not represented as a runtime pass.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning
  remains non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing covers the staged task and reports zero model files.
- JSON/JSONL, workflow YAML, shell syntax, whitespace, PostgreSQL parsing,
  staged scope, and secret-safety checks pass.

## Skills and external-work boundary

The Supabase and Supabase Postgres best-practices skills informed the private
security-definer helper, RLS, immutable server-written ledgers, least-privilege
grants, and FK indexes. No live Supabase migration occurred: the authenticated
MCP connection still requires a client reload before tools become available in
this process.

GitHits remained disabled by explicit user instruction and was not called. No
Flickr API call, Flickr record import, B2 operation, production workflow
dispatch, YOLOE work, BioCLIP work, scientific model call, or scientific
inference occurred. The user-reported Flickr fetch remains external and active
from its 50,000-image checkpoint; no partial result was consumed.

BioMiner advanced during this task and remains active and dirty at published
SHA `63514b94477001b9d51c487bf2f5eb0c31ab484e`. Only its published
`CURRENT_STATE.md` coordination record was read. That record still lists live
current-policy GBIF acquisition and durable-media admission as unfinished and
contains no immutable handoff, so no active BioMiner output or supplied GBIF
archive was copied into ButterflyLens.

Known limitation: a project must set the exact new policy version and its
service materializer must append provider constraints and receipts before any
live public location can pass RLS. This is intentional fail-closed behavior,
not an unavailable-data zero.

Next safe task: Task 13.4 after this exact commit is pushed and its Pages
deployment is verified.
