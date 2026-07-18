# ButterflyLens Darwin Core evidence package

Policy version: `butterflylens-darwin-core-export-policy:v1.0.0`

Last reviewed: 18 July 2026

## Export boundary

ButterflyLens prepares a deterministic Darwin Core Archive only from an exact
`release_ready_occurrence_candidate` receipt. Package preparation is not
publication, provider submission, ALA acceptance, or proof of biological
presence or absence. The manifest therefore records
`prepared_not_published` and `not_submitted`. Submission remains a later,
explicitly authorised and separately validated action.

No production archive or new occurrence is currently asserted by this
repository. The committed fixture tests software structure only.

## Package contents

The archive follows the [TDWG Darwin Core Text guide](https://dwc.tdwg.org/text/)
with one `Occurrence` core and nine core-linked extensions. It uses the
[current Darwin Core terms](https://dwc.tdwg.org/terms/) reviewed on 18 July
2026.

| Requested evidence | Archive file | Darwin Core class |
|---|---|---|
| occurrence | `occurrence.txt` | `dwc:Occurrence` core |
| taxon | `taxon.txt` | `dwc:Taxon` |
| event | `event.txt` | `dwc:Event` |
| location | `location.txt` | `dcterms:Location` |
| identification | `identification.txt` | `dwc:Identification` |
| measurement | `measurement.txt` | `dwc:MeasurementOrFact` |
| multimedia | `multimedia.txt` | `ac:Media` |
| provenance | `provenance.txt` | `dwc:Provenance` |
| review | `review.txt` | `dwc:Assertion` |
| quality | `quality.txt` | `dwc:Assertion` |

`meta.xml` maps every column to its term URI and every extension row back to
the unique occurrence core identifier. `evidence-manifest.json` records the
policy and standards versions, exact code SHA, row counts, byte counts,
per-file SHA-256 checksums, source release receipts, and a canonical package
fingerprint. The manifest is written last. Archive members have fixed
timestamps and ordering so identical governed input produces identical bytes.

The current Darwin Core Data Package guide was also reviewed. This export uses
the Text/Darwin Core Archive core-extension model because it preserves all ten
requested evidence domains as explicit files; it does not claim DwC-DP profile
conformance.

An authorized worker can invoke the offline builder with an exact JSON-shaped
request:

```bash
uv run python scripts/build_darwin_core_evidence_package.py \
  --input governed-release-records.json \
  --output butterflylens-evidence.zip
```

The command performs no network or provider call. It writes the archive
atomically and prints its physical SHA-256, semantic package fingerprint, and
the two non-publication states. Unknown input fields are rejected.

## Scientific, privacy, and rights controls

The exporter fails closed unless every input record:

- is release-ready and explicitly not yet published;
- binds the exact release, sensitive-location, consensus, expert-gate,
  duplicate, conflict, quality, rights, taxon, media, and packet fingerprints;
- has matching candidate/media rights fingerprints;
- supplies a complete date and a governed valid public H3 cell;
- supplies a public HTTPS source page, licence, rights holder, creator, and
  attribution; and
- uses an expert event fingerprint exactly when expert review was configured.

Only the generalized public H3 identifier is exported. Raw, verbatim, or more
precise coordinates are not accepted by the typed input or mapped in
`meta.xml`. Information-withheld and generalization statements remain visible.

Review rows contain consensus/adjudication fingerprints only—never account,
profile, email, comment, or reviewer identity. Multimedia rows contain source
and rights metadata, not image bytes. Access URLs are optional and must be
credential-free HTTPS URLs without query strings or fragments; signed URLs are
rejected. Targeted failure-discovery evidence cannot be represented as the
population-quality basis.

BioMiner's active GBIF/Flickr work remains outside the package until it supplies
an immutable governed handoff. The rebuilt ButterflyLens ALA baseline remains
authoritative baseline evidence. No Flickr API call, YOLOE, or BioCLIP work is
part of export generation.
