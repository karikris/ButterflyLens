# ButterflyLens redesign 0.1.3 — TaxaLens interaction precedent audit

Status: complete against the immutable TaxaLens Git object
`e845dd98493979f37b04dbb6538e0d7b8758ca11`.

Date: 2026-07-19

## Inspection method and boundary

Every source statement in this report was inspected with `git show` or
`git grep` against the exact commit above. The TaxaLens worktree has unrelated
user-owned changes, but none were read as product authority. No broad source,
demo data, candidate media, or generated artifact was copied into ButterflyLens.

The pinned implementation is a precedent, not an upstream data handoff.
ButterflyLens retains its own contracts, rebuilt authoritative baseline,
Supabase RPC, rights gates, and public product vocabulary.

## Precedent matrix

| Requested area | Pinned TaxaLens behavior | ButterflyLens decision |
| --- | --- | --- |
| `ReviewRepository` | Port defines campaign/items/events loading, append, current-decision projection, consensus, canonical receipt export, and local campaign clear | **Adopt the port shape, adapt the result**: ButterflyLens append must return a local/remote receipt and expose sync state; keep current state as a projection over retained events |
| IndexedDB event store | Versioned database stores campaigns, items, events, current projections, and sync status. One transaction validates the event/ledger, appends the event, updates current decisions, and queues its ID. Duplicate IDs are accepted only when canonical content matches | **Adopt selectively**: transaction/store separation, canonical duplicate check, derived projection, ordered event sequence, pending outbox, strict decode, and fail-closed seed conflict are strong patterns |
| Local notification | IndexedDB append/clear dispatches a validated `CustomEvent` on `window`; the map projection hook increments a revision and reloads the ledger | **Extend, do not copy as complete**: this updates the same document only. No `BroadcastChannel` exists at the pinned SHA, so ButterflyLens also needs a same-origin cross-tab channel and must still self-notify the sending tab |
| Offline sync | `OfflineFirstReviewRepository` commits locally first, serializes sync per campaign, marks attempts/success/failure, preserves pending IDs, and retries on `online` | **Adopt the state machine** with bounded retry and receipt validation; add remote idempotency and authoritative server-receipt storage |
| Map maturity | MapLibre layers distinguish baseline, pending Flickr candidates, reviewed-positive, reviewed-negative, uncertain, and release-ready evidence. Filters, legend, accessible summary/table, scope hierarchy, URL state, and fail-closed unavailable/loading/failure states are separate | **Adopt the semantic separation and accessibility pattern**, not TaxaLens styling or data. ButterflyLens must keep candidate, human assessment, consensus, quality, and release distinct |
| Local map projection | A verified campaign plus explicit campaign-item-to-H3 bindings projects IndexedDB events into cells. It replaces only the committed campaign's review counts and explicitly preserves release-ready counts | **Adopt**: explicit bindings, count reconciliation, event-count receipt, and “local review cannot create release” are directly relevant to immediate map updates |
| Candidate drawer | No component or source symbol named drawer exists. Map clicks select an aggregate H3 cell and render `SelectedGeographyDetails`; source/record worklists create verification deep links | **Do not claim a port**. ButterflyLens must build the required individual candidate drawer from its own record/media/rights contracts. Aggregate cell details are a useful secondary pattern only |
| Verification workspace | Hydrates repository state, checksum-verifies a bounded media cache, gates scientific controls on displayed media, records duration, queues append-only writes, exposes progress/history/conflicts/quality, supports deep links, and falls back to memory if IndexedDB is unavailable | **Adopt interaction invariants, not the broad console**: verified media gate, honest persistence state, one-item flow, abstention, duration, progress, receipt, conflict visibility, and fail-closed fallbacks. Rebuild in ButterflyLens's simpler public Verify page |
| Reset behavior | Cancels media preparation, invalidates the queued-write generation, awaits the current writer, clears media cache and the selected local campaign, clears legacy local storage, closes/recreates the local repository, and resets controller state. It does not delete remote evidence | **Adopt with tests**: make reset campaign-scoped, await writes, preserve remote ledger, close subscriptions/channels, and keep UI state unchanged on repository failure where possible |
| Supabase adapter | Reads tables directly and appends directly to `verification_events`; duplicate conflicts are resolved by re-reading canonical events. `appendEvent` returns `void` | **Reject for direct reuse**: ButterflyLens has revoked direct event insertion and requires `public.submit_review_event`. Its adapter must call the RPC and validate/store the four-field authoritative receipt |

## Repository and IndexedDB details worth preserving

The TaxaLens repository contract encodes three important scientific semantics:

- events are append-only and superseded events remain in receipt exports;
- current decisions are derived projections, not mutable truth rows; and
- consensus is a distinct projection over campaign rules, items, and events.

The IndexedDB adapter reinforces those semantics in one read-write transaction.
It verifies campaign/item identity, rejects a reused event ID with different
canonical content, validates the proposed event against the full existing
ledger, records a deterministic sequence, updates the cached projection, and
adds the event to the pending set. Loading current decisions accepts the cached
projection only when its event count matches the ledger; otherwise it rebuilds.

The receipt is canonical JSON containing the campaign, sorted items, complete
event ledger, current decisions, consensus, and explicit append-only/current-
projection semantics. ButterflyLens should keep that inspectability, while its
smaller per-submission UI receipt should additionally include the local commit
state and the exact Supabase RPC acknowledgement when available.

## Notification and immediate projection

