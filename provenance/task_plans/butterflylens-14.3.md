# ButterflyLens Task 14.3 plan

Task: Add ALA submission preparation.

Commit: `feat(export): prepare ALA contribution package`

## Scope

- Prepare one deterministic, offline ALA contribution archive from an exact
  ButterflyLens Darwin Core evidence archive.
- Add EML dataset metadata, an explicit dataset licence, attribution,
  provider-agreement checklist, quality report, and evidence manifest.
- Verify every inherited member and preserve the prepared-not-published,
  generalized-location, fingerprint-only-review, and no-media-byte boundaries.
- Distinguish a package ready for human submission from one blocked by pending
  provider agreement or other human attestations.
- Provide an atomic local writer and a strict CLI with no network or submission
  capability.

## Verification

- Fixture-backed archive, EML, licence, attribution, checklist, quality,
  inherited-checksum, tamper, privacy, determinism, exact-parser, and no-submit
  tests.
- Full Python, web, Edge, rights, licensing, provenance, and safety gates.
- Exact commit, non-force `main` push, exact-SHA Pages and served-policy check.

## Current requirements and boundaries

Current ALA guidance prefers Darwin Core Archive and requires title,
description, licence, administrative contact name/email, creator, citation,
and provider URL metadata. A detailed dataset should have an ALA Data Provider
Agreement. Preparation records these as exact evidence-bearing checks; it does
not infer approval, send email, open an issue, upload an archive, or call a
provider endpoint.

GitHits remains disabled. BioMiner remains active and supplies no immutable
GBIF handoff, so no partial BioMiner or external Flickr-fetch output is copied.
No Flickr API, provider submission, YOLOE, or BioCLIP work occurs.
