# Evidence fingerprint contract

ButterflyLens uses two related but non-interchangeable SHA-256 identities.

1. A **physical checksum** hashes the exact bytes fetched, stored, or exported.
2. A **semantic fingerprint** hashes a versioned JSON preimage that states what
   an evidence object means and which earlier evidence it depends on.

Matching bytes do not prove matching meaning, and matching semantic payloads do
not prove that separately stored bytes are intact. Records that have both must
carry both.

## Semantic preimage

`butterflylens-evidence-fingerprint:v1.0.0` calculates `digest` as SHA-256 over
the UTF-8 bytes of RFC 8785 JSON Canonicalization Scheme output for the exact
`preimage` object. The digest and `recorded_at` fields are outside the preimage.

The preimage contains:

- an enumerated `fingerprint_kind`;
- an opaque stable `subject_id`;
- the exact schema version governing `payload`;
- the semantic `payload`; and
- sorted parent fingerprint references with explicit relationships.

Parents are sorted by `relationship`, then `fingerprint_kind`, then `digest`,
using ascending Unicode code-point order for the ASCII vocabularies in this
contract. Duplicate parent objects are rejected. Array order inside the
domain payload remains meaningful and is never automatically sorted.

## Canonical JSON restrictions

The preimage must be I-JSON compatible before hashing:

- object property names are unique;
- strings are valid Unicode and are preserved without normalization;
- numbers are finite IEEE-754 binary64 values;
- negative zero is rejected rather than normalized to positive zero;
- identifiers and integers that may exceed the interoperable integer range are
  encoded as strings; and
- no timestamp, random ID, process-local path, credential, signed URL, or
  unredacted private value is added unless it is explicitly part of the
  versioned semantic contract.

Hash implementations must use a conforming RFC 8785 implementation. Sorting
keys and calling a language's ordinary JSON serializer is not accepted as a
general substitute because number and Unicode behavior can diverge.

## Required kinds

The v1 vocabulary covers every fingerprint required by the current build
contract: taxon concept, name assertion, query definition, physical API
request, source Flickr record, downloaded image, perceptual duplicate group,
YOLOE route, full-frame visual input, BioCLIP embedding, reference bank,
prototype, candidate score, review event, consensus, quality snapshot,
geographic-impact cell, release candidate, and export manifest. It also covers
the project, run-input, provider-snapshot, API-response, media-object,
model-artifact, preprocessing, artifact-manifest, and map-snapshot envelopes
needed to connect those records.

A new evidence kind or different preimage meaning requires a contract version
change. It must not be squeezed into a misleading existing kind.

## Meaning and limits

A fingerprint establishes repeatable identity only when its preimage is
available and recomputation succeeds. It does not establish:

- data or media rights;
- provider truth;
- taxonomic correctness;
- independent human verification;
- calibrated model probability;
- biological occurrence or absence;
- release readiness; or
- freedom from deliberate SHA-256 collision attacks forever.

Every consumer validates the schema, recomputes the digest, validates parent
availability, and applies the independent rights, review, quality, and release
gates appropriate to the evidence layer.