Pinned TaxaLens does not use `BroadcastChannel`. Its
`localReviewLedgerEvents.ts` dispatches a `CustomEvent` on the current window.
`useLocalGeographicReviewProjection` subscribes, increments a revision, aborts
the previous load, reopens the IndexedDB repository, loads events, validates
the committed campaign and H3 bindings, and rebuilds the map projection.

This is the correct invalidation model—announce identity, then reload from the
ledger—but incomplete for multiple tabs. ButterflyLens should use both:

1. a same-document custom event for immediate sender updates; and
2. a named `BroadcastChannel` for other same-origin tabs/windows.

Both messages should contain only schema version, campaign/item/event identity,
and operation. They should never contain reviewer reliability, private identity,
raw coordinates, comments, or the scientific projection itself.

## Map maturity and scientific guardrails

The TaxaLens map is substantially more mature than ButterflyLens's current
static SVG:

- global/country/admin scope hierarchy and stable URL state;
- verified Parquet inputs queried locally in a bounded DuckDB worker;
- MapLibre layers plus keyboard/table alternatives;
- baseline, pending candidate, reviewed positive, reviewed negative, uncertain,
  media-failure/skipped projection, and release-ready counts;
- maturity filters, legends, tooltips, scope ranking, selected-cell details,
  quality milestone state, export, network, performance, accessibility, reduced-
  motion, forced-colour, and no-WebGL tests;
- explicit unknown/unavailable states rather than inferred absence.

The local overlay has the most important invariant: it may replace the review
counts belonging to the same explicitly bound campaign, but it leaves retained
`releaseReadyCount` and release-ready cell state unchanged. It rejects totals
that exceed the candidate count. Its review projection separately calculates
pending, positive, negative, uncertain, media failure, skipped, quality-valid,
and release-ready states and leaves `scientificClaimAllowed=false`.

ButterflyLens should adopt that maturity vocabulary and reconciliation logic.
It should not copy TaxaLens's current map data, demo campaign, styling, or
source-specific assumptions. The required ButterflyLens sequence remains:
global baseline → amber candidate → individual record/image → BioCLIP candidate
when real evidence exists → human assessment → stored receipt → immediate
record/map state → 20-image set → community milestone.

## Candidate selection and drawer gap

TaxaLens offers:

- aggregate map-cell selection and `SelectedGeographyDetails`;
- an accessible sortable cell table and stable cell deep link;
- review-priority and evidence-record actions that generate an exact Verify
  deep link; and
- a Verify notice that fails closed when the routed Flickr candidate lacks a
  committed checksum-verified image.

It does not offer the required ButterflyLens individual candidate drawer that
combines provider record, rights state, public image or link-only fallback,
model/reference evidence, review CTA, and post-review receipt. That surface is
new ButterflyLens work. The useful precedent is the stable selected identity
and fail-closed deep-link behavior, not a nonexistent component.

## Verification workspace and reset assessment

The workspace correctly prevents a scientific decision until a checksum-
verified image has actually displayed. It keeps Can't view and Skip available,
measures duration from image open, appends rather than overwrites corrections,
shows persistence failures, and separates a local review from a server claim.
The controller serializes writes with a promise chain and hydrates from the
repository before enabling durable decisions.

Its reset sequence is a strong starting point because it:

- aborts active cache work;
- increments a write generation so stale completion callbacks cannot report
  success into the cleared session;
- waits for the in-flight write chain;
- clears only local media and the selected campaign ledger;
- removes legacy local state;
- closes and recreates the default repository; and
- resets the view/controller state only after storage operations succeed.

ButterflyLens must add explicit disposal of cross-tab channels/subscriptions
and must never map this reset to a remote delete. A locally queued event that
has already received a remote receipt is immutable remote evidence.

## Supabase incompatibility

TaxaLens's Supabase repository is not compatible with the current ButterflyLens
security boundary. It calls `.from('verification_events').insert(...)` and
returns no receipt. ButterflyLens explicitly revokes authenticated direct insert
and derives reviewer/campaign/media identity inside `submit_review_event`.

The ButterflyLens remote adapter must therefore be original and narrow:

- call only `rpc('submit_review_event', namedArguments)`;
- map versioned UI/domain values to the database vocabulary;
- validate exactly one returned receipt row and all four fields;
- make duplicate retry idempotent or fail visibly without a false synced state;
- store the acknowledgement against the local event in IndexedDB; and
- never expose the service role or bypass row-level ownership.

## Selective reuse decision

Adopt as architecture:

- repository port and append-only/current-projection semantics;
- IndexedDB transaction, projection cache, outbox, and canonical duplicate
  detection;
- offline-first ordered synchronization states;
- same-tab invalidation followed by authoritative reload;
- explicit item-to-cell bindings and release-preserving map overlay;
- verified-media decision gate, duration, progress, receipt, and reset sequence;
- map accessibility, maturity, and unavailable-state test categories.

Rebuild for ButterflyLens:

- public four-page information architecture;
- individual candidate drawer and one-image Verify experience;
- `BroadcastChannel` cross-tab invalidation;
- RPC/receipt remote adapter and idempotency;
- 20-image set and community milestone projection;
- ButterflyLens contract/value adapters and public styling.

Do not copy:

- the broad TaxaLens research console;
- demo Flickr campaign/data or committed source artifacts;
- direct-table Supabase writes;
- TaxaLens branding, route hierarchy, or exact visual design;
- any model output, candidate media, or scientific result.

## Evidence boundary

BioMiner remains in its Flickr-metadata fetch, so this audit neither inspects
nor copies mutable BioMiner output. No Flickr API call occurred. YOLOE and
BioCLIP remain unfinished. This report changes no ButterflyLens runtime or
scientific state.
