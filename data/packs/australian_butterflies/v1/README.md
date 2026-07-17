# Australian butterfly taxonomy pack v1

This pack is a frozen, reproducible interpretation of the accepted taxa in the
Australian Faunal Directory (AFD) `PAPILIONOIDEA` checklist hierarchy. It is
the ButterflyLens Australian butterfly scope, not a claim that taxonomy is
settled or that every provider uses compatible concepts.

The included ranks are superfamily, family, subfamily, tribe, genus, species,
and subspecies. AFD intermediate ranks such as subtribe and subgenus remain in
each record's `source_parent_path`; they are not silently discarded from the
source lineage. The normalized `parent_path` contains the configured included
ranks. Every v1 row has `taxonomic_status: accepted` because it comes from the
frozen AFD checklist hierarchy, rather than the separate AFD names/synonyms
view.

## Rebuild

Acquisition is the only networked step and is deliberately explicit:

```bash
python3 scripts/build_butterfly_taxonomy.py acquire-afd \
  --output data/packs/australian_butterflies/v1/sources/afd_papilionoidea.json

python3 scripts/build_butterfly_taxonomy.py build-scope \
  --snapshot data/packs/australian_butterflies/v1/sources/afd_papilionoidea.json \
  --output-dir data/packs/australian_butterflies/v1
```

Provider identity acquisition is also explicit. ALA is queried in bounded bulk
batches, GBIF requests use at most four workers with a per-request delay, and
iNaturalist is extracted from its provider-published monthly taxonomy archive:

```bash
python3 scripts/crosswalk_butterfly_taxonomy.py acquire-ala \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --output data/packs/australian_butterflies/v1/sources/ala_name_matches.json

python3 scripts/crosswalk_butterfly_taxonomy.py acquire-gbif \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --output data/packs/australian_butterflies/v1/sources/gbif_name_matches.json

python3 scripts/crosswalk_butterfly_taxonomy.py acquire-inaturalist \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --archive /path/to/inaturalist-taxonomy.dwca.zip \
  --output data/packs/australian_butterflies/v1/sources/inaturalist_taxonomy_matches.json

python3 scripts/crosswalk_butterfly_taxonomy.py build-crosswalk \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --ala data/packs/australian_butterflies/v1/sources/ala_name_matches.json \
  --gbif data/packs/australian_butterflies/v1/sources/gbif_name_matches.json \
  --inaturalist data/packs/australian_butterflies/v1/sources/inaturalist_taxonomy_matches.json \
  --output-dir data/packs/australian_butterflies/v1

python3 scripts/crosswalk_butterfly_taxonomy.py build-conflicts \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --output-dir data/packs/australian_butterflies/v1

# Explicit live acquisition; default tests never run this command.
python3 scripts/build_butterfly_names.py acquire-ala-profiles \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --output data/packs/australian_butterflies/v1/sources/ala_species_profiles.json \
  --workers 4

python3 scripts/build_butterfly_names.py build-scientific \
  --taxa data/packs/australian_butterflies/v1/taxa.jsonl \
  --crosswalk data/packs/australian_butterflies/v1/crosswalk.jsonl \
  --profiles data/packs/australian_butterflies/v1/sources/ala_species_profiles.json \
  --output-dir data/packs/australian_butterflies/v1
```

Default tests make no provider calls. They validate the checked-in snapshot,
checksums, hierarchy, rank policy, and stable ButterflyLens keys.

## Scope and limitations

- “Australian” follows the AFD Australian-fauna scope, including external
  Australian territories represented by AFD; it is not a continental-occurrence
  filter.
- The pack does not infer biological presence or absence from occurrence data.
- A taxon row is not an occurrence, image label, human verification, or release
  decision.
- ALA, GBIF, and iNaturalist identifiers are a separate reconciliation layer.
  Missing or incompatible concepts remain explicit conflicts.
- A top-level provider identifier is populated only for an exact, same-rank,
  classification-compatible current/accepted provider match. Provider-returned
  alternatives remain in the frozen source receipts even when the top-level ID
  is null.
- `complete`, `partial`, and `unresolved` describe identifier availability only;
  they are not quality, truth, occurrence, or human-review states.
- Even three aligned provider identifiers establish only name/rank/classification
  alignment, not full biological concept equivalence. Concept circumscription
  is `not_established` unless later taxonomic evidence resolves it.
- A parenthesized AFD subgenus is removed only from the provider query name. The
  accepted AFD name and full source lineage remain unchanged, and every such
  normalization is declared on the crosswalk row.
- Every non-matched provider relationship has one open row in `conflicts.jsonl`.
  It retains the provider candidate and source receipts, withholds the provider
  ID from the usable crosswalk field, and prohibits automatic resolution. A
  provider miss is kept as a gap, not converted into absence or incompatibility.
- `name_assertions.jsonl` treats accepted names and ALA-linked synonyms as
  sourced assertions, not interchangeable labels. Each row has a stable ID,
  language and region scope, source fingerprints, trust tier, review state,
  homonym risk, and explicit query eligibility. Scientific-name language uses
  BCP 47 `zxx` because Latinized nomenclature is not assumed to be Latin text.
- A synonym attached by the ALA species index remains a provider-linked,
  unreviewed assertion. Cross-taxon normalized-name collisions are excluded
  from query use and no synonym changes the accepted AFD concept.
- Source updates require a new frozen snapshot, review of the diff, and a new
  version or documented compatible revision. Live provider state never mutates
  this checked-in snapshot.

## Source, rights, and citation

The source is the [Australian Faunal Directory Papilionoidea checklist](https://biodiversity.org.au/afd/taxa/PAPILIONOIDEA),
maintained by the Australian Biological Resources Study. The exact retrieval
time, response receipts, compiler string, root concept identifier, source
last-modified value, checksums, and citation are in `manifest.json` and the
frozen source snapshot.

DCCEEW states that its website material is available under CC BY 4.0 unless
otherwise specified, excluding third-party content, logos, the Coat of Arms,
and other listed exclusions. This pack contains checklist taxonomy and no
source images or logos. Attribution: Australian Biological Resources Study,
Australian Faunal Directory; Department of Climate Change, Energy, the
Environment and Water. See the [DCCEEW copyright notice](https://www.dcceew.gov.au/about/copyright)
and [ABRS citation guidance](https://www.dcceew.gov.au/science-research/abrs/online-resources/citation).

The provider crosswalk also retains the [ALA terms](https://www.ala.org.au/terms-of-use/),
[GBIF terms](https://www.gbif.org/terms), and [iNaturalist terms](https://www.inaturalist.org/pages/terms).
The iNaturalist source receipt includes the archive's own EML publication date,
checksum, member CRC, and intellectual-rights statement. Only taxonomic names,
identifiers, ranks, and classification fields are extracted; no observations,
accounts, coordinates, common-name files, or media are included.
