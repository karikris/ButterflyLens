# Third-Party Software Licence Audit

Audit date: `2026-07-17`

This is the Phase 0 software licence gate for ButterflyLens. It records intended or candidate components, not an assertion that every component is already installed or distributed. Exact versions, revisions, checksums, transitive dependencies, bundled notices, and licence texts must be regenerated from lockfiles and model manifests before every release.

This audit is engineering evidence, not legal advice.

## Gate outcome

- BioMiner, TaxaLens, BioCLIP 2.5, the proposed data stack, and the proposed public-web stack use permissive licences compatible with an AGPL-3.0 work when their notice and attribution conditions are met.
- YOLOE is the controlling dependency. The official THU-MIG repository is AGPL-3.0, incorporates Ultralytics code, and Ultralytics currently offers AGPL-3.0 or commercial licensing for its code and models.
- No Ultralytics Enterprise licence has been supplied or found in the scoped repositories.
- Therefore ButterflyLens must not be published under an incompatible MIT-only licence while it uses that YOLOE path. The final repository decision is recorded separately in `LICENSE_DECISION.md` after the data-rights audit.
- No dependency may be added merely because this table lists it. A pinned direct dependency, lockfile, transitive-licence report, vulnerability audit, and release notice remain required.

## Upstream application boundaries

| Component | Evidence inspected | Licence | Compatibility and obligations |
| --- | --- | --- | --- |
| BioMiner | Local `LICENSE` at audit SHA `2643bf3c1caffe2f68ba837d99064a0c99192c7c`; baseline SHA `3c7665df3a828b2ea925ee8b549bf843c569f540` remains separately recorded. | MIT | Compatible. Preserve copyright and permission notice for copied or substantially adapted source. Prefer artifacts/contracts/adapters over copying. Dirty working-tree files are not licensed inputs to ButterflyLens. |
| TaxaLens | Local `LICENSE` and `pyproject.toml` at audit SHA `82786e3e8fbfa1076342bd6683ce69707821fe08`; baseline SHA `a5946d8423b84249d908cdf38ececfa94ca29f56` remains separately recorded. | MIT | Compatible. Preserve notice for copied or substantially adapted source. Prefer committed schemas, artifacts, and thin adapters. Dirty working-tree files are excluded. |

The upstream audit SHAs changed after the repository baseline was captured. That change is evidence of moving upstream state, not permission to update an integration silently. Every migration must pin one immutable origin SHA.

## Models and local vision runtime

