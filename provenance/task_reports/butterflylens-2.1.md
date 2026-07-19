# Task report — ButterflyLens 2.1

Task: Build the accepted Australian butterfly taxonomy
Status: Complete at the task implementation commit
Starting SHA: `c4836c9b365619fe7cbb9a78d9e8e11c27751bf3`
Ending SHA: the commit containing this report; resolve with `git log -1 --format=%H -- provenance/task_reports/butterflylens-2.1.md`
Remote SHA: must equal the ending SHA after the Task 2.1 push; the push receipt is appended to `provenance/commits.jsonl` in the next provenance-bearing commit
BioMiner SHA: `d71bceabf75748a25df39d0025e8da907f295f8c`
TaxaLens SHA: `95f9081567d6c96abdc5b5614d7e401d15ad4f03`

Primary model: `bounded-model`
Reasoning effort: `xhigh`
Codex session: `019f7038-92ae-7021-8318-53ca97648404`
Skill used: none matched taxonomy-pack construction; the previously loaded GitHub skill was not needed for local implementation
GitHits records: `butterflylens-2.1`, `butterflylens-2.1.1`, `butterflylens-2.1.2`, `butterflylens-2.1.3` (service unavailable after the single recorded attempt)
Valyu records: `butterflylens-2.1`, `butterflylens-2.1.1`, `butterflylens-2.1.2`, `butterflylens-2.1.3` (service unavailable; official-source web fallback for mutable facts)

## Outcome

The pack freezes the Australian Faunal Directory Papilionoidea hierarchy and
retains 1,127 accepted rows across superfamily, family, subfamily, tribe, genus,
species, and subspecies. Fifteen source-only intermediary nodes remain in
`source_parent_path` rather than being silently discarded.

The provider crosswalk contains one row per AFD taxon. It populates ALA, GBIF,
or iNaturalist identifiers only for exact, same-rank,
classification-compatible accepted/current results. The frozen source state
produced 553 complete, 560 partial, and 14 unresolved identifier rows. These
are availability states, not biological or human-verification claims.

The conflict ledger contains 741 open taxon-provider relationships: 56 ALA,
500 GBIF, and 185 iNaturalist. Every row retains its reasons, provider
candidate, and source fingerprints; every usable provider identifier remains
withheld for that relationship; automatic resolutions are zero.

## Files and artifacts

- `data/packs/australian_butterflies/v1/taxa.jsonl`
- `data/packs/australian_butterflies/v1/crosswalk.jsonl`
- `data/packs/australian_butterflies/v1/conflicts.jsonl`
- `data/packs/australian_butterflies/v1/manifest.json`
- frozen AFD, ALA, GBIF, and iNaturalist source receipts under `sources/`
- deterministic acquisition/build commands under `scripts/`
- offline taxonomy tests under `tests/`

No database migration, occurrence record, coordinate, account, vernacular-name
file, source image, model artifact, or media asset was added.

## Rights and privacy

The rights manifest binds every tracked pack JSON/JSONL artifact to its exact
SHA-256, source, rights basis, and attribution. AFD/ALA provider terms, GBIF
terms, and the iNaturalist archive EML rights statement are preserved. The pack
contains factual taxonomy fields and matcher diagnostics only. There is no
personal information or sensitive location data.

## Verification

- 17 offline taxonomy tests cover hierarchy, stable keys, source receipts,
  checksums, exact-match ID gating, complete crosswalk coverage, conflict
  completeness, conflict ID recomputation, open resolution state, and
  scientific-language safeguards.
- Scope, crosswalk, and conflict builds are deterministic from the frozen
  snapshots when their recorded generation timestamp is supplied.
- `python3 scripts/verify_rights.py` passes with all pack payloads covered.
- `python3 scripts/verify_licensing.py` passes.
- Provenance JSONL parses and `git diff --cached --check` passes.

Successful task-gate commands:

```text
python3 -m unittest tests/test_butterfly_taxonomy_pack.py -v
python3 scripts/build_butterfly_taxonomy.py build-scope --snapshot <isolated-pack>/sources/afd_papilionoidea.json --output-dir <isolated-pack> --generated-at 2026-07-17T15:06:19Z
python3 scripts/crosswalk_butterfly_taxonomy.py build-crosswalk --taxa <isolated-pack>/taxa.jsonl --ala <isolated-pack>/sources/ala_name_matches.json --gbif <isolated-pack>/sources/gbif_name_matches.json --inaturalist <isolated-pack>/sources/inaturalist_taxonomy_matches.json --output-dir <isolated-pack> --generated-at 2026-07-17T15:54:54Z
python3 scripts/crosswalk_butterfly_taxonomy.py build-conflicts --crosswalk <isolated-pack>/crosswalk.jsonl --output-dir <isolated-pack> --generated-at 2026-07-17T16:01:22Z
for f in taxa.jsonl crosswalk.jsonl conflicts.jsonl manifest.json; do cmp "data/packs/australian_butterflies/v1/$f" "<isolated-pack>/$f"; done
python3 scripts/verify_licensing.py
python3 scripts/verify_rights.py
BUTTERFLYLENS_TSC=/home/toffe/github/karikris/taxalens/apps/web/node_modules/.bin/tsc python3 packages/contracts/tests/check_parity.py
python3 -c "import json,pathlib; [json.loads(line) for path in pathlib.Path('provenance').glob('*.jsonl') for line in path.read_text().splitlines() if line.strip()]"
python3 -c "import pathlib,yaml; yaml.safe_load(pathlib.Path('provenance/taxalens_migration_manifest.yaml').read_text())"
git diff --cached --check
```

Results: 17/17 tests passed; the isolated frozen-pack rebuild was byte-for-byte
identical; licensing, rights, contract parity, provenance parsing, and staged
whitespace checks passed.

Browser/accessibility: not applicable; no UI changed.
Replay verification: not applicable; no replay changed.
Worker verification: not applicable; no worker changed.
Performance result: no performance claim; provider acquisition was bounded but not benchmarked.

## Scientific claims

Allowed: the pack is a frozen interpretation of accepted taxa in the selected
AFD Papilionoidea checklist, and the recorded provider identifier availability
is true for the exact checked-in snapshots.

Blocked: taxonomic completeness outside AFD scope; full concept equivalence;
biological presence or absence; official ground truth; occurrence status;
image identity; human verification; and automatic resolution of any open
conflict.

Known limitations: provider taxonomies change; GBIF's current matcher lacks
some intermediary ranks; names/ranks/classification do not prove identical
circumscription; and all 741 conflicts remain open pending evidence-based
taxonomic review.

Human work remaining: taxonomic review may resolve conflicts with cited
evidence. Task 2.2 must add sourced synonyms and governed vernacular-name
assertions without treating this crosswalk as name authority.

Next safe task: ButterflyLens 2.2 — build trusted butterfly names.
