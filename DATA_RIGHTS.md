# Data, API, Media, and Community Rights Audit

Audit date: `2026-07-17`

ButterflyLens separates permission to query an API, permission to store metadata, permission to download media, permission to transform or run models over media, permission to display media, and permission to redistribute evidence. Passing one of these gates never implies the others.

This document is engineering evidence, not legal advice. Provider terms can change; release requires a fresh verifier run against the stored source/terms snapshots.

## Gate outcome

No provider credential, boundary geometry, source-image collection in Git,
human-verified reference bank, community review, or export is stored in
ButterflyLens at this audit. Permitted reference source objects exist only in
the ignored local cache. A selected ALA occurrence snapshot now exists under
the controls below. The remaining statuses define what must be true before
later artifacts become eligible.

| Source | Current status | Release gate |
| --- | --- | --- |
| Flickr API | No key configured or call made. | Register the application/use, accept current API terms, identify commercial status, activate the single global budget, and pass per-photo rights/display/removal checks. |
| Atlas of Living Australia (ALA) | Selected evidence snapshot frozen on 17 July 2026; downstream public-product release remains blocked for three dataset-rights conflicts. | Preserve the exact query/archive fingerprint, contributing-resource citations, per-row licence, quality/sensitivity state, dataset review state, and downstream eligibility. Resolve or exclude the flagged resources and recheck terms before release. |
| GBIF | Bounded candidate-reference metadata imported; compatible media licences classified, but every GBIF media host remains download-blocked and no DOI was minted. | Approve each required provider host and retain dataset, publisher, occurrence, media, creator, licence, attribution, and source fingerprints before any later byte acquisition. |
| iNaturalist | Automated `cc0`/`cc-by`, exact-taxon, host, download, and decode gate complete: 2,906 provisional objects valid and four HTTP 404 rows quarantined. | Keep every candidate unreviewed, enforce the commercial-AI-training prohibition, preserve creator/licence/source evidence, and complete later duplicate, routing, embedding, and human-review gates. |
| ABS ASGS boundaries | ALA-indexed LGA 2023 contextual values selected; no geometry copied. | Retain the ALA layer metadata receipt, CC BY 4.0 attribution, and statistical-boundary qualification; a future geometry file requires its own checksum and gate. |
| DCCEEW IBRA 7 | ALA-indexed IBRA v7 region values selected; no geometry copied. | Retain the ALA layer metadata receipt and CC BY 4.0 attribution; a future geometry file requires its own checksum and gate. |
| Community reviews/comments | No accounts, terms acceptance, or review event exists. | Publish participant terms/privacy/moderation, collect versioned acceptance, and bind every event to its licence/consent version. |

## Rights manifest contract

Every dataset, API response, source object, media object, boundary, review event, derivative, public thumbnail, model input, and export must resolve to a rights record containing at least:

- immutable ButterflyLens fingerprint and source identity;
- provider, source URL or endpoint, source object/dataset identifier, and retrieval timestamp;
- rights holder and creator where available;
- exact licence code, licence URI/version, provider terms URI/version or snapshot hash, and attribution text;
- allowed/blocked states for metadata storage, download, cache, transformation, model inference, model training, public display, redistribution, commercial use, and export;
- privacy, sensitive-location, cultural-authority, embargo, and jurisdiction constraints;
- cache expiry or revalidation time;
- current visibility, removal request, takedown deadline, quarantine, and downstream invalidation state;
- human/legal decision evidence for any exception.

Unknown is a blocking value, never equivalent to allowed. Source identity and rights state remain attached when records are deduplicated, aggregated, embedded, reviewed, or exported.

## Flickr

Authoritative sources inspected:

