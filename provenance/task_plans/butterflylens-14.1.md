# ButterflyLens Task 14.1 plan

Task: Define release-ready occurrence policy.

Commit: `feat(release): define occurrence release gates`

## Scope

- Define one deterministic policy containing every required gate.
- Distinguish a release-ready occurrence candidate from a published occurrence.
- Add an immutable database receipt tied to exact human, qualified, expert,
  coordinate/date, duplicate, rights, quality, conflict, packet, sensitive-
  location, and candidate fingerprints.
- Require a validated receipt in the existing public release RLS policy.
- Document the policy and expose it from the public project shell.

## Verification

- Focused deterministic planner, database, policy, and pgTAP-count tests.
- PostgreSQL and PL/pgSQL parsing; runtime pgTAP only if a local database exists.
- Full Python, web, Edge, rights, licensing, provenance, and safety gates.
- Exact commit, non-force `main` push, exact-SHA Pages and served-policy check.

## Boundaries

BioMiner's published coordination record was inspected at task start. Its
scientific/Flickr/GBIF work remains active and supplies no immutable GBIF
handoff, so no partial output is copied. The rebuilt ButterflyLens ALA baseline
remains authoritative. GitHits stays disabled; Flickr API, YOLOE, and BioCLIP
work remain outside this task.
