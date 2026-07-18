# ButterflyLens 11.2 — Deterministic evidence tools

Status: **implemented and deterministic; no OpenAI transport or provider call**.

Starting SHA: `f9b96814f335684cf311b70b622e2cade0188b9b`.

## Outcome

ButterflyLens now exposes the exact fourteen required read-only tools through a
single deterministic registry. The model-facing contract uses strict function
schemas: all object properties are required, additional properties are rejected,
and optional selectors are required nullable fields with separate semantic
checks. The tracked generated contract must exactly match its Python authority.

Every result uses one strict bounded scalar-fact envelope, contains no arbitrary
payload object, attaches allowlisted artifact citations, and has an RFC 8785
SHA-256 result fingerprint. Results are capped at 20 records and 65,536 encoded
bytes. Input and output schemas, citation membership, duplicate citations,
finite values, and result fingerprints are validated on every invocation.

## Evidence behavior

Eighteen readable artifacts are pinned to exact Task 11.1 commit
`f9b96814f335684cf311b70b622e2cade0188b9b` and SHA-256. Startup fails closed
when any current byte differs. Tests also retrieve every path from that exact
Git object and verify its checksum, so repository/commit/path/fingerprint
citations cannot silently name a different revision.

`inspect_species`, species evidence tracing, submitted pipeline inspection,
and the two recommendation tools use real committed evidence. The latter
produce deterministic species-level workflow priorities from reference gaps,
open provider conflicts, or selected provisional reference media. They are
explicitly targeted failure-discovery/review work—not representative sampling,
quality, occurrence, rarity, conservation, importance, or a person/species
ranking.

Map scope can expose the 463-species authoritative national checklist but
withholds ALA occurrence counts and reports Flickr/map cells as unavailable.
ALA/Flickr comparison therefore returns no difference. Flickr candidates,
classifications, consensus, private reviewer quality, live worker state,
geographic contribution, and impact metrics return cited null unavailable
states because no completed governed snapshot exists. Missing heartbeat is not
silently called offline; missing source records are not zero or absence.

Reviewer and contributor operations are self-only at the model contract. Model
arguments never grant authorization. No private controls, expected answers,
identity, precise sensitive region, reviewer weight, ranking, speed, probability,
model-memory taxon, or scientific authority is returned.

## Parallel work

BioMiner was re-read at `b6d9af957d27ea0f6bb012e030be089d8435f437`
and remains dirty/ahead with active dynamic-pooling/BioCLIP and Flickr work.
No output, log, workstore, configuration, credential, GBIF file, or Flickr
record was read or copied. The GBIF Parquet handoff and Task 10.4 remain
deferred. Flickr API and GitHits were not called. YOLOE and BioCLIP were not run.

## Verification

- Twenty-seven focused evidence-tool tests and seven frozen-requirements tests
  pass together.
- The final full locked Python suite passed: 434 tests.
- Every one of the fourteen tools returns schema-valid, citation-complete,
  bounded JSON in the all-tools test.
- Artifact tampering, extra/model-invented arguments, malformed identifiers,
  invalid scope semantics, unknown taxa, and cross-person reviewer access fail
  closed. Repository readers return defensive copies so callers cannot mutate
  the verified in-memory evidence cache.
- Rights verification passed for 52 tracked provider payloads.
- Licence verification passed for 405 tracked files, two dependency manifests,
  and zero model files.
- Generated-contract equality, JSON/JSONL, staged secret/model/media,
  whitespace, exact commit subject, and non-force push verification are release
  gates.
