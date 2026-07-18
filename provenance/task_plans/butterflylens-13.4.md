# ButterflyLens Task 13.4 plan

Task: Add removal and rights requests.

Commit: `feat(rights): add media takedown workflow`

## Scope

- Add private requester intake and public, non-identifying request status.
- Quarantine requested media and all directly traceable descendants before review.
- Inventory source, cache, display, model, review, map, packet, export, mirror,
  and signed-access dependencies by immutable fingerprint.
- Require append-only authority, dependency-action, and completion evidence.
- Suppress affected public releases while any request exists.
- Document the rights-request workflow and its prelaunch contact blocker.
- Do not call Flickr, run models, copy partial BioMiner work, or mutate production.

## Verification

- Static contract tests and pgTAP assertions for schema/RLS/RPC boundaries.
- Full Python, TypeScript, Deno, web-build, rights, and licence gates.
- SQL parse checks; live pgTAP only if a local PostgreSQL runtime is available.
- Commit and push `main`, then verify the exact GitHub Pages SHA and served policy.

## Parallel-work boundary

BioMiner's coordination record was inspected at task start. Its Flickr/GBIF
work remains active and dirty, so no partial output is admitted. GitHits stays
disabled. YOLOE and BioCLIP stay unfinished and are not run.
