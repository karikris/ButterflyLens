# ALA baseline occurrence evidence

Snapshot `ala-papilionoidea-au-20260717-d33d4d367525` is the frozen public
ButterflyLens selection of ALA occurrence evidence for the accepted
Papilionoidea root in processed country `Australia`. It is a selected baseline,
not complete truth, a biological absence model, or human verification of the
provider taxon labels.

## Frozen acquisition

The asynchronous ALA download was submitted at `2026-07-17T17:47:54Z` and
retrieved at `2026-07-17T17:49:34Z`. Its public request fingerprint is
`f64311fd0551cd510db13f8eedcfe17213ec0eba460b29e6454b82953c131aa1`.
The exact query and filters are:

```text
q=lsid:https://biodiversity.org.au/afd/taxa/3ebff933-1678-4cbd-8d85-05c4bc48487c
fq=country:Australia
fq=license:("CC-BY" OR "CC-BY 3.0 (Au)" OR "CC-BY 3.0 (Int)" OR "CC-BY 4.0 (Au)" OR "CC-BY 4.0 (Int)" OR "CC-BY-Int" OR "CC0" OR "PDM")
disableAllQualityFilters=true
```

No coordinate or basis-of-record filter was applied. Provider default quality
filters were disabled so the public processed rows and their quality assertions
could be retained and evaluated explicitly. This does not endorse rows that ALA
flags as suspect.

Only attribution-only CC BY variants, CC0, and Public Domain Mark rows enter
this public frozen artifact. NonCommercial, NoDerivatives, ShareAlike,
unspecified, record-level-unspecified, and `other` licence values are outside
this selected public snapshot. Exclusion is a downstream rights decision, not a
claim that those provider records are invalid.

The provider archive contains 236,897 rows from 53 data resources. It preserves
the ALA-generated `citation.csv`, `README.html`, and `headings.csv` alongside
the selected occurrence CSV. The receipt records 84 provider/resource citation
entries, per-resource row and licence counts, DOI/citation text where supplied,
data-generalisation and information-withheld notices, and the archive member
inventory.

## Coordinates, sensitivity, and evidence categories

The archive contains only the coordinates and sensitivity state available from
ALA's public download. ButterflyLens must never reconstruct withheld locations
or imply more precision than a generalized record supports.

For this exact snapshot:

- 236,303 rows have ALA spatial-validity value `true` and 594 have `false`;
- 6,277 rows have no processed latitude/longitude;
- 265 rows are marked `generalised`, 115 `alreadyGeneralised`, and 236,517 have
  no supplied sensitive flag;
- basis-of-record values comprise 81,630 human observations, 40 machine
  observations, 2,892 material samples, 1,189 observations, 21,695 occurrences,
  and 129,451 preserved specimens.

These are source-snapshot counts, not quality conclusions. Coordinate, record
type, date, and sensitive-data eligibility are added as explicit normalized
fields in subtask 2.3.2. Sensitive rows remain eligible only at a geographic
resolution consistent with their public generalization.

## Normalized occurrence artifact

`ala_baseline_occurrences.parquet` contains all 236,897 selected source rows in
ALA record-ID order under the closed
`butterflylens-ala-normalized-occurrence/v1` schema. It uses four bounded row
groups, Zstandard compression, and a semantic fingerprint per row. The
artifact is 23,596,954 bytes with SHA-256
`5f2d64e2993cedd8409fedbb3bc9485cef6e8d511005003332375bd134128b81`.

Normalization preserves provider occurrence/taxon/resource identity,
processed and raw basis of record, public coordinates and uncertainty, event
date, record licence and rights, sensitive/generalisation state, ordered
quality assertions, state/territory, IBRA, LGA, and source reference. A stable
ButterflyLens taxon key is attached only for an exact ALA `taxonConceptID`
crosswalk match: 226,613 rows match and 10,284 remain explicit unmatched
provider taxon assertions. Neither state is human verification.

Spatial eligibility is deliberately separate from retention. The normalized
snapshot has 229,652 rows eligible at all configured public resolutions, 375
publicly generalized rows eligible only for the later coarse cell, 6,277 rows
excluded from spatial aggregation because processed coordinates are missing,
and 593 otherwise coordinate-bearing rows excluded as spatially suspect. One
of the 594 source rows with `spatiallyValid=false` is already counted under the
higher-priority missing-coordinate exclusion; the source flag itself remains
preserved on every row.

`temporal_evidence_band` distinguishes pre-1900 and 1900–1949 historical
evidence, later periods, undated/unparseable values, and dates outside the
declared 1600-to-snapshot-year range. These bands are transparent analytical
conventions, not provider record types or evidence of biological absence.
`evidence_category` separately retains human observation, machine observation,
unspecified observation, material sample, preserved specimen, fossil specimen,
unspecified occurrence, and fallback states; a category with zero selected
rows is still part of the contract.

Rebuild the normalized artifacts without provider access:

```bash
uv sync --frozen
uv run python scripts/build_ala_baseline.py normalize \
  --archive data/packs/australian_butterflies/v1/ala/sources/ala_occurrence_download.zip \
  --receipt data/packs/australian_butterflies/v1/ala/ala_snapshot_receipt.json \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --output data/packs/australian_butterflies/v1/ala/ala_baseline_occurrences.parquet \
  --schema-output data/packs/australian_butterflies/v1/ala/schemas/ala_baseline_occurrence.schema.json \
  --manifest data/packs/australian_butterflies/v1/ala/ala_normalization_manifest.json \
  --generated-at 2026-07-17T18:15:26Z
```