| Component | Intended use | Licence evidence | Decision and obligations |
| --- | --- | --- | --- |
| `hf-hub:imageomics/bioclip-2.5-vith14` | Locally downloaded and fingerprinted BioCLIP weights; local MPS inference | [Hugging Face model page](https://huggingface.co/imageomics/bioclip-2.5-vith14/tree/main) identifies MIT. | Allowed subject to pinning the exact revision, weights checksum, model card, preprocessing revision/fingerprint, and runtime metadata. Do not redistribute training datasets by implication. Do not upload provider images to Hugging Face by default. |
| Imageomics BioCLIP 2 code | Model integration reference | [Imageomics BioCLIP 2 repository](https://github.com/Imageomics/bioclip-2) states MIT and notes third-party provenance. | Compatible; retain notices and inspect `HISTORY.md`/third-party provenance at the pinned revision before importing code. Artifact-first integration remains preferred. |
| OpenCLIP | Local model loader and preprocessing runtime | [OpenCLIP licence](https://github.com/mlfoundations/open_clip/blob/main/LICENSE) is MIT. | Compatible; pin package and preserve notice. Verify the model-specific licence independently; the loader licence does not license every checkpoint. |
| PyTorch | Local Apple MPS tensor runtime | [PyTorch licence](https://github.com/pytorch/pytorch/blob/main/LICENSE) is BSD-3-Clause-style with extensive upstream notices. | Compatible; preserve copyright, conditions, disclaimer, and bundled third-party notices. |
| THU-MIG YOLOE | Image routing, never species classification | [THU-MIG/yoloe](https://github.com/THU-MIG/yoloe) is identified as AGPL-3.0 and includes an `ultralytics` tree. | Strong-copyleft gate. Use only under a documented AGPL-compliant complete-source release or a separately documented commercial licence. Pin code and model revisions/checksums. |
| Ultralytics code and YOLO models | YOLOE implementation/model path | [Ultralytics licence guidance](https://www.ultralytics.com/license) and [current terms](https://www.ultralytics.com/legal/terms-of-service) identify AGPL-3.0 open-source use or a commercial licence. | No Enterprise evidence exists. If used, publish the complete applicable source, scripts, configuration, and corresponding-source offer required by the selected terms; make network users able to obtain source. A future Enterprise decision must include the executed agreement and scope, not a sales-page assumption. |

Model weights and source code are separately fingerprinted licence subjects. A permissive application dependency never overrides a model licence, and a model card never licenses provider images used as inputs or references.

## Data, storage, and geospatial software

| Component | Candidate role | Licence | Source and release obligation |
| --- | --- | --- | --- |
| PostgreSQL | Primary relational database | PostgreSQL Licence | [Supabase architecture documentation](https://supabase.com/docs/guides/getting-started/architecture) identifies the upstream licence. Preserve applicable notices if redistributed. |
| Supabase platform repository | Hosted database/auth/RLS/edge operational reference | Apache-2.0 | [Supabase repository licence](https://github.com/supabase/supabase/blob/master/LICENSE). Preserve licence/NOTICE conditions for redistributed source; hosted-service terms and privacy are separate contracts. |
| `@supabase/supabase-js` | Browser/server client | MIT | [Official client repository](https://github.com/supabase/supabase-js). Pin package and lockfile. Never expose secret/service-role keys. |
| DuckDB | Local analytics and deterministic artifact queries | MIT | [DuckDB repository](https://github.com/duckdb/duckdb). Preserve notice. Audit separately bundled extensions before enabling them. |
| Polars | Dataframe and Parquet processing | MIT | [Polars repository](https://github.com/pola-rs/polars). Preserve notice and audit optional dependencies selected by extras. |
| Apache Arrow / PyArrow | Parquet and Arrow interoperability | Apache-2.0 | [Apache Arrow repository](https://github.com/apache/arrow/). Preserve licence and NOTICE. |
| H3 | Hierarchical spatial cells | Apache-2.0 | [H3 repository](https://github.com/uber/h3). Preserve licence and `NOTICE`; audit each language binding and version. |
| MapLibre GL JS | Public map renderer | BSD-3-Clause with bundled third-party notices | [MapLibre licence file](https://github.com/maplibre/maplibre-gl-js/blob/main/LICENSE.txt). Reproduce source/binary notices and non-endorsement conditions. No external basemap or tile provider is selected by this software choice. |

The initial public map should render ButterflyLens-owned evidence layers and separately licensed Australian boundaries without silently introducing a tile-provider contract. Any later basemap, glyph, sprite, geocoder, or tile service is a new licence-and-terms gate.

## Public web and testing candidates

| Component | Candidate role | Licence | Evidence and obligation |
| --- | --- | --- | --- |
| React / React DOM | Public application UI | MIT | [React licence](https://github.com/facebook/react/blob/main/LICENSE). Preserve notice. |
| React Aria Components | Accessible interaction primitives | Apache-2.0 | [React Spectrum repository](https://github.com/adobe/react-spectrum). Preserve licence and `NOTICE`. |
| Vite and official React plugin | Build system | MIT | [Vite repository](https://github.com/vitejs/vite). Generate and publish the production dependency licence report. |
| TypeScript | Type checking and compiler | Apache-2.0 | [TypeScript repository](https://github.com/microsoft/TypeScript). Preserve applicable notice when redistributed. |
| Vitest | Unit/component tests | MIT | [Vitest repository](https://github.com/vitest-dev/vitest). Development-only unless a production bundle proves otherwise. |
| Playwright | Chromium/Firefox/WebKit E2E and visual testing | Apache-2.0 | [Playwright repository](https://github.com/microsoft/playwright). Preserve licence and `NOTICE`; browser binaries carry their own terms/notices. |
| OpenAI JavaScript/TypeScript SDK | Server-side Responses API client | Apache-2.0 | [Official SDK licence](https://github.com/openai/openai-node/blob/main/LICENSE). API/service terms and model availability are separate runtime gates. |

No version is approved by a floating range. The later application scaffold must select exact direct versions, commit lockfiles, and reject unknown, unlicensed, source-available-only, SSPL, Commons Clause, Business Source, non-commercial, or incompatible copyleft production dependencies unless this audit is deliberately amended.

## Required release evidence

The software-licence verifier must fail unless all applicable conditions are true:

1. the root repository licence matches `LICENSE_DECISION.md`;
2. every direct dependency has an exact version and SPDX-compatible licence result;
3. every transitive production dependency is present in a generated report;
4. all Apache/BSD/MIT notices required by distributed bundles are preserved;
5. every model has an immutable revision, checksum, model-card snapshot, and separate licence status;
6. YOLOE is either absent, covered by documented commercial terms, or included under the selected AGPL complete-source path;
7. production builds emit a third-party licence file;
8. no unreviewed basemap, tiles, glyphs, sprites, model, browser binary, extension, or hosted service is introduced;
9. data and media rights pass the independent `DATA_RIGHTS.md` gate.

