# ButterflyLens 8.5 — Append-only reviews and comments

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `8b2fe6a88c2862ede04da68421d0fb36b0d06efd`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 8.5 closes direct browser inserts into `review_events` and adds one
authenticated, fixed-search-path submission RPC. The RPC derives the private
reviewer identity from `auth.uid()` and the assigned profile, then derives the
campaign, media item, exact question, and image SHA-256 from the locked
assignment. The client cannot supply or override those identity fields.

Every new event records:

- stable review-event and assignment IDs;
- reviewer, campaign, and media-item identity;
- exact question and image SHA-256;
- decision and optional accepted alternative project taxon;
- comment, including an explicit empty string when none is supplied;
- required 1–5 confidence;
- decision time and required bounded duration;
- current superseded event when correcting;
- source version and a required model version or explicit unavailable state;
- blind payload and assignment-policy fingerprints, blind/post-disclosure
  state, false scientific-claim flag, event fingerprint, and recorded time.

The assignment row is locked during submission. Event append and assignment
transition to `responded` occur in one transaction, preserving the original
response timestamp across corrections. Authenticated users retain self-read
access but have no direct insert, update, delete, or sequence path.

An assignment-scoped advisory lock serializes event lineage. The first event
cannot claim a predecessor. Every correction must supersede the current event,
remain within the same assignment/campaign/item/reviewer identity, and have a
non-regressing decision time. Earlier events are never updated or deleted. If
post-decision context was already disclosed, the correction is explicitly
marked `post_disclosure_correction` so later quality logic cannot mistake it
for an untouched blind decision.

The credential-free web replay remains a local draft and does not fake a
stored event. A configured authenticated Supabase client can call the RPC;
wiring production credentials and error handling is deliberately not simulated
in this static submission.

## Evidence and provenance

The Supabase and Supabase Postgres best-practices skills informed Auth-derived
identity, fixed search paths, privilege revocation, row locks, advisory locks,
foreign keys, and atomic state changes. Current official Supabase RLS and Data
API guidance was used because Valyu remained unavailable. GitHits remained
unavailable and was not retried.

TaxaLens' immutable append-only event and supersession precedent was inspected.
No TaxaLens code, data, or stored event was copied; the migration and tests are
original ButterflyLens implementation. No Flickr API call, YOLOE work, BioCLIP
work, model artifact, scientific score, or biodiversity claim was produced.

## Verification

- Targeted append-only review/database/RLS suite — 20 tests passed.
- pgTAP fixture — 14 assertions defined for RPC security, privileges,
  append-only controls, trigger presence, and core fields.
- Docker-backed pgTAP execution — unavailable because this runtime cannot
  access the Docker daemon; the fixture was not reported as executed.
- Full Python suite — 298 tests passed.
- Contract parity — passed (24 schemas, 20 valid fixtures, 20 invalid
  fixtures, 20 versions, 15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check passed.
- Rights verification — passed for 52 tracked provider payloads.
- Licence verification — passed for 289 tracked files, 2 dependency
  manifests, and 0 model files.
- Provenance JSONL validation, staged whitespace validation, and staged secret
  scan — passed.

## Privacy and scientific boundary

The event stores an internal reviewer-profile key, not a public Auth ID. The
RPC returns only the stable event/assignment IDs, fingerprint, and recorded
time. A review event is evidence of one person's assessment; it is not
consensus, expert approval, human support, taxonomic truth, or release
readiness. Conflict projection and independent adjudication remain Task 8.6.