The checked-in Parquet, schema, and normalization manifest reproduce
byte-for-byte under the locked Python/PyArrow environment.

## Contextual geography

The download requests ALA-indexed `cl11185` (IBRA version 7 regions) and
`cl11170` (Local Government Areas 2023). The frozen ALA spatial-layer receipt
identifies DCCEEW and the Australian Bureau of Statistics as their respective
sources and CC BY 4.0 as the licence. The LGA values are ABS Mesh Block
approximations for statistical use, not official legal boundaries. No boundary
geometry is copied into this snapshot.

`ala_baseline_cells.parquet` materializes 23,744 deterministic aggregate rows:
one Australia row, 9 ALA `stateProvince` assertions, 87 IBRA v7 assertions,
532 LGA 2023 statistical approximations, 630 occupied H3 resolution-3 cells,
4,986 occupied resolution-5 cells, and 17,499 occupied resolution-7 cells.
The 230,027 spatially eligible source rows contribute to the Australia and
coarse H3 rollups; 229,652 all-resolution-eligible rows contribute to regional
and local H3. Missing scope labels are counted in
`ala_aggregation_manifest.json` rather than silently assigned.

The configured H3 levels are coarse 3, regional 5, and local 7, following the
pinned BioMiner geography contract. All 375 publicly generalised rows may
contribute only to Australia, their supplied state/territory assertion, and H3
resolution 3. They never enter IBRA, LGA, regional H3, or local H3 aggregates.
H3 centers are derived cell centers, not occurrence coordinates. Every row
retains a digest over the exact ordered normalized occurrence fingerprints that
contributed to it. Counts remain selected ALA baseline occurrence evidence;
an unoccupied cell is not evidence of biological absence.

Rebuild the aggregate artifact, schema, and manifest without provider access:

```bash
uv run python scripts/build_ala_baseline.py aggregate \
  --occurrences data/packs/australian_butterflies/v1/ala/ala_baseline_occurrences.parquet \
  --normalization-manifest data/packs/australian_butterflies/v1/ala/ala_normalization_manifest.json \
  --output data/packs/australian_butterflies/v1/ala/ala_baseline_cells.parquet \
  --schema-output data/packs/australian_butterflies/v1/ala/schemas/ala_baseline_cell.schema.json \
  --manifest data/packs/australian_butterflies/v1/ala/ala_aggregation_manifest.json \
  --generated-at 2026-07-17T18:50:27Z
```

## Dataset and snapshot publication

`ala_dataset_manifest.parquet` contains one row for each of the 53 selected
ALA data resources. Exact resource UID joins reconcile every selected row and
processed licence count with the resource-level citation entry. DOI, citation,
rights, data-generalisation, information-withheld, download-limit, provider,
and resource fields remain explicit. The other 31 provider, collection, and
institution citation entries remain fingerprinted in
`ala_snapshot_receipt.json`; no unsupported hierarchy is inferred between
them and the resource rows.

Conservative citation-rights screening flags `dr1097`, `dr30019`, and `dr635`,
covering 16,753 selected rows, because their citation text contains
NonCommercial terms despite the allowlisted processed licences on selected
rows. This flag is not a legal conclusion. Under ButterflyLens's
unknown-is-blocking rule, downstream public-product and commercial use is
blocked until those resources are resolved or excluded. Four resource
citations describe information withheld and one describes data
generalisation; the exact text remains available and never authorizes finer
coordinates or reconstruction.

`ala_snapshot_manifest.json` is written after the dataset artifact and binds
the archive, receipt, attribution, normalized occurrences, aggregate cells,
three Parquet schemas/manifests, exact counts, rights-review state, and build
versions. The root pack manifest exposes this snapshot without relabelling ALA
provider assertions as human verification or unoccupied cells as absence.

Rebuild the publication artifacts without provider access:

```bash
uv run python scripts/build_ala_baseline.py publish-manifest \
  --receipt data/packs/australian_butterflies/v1/ala/ala_snapshot_receipt.json \
  --attribution data/packs/australian_butterflies/v1/ala/ala_attribution.json \
  --occurrences data/packs/australian_butterflies/v1/ala/ala_baseline_occurrences.parquet \
  --normalization-manifest data/packs/australian_butterflies/v1/ala/ala_normalization_manifest.json \
  --cells data/packs/australian_butterflies/v1/ala/ala_baseline_cells.parquet \
  --aggregation-manifest data/packs/australian_butterflies/v1/ala/ala_aggregation_manifest.json \
  --dataset-output data/packs/australian_butterflies/v1/ala/ala_dataset_manifest.parquet \
  --dataset-schema-output data/packs/australian_butterflies/v1/ala/schemas/ala_dataset_manifest.schema.json \
  --snapshot-manifest data/packs/australian_butterflies/v1/ala/ala_snapshot_manifest.json \
  --pack-manifest data/packs/australian_butterflies/v1/manifest.json \
  --generated-at 2026-07-17T19:14:01Z
```

## Reproduction

Submitting a new provider snapshot is an explicit network action. ALA's bulk
service requires a contact email; the command does not persist it, requests no
notification, and does not mint a DOI:

```bash
python3 scripts/build_ala_baseline.py acquire-snapshot \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --output-dir data/packs/australian_butterflies/v1/ala \
  --email "$ALA_DOWNLOAD_EMAIL"
```

Default tests never submit or poll a provider job. `ala_snapshot_receipt.json`
contains the request, policy, source-contract hashes, dataset/licence inventory,
source archive checksum, and snapshot fingerprint. `ala_attribution.json`
contains the public attribution and citation requirements. A new acquisition is
a new snapshot; it must not silently overwrite a submitted competition bundle.
