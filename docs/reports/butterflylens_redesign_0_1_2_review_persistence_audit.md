# ButterflyLens redesign 0.1.2 — review persistence and projection audit

Status: complete at ButterflyLens
`4dfebad154c47119d48ccc43f82832991c9c1bc8`.

Date: 2026-07-19

## Outcome

ButterflyLens has a strong append-only Supabase review schema and an
authenticated submission RPC, but the public Verify experience is a disconnected
React draft. There is no browser repository, IndexedDB event ledger, outbox,
Supabase client, receipt display, cross-context notification, current-record
projection, map consumer, quality consumer, or community consumer in the web
application.

The missing product link is therefore not a database-table rewrite. It is a
typed offline-first repository and projection boundary between the existing
Verify controls and the existing append-only server contract.

## Current end-to-end trace

| Stage | Current implementation | Persisted? | Consumer/effect |
| --- | --- | --- | --- |
| Review item | `submittedReviewItem` is one rights-cleared Wikimedia fixture | Bundled static JSON/module state | Verify page only |
| Draft outcome | `ReviewLanding` holds `outcome` in `useState` | No | Updates the draft contribution card only |
| Draft comment | `comment` in `useState` | No | Echoed in the same component |
| Alternative taxon | `alternativeTaxon` in `useState`, enabled by a component prop | No | Echoed in the same component; no accepted-taxon lookup |
| Media readiness | `verifiedImageDisplayed` is set by image load/error | No | Gates Yes, No, and Can't tell |
| Blind lock/reveal | `decisionLocked` and `contextRevealed` in `useState` | No | Locks only the current React instance; “Start a new blind draft” deletes the local draft state |
| Submit action | No submit button or handler; form submission only calls `preventDefault()` | No | Page explicitly says it does not submit or claim a stored review |
| Local database | No IndexedDB usage or dependency | No | None |
| Same-tab/cross-tab notification | No custom ledger event, `BroadcastChannel`, storage event, or subscription | No | None |
| Remote adapter | No `@supabase/supabase-js` dependency and no `.rpc()` call in the web app | No | None |
| Server RPC | `public.submit_review_event(...)` in migration `20260718015500` | Yes, when called by an authenticated assigned reviewer | Atomically appends a review event and marks the assignment responded |
| Consensus | Append-only `public.consensus` schema and deterministic Python calculation/storage-row code exist | Schema yes; submitted completed consensus count is 0 | No browser or automatic runtime materializer is connected to Verify |
| Map | `SubmittedEvidenceMap` imports a frozen ALA browser snapshot | Static only | It explicitly reports human review unavailable and never reads review events |
| Quality | `submittedQualityProjection.json` reports reviewed sample 0 | Static only | Never refreshes after a draft or stored event |
| Community | `submittedContributorImpact.json` has every self-only metric unavailable | Static only | Never refreshes after a draft or stored event |

A reload, unmount, tab close, or “Start a new blind draft” loses the current
choice. A second tab cannot observe it. No current public action can reach the
server RPC.

## Existing Supabase submission boundary

`public.submit_review_event` is a fixed-empty-search-path
`security definer` function. Execution is revoked from `public` and `anon` and
granted only to `authenticated`; direct browser insert/update/delete access to
`review_events` is denied. The function:

1. requires `auth.uid()`;
2. locks an assignment owned by the active reviewer in an open campaign;
3. requires committed, decodable, rights-allowed, display-allowed media;
4. derives campaign, media, reviewer, question, and image identity server-side;
5. validates an optional accepted alternative species and correction target;
6. records the blind state and `scientific_claim_allowed=false`;
7. appends the event under trigger-enforced correction lineage;
8. sets the assignment to `responded` and preserves its first `responded_at`;
9. returns `stored_review_event_id`, `stored_assignment_id`,
   `stored_event_fingerprint`, and `stored_recorded_at`.

That four-field row is already a useful authoritative remote receipt. The
transaction also accepts corrections against a responded assignment and
requires them to supersede the current event without mutating history.

Important integration gaps remain:

- UI values `cant_tell` and `cant_view` differ from database values
  `cannot_tell` and `cannot_view`; a versioned adapter is required.
