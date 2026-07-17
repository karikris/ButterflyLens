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
