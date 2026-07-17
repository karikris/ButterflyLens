# ButterflyLens Build Week Baseline

This document fixes the repository and upstream state from which ButterflyLens begins. It distinguishes pre-existing work from work created in this repository and does not claim that upstream artifacts have been imported, validated, or released by ButterflyLens.

## Repository identity

| Field | Baseline value |
| --- | --- |
| Repository | `karikris/ButterflyLens` |
| Visibility | Public |
| Description | Australia’s live butterfly evidence map and community verification platform. |
| Repository created | `2026-07-17T13:25:55Z` |
| Default branch | `main` |
| First commit | `db0657fd432b698c167d559328a57b0befef6664` |
| First commit time | `2026-07-17T23:26:47+10:00` |
| Primary Codex thread | `019f7038-92ae-7021-8318-53ca97648404` |

The remote was empty at creation. The first commit added only `.gitignore`, `README.md`, and `provenance/githits.jsonl`. No licence was selected and no application, model, image, occurrence, or review artifact existed in ButterflyLens at that SHA.

## Development environment

Captured on `2026-07-17` in the repository creation environment:

| Tool | Version |
| --- | --- |
| Python | `3.14.4` |
| Node.js | `22.22.1` |
| npm | `9.2.0` |
| uv | `0.11.19` (`x86_64-unknown-linux-gnu`) |
| pnpm | Not installed |
| Bun | Not installed |
| Git | `2.53.0` |
| GitHub CLI | `2.46.0` |

These values describe the repository-creation host, not the target Apple M5 Pro worker. No MPS, unified-memory, or model-runtime claim is made from this Linux baseline.

## Upstream repositories

| Upstream | Branch | Commit | Working-tree condition at capture |
| --- | --- | --- | --- |
| `karikris/BioMiner` | `main` | `3c7665df3a828b2ea925ee8b549bf843c569f540` | User-owned untracked files were present. |
| `karikris/taxalens` | `main` | `a5946d8423b84249d908cdf38ececfa94ca29f56` | A user-owned modified provenance report and an untracked file were present. |

The dirty upstream working trees are treated as read-only. Only committed paths at the SHAs above count as baseline evidence. No uncommitted upstream file may be attributed to ButterflyLens or imported without a later explicit decision and manifest entry.

## Available committed upstream artifacts

BioMiner exposes committed schema and manifest code suitable for later audit, including:

- target-aware few-shot contract documentation;
- detection, geography, reference, run-manifest, and work-store schemas;
- reference and evaluation fixtures;
- an existing GitHits provenance ledger.

TaxaLens exposes a larger committed evidence-facade and demonstration surface suitable for later artifact-first evaluation, including:

- JSON Schemas and Python/TypeScript geographic, verification, judge-bundle, and replay contracts;
- verification campaigns, items, events, consensus, quality snapshots, and repository-storage fixtures;
- BioMiner Phase 14/15 import manifests and committed Parquet/JSON demonstration artifacts;
- geographic-impact cells and summaries;
- stored analyst request/run fixtures and hosted replay provenance;
- BioMiner migration state and Build Week submission provenance.

Availability is not compatibility. Phase 1 must audit each artifact, its schema version, rights, provenance, and source SHA before ButterflyLens consumes it.

## Work that predates ButterflyLens

The following is pre-existing and must not be counted as new ButterflyLens work:

- BioMiner’s taxonomy, query, acquisition, geography, model, calibration, evaluation, and worker capabilities;
- TaxaLens’s verification, consensus, quality, geographic-impact, replay, and evidence-facade patterns;
- all committed and uncommitted artifacts in those repositories;
- provider data, media, model weights, schemas, reports, and demonstration fixtures created before the ButterflyLens repository time;
- the product goal and competition specification supplied by Kris Kari.

## Work considered new

New ButterflyLens work begins with commit `db0657fd432b698c167d559328a57b0befef6664` and is limited to files authored or deliberately imported into this repository with provenance after `2026-07-17T13:25:55Z`.

An upstream-derived artifact counts as ButterflyLens work only when its migration manifest records the upstream repository, immutable commit, source path, integration method, licence/rights decision, and ButterflyLens destination. Existing upstream capability itself never becomes new work merely because ButterflyLens consumes it.