- The UI does not possess an assignment ID, review-event ID, confidence,
  duration, source version, explicit model-unavailable version, supersession
  target, or canonical event fingerprint.
- The server accepts the caller's fingerprint after shape/uniqueness checks but
  does not recompute the canonical digest inside the RPC; client canonicalization
  and a server-verifiable contract must stay explicit.
- A duplicate retry currently meets unique constraints rather than returning
  the prior receipt as an idempotent acknowledgement.
- There is no browser auth/assignment-loading path in the current public app.

The migration's privilege and fixed-search-path choices align with current
[Supabase database-function guidance](https://supabase.com/docs/guides/database/functions):
`security invoker` is the safe default; a necessary `security definer` must fix
its search path and qualify relations; function execution should be explicitly
revoked and regranted. The JavaScript client can invoke a Postgres function and
pass named arguments through
[`rpc()`](https://supabase.com/docs/reference/javascript/rpc). The July 2026
Supabase changelog contains no RPC change that alters this audit; its announced
future TypeScript 5 floor is already below this app's TypeScript 7 toolchain.

## Consensus and current-state semantics

`review_events` and `consensus` are deliberately append-only. Review correction
lineage points at the superseded event. Consensus has separate unweighted
community, qualified, and release layers; model votes are forbidden as human
votes, dissent is retained, and a release outcome requires every explicit
gate. Current state must therefore be derived as a projection over retained
events/snapshots, never by overwriting the ledger.

No committed web code currently performs that projection. The static submitted
tool output also states that no completed fingerprinted review consensus is
stored. A single new review may update “current human assessment” and local
progress immediately, but it must not fabricate consensus, quality, occurrence
release, or scientific truth.

## Required persistence and projection chain

The implementation contract should be:

`Verify decision → canonical append-only local event → IndexedDB transaction →
local receipt + current projection → same-tab and cross-tab notification →
record/map/community rerender → queued authenticated RPC → authoritative remote
receipt → synced local outbox state → later governed consensus projection`.

IndexedDB is the appropriate browser ledger: MDN documents it as a low-level
client-side store for significant structured data with indexes and transactional
operations ([IndexedDB API](https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API)).
For cross-tab invalidation, MDN documents `BroadcastChannel` as same-origin
communication between windows, tabs, frames, and workers; the sending channel
does not receive its own message
([BroadcastChannel](https://developer.mozilla.org/en-US/docs/Web/API/BroadcastChannel)).
The repository must therefore emit an explicit same-tab event as well as a
channel message, then reload the authoritative projection rather than passing
mutable scientific state in the notification.

Minimum interfaces and states:

- `ReviewRepository`: load assignment/item/events/current decision, append,
  export receipt, and retain corrections;
- `LocalReviewRepository`: IndexedDB ledger, current projection, pending outbox,
  sync receipt, and deterministic reset of only the selected local campaign;
- `RemoteReviewRepository`: invoke `submit_review_event`, validate the exact
  returned receipt, and never directly mutate tables;
- `OfflineFirstReviewRepository`: local commit first, bounded ordered sync,
  idempotent retry, reconnect sync, and visible `local_only | syncing | synced |
  sync_error` state;
- projection notification: campaign/item/event identity only, no private
  reviewer data or coordinates;
- public projection: candidate → locally reviewed → remotely stored → consensus
  states remain distinct and scientific release remains separately gated.

## Missing product links and acceptance implications

- Verify needs a real submit action with pending, success, retry, and correction
  states and an inspectable receipt.
- The selected candidate drawer and record page need to read the projected
  current event after local commit.
- Explore needs a review overlay keyed through an explicit candidate-to-cell
  binding; no coordinate inference is allowed.
- Community needs aggregate/set progress derived from eligible stored events;
  private reliability and ranking remain excluded.
- The current visitor needs a private contribution projection without exposing
  reviewer identity or reliability.
- Quality and consensus may change only when their governed materializers
  produce new snapshots; they must not increment optimistically.
- Reset must clear only local campaign state and subscriptions, never delete or
  rewrite remote review or consensus records.

## Evidence boundary

This audit makes no database or runtime change and performs no Supabase project
call. BioMiner remains in its Flickr-metadata fetch, so no partial candidate
record is consumed. No Flickr API call occurred. YOLOE and BioCLIP remain
unfinished.
