# ButterflyLens media rights and removal policy

Policy version: `butterflylens-media-rights:v1.0.0`

Last reviewed: 18 July 2026

Status: **prelaunch workflow; the private request channel and legal operator
must be published before community writes or public media display are enabled**.

## What can be requested

A photographer, owner, rights holder, authorised agent, provider, privacy
claimant, or person acting on a legal basis may request a Flickr photo or other
controlled media object to be removed. A request may concern takedown, privacy,
licence or attribution correction, or a source that has become unavailable.

Do not submit contact details, identity documents, private evidence, or the
substance of a rights claim in a public GitHub issue. ButterflyLens does not
yet publish a private operator-controlled request channel, so it must not
claim that a live form or operational response service exists.

## Fail-closed handling

An accepted intake immediately disables download, model inference, display,
and redistribution for the target. Flickr requests quarantine every controlled
object for the photo and its public-display cache. Other requests quarantine
the target and its descendants. Existing signed URLs cannot be recalled, so
unexpired signing receipts are inventoried for expiry or invalidation and no
new URL may be issued for quarantined media.

Public release candidates are suppressed when their media, any media ancestor,
or their Flickr source is subject to a request. Quarantine is not silently
reversed after an unverified request: restoration requires a separate, current
provider and rights revalidation with its own evidence.

## Removal graph and completion

The workflow inventories every known dependency by kind and immutable
fingerprint, including source records, caches, public displays, thumbnails,
model inputs, embeddings, reviews, public cells, evidence packets, exports,
mirrors, and signed URLs. A service worker may add dependencies discovered
during traversal, but cannot delete or rewrite the ledger.

Each action records the actor class, time, reason, downstream effect, evidence
fingerprints, and an event fingerprint. A curator can mark authority verified
or rejected. Completion is allowed only after authority is verified, the
worker supplies the exact canonical dependency-inventory fingerprint, and
every dependency has one terminal outcome: purged, removed, invalidated, or
retained under independently verified rights. The public status reveals no
requester identity or private claim detail.

For Flickr material, the deadline is exactly 24 hours from receipt. This
implements the [Flickr API Terms of Use](https://www.flickr.com/help/terms/api),
which require an application to remove a user's photos or other information
within 24 hours when the owner asks and to reflect private-state changes as
soon as reasonably possible. Flickr users retain ownership and their terms or
licences continue to control permitted use.

## Privacy, appeals, and retained evidence

Requester identity, contact reference, private detail, and authority evidence
belong in a private table or an approved external case system. Curators see
only what they need to assess and resolve the request. Public and ordinary
authenticated readers never receive those fields.

The append-only audit may retain a non-content tombstone, target and dependency
fingerprints, decisions, and proof of action where proportionate. It does not
justify keeping removed image bytes, private claim documents, or public owner
profiles. A declined request and any later appeal are recorded rather than
overwriting history. Applicable legal obligations and the
[community privacy policy](PRIVACY.md) continue to apply.
