# ButterflyLens 8.6 — Conflict and adjudication workflow

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `1cea643623f2f20a2bea72afc754c7b194db3278`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 8.6 adds normalized conflict snapshots, independent adjudication
assignments, a blind adjudication queue, and an append-only adjudication event
ledger. The service-only conflict function locks a campaign/item pair and
derives current decisive evidence from review events that have not been
superseded. It refuses to create a conflict without at least two distinct
reviewers and two distinct decision signatures, then retains exact foreign-key
links, fingerprints, and internal reviewer lineage for every source event.

An adjudicator cannot be any source reviewer. Assignment also requires an
active profile, active project membership, verified qualification, and an
expert, curator, or administrator project role. A partial unique index permits
only one active assignment per conflict, and resolved conflicts cannot be
assigned again.

The security-invoker queue exposes only stable assignment/campaign/item IDs,
question, status, policy and conflict fingerprints, conflict kind and count,
media integrity, rights, and a false scientific-claim flag. It excludes source
decisions, comments, model versions, Auth IDs, and all source reviewer
identities.

The authenticated submission RPC derives the adjudicator from `auth.uid()`,
locks the assignment, and derives the conflict, project, campaign, item,
question, image hash, exact source-event fingerprints, and source reviewers.
It stores decision, optional governed alternative taxon, comment, confidence,
time, duration, source/model versions, independence state, policy, lineage and
event fingerprints. The event is append-only and atomically marks its
assignment responded. Adjudication never updates or deletes the dissenting
reviews.

## Evidence and provenance

The Supabase and Supabase Postgres best-practices skills informed fixed search
paths, layered grants and RLS, security-invoker projection, normalized foreign
keys, partial and access-path indexes, assignment/advisory locks, and atomic
state changes. Current official Supabase RLS and Data API guidance was reused
because Valyu remained unavailable. GitHits remained unavailable and was not
retried.

TaxaLens' immutable exact-conflict-event, independent-adjudicator, append-only
event, and consensus precedent was inspected. No TaxaLens code, data, stored
event, or conflict was copied; this is an original ButterflyLens migration and
test suite. No Flickr API call, YOLOE work, BioCLIP work, model artifact,
scientific score, or biodiversity claim was produced.

## Verification

- Targeted conflict/adjudication/review/assignment/RLS suite — 26 tests passed.
- pgTAP fixture — 28 assertions defined for tables, RLS, privileges,
  functions, triggers, indexes, exact-event links, and required fields.
- Docker-backed pgTAP execution — unavailable because this runtime cannot
  access the Docker daemon; the fixture was not reported as executed.
- Full Python suite — 305 tests passed.
- Contract parity — passed (24 schemas, 20 valid fixtures, 20 invalid
  fixtures, 20 versions, 15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check passed.
- Rights verification — passed for 52 tracked provider payloads.
- Licence verification — passed for 293 tracked files, 2 dependency
  manifests, and 0 model files.
- Provenance JSONL, staged whitespace, staged secret-pattern, and model-artifact
  validation — passed.

## Privacy and scientific boundary

Internal source-reviewer keys exist only to prove independence and are not
granted to browser roles. The adjudicator sees neither source identities nor
source decisions before submitting. Adjudication is a retained human decision
over a recorded disagreement; it is not taxonomic truth, a model label,
consensus release, occurrence publication, or scientific approval. Existing
release gates must separately consume a later governed consensus projection.
