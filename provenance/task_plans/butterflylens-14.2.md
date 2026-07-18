# ButterflyLens Task 14.2 plan

Task: Add Darwin Core export.

Commit: `feat(export): generate Darwin Core evidence package`

## Scope

- Generate a deterministic Darwin Core Archive with one Occurrence core and
  explicit Taxon, Event, Location, Identification, MeasurementOrFact, Media,
  Provenance, Review, and Quality extensions.
- Admit only exact release-ready receipt lineage and keep package preparation
  distinct from occurrence publication or provider submission.
- Export generalized public H3 location only, never raw coordinates.
- Retain media licence, rights holder, attribution, source link, release gate,
  review, quality, and evidence-packet fingerprints without reviewer identity.
- Write an exact checksum/row-count manifest last and expose an atomic writer.

## Verification

- Fixture-backed archive structure, meta.xml mapping, row linkage, rights,
  privacy, release-gate, determinism, checksum, and safe-ID tests.
- Full Python, web, Edge, rights, licensing, provenance, and safety gates.
- Exact commit, non-force `main` push, exact-SHA Pages and served-policy check.

## Standards and boundaries

The current TDWG Darwin Core terms, conceptual model, and Text/Darwin Core
Archive guide define the external vocabulary and archive shape. The newer
Darwin Core Data Package guide was reviewed, but its reserved relational table
model flattens some of the ten explicitly requested domains; this task uses the
normative Text core/extension model so every requested domain remains separately
inspectable. GitHits remains disabled.

BioMiner's published coordination record remains active and supplies no
immutable GBIF handoff, so no partial BioMiner or external Flickr-fetch output
is copied. No Flickr API, provider submission, YOLOE, or BioCLIP work occurs.
