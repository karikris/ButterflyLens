# ButterflyLens 14.1 — Occurrence release gates

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`54f51388e0b74f958e82802a48e8da19cab95c60`.

## Outcome

ButterflyLens now defines release readiness as one closed, deterministic set of
nine independently evidenced gates: human-supported identity, qualified
consensus, configured expert review, coordinate/date validity, duplicate
independence, rights/provenance, representative quality, absence of unresolved
conflict, and a complete evidence packet. Missing, stale, unrelated, unknown,
or superseded evidence blocks the decision.

The Python planner accepts exactly those gates, normalizes their evidence, and
emits a canonical fingerprint. Its only successful state is
`release_ready_occurrence_candidate`; both publication and scientific-claim
flags remain false. Input order cannot alter the decision fingerprint.

## Database boundary

The migration adds one append-only, service-written receipt per release
candidate. Before admitting a receipt, the trigger validates the exact latest
community, qualified, and release consensus lineage; the campaign's configured
expert rule and current verified expert event when required; a blind
representative quality snapshot; a publishable sensitive-location receipt;
committed allowed rights with no takedown; no unresolved human conflict; and
the candidate's evidence packet. It stores the exact sorted fingerprint set and
rejects mutation.

Anonymous release visibility now requires the intersection of the occurrence
release receipt, the sensitive-location receipt, and the no-takedown check. A
nominally approved or exported candidate cannot bypass any of those controls.
Curators may inspect receipt evidence only through project-scoped RLS; browser
roles cannot create it.

`OCCURRENCE_RELEASE.md`, `DATA_RIGHTS.md`, the README, and the public footer
state the same boundary. A release-ready candidate is still not a published
occurrence, ALA record, provider submission, or proof of species presence or
absence.

## Verification

- 534 locked Python tests pass, including ten focused planner, database, policy,
  and pgTAP-count tests.
- The migration and database contract pass PostgreSQL parsing as 26 and 50
  statements respectively. Both PL/pgSQL trigger functions pass the underlying
  PL/pgSQL parser.
- The 44-assertion pgTAP contract covers the receipt schema, indexes, RLS,
  triggers, grants, immutable boundary, fixed-search-path helper, and public
  release policy. Runtime pgTAP is unavailable because neither a local
  PostgreSQL server nor permitted Docker socket is available; no runtime pass
  is claimed.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing, provenance syntax, staged scope, secret safety, workflow YAML,
  shell syntax, whitespace, and large-file checks are completed immediately
  before commit.

## Skills and external-work boundary

The Supabase and Supabase Postgres best-practices skills informed the fixed-
search-path security-definer helper, indexed foreign keys, append-only receipt,
least-privilege grants, project-scoped RLS, and fail-closed evidence queries.
No live Supabase migration occurred: OAuth succeeded earlier, but this client
still requires a reload before project MCP tools become available.

GitHits remained disabled by explicit user instruction and was not called. No
Flickr API call, Flickr data import, provider submission, occurrence
publication, B2 operation, production workflow dispatch, YOLOE work, BioCLIP
work, scientific model call, or scientific inference occurred. The user-
reported Flickr fetch remains external and active from its 50,000-image
checkpoint; no partial result was consumed.

BioMiner was inspected only through its published `CURRENT_STATE.md`
coordination record. It advanced from the task-start SHA
`28babac4eb1aca476eec9274c28d6e5c61d01e10` to
`882cd15422aa3796a0306a8f2c335f04a76a7482` and remains active with local
Flickr/dynamic-pooling work. Its record still provides no immutable GBIF
handoff, so no active BioMiner output or supplied GBIF archive was copied into
ButterflyLens. The rebuilt ButterflyLens ALA baseline remains authoritative.
TaxaLens remained at `e845dd98493979f37b04dbb6538e0d7b8758ca11`; its dirty
user work was not touched or imported.

Known limitation: the receipt validator is implemented and statically tested
but has not run against a live Supabase database. The repository contains no
release receipt and makes no new occurrence claim. Creating receipts,
publishing occurrences, or submitting to ALA requires later authorized,
runtime-verified work.

Next safe task: generate the fingerprinted Darwin Core evidence package after
this exact commit is pushed and its GitHub Pages deployment is verified.
