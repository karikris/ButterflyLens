# ButterflyLens ALA contribution preparation

Policy version: `butterflylens-ala-contribution-policy:v1.0.0`

Last reviewed: 18 July 2026

## Preparation boundary

ButterflyLens can prepare one deterministic Atlas of Living Australia (ALA)
handoff archive from an exact [Darwin Core evidence package](DARWIN_CORE_EXPORT.md).
Preparation does not publish an occurrence, submit data, accept provider terms,
open a support request, send email, upload a file, or establish ALA acceptance.
There is intentionally no submission option or network client in the builder.

The package is `ready_for_human_submission` only when every provider check has
an explicit evidence fingerprint and the representative quality review has no
declared blocker. Otherwise it records either
`blocked_pending_provider_requirements` or `blocked_quality_review`. Every
state still carries `prepared_not_published`, `not_submitted`, and
`human_submission_required`.

No production contribution archive or ALA submission is claimed by this
repository. The committed tests use a one-record synthetic software fixture
and an `.invalid` administrative contact.

## ALA requirements represented

Current [ALA dataset-sharing guidance](https://support.ala.org.au/support/solutions/articles/6000261427-sharing-a-dataset-with-the-ala)
prefers Darwin Core Archive and requires title, description, licence,
administrative contact name and email, creator, citation, and provider URL.
The prepared `eml.xml` includes each of those fields plus purpose, methods,
keywords, and geographic, taxonomic, and temporal scope.

The current [ALA Terms of Use](https://www.ala.org.au/terms-of-use/) say that a
detailed or extensive dataset should have an ALA Data Provider Agreement. The
checklist therefore cannot become ready while that agreement, authority,
licence, attribution, sensitive-data review, administrative contact, update
and removal process, or third-party media terms remain pending. A passed check
must cite a SHA-256 evidence URN; a boolean alone cannot claim completion.

ALA guidance accepts CC0, CC BY, and CC BY-NC and states a preference for those
Creative Commons licences. This policy accepts their current 1.0/4.0 forms for
the dataset records. It never overwrites the licence, creator, rights holder,
attribution, or source link attached to an individual media record.

## Package contents

The contribution remains a Darwin Core Archive. It preserves every byte of the
verified source core, extensions, `meta.xml`, and source evidence manifest,
then adds:

| Requirement | Artifact |
|---|---|
| dataset metadata | `eml.xml` |
| licence | `licence.json` |
| attribution | `attribution.txt` |
| provider agreement checklist | `provider-agreement-checklist.json` |
| quality report | `quality-report.json` |
| evidence manifest | `ala-evidence-manifest.json` |

The final manifest binds both source archive identities, every inherited and
generated file checksum, record count, preparation gates, artifact paths,
privacy properties, fixed member order, code SHA, and canonical package
fingerprint. It is written last. Fixed timestamps, permissions, compression,
and ordering make identical governed input byte-identical.

The quality report derives record count, release-receipt count, and
representative-audit fingerprints from the verified Darwin Core archive. It
does not invent precision, treat targeted failure discovery as a population
sample, interpret model scores as probabilities, claim absence from no
detection, or claim provider acceptance.

## Offline operator workflow

An authorised operator can prepare a private handoff locally:

```bash
uv run python scripts/prepare_ala_contribution.py \
  --input governed-ala-preparation.json \
  --darwin-core-archive butterflylens-evidence.zip \
  --output butterflylens-ala-handoff.zip
```

The exact input names the expected source archive SHA-256 and semantic package
fingerprint. The builder rejects unknown fields, archive tampering, unexpected
members, unsafe paths, encrypted files, wrong checksums, incompatible policy
states, missing release receipts, and metadata identity drift. It writes
atomically and prints a local preparation receipt. It cannot submit.

The EML includes an administrative contact because ALA requires one. The final
manifest therefore marks the archive `private_operator_handoff` and
`contains_administrative_contact`; it must not be published as a public website
asset. The Darwin Core evidence itself continues to contain only generalized
public H3 locations, fingerprint-only review evidence, and media metadata—no
raw coordinates, reviewer identity, or media bytes.

BioMiner's active GBIF/Flickr work remains outside this package until it
provides an immutable governed handoff. The rebuilt ButterflyLens ALA baseline
remains authoritative. No Flickr API call, YOLOE, or BioCLIP work is part of
ALA package preparation.
