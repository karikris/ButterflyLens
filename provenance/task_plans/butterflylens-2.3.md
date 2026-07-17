# Task plan — ButterflyLens 2.3

Task ID: `butterflylens-2.3`

Objective: freeze, normalize, spatially aggregate, and manifest a
rights-compatible Australian ALA baseline occurrence-evidence snapshot.

Competition criterion improved: reproducible Australian baseline evidence and
an inspectable geographic foundation for the blue ALA map layer.

Starting SHA: `78efdc8bdd69a8d58d6e16bfc6d72e1056f9be16`

Remote main SHA: `78efdc8bdd69a8d58d6e16bfc6d72e1056f9be16`

BioMiner SHA: `d71bceabf75748a25df39d0025e8da907f295f8c`

TaxaLens SHA: `95f9081567d6c96abdc5b5614d7e401d15ad4f03`

Relevant agent files read: root `AGENTS.md`; `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`, `ARCHITECTURE.md`, and
`TASK_TEMPLATE.md`.

Relevant skill: none matches deterministic ALA occurrence acquisition and
Parquet geography construction.

GitHits needed: yes; the service is unavailable after the single recorded
attempt, so it will not be retried. Local pinned BioMiner contracts and official
provider documentation are the fallback evidence.

Valyu needed: yes for current ALA API, citation, terms, sensitive-data, and
spatial-layer facts; the service is unavailable, so official ALA HTTPS sources
are recorded as the fallback.

Expected files: explicit acquisition/build commands, frozen ALA source and
contract receipts, normalized occurrence and dataset Parquet files, spatial
cell Parquet, attribution, snapshot manifest, tests, rights records, and task
provenance.

Contracts affected: ALA snapshot v1, normalized occurrence v1, dataset manifest
v1, spatial-cell v1, and snapshot manifest v1.

Data/rights implications: admit only public-product-compatible record licence
values; preserve each row's provider/resource/licence/citation; retain only
ALA-public generalized sensitive coordinates; attribute ALA, DCCEEW, ABS, and
every contributing resource represented in the provider citation file.

Scientific risks: treating the selected ALA snapshot as complete truth;
promoting provider taxon assertions into human verification; inferring absence;
mixing specimens, machine observations, and field observations; hiding spatial
issues or coordinate uncertainty; or assigning false precision to generalized
records.

Security/privacy risks: persisting the required download contact email,
reconstructing sensitive coordinates, exposing temporary job credentials, or
including source media. The email is submitted only to ALA and is not stored;
the snapshot contains public occurrence metadata and no downloaded media.

Tests: offline snapshot integrity and policy tests; schema and row invariants;
deterministic Parquet rebuild comparison; spatial rollup reconciliation; rights,
licensing, provenance, and contract verifiers; Python compilation; and
`git diff --check`.

Rollback/recovery: every derived artifact is regenerated from the immutable
source archive; the provider archive and manifest are content fingerprinted;
each numbered subtask is a separate commit; no upstream working-tree file is
copied.
