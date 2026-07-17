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

## Contextual geography

The download requests ALA-indexed `cl11185` (IBRA version 7 regions) and
`cl11170` (Local Government Areas 2023). The frozen ALA spatial-layer receipt
identifies DCCEEW and the Australian Bureau of Statistics as their respective
sources and CC BY 4.0 as the licence. The LGA values are ABS Mesh Block
approximations for statistical use, not official legal boundaries. No boundary
geometry is copied into this snapshot.

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
