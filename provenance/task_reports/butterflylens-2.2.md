# Task report — ButterflyLens 2.2

Task: Build trusted butterfly names
Status: Complete at the task implementation commit
Starting SHA: `ce6a6b82d8bfaf3d651a26911ce2af9aa6d9ade7`
Ending SHA: the commit containing this report; resolve with `git log -1 --format=%H -- provenance/task_reports/butterflylens-2.2.md`
Remote SHA: must equal the ending SHA after the Task 2.2 push; the push receipt is appended to `provenance/commits.jsonl` in the next provenance-bearing commit
BioMiner SHA: `d71bceabf75748a25df39d0025e8da907f295f8c`
TaxaLens SHA: `95f9081567d6c96abdc5b5614d7e401d15ad4f03`

Primary model: `gpt-5.6-sol`
Reasoning effort: `xhigh`
Codex session: `019f7038-92ae-7021-8318-53ca97648404`
Skill used: none matched taxonomy-name construction or Indigenous data-governance policy
GitHits records: `butterflylens-2.2`, `butterflylens-2.2.1`, `butterflylens-2.2.2`, `butterflylens-2.2.3`, `butterflylens-2.2.4` (service unavailable after the single recorded attempt)
Valyu records: `butterflylens-2.2`, `butterflylens-2.2.1`, `butterflylens-2.2.2`, `butterflylens-2.2.3`, `butterflylens-2.2.4` (service unavailable; official-source fallback where current facts were required)

## Outcome

The pack contains 3,641 provenance-rich name assertions: 1,127 accepted
scientific names, 1,383 provider-linked scientific synonyms, and 1,131
English Australian vernacular assertions. These are name assertions, not
media labels, occurrence evidence, or human verification.

Every assertion binds its ButterflyLens taxon key, exact name, language,
region, source and response fingerprints, trust tier, review state, retrieval
date, homonym risk, and query eligibility. The final global collision analysis
leaves 3,214 assertions query eligible, excludes 408 assertions involved in
cross-taxon normalized-name collisions, and excludes 19 single-token
vernacular assertions. Exclusion is a conservative retrieval decision, not a
claim that a name is wrong.

The First Nations language-name policy requires specific language and
Country/community identity, cultural authority, purpose-specific permission,
attribution, and revocable review evidence. Assertion and append-only decision
schemas enforce independent permission fields. No authorized source was
available, so the assertion and decision datasets are intentionally empty and
the review manifest records zero approved, pending, authorized-source, and
query-eligible assertions with every permission blocked by default.

## Files, contracts, and artifacts

- `data/packs/australian_butterflies/v1/name_assertions.jsonl`
- `data/packs/australian_butterflies/v1/sources/ala_species_profiles.json`
- `data/packs/australian_butterflies/v1/schemas/first_nations_name_assertion.schema.json`
- `data/packs/australian_butterflies/v1/schemas/first_nations_name_decision.schema.json`
- `data/packs/australian_butterflies/v1/first_nations_name_assertions.jsonl`
- `data/packs/australian_butterflies/v1/first_nations_name_decisions.jsonl`
- `data/packs/australian_butterflies/v1/first_nations_name_review_manifest.json`
- `FIRST_NATIONS_NAMES.md`
- deterministic acquisition/build commands under `scripts/`
- offline quality and governance tests under `tests/`

No database migration, occurrence record, coordinate, personal contact,
community decision, source image, model artifact, or media asset was added.

## Rights and privacy

The ALA profile snapshot retains only taxon concepts, classifications, names,
variants, source metadata, and raw response hashes. Provider media arrays,
occurrences, coordinates, and users are excluded. Each derived name assertion
retains per-row source attribution and the exact profile response fingerprint.

The First Nations datasets contain zero knowledge or names. Schema fixtures are
explicitly synthetic and use no real community, language name, taxon name,
contact, or authorization. Future private contact and decision evidence must be
opaque references and cannot be published in the pack.

## Verification

Successful task-gate commands:

```text
python3 -m unittest tests/test_butterfly_taxonomy_pack.py tests/test_butterfly_name_pack.py tests/test_first_nations_name_policy.py -v
python3 -m py_compile scripts/build_butterfly_names.py
python3 scripts/build_butterfly_names.py build-scientific ... --generated-at 2026-07-17T16:41:15Z
python3 scripts/build_butterfly_names.py build-vernacular ... --generated-at 2026-07-17T16:49:39Z
python3 scripts/build_butterfly_names.py build-first-nations-empty ... --generated-at 2026-07-17T17:05:00Z
cmp <checked-in-name-and-first-nations-artifacts> <isolated-rebuild-artifacts>
python3 scripts/verify_rights.py
python3 scripts/verify_licensing.py
BUTTERFLYLENS_TSC=/home/toffe/github/karikris/taxalens/apps/web/node_modules/.bin/tsc python3 packages/contracts/tests/check_parity.py
python3 -c "parse every provenance JSONL record and the TaxaLens migration YAML"
git diff --cached --check
```

Results: 40/40 name, taxonomy, and governance tests passed; the isolated rebuild
was byte-for-byte identical; licensing and contract parity passed; provenance
JSONL/YAML and rights JSON parsed. The staged rights and whitespace results are
recorded after staging below in the commit test evidence.

Browser/accessibility: not applicable; no UI changed.
Replay verification: not applicable; no replay changed.
Worker verification: not applicable; no worker changed.
Performance result: no performance claim; bounded ALA acquisition was not benchmarked.

## Scientific and cultural claims

Allowed: the checked-in sources yielded the recorded accepted, synonym, and
English vernacular assertions for the exact frozen snapshot; the query flags
are deterministic applications of the documented pack policy; zero First
Nations assertions were authorized or imported.

Blocked: name correctness beyond the cited source; synonym equivalence as an
accepted concept; a query term as a species label; exhaustive Australian name
coverage; human verification; cultural authority not evidenced in an
authorization decision; any First Nations name, translation, geographic
assignment, or permission inferred from model memory or public availability.

Known limitations: 56 AFD taxa lack an exact usable ALA profile crosswalk;
provider names change; lexical collision screening does not measure every
real-world ambiguity; no authorized First Nations source was available; and
all source assertions remain unreviewed unless explicitly stated otherwise.

Human work remaining: relevant communities may choose to propose and authorize
a First Nations language-name assertion under the documented workflow. Human
taxonomic review may also resolve provider synonym or concept conflicts with
cited evidence.

Next safe task: ButterflyLens 2.3 — freeze ALA baseline occurrence evidence.
