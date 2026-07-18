# ButterflyLens 13.4 — Media takedown workflow

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`c0d30d9a1844f3767a1edc94fdefa352f1be3b3a`.

## Outcome

ButterflyLens now has a fail-closed, fingerprinted workflow for Flickr-owner
and generic media rights requests. Authenticated permanent participants can
open a private request, while an operator-controlled service route can admit a
request from a future external private channel. The public request row contains
only a generic non-identifying summary. A security-invoker status view exposes
the request stage to the requester and curators through underlying RLS.
Requester linkage, contact reference, private detail, and authority evidence
remain in `private` schema storage with no browser read grant.

Flickr intake creates the existing exact-24-hour removal case. Its trigger now
correctly quarantines committed objects while leaving pending objects pending
and disabling every rights flag, avoiding the prior pending-object constraint
collision. Non-Flickr intake recursively quarantines the target and every
controlled descendant. New signed URLs are already blocked by the existing B2
rights gate.

## Removal graph and public suppression

The service inventories source records, caches, display assets, thumbnails,
model inputs, embeddings, reviews, public cells, evidence packets, exports,
duplicate mirrors, and unexpired signing receipts by immutable fingerprint.
A worker can add a newly discovered dependency only before it seals the exact
sorted dependency inventory. Requests, requester records, dependencies,
inventory receipts, and events all reject update and delete.

Authority decisions are curator-only. Dependency actions are service-only.
Completion requires verified authority, the exact sealed inventory fingerprint,
and one terminal action for every dependency. Terminal actions and completion
cannot be duplicated. Independent-rights retention requires explicit evidence.
A rejected request stays quarantined; restoration requires a separate current
provider and rights revalidation rather than an unaudited state reversal.

Release and geographic-impact RLS now traverse candidate media ancestors and
the Flickr source. A matching request suppresses the affected release and any
associated public map impact even when every earlier release and sensitive-
location gate passed.

## Policy and provider boundary

`MEDIA_RIGHTS.md` documents the workflow, the exact prelaunch operator/private-
channel blocker, and the prohibition on putting private claims in GitHub
issues. The public footer and README link the policy without presenting a live
request form.

Current official Flickr API terms say photographers own their photos, API use
does not override owner restrictions, owner-requested material must leave an
application within 24 hours, and private-state changes and cached copies must
be handled as soon as reasonably possible. Exact sources and implementation
inferences are frozen in `provenance/valyu.jsonl`.

## Verification

- 524 locked Python tests pass, including nine focused media-takedown schema,
  RLS, policy, completion, and pgTAP-count tests.
- The migration and database contract pass PostgreSQL parsing as 75 and 53
  statements respectively. All fourteen PL/pgSQL functions pass the underlying
  PL/pgSQL parser; pglast's high-level decoder cannot decode PostgreSQL 18's
  trigger-variable JSON representation, so no decoded-AST claim is made.
- The 47-assertion pgTAP contract covers tables, private separation, RLS,
  indexes, triggers, RPCs, least-privilege grants, fixed-search-path helpers,
  and public suppression policies. Runtime pgTAP is unavailable because no
  PostgreSQL server is listening and Docker access is denied; this is not
  represented as a runtime pass.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing covers the staged task and reports zero model files.
- JSON/JSONL, workflow YAML, shell syntax, whitespace, PostgreSQL parsing,
  staged scope, and secret-safety checks pass.

## Skills and external-work boundary

The Supabase and Supabase Postgres best-practices skills informed private
requester separation, empty-search-path security-definer helpers, indexed
foreign keys, append-only evidence, RLS, and narrow RPC grants. No live
Supabase migration occurred: the authenticated MCP connection still requires a
client reload before project tools become available in this process.

GitHits remained disabled by explicit user instruction and was not called. No
Flickr API call, Flickr record import, B2 operation, production workflow
dispatch, media deletion, YOLOE work, BioCLIP work, scientific model call, or
scientific inference occurred. The user-reported Flickr fetch remains external
and active from its 50,000-image checkpoint; no partial result was consumed.

BioMiner was inspected only through its published `CURRENT_STATE.md`
coordination record. It advanced from the task-start SHA
`7e7ae4d767ca432cab386d5538a01bd15ff31f09` to
`e7e31e8a9cc385260f09e13b3429be8d5a25d26c` and remains active with untracked
Flickr/dynamic-pooling work. Its record still provides no immutable GBIF
handoff, so no active BioMiner output or supplied GBIF archive was copied into
ButterflyLens. The rebuilt ButterflyLens ALA baseline remains authoritative.

Known limitation: a legal operator, private request channel, retention schedule,
and production deployment are still required. The workflow governs intake and
proof but does not itself purge B2 objects, invalidate provider caches, or send
requester correspondence. Those actions require the future service worker and
operator, and their fingerprints must be recorded before completion.

Next safe task: the next numbered goal task after this exact commit is pushed
and its GitHub Pages deployment is verified.
