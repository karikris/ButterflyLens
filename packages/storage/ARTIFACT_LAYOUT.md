# ButterflyLens B2 artifact layout

The machine-readable contract is `artifact-layout.v1.json`. It uses two B2
buckets because B2 S3-compatible object ACLs follow the bucket ACL: every
class is private except separately approved public thumbnails, which live in
a dedicated public bucket. Bucket names, account IDs, credentials, endpoints,
signed URLs, requester identities, and personal information never appear in
object keys or semantic fingerprints.

Every final key is immutable and contains the physical SHA-256 digest. The
run-scoped path preserves operational ownership while manifests connect the
physical checksum to semantic fingerprints, rights decisions, source-media
dependencies, schema versions, B2 version IDs, and byte counts. An ETag is
recorded only as transport metadata and is never treated as SHA-256.

## Publication protocol

1. Build in a private local staging directory and calculate SHA-256 and byte
   count before upload.
2. Local commits use a temporary file on the destination filesystem, `fsync`,
   atomic rename, and directory `fsync`.
3. Upload non-manifest objects to their final content-addressed keys using a
   signed payload hash. Do not overwrite an observed final key.
4. Record the returned B2 version ID and verify key, version, byte count, and
   media type with `HEAD`. Consumers recalculate SHA-256 after `GET`; neither
   ETag nor object name alone is sufficient.
5. Upload subordinate manifests only after every object they name verifies.
   Upload the immutable root run manifest last.
6. Validate the root manifest, then compare-and-swap the database pointer from
   the expected prior fingerprint to the new manifest fingerprint. Readers
   ignore staging prefixes and any run without the published pointer.

B2 `PUT` is not assumed to provide create-if-absent semantics. Concurrent
writers coordinate through the database lease/fencing contract. Because keys
are content addressed, an equal-key race is acceptable only after canonical
preimage and physical-byte checks agree; otherwise the run is quarantined.

## Access and cache policy

Application keys are bucket- and prefix-restricted with the minimum required
capabilities. Delete capability is held by the removal worker, not ordinary
writers. Private objects use server-side encryption and short-lived presigned
`GET` or `HEAD` URLs (300 seconds by default, 900 seconds hard maximum). URLs
are issued only after authorization and active-rights checks and are never
stored, fingerprinted, placed in manifests, or logged with their query string.

The local cache lives outside the repository at
`$XDG_CACHE_HOME/butterflylens/v1`, uses `0700` directories and `0600` files,
and verifies SHA-256 on every read. Cache writes use the same fsync-and-rename
protocol. Review media expires after one hour; other private media expires
after at most one day. A removal case bypasses TTL and purges immediately.

## Rights and removal

Object crops exist only when transformation and inference are explicitly
permitted. Public thumbnails additionally require public-display and
redistribution permission; internal access never implies publication.
YOLOE and BioCLIP are unfinished in this goal, so the layout reserves their
classes but no crop, full-frame input, or embedding is created.

On a removal request, quarantine the source association first, stop signing,
remove public projections, and traverse every derivative, review, map, report,
release, export, mirror, and cache dependency. Delete all B2 versions when no
independent active rights basis remains. Preserve only a non-personal
fingerprinted tombstone and completion receipt. Removable media must not use
compliance Object Lock because retention could prevent the 24-hour workflow;
lifecycle rules are cleanup assistance, never completion evidence.

Official B2 behavior frozen for this contract was reviewed on 2026-07-18:

- S3-compatible object ACLs are bucket-level and object tagging is incomplete;
- presigned URLs are supported;
- lifecycle expiration hides a current version and noncurrent-version rules
  delete old versions; and
- Object Lock prevents modification or deletion until retention expires.

The layout does not create buckets or grant credentials. Deployment names and
retention durations remain environment configuration subject to the same
rights and security gates.
