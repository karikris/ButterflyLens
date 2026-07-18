# ButterflyLens 9.4 — Layered consensus policy and calculation

Status: **implemented locally; database integration gate unavailable in this
environment**.

Starting SHA: `34fc90a1a2af6d030abdaecd68fe5b07845fc67e`

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. Its active work was not inspected and no BioMiner data
was copied.

## Outcome

The versioned policy and deterministic projection now calculate all three
required layers. Community evidence is always unweighted and reports every
effective review, support/opposition count, uncertain/media/deferred count, and
minority dissent. Qualified consensus uses only governed qualified reviewers;
missing reliability falls back to weight 1, while exact private blocker-free
domain snapshots may alter separately labelled totals.

Neither raw nor weighted majority resolves disagreement. Yes/no conflict stays
blocked until an independent qualified adjudication cites every exact
conflicting decisive event. Adjudication may resolve qualified consensus while
the community layer remains blocked with its original conflict and dissent.
Corrections are same-reviewer, chronological, acyclic, and produce one current
effective event.

Release consensus adds no vote. It requires a supported qualified outcome plus
explicit rights, provenance, calculated conflict resolution, quality, expert,
and authorization gates. A supplied conflict gate cannot contradict the
calculated human state. Release-ready remains a candidate state, not a
published occurrence.

Postgres stores fingerprinted per-layer summaries, composite reliability and
exact adjudication fingerprints, monotonic revisions, and supersession. A
fixed-search-path admission trigger enforces layer methods, count/event parity,
no model vote, no scientific claim, release gates, and community unweighting.
Consensus snapshots are append-only; browser writes remain closed and existing
respondent/curator RLS reads remain in force.

## Evidence and boundaries

The Supabase skills informed explicit privileges, fixed search paths,
foreign-key indexes, advisory locking, and RLS preservation. Current official
Supabase guidance was used because Valyu remained unavailable. TaxaLens
consensus precedent was inspected from an immutable commit; no source, fixture,
review, label, score, or result was copied.

No Flickr API call, YOLOE work, BioCLIP work, model inference, provider data,
public reviewer ranking, release action, or biodiversity result occurred.
YOLOE and BioCLIP remain explicitly unfinished.

## Verification

- Focused layered-consensus algorithm, policy, and database suites — 19 tests
  passed; combined consensus/reliability regression suite — 30 tests passed.
- Full Python suite — 350 tests passed.
- Contract parity — passed (24 schemas, 20 valid, 20 invalid, 20 versions,
  15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check and production
  build passed.
- Web dependency report — 116 packages verified; review-media fingerprint
  passed.
- pgTAP fixture — 25 assertions defined; Docker-backed execution remains
  unavailable and is not reported as executed.
- Supabase CLI migration generation remains unavailable; the timestamped
  migration follows the existing repository convention.
- Rights verification passed for 52 tracked provider payloads; licence
  verification passed for 319 tracked files, 2 dependency manifests, and 0
  model files.
- JSONL provenance, staged whitespace, secret, model-file, cache, and large-file
  gates passed.
