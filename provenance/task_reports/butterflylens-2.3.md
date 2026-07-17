# Task report — ButterflyLens 2.3

Task: Freeze ALA baseline occurrence evidence
Status: Complete at the task implementation commit
Starting SHA: `78efdc8bdd69a8d58d6e16bfc6d72e1056f9be16`
Ending SHA: the commit containing this report; resolve with `git log -1 --format=%H -- provenance/task_reports/butterflylens-2.3.md`
Remote SHA: must equal the ending SHA after the Task 2.3 push; the push receipt is appended to `provenance/commits.jsonl` in the next provenance-bearing commit
BioMiner SHA: `d71bceabf75748a25df39d0025e8da907f295f8c`
TaxaLens SHA: `95f9081567d6c96abdc5b5614d7e401d15ad4f03`

Primary model: `gpt-5.6-sol`
Reasoning effort: `xhigh`
Codex session: `019f7038-92ae-7021-8318-53ca97648404`
Skill used: none matched this provider-evidence pipeline
GitHits records: `butterflylens-2.3`, `butterflylens-2.3.1`, `butterflylens-2.3.2`, `butterflylens-2.3.3`, `butterflylens-2.3.4` (service unavailable after the single recorded attempt)
Valyu records: `butterflylens-2.3`, `butterflylens-2.3.1`, `butterflylens-2.3.2`, `butterflylens-2.3.2-dependency-lock`, `butterflylens-2.3.3`, `butterflylens-2.3.4` (service unavailable; official-source fallback)

## Outcome

The frozen ALA baseline contains 236,897 selected Papilionoidea occurrence
rows from 53 data resources. It preserves the original provider archive,
query fingerprint, headings, 84 citation entries, per-record licences,
quality assertions, sensitive/generalisation state, coordinates and
uncertainty, contextual geography, provider identities, and source links.

The deterministic normalized artifact contains all 236,897 rows in a typed
45-column Parquet schema. Exact taxon identifier joins resolve 226,613 rows;
10,284 provider assertions remain explicitly unmatched. Spatial policy makes
230,027 rows eligible at some level, limits 375 generalized rows to coarse
geography, excludes 6,277 rows with missing coordinates, and excludes 593
spatially suspect rows.

The aggregate artifact contains 23,744 rows across Australia, state/territory,
IBRA, LGA statistical approximations, and H3 resolutions 3, 5, and 7. Every
aggregate retains source-row counts and ordered lineage digests. H3 centers
are indexing metadata, not occurrence coordinates, and unoccupied cells are
never represented as biological absence.

The publication manifest joins each of the 53 exact resource UIDs to its
citation and selected-row licence counts. Conservative screening flags
`dr1097`, `dr30019`, and `dr635`, covering 16,753 rows, because resource-level
citation rights contain potentially restrictive NonCommercial wording that
conflicts with selected processed licences. The evidence snapshot is retained,
but downstream public-product release is blocked pending resolution or
exclusion. This screening is not a legal conclusion.

## Files and artifacts

- immutable ALA source archive, receipt, attribution, and source-contract
  fingerprints under `data/packs/australian_butterflies/v1/ala/`
- deterministic normalized occurrence and aggregate-cell Parquet artifacts
- typed occurrence, aggregate, and dataset-manifest schemas
- normalization, aggregation, dataset, and snapshot manifests
- root pack publication state and rights/provenance inventory
- offline acquisition, normalization, aggregation, publication, and policy
  tests under `scripts/` and `tests/`

No source image, private contact email, DOI request, user account, inferred
absence, reconstructed sensitive coordinate, boundary geometry, or human
verification record was added.

## Rights, privacy, and scientific controls

The source selection filter accepts only processed CC0, Public Domain Mark,
and attribution-only CC BY variants. That filter is not a substitute for exact
resource citation review. All 53 resource citations remain verbatim, including
four information-withheld notices and one data-generalisation notice. Thirty-one
provider, collection, and institution entries remain in the source receipt
without an invented resource hierarchy.

Public generalized coordinates are preserved exactly as supplied and routed
only to Australia, state/territory, and H3 resolution 3. Missing, suspect, or
withheld detail is not reconstructed. Provider taxon assertions, contextual
labels, and occurrence rows are evidence states rather than expert or human
verification.

## Verification

Successful task-gate commands:

```text
uv lock --check
uv sync --frozen
uv pip check
uv run python -m unittest tests/test_butterfly_taxonomy_pack.py tests/test_butterfly_name_pack.py tests/test_first_nations_name_policy.py tests/test_ala_baseline_snapshot.py -v
uv run python -m py_compile scripts/build_ala_baseline.py tests/test_ala_baseline_snapshot.py
uv run python scripts/build_ala_baseline.py normalize ...
uv run python scripts/build_ala_baseline.py aggregate ...
uv run python scripts/build_ala_baseline.py publish-manifest ...
cmp <checked-in-ALA-derived-artifacts> <isolated-rebuild-artifacts>
python3 scripts/verify_rights.py
python3 scripts/verify_licensing.py
BUTTERFLYLENS_TSC=../taxalens/apps/web/node_modules/.bin/tsc uv run python packages/contracts/tests/check_parity.py
python3 -c "parse every provenance JSONL/JSON/YAML artifact"
git diff --cached --check
```

Results: the complete offline suite, isolated byte-identical rebuilds,
licensing, rights coverage, dependency integrity, contract parity, provenance
parsing, secret scan, large-file review, and staged whitespace gate passed.

Browser/accessibility: not applicable; no UI changed.
Replay verification: not applicable; no replay changed.
Worker verification: not applicable; no worker changed.
Performance result: no performance claim; provider acquisition and local
rebuilds were not benchmarked.

## Claims and remaining work

Allowed: these artifacts accurately describe the exact frozen provider archive
and the deterministic policies applied to it. The recorded spatial, taxonomy,
quality, citation, and rights states are evidence for this snapshot only.

Blocked: biological absence; authoritative distribution; taxonomy correctness;
human verification; precise sensitive location; blanket ALA licensing; legal
clearance; public-product release of the three flagged resources; or currency
beyond the recorded snapshot and provider-page retrieval dates.

Known limitations: provider records and rights metadata change; exact taxon-ID
matching leaves unmatched assertions; contextual labels are provider fields,
not copied boundary geometry; resource rights conflicts require human review;
and aggregate counts do not establish occupancy or abundance.

Human work remaining: resolve or exclude the three flagged resources before a
downstream public-product release, and perform evidence-based taxonomic or
occurrence review where later product claims require it.

Next safe task: ButterflyLens 2.4 — prepare model-ready evidence without
weakening the snapshot's rights, sensitivity, provenance, or scientific gates.
