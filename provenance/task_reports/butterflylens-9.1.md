# ButterflyLens 9.1 — Reviewer control items

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `82fbc7f167cc8b75e86661cbb4b270c9a1c9e7d3`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 9.1 adds a private, closed catalog for known butterfly, known
non-butterfly, ambiguous image, duplicate, media failure, and life-stage
controls. Control sets, expected answers, evidence citations, evidence and
ground-truth fingerprints, source versions, and exact assignment bindings stay
in the private schema and are unavailable to guest and reviewer roles.

Every item must belong to a fully blind `reviewer_control` campaign, the same
project as its control set and governed media, and rights/integrity-passing
media. Type-specific constraints fix valid expected-answer shapes. Duplicate
targets must be distinct same-project media. Control truth and hidden
assignment bindings are append-only; only active sets can bind an exact
campaign/media assignment.

No real control item was fabricated. The existing Wikimedia fixture is
rights-cleared but its taxon label remains a provider assertion, not verified
ground truth. An item can enter an active set only with governed human/reference
evidence, fingerprint, citation, and version.

## Evidence and boundaries

The Supabase skills informed use of the non-exposed private schema, fixed
search paths, explicit revocation, foreign-key indexes, immutable triggers,
and exact assignment binding. TaxaLens control-evaluation precedent was
inspected; no code, labels, control data, or measurements were copied.

No Flickr API call, YOLOE work, BioCLIP work, model artifact, reviewer score,
scientific claim, or biological ground-truth assertion was produced. Task 9.2
owns the reliability policy and Task 9.3 owns estimates; neither is claimed
here.

## Verification

- Targeted control schema suite — 6 tests passed.
- pgTAP fixture — 18 assertions defined; Docker-backed execution remains
  unavailable and is not reported as executed.
- Full Python suite — 311 tests passed.
- Contract parity — passed (24 schemas, 20 valid, 20 invalid, 20 versions,
  15 vocabularies; TypeScript 7.0.2).
- Web review suite — 6 Vitest tests passed; TypeScript check passed.
- Rights verification — passed for 52 tracked provider payloads.
- Licence verification — passed for 297 tracked files, 2 dependency
  manifests, and 0 model files.
- Provenance JSONL and staged whitespace validation — passed.
