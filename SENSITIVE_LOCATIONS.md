# Sensitive butterfly location policy

Policy version: `butterflylens-sensitive-location-policy:v1.0.0`

Status: implemented as a fail-closed publication gate

Last updated: 18 July 2026

ButterflyLens protects sensitive butterfly locations at the public map and
release boundary. A provider making a location available does not by itself
authorize ButterflyLens to publish that location at its source precision.
Every public location must have a versioned policy decision, exact provider
permission evidence, a materialized permitted scope, and an append-only
publication receipt.

This is a product data-handling policy, not legal advice and not a claim that a
taxon is biologically present or absent from any place.

## Non-negotiable rules

- **Unknown means withheld.** Unknown taxon sensitivity, unknown provider
  permission, missing lineage, missing resolution mapping, or a missing policy
  receipt prevents the map or release row from being read publicly.
- No public table, policy receipt, moderation record, analytics event, model
  prompt, comment, or log may contain source occurrence latitude or longitude.
- Public geometry is a pre-materialized named scope or H3 cell. ButterflyLens
  does not derive or reveal a finer cell at read time.
- The strictest ceiling wins across taxon policy and every provider location
  used for the public target.
- A sensitive taxon can be `generalised` or `withheld`; it cannot publish an
  `exact` source location.
- A versioned rule must explicitly allow the public scope and set a minimum
  aggregate record count. No count threshold is silently invented.
- Generalisation does not verify taxon identity. An empty public cell is not
  evidence of biological absence.
- Curators and workers must not infer, reconstruct, reverse-geocode, or combine
  public and private fields to recover a protected source location.

## ALA boundary

Only ALA public processed coordinates and provider-supplied sensitivity state
may enter the rebuilt baseline. ButterflyLens preserves ALA Sensitive Data
Service generalisation and information-withheld notices and never requests a
protected coordinate merely to improve the public map.

The authoritative rebuilt snapshot demonstrates the current materialization
rule. Its 375 publicly generalised rows contribute only to Australia, their
provided state/territory assertion, and H3 resolution 3. They contribute to no
IBRA, LGA, H3 resolution 5, or H3 resolution 7 aggregate. A later snapshot
must produce new fingerprinted provider constraints and receipts; this
precedent must not be assumed to authorize a different resolution.

## Flickr boundary

Flickr geo permissions and the photo's public geo state control whether a
Flickr location may be used. A public photo is not proof that all of its geo
fields are public. Non-public geo, absent geo, and geo excluded from the target
cannot contribute to public geometry.

Flickr accuracy is retained as provider evidence on the private constraint.
**No accuracy-to-H3 guess** is allowed. Using a Flickr location requires an
explicit reviewed mapping version that converts the provider accuracy and
permission evidence to a maximum public H3 resolution. No Flickr API call is
part of this policy implementation.

## Publication receipt

The service role writes two immutable ledgers:

1. a provider constraint binds ALA or Flickr snapshot fingerprints, disclosure
   state, whether its location was used, permission evidence, and an explicit
   maximum H3 resolution; and
2. a publication receipt binds one map/release target fingerprint, the project
   policy version, taxon sensitivity evidence, allowed scopes, minimum count,
   every provider constraint fingerprint, the effective strictest resolution,
   and the exact pre-materialized public scope.

Database row-level security denies anonymous access to a nominally public map
or release row until a matching `publish` or `generalised` receipt exists.
Authenticated community users cannot write, update, or delete either ledger.
Authorized curators may inspect the private evidence under project-scoped RLS;
only the service boundary may append it. Receipts are audit evidence and set
`scientific_claim_allowed = false`.

## Private source handling

If protected coordinates are ever legitimately obtained for upstream
processing, they remain in a separately authorized private evidence system
with least-privilege access, bounded retention, encryption, access logging, and
documented provider purpose. They do not enter the public PostgreSQL schema,
static replay, browser bundle, public object storage, downloadable export, or
community review payload.

Deletion, correction, breach handling, Flickr-owner data, and community data
rights remain governed by [the community privacy policy](PRIVACY.md). Reports
or abusive disclosure of a protected location are handled under
[the moderation workflow](MODERATION.md), without deleting the underlying
scientific audit event.

## Current provider references

- [ALA documentation](https://docs.ala.org.au/) describes public occurrence
  processing, sensitive-data generalisation, and protected API boundaries.
- [Flickr setLocation](https://www.flickr.com/services/api/flickr.photos.geo.setLocation.html)
  documents provider accuracy levels and geo privacy preferences.
- [Flickr setPerms](https://www.flickr.com/services/api/flickr.photos.geo.setPerms.html)
  documents explicit geo visibility permissions.
- [Flickr API terms and privacy guidance](https://www.flickr.com/services/developer/api/)
  require applications to respect member privacy settings.