- [Flickr API Terms of Use](https://www.flickr.com/help/terms/api)
- [Flickr Terms and Conditions](https://www.flickr.com/help/terms)
- [Flickr API developer limits](https://www.flickr.com/services/developer/api/)

### API and application controls

- The documented provider guidance says applications staying below 3,600 queries per hour across the whole key should be acceptable. ButterflyLens deliberately uses a lower hard envelope of 3,500, a normal planned ceiling of 3,000, a reserve of at most 500, and a 100-call safety remainder.
- One token bucket must cover every method, retry, comment, manual action, and judge action. Multiple keys or identities must never be coordinated to evade limits.
- A public release must prominently show: “This product uses the Flickr API but is not endorsed or certified by SmugMug, Inc.”
- Do not use the Flickr logo without written permission, do not imply endorsement, and do not replicate Flickr’s essential user experience.
- Publish a privacy disclosure for visitor and provider data.
- The public application must display no more than 30 Flickr user photos per page.
- Commercial use requires the appropriate Flickr application/key determination. ButterflyLens currently has no commercial or non-commercial API approval evidence.

### Photo and owner controls

- Flickr/SmugMug does not own user photos; the user/photographer does. API access does not override an all-rights-reserved notice, Creative Commons licence, private state, or owner-specific condition.
- Discovery metadata may be retained only under the API/provider terms and its source identity. A photo enters download, transformation, inference, display, or redistribution lanes only when the rights manifest records a compatible basis for that exact use.
- Show the source link, photographer/owner attribution, exact photo licence, and required Flickr notice with each public display context.
- Cache photos only for a reasonable service period. Revalidate visibility/licence and remove cached copies that become private as soon as reasonably possible.
- Remove a Flickr user’s photo or other information from the application within 24 hours of an owner request; quarantine downstream thumbnails, model inputs, embeddings, reviews, public cells, packets, and exports until the removal graph is resolved.
- Never include private media. Do not use Flickr data for unlawful discrimination, surveillance, rights violations, or other prohibited purposes.

The discovery claim is limited to: “All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.” It is never an exhaustive Flickr claim, a species label, or permission to reuse an image.

## Atlas of Living Australia

Authoritative sources inspected:

- [ALA Terms of Use](https://www.ala.org.au/terms-of-use/)
- [ALA Sensitive Data Service](https://sds.ala.org.au/)

ALA aggregates content from data providers. ButterflyLens must:

- retain occurrence ID, dataset/provider identity, provider-specific licence, attribution wording, source link, retrieval date, and the frozen query/snapshot manifest;
- comply with each data provider’s licence rather than assuming one blanket ALA licence;
- acknowledge and attribute the relevant providers in derived products and publications;
- preserve quality assertions, coordinate uncertainty, sensitive/generalized state, basis of record, dates, and provider restrictions;
- never reverse, refine, or expose coordinates beyond the permitted generalized resolution;
- re-run rights and sensitivity checks before public cells, record drilldowns, exports, or contribution packets;
- make no guarantee of completeness or accuracy and never promote an ALA comparison into a biological absence claim.

`ALA baseline occurrence evidence` means a versioned selected snapshot, not all ALA knowledge.

The frozen public snapshot
`ala-papilionoidea-au-20260717-d33d4d367525` uses the accepted ALA
Papilionoidea root, processed country `Australia`, no coordinate or
basis-of-record acquisition filter, and disabled default quality filters so
quality assertions remain explicit. Its public rights allowlist is limited to
CC0, Public Domain Mark, and attribution-only CC BY variants. NonCommercial,
NoDerivatives, ShareAlike, unspecified, record-level-unspecified, and `other`
values do not pass the processed-record licence filter. This is a conservative
selection gate, not a statement about record validity or a substitute for the
dataset citation review.

The archive retains ALA's provider citation file, including per-resource DOI,
citation, rights, generalisation, information-withheld, download-limit, and row
count fields where supplied. It contains public processed occurrence metadata
only: no provider media is downloaded. The bulk service required a contact
email, but ButterflyLens requested no notification or DOI and does not persist
the email. The archive, provider API contracts, query policy, and attribution
are fingerprinted under `data/packs/australian_butterflies/v1/ala/`.

The dataset publication manifest joins all 53 selected data-resource UIDs to
their exact citation entries. Conservative text screening finds potentially
restrictive NonCommercial wording for `dr1097`, `dr30019`, and `dr635`, covering
16,753 selected rows. This is not a legal conclusion, but it is a blocking
downstream public-product and commercial-use review state under the
unknown-is-blocking rule. The selected snapshot remains preserved as evidence
with its exact processed licences and citation conditions; later public
projections must resolve or exclude those resources. Four citation entries
also describe information withheld and one describes data generalisation;
those texts remain verbatim and do not authorize reconstruction of withheld
information.

## GBIF

Authoritative sources inspected:

- [GBIF Data User Agreement](https://www.gbif.org/terms/data-user)
- [GBIF Terms and data licensing](https://www.gbif.org/terms)
- [GBIF citation guidelines](https://www.gbif.org/citation-guidelines)

ButterflyLens must retain publisher ownership identifiers with every forwarded record, comply with the licence selected by each publisher, and publicly acknowledge/cite publishers. Prefer DOI-bearing downloads; when APIs or combined sources are used, preserve dataset keys and register/cite a derived dataset where appropriate.

GBIF occurrence datasets may be CC0, CC BY, or CC BY-NC. The most restrictive applicable use gate survives aggregation. A record licence never automatically covers associated media: inspect and retain each image licence, creator, attribution, and parent occurrence citation separately. GBIF does not warrant data quality/completeness; reference-provider labels remain provisional evidence until reviewed.

## iNaturalist

Authoritative sources inspected:

- [iNaturalist Terms of Use](https://www.inaturalist.org/pages/terms)
- [iNaturalist API recommended practices](https://www.inaturalist.org/pages/api%2Brecommended%2Bpractices)
- [iNaturalist media-licence guidance](https://help.inaturalist.org/en/support/solutions/articles/151000169918)

Required controls:

- iNaturalist users retain ownership of their media. Observation data, images, and sounds have independently selectable licences; the default is CC BY-NC, and some items are all rights reserved or use other Creative Commons terms.
- Never infer media permission from an observation licence. Retain the exact creator, media licence, attribution, source, and parent observation for each item.
- All-rights-reserved media requires explicit permission for any ButterflyLens use beyond a source link/metadata allowed by the platform terms.
- Treat CC BY-NC as ineligible for a commercial lane; treat NoDerivatives and ShareAlike media as separate transformation/redistribution gates. Do not collapse all Creative Commons variants into “open”.
- The current terms prohibit use of iNaturalist data for commercial AI/ML/LLM training. ButterflyLens does not use iNaturalist data for commercial model training and must re-evaluate any later training, calibration, or fine-tuning proposal.
- Prefer observation exports or the DOI-bearing GBIF dataset for bulk acquisition. If the API is used, follow current guidance of about one request per second and around 10,000 requests per day, avoid coordinated IP evasion, use efficient page sizes/filters, and identify the application with an appropriate user agent.
- No API provider image is uploaded to a remote model service by default. Reference processing is local and only after the rights manifest permits the exact use.

## Reference images and derived model artifacts

ALA, GBIF, and iNaturalist observations are candidate reference evidence, not automatically verified reference images.

The Task 2.4.1 import uses pinned BioMiner commit
`d71bceabf75748a25df39d0025e8da907f295f8c` for 742 bounded GBIF and
iNaturalist queries across 371 exactly crosswalked species. It stores 12,980
provider-labelled observations and 24,329 media-candidate metadata rows, but
downloads zero image bytes and marks every media row unreviewed. Three taxon
conflicts, 45 quarantined media rows, and 1,651 GBIF rows awaiting the
automated licence gate cannot enter support. The 22,633 iNaturalist rows marked
allowed passed only the import-time `cc0`/`cc-by` photo-licence filter; that is
not taxonomic verification, decode validation, display approval, or final
reference admission. The archived checkpoint ledger records 769 requests and
27 recovered rate-limit retries. The frozen ALA snapshot remains candidate
observation evidence but contributes zero reference media because its source
contract did not capture media metadata; no URL or image label is inferred.

Task 2.4.2 links exact provider identities without collapsing their source or
rights evidence. It records 10,453 observation mirror groups and 93 media
mirror candidates. Five observation groups retain taxon conflicts and one
media candidate retains a `cc-by`/`cc-by-nc` licence conflict; all remain
blocked for resolution. Normalizing equivalent Creative Commons code and URL
spellings is comparison-only and does not broaden permitted use. Because no
media bytes are present, the linkage asserts neither byte equality nor
perceptual duplication, and it selects no canonical media row.

Task 2.4.3 admits only `cc0` and `cc-by` media with complete required
attribution into the automated download lane. NonCommercial, ShareAlike,
NoDerivatives, combined variants, missing, conflicting, and unrecognized
licences remain blocked; the policy makes no compatibility conclusion about
those terms. Exact taxon and mirror-conflict gates apply independently of
licensing. Provider-host approval is also independent: GBIF metadata may pass
the licence classifier while remaining blocked from download because its
publisher host has no approved policy. The current executable lane is limited
to HTTPS objects on iNaturalist's open-data host.

The selected lane caps each species at 20 independent observations and each
observer at 50 objects across the bank. Source bytes are content-addressed in
ignored local cache and are not committed. Checksums and decode evidence do
not broaden source rights, establish human verification, or authorize public
display. Cache loss remains a durability risk until permitted objects are
committed to the configured private object store.

The pinned download run selected 2,910 rows. It produced 2,906 valid local
decodes and quarantined four permanent HTTP 404 responses; no request retry was
needed. The valid rows reference 2,905 unique SHA-256 content identities and
1,127,087,982 content-addressed source bytes. One repeated content identity is
retained as separate source evidence. All 2,910 outcomes, including the four
failures, remain in the media-object inventory and command report. None is
human verified.

Task 2.4.4 does not substitute a detector for the unavailable audited YOLOE
runtime. All 2,906 decoded objects remain explicitly pending routing and the
four failed downloads remain separately quarantined. The readiness artifact
contains no detection, route, crop, model output, or source-image bytes and
does not broaden any source permission.

- CC0 and compatible CC BY media may enter allowed lanes with provenance and attribution.
- CC BY-NC, CC BY-ND, CC BY-SA, and combined variants require explicit use-specific gates; no blanket compatibility is asserted.
- All-rights-reserved, unknown, private, embargoed, culturally restricted, or removed media is blocked absent documented permission.
- Crops, resized images, thumbnails, full-frame transformations, embeddings, prototypes, and scores retain the source-media rights fingerprint and removal dependency.
- Public thumbnails are separately approved artifacts; internal model permission does not imply public-display permission.
- Model embeddings do not erase source rights. Removal propagation may invalidate or require rebuilding an embedding, prototype, score, review item, map cell, quality snapshot, release candidate, or export.
- ButterflyLens never redistributes provider training datasets or represents model weights as licensing their training images.

## Australian boundary datasets

### ABS ASGS

The [ABS copyright statement](https://www.abs.gov.au/website-privacy-copyright-and-disclaimer) provides website material under CC BY 4.0 International except identified exclusions and third-party material. As of the audit date, the [ASGS page](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs) identifies Edition 3 as the latest release and Edition 4 as a future release beginning `2026-07-22`.

For Task 2.3, ButterflyLens selects ALA contextual field `cl11170`, “Local
Government Areas 2023.” ALA's frozen layer metadata identifies the Australian
Bureau of Statistics source, Edition 3 download and metadata pages, and CC BY
4.0. It states that the values are Mesh Block approximations for statistical
use and do not match official legal boundaries. No ABS geometry, logo, Coat of
Arms, trademark, microdata, or third-party content is copied. Public
attribution uses “Source: Australian Bureau of Statistics” for the indexed
values; a future direct geometry download must receive a separate checksum and
product-level review.

### IBRA 7

For Task 2.3, ButterflyLens selects ALA contextual field `cl11185`, “IBRA
version 7 regions.” ALA's frozen layer metadata identifies the Department of
Climate Change, Energy, the Environment and Water as source and CC BY 4.0 as
the licence for this indexed layer. No IBRA geometry is copied. The contextual
value is a boundary/rollup assertion attached by ALA, not occurrence evidence,
identity evidence, or proof of absence; a future direct geometry download must
receive a separate checksum and resource-level review.

### Map services

No external basemap, tile provider, geocoder, glyph service, sprite service, or map telemetry provider is selected at this gate. Adding any one requires a separate terms, privacy, caching, attribution, and redistribution decision. A MapLibre software licence alone does not grant map-data rights.

## Community reviews, comments, and identity

Before write access opens, ButterflyLens must publish versioned participant terms, privacy, moderation, expert-verification, removal, and acceptable-use documents. Each accepted version binds:

- the contributor’s pseudonymous/private identity handling;
- a non-exclusive permission for ButterflyLens to store, process, display where configured, audit, reproduce in evidence packets, and export their review decision/comment with provenance;
- the contributor’s representation that comments and alternative evidence do not infringe rights or expose sensitive/private information;
- append-only scientific-audit handling, supersession instead of silent rewriting, and the distinction between account deletion, public pseudonymization, and retained de-identified integrity evidence;
- moderation, appeal, research use, and configured downstream-release scope.

No public-domain dedication or Creative Commons licence for community review text is assumed at Phase 0. Public/research licensing must be an explicit human decision before campaigns open. Reviewer reliability stays private and is never included in a public export.

## First Nations language names and knowledge

No First Nations name assertion is present or approved. Such assertions require the language, stable identifier where available, Country/community, source, cultural authority/publication, permitted use, query eligibility, attribution, and review state. No machine translation, invented name, pan-Aboriginal generalization, query use, or public release is permitted without the relevant authority and purpose-specific approval. Open-data defaults do not override Indigenous authority. The complete field, review-state, independent-permission, query, correction, and withdrawal gates are defined in [First Nations Language-Name Governance](FIRST_NATIONS_NAMES.md).

## Removal and downstream invalidation

Every removal request receives a stable case ID, requester/authority basis, received timestamp, provider deadline, affected fingerprints, quarantine state, resolution, appeal state, and completion evidence. The removal graph must reach source cache, public display, derivatives, model artifacts, review queues, maps, quality outputs, release packets, exports, mirrors, and signed URLs.

Audit events remain append-only, but removed copyrighted/private content is not retained publicly merely to preserve history. Evidence ledgers may retain the minimum non-content tombstone and cryptographic identifiers permitted by law and policy.
