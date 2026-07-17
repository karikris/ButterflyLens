# ButterflyLens Licence Decision

Decision date: `2026-07-17`

**Decision: PASS — license ButterflyLens code and configuration as `AGPL-3.0-only`.**

This is an engineering decision under the user-supplied licence gate, not legal advice. No post-change human review attestation has yet been recorded.

## Why AGPL-3.0-only

ButterflyLens’s required architecture includes YOLOE as an image router when licensing permits. The audited THU-MIG YOLOE repository is AGPL-3.0 and incorporates Ultralytics code. Ultralytics’ current licence guidance offers an AGPL-3.0 path for a fully open-source work or separate commercial terms.

No Ultralytics Enterprise licence, R&D licence, or other executed commercial agreement has been supplied or found in the scoped repositories. No permissively licensed replacement detector has been selected and validated. An MIT-only ButterflyLens licence would therefore create an avoidable incompatibility with the intended YOLOE path.

Selecting `AGPL-3.0-only` from the start preserves a coherent complete-source path and is compatible with the audited MIT, BSD-3-Clause, Apache-2.0, and PostgreSQL-licensed software when their notices and conditions are met.

## Scope

Unless a file states otherwise, the root `LICENSE` applies to original ButterflyLens software and configuration, including:

- the public web application;
- worker and edge services;
- shared contracts, evidence, map, verification, community, and OpenAI packages;
- database migrations, deployment configuration, scripts, and tests;
- modifications or adaptations that form part of the ButterflyLens work.

The licence does **not** relicense:

- BioMiner or TaxaLens source retained in their own repositories;
- third-party packages, code, browser binaries, or bundled notices;
- BioCLIP, YOLOE, Ultralytics, or other model weights/code beyond their own terms;
- ALA, GBIF, iNaturalist, Flickr, ABS, DCCEEW, or other provider data/media/boundaries;
- photographer, observer, reviewer, commenter, cultural-authority, or community content;
- trademarks, logos, the Commonwealth Coat of Arms, or third-party branding.

Those materials remain governed by `THIRD_PARTY_LICENSES.md`, `DATA_RIGHTS.md`, their item-level manifests, and their source terms.

## Network and distribution obligations

Every public ButterflyLens network deployment must:

1. keep the corresponding source for the deployed version available to network users in the manner required by AGPL-3.0 section 13;
2. link the running service to the exact public source commit and root licence;
3. publish modifications, build/deployment configuration, and the preferred form for making changes to the applicable work;
4. preserve all required third-party copyright, licence, attribution, and `NOTICE` material;
5. generate and publish the production dependency licence report;
6. avoid private modules, models, configuration, or server functions that form part of the applicable AGPL work but are omitted from corresponding source;
7. keep secrets, credentials, private reviewer data, and provider-restricted content out of source while documenting the interfaces and non-secret configuration needed to run the work.

AGPL source availability never authorizes release of provider-restricted data, copyrighted images, sensitive coordinates, private reviewer-quality evidence, secrets, or cultural knowledge.

## YOLOE status

Current status: **AGPL-3.0 path selected; no Ultralytics Enterprise licence documented; no YOLOE code or weight has yet been imported or downloaded into ButterflyLens.**

Before YOLOE runs, its code repository/revision, model ID/revision, checksums, licence snapshots, third-party components, corresponding-source boundary, and runtime integration must be recorded. YOLOE remains a router, never a species classifier.

## Alternatives and change control

The decision may change only through a new audited, human-reviewed commit that chooses one of:

- an executed Ultralytics commercial licence whose scope covers the exact ButterflyLens use;
- a permissively licensed detector whose code, weights, training provenance, accuracy, and Apple MPS operation pass the required gates;
- removal of YOLOE and an approved architecture that still satisfies the product outcome.

Changing the detector does not automatically relicense existing ButterflyLens contributions or remove obligations already triggered by distributed/networked AGPL versions.

## Release gate

Release is blocked unless both commands pass at the exact release SHA:

```text
python3 scripts/verify_licensing.py
python3 scripts/verify_rights.py
```

The checks are intentionally conservative. A passing Phase 0 repository with no provider artifacts does not authorize a later data/model release; adding dependencies, models, provider artifacts, boundary files, community writes, or deployments introduces new manifest requirements.
