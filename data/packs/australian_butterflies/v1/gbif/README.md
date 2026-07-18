# GBIF Australian Papilionoidea occurrence evidence

This directory records and builds the operator-supplied GBIF occurrence
download `0004170-260715120105164` for Australian Papilionoidea.

Citation:

> GBIF.org (18 July 2026) GBIF Occurrence Download
> https://doi.org/10.15468/dl.7uut3k

The independently rebuilt ButterflyLens ALA baseline remains authoritative.
GBIF is a complementary occurrence-evidence and provenance source; it does not
replace the ALA species or spatial baseline.

## Scientific boundary

Rows are processed provider assertions distributed through GBIF. They are not
human verification, a ButterflyLens identification, ground truth, evidence of
current presence, or evidence of absence. Downstream work must retain provider
issues, coordinate uncertainty, geospatial warnings, information-withheld and
generalisation text, taxonomy status, and exact source identity.

## Rights boundary

The download-level licence is CC BY-NC 4.0. Its 126 constituent datasets report
76 CC BY 4.0, 28 CC BY-NC 4.0, and 22 CC0 rights statements. Occurrence and
multimedia rows can carry their own licences, rights holders, and attributions.
No record or media object is made public merely because it is present here.
ButterflyLens public release remains blocked pending record-level rights,
sensitivity, privacy, provenance, quality, and human-review gates.

The raw 261,743,165-byte DWCA is intentionally not stored in Git. Its exact
SHA-256 and member inventory are frozen in `gbif_download_receipt.json` so an
operator can acquire and verify it separately before running the offline
Parquet builder. No media bytes are downloaded, and no Flickr API call is made.

## Rebuild

Acquisition is the only network-enabled command and is never run by default
tests:

```sh
uv run python scripts/build_gbif_evidence.py acquire \
  --receipt data/packs/australian_butterflies/v1/gbif/gbif_download_receipt.json \
  --output /operator/controlled/0004170-260715120105164.zip
```

The build is offline and receipt-bound:

```sh
uv run python scripts/build_gbif_evidence.py build \
  --archive /operator/controlled/0004170-260715120105164.zip \
  --receipt data/packs/australian_butterflies/v1/gbif/gbif_download_receipt.json \
  --output-dir data/packs/australian_butterflies/v1/gbif \
  --generated-at 2026-07-18T16:09:03Z
```

The checked-in build contains:

- 571,755 processed occurrence-evidence rows in
  `gbif_occurrences.parquet`;
- 542,052 media-metadata rows in `gbif_multimedia.parquet`, with no media
  bytes; and
- 126 constituent dataset/citation/rights rows in `gbif_datasets.parquet`.

`gbif_evidence_manifest.json` binds every Parquet file and closed schema to
the source receipt with physical and logical SHA-256 fingerprints. The root
pack and rights manifests keep all GBIF data display/redistribution blocked.
