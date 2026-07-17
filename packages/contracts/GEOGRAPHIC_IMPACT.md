# Geographic-impact contract

ButterflyLens compares evidence in Australian H3 cells without turning a map
symbol into a biological conclusion.

## Evidence layers

- **ALA baseline occurrence evidence** is a rights-checked, sensitivity-aware,
  conservatively reconciled snapshot. It is not an exhaustive range.
- A **Flickr discovery candidate** is admitted by the published search plan. A
  query association, source label, comment, geographic cluster, or model score
  does not establish the depicted taxon or an occurrence.
- A **community-reviewed candidate** has an effective append-only review event
  but may remain uncertain, non-target, or blocked.
- A **human-supported candidate** has the configured decisive human evidence.
  It is not automatically release-ready.
- A **release-ready occurrence candidate** passes the configured taxonomic,
  review, coordinate, duplicate, rights, quality, provenance, and release
  gates. It remains a candidate until an authorized downstream publisher
  accepts it under its own process.

The public layer language is therefore potential coverage-gap cell,
human-supported additional cell, and release-ready additional cell. A
candidate-only cell is not a new occurrence, confirmed range extension,
knowledge gain, or proof that the taxon is absent from ALA or Australia.

## Count and availability semantics

Every count has an explicit state:

- `available` carries a measured non-negative integer and no unavailable reason;
- `unavailable`, `withheld`, and `not_applicable` carry `null` plus a reason.

Zero is valid only in the available state. Missing provider snapshots, blocked
rights, failed processing, sensitive-data withholding, or unsupported joins
must never be encoded as zero.

Impact flags likewise separate an available `true` or `false` from an
unavailable `null`. A false flag says the configured deterministic condition
was not met in the selected snapshots; it does not say the corresponding
biological phenomenon is absent.

## Spatial and provider rules

- Every cell binds grid name, H3 version, resolution, source precision, target,
  project, run, snapshots, provider union, review projection, quality state,
  and evidence fingerprints.
- Fine coordinates may be rolled up to a coarser parent. Coarse or generalized
  evidence may not be assigned to an invented finer child.
- Withheld source coordinates stay withheld. The public contract contains no
  raw coordinate field and must not be used to reverse engineer a location.
- ALA, GBIF, and iNaturalist relationships are reconciled before baseline
  counts. An iNaturalist observation delivered through GBIF is not blindly
  added to an independent direct snapshot.
- Provider absence or a missing direct snapshot is unavailable, not zero.

## Live and submitted snapshots

`submitted` binds the immutable competition source commit. `live` binds the
latest admitted append-only projection plus a worker-heartbeat fingerprint.
The live snapshot can truthfully be stale or unavailable while the submitted
snapshot and last committed data remain queryable.

The map and synchronized table consume the same query and snapshot
fingerprints. WebGL is an enhancement; exact values, drilldown, record links,
review actions, and exports remain available in the non-WebGL path.
