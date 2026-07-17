# Evidence fingerprint contract

ButterflyLens uses two related but non-interchangeable SHA-256 identities.

1. A **physical checksum** hashes the exact bytes fetched, stored, or exported.
2. A **semantic fingerprint** hashes a versioned JSON preimage that states what
   an evidence object means and which earlier evidence it depends on.

Matching bytes do not prove matching meaning, and matching semantic payloads do
not prove that separately stored bytes are intact. Records that have both must
carry both.

## Semantic preimage

`butterflylens-evidence-fingerprint:v1.1.0` calculates `digest` as SHA-256 over
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

The Python implementation uses the pinned `rfc8785` package after recursively
rejecting values outside the I-JSON domain. The TypeScript implementation uses
ECMAScript JSON string/number serialization, UTF-16 property ordering, strict
Unicode checks, and a local SHA-256 implementation. Frozen cross-language
vectors are release gates. Neither implementation mutates the supplied
preimage when it orders parent references.

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

The v1.1 vocabulary covers every fingerprint required by the current build
contract: taxon concept, name assertion, query definition, logical query
association, physical API request, source response, source Flickr record,
downloaded image, perceptual duplicate group,
YOLOE route, full-frame visual input, BioCLIP embedding, reference bank,
prototype, candidate score, review event, consensus, quality snapshot,
geographic-impact cell, release candidate, and export manifest. It also covers
the project, run-input, provider-snapshot, source-response, media-object,
model-artifact, preprocessing, artifact-manifest, and map-snapshot envelopes
needed to connect those records.

A new evidence kind or different preimage meaning requires a contract version
change. It must not be squeezed into a misleading existing kind. Version 1.0
remains readable for existing records; v1.1 adds `logical_query_association`
and replaces the ambiguous v1.0 `api_response` vocabulary item with
`source_response`. Writers emit v1.1.

## Lineage traversal

`EvidenceLineageGraph` validates every record before indexing it. Construction
fails when a digest is duplicated, a parent is absent, the declared parent
kind differs from the referenced record, or the graph contains a cycle. It
never fetches a missing parent or silently truncates a lineage.

Python and TypeScript expose deterministic direct-parent, direct-child,
ancestor, descendant, reachability, and parent-before-child topological
traversals. Breadth-first traversals order nodes by minimum distance and then
digest; topological ties use digest order. Returned records are defensive
copies, so consumer mutation cannot change the validated graph.

When a content-addressed store encounters an existing digest,
`assert_same_fingerprint_identity` / `assertSameFingerprintIdentity` compares
the canonical preimages. An equal preimage is a duplicate identity; a
different preimage raises `FingerprintCollisionError`. This defensive branch
does not claim that the test suite can find or rule out cryptographic SHA-256
collisions.

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
