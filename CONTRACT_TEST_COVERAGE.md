# ButterflyLens contract test coverage

Coverage inventory version: `butterflylens-contract-test-coverage:v1.0.0`

Last reviewed: 18 July 2026

## Executable boundary

`tests/test_contract_coverage.py` is the tracked inventory gate for governed
fingerprints, JSON Schemas, versioned policies, and submitted/live projections.
It discovers surfaces from Git rather than accepting an undocumented count.
A new tracked surface fails until it has positive and negative evidence in the
registry and the named test exists.

The gate supplements the focused domain tests. It does not claim that line
execution alone proves scientific validity, provider rights, privacy, or
production behavior.

## Inventory

| Surface | Governed inventory | Coverage rule |
|---|---:|---|
| current semantic fingerprint kinds | 29 | each validates, then rejects a digest mutation |
| fingerprint parent relationships | 8 | each validates; an unknown relationship fails |
| tracked JSON Schemas | 41 | every schema is structurally valid and belongs to one named positive/negative group |
| cross-language contract schemas | 24 | all are reachable from 20 positive and 22 negative parity roots |
| versioned policies | 11 | every discovered version/source pair has named positive and negative tests |
| governed projection families | 12 | every submitted JSON and exported projection symbol is registered with both test directions |
| submitted JSON artifacts | 7 | every fingerprint field is a SHA-256 or explicit null; private keys are absent |

The policy inventory covers ALA contribution preparation, community
moderation/privacy, Darwin Core export, Flickr public display, layered
consensus, media rights/removal, occurrence release, representative audit,
reviewer reliability, and sensitive locations.

The projection inventory covers the authoritative public ALA baseline,
classification maturity, contributor impact, Flickr display, monitoring,
operations submitted/live selection, quality, review disclosure, species,
OpenAI artifacts, OpenAI replay, and worker-offline fallback.

## Scientific and operational assertions

The registered negative tests preserve the project-wide boundaries:

- the retired fingerprint v1.0 version, digest mutation, unknown vocabulary,
  schema mutation, and lineage drift fail closed;
- provider assertion, machine score, geography, and a passed checkbox cannot
  create human or scientific authority;
- targeted failure discovery cannot become a population-quality estimate;
- submitted state cannot claim live telemetry;
- unreviewed, rights-blocked, sensitive, removed, or unlicensed evidence
  cannot enter public release or export;
- reviewer and administrative contact identity are absent from submitted
  public JSON; and
- the public site remains queryable from the submitted snapshot when the M5
  worker is offline.

The pre-task full Python suite was also run through the Python standard-library
trace counter. It observed execution in every tracked Python contract,
verification, OpenAI, storage, worker, and builder module reached by the suite.
That trace is supporting evidence only; the registry and domain assertions are
the semantic gate.

All Task 15.1 tests are deterministic and offline. They make no Flickr, ALA,
GBIF, OpenAI, Supabase, B2, model, or other provider call; download no weights;
and require no credential or M5 worker.
