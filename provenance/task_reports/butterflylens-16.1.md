# ButterflyLens 16.1 — freeze submitted snapshot

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`0e07f175fa07650e90606ca07b2286807010f1de`.

## Outcome

ButterflyLens now has one canonical, immutable, credential-free Submitted
snapshot at `data/submission/v1/submitted_snapshot.json`. Its RFC 8785
fingerprint is
`sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de`.
The freeze command rebuilds it only from the exact committed source tree and
compares the whole document, so a changed source file, Git object, count,
state, right, or null value fails verification.

Seventeen source artifacts retain both their physical SHA-256 and Git blob,
plus the last commit that changed each path. Directory-level pack, Flickr
planner, and worker versions retain Git tree identities. The source tree is
`0e07f175fa07650e90606ca07b2286807010f1de` / tree
`adf748c89ecbcc60100932104e77c1e4fc0cddfe`. The containing Task 16.1 commit is
recorded by the next task's normal push receipt because a commit cannot include
its own SHA without circular mutation.

## Frozen evidence

- ALA baseline: authoritative rebuilt ButterflyLens snapshot
  `ala-papilionoidea-au-20260717-d33d4d367525`, fingerprint
  `d33d4d36752579ba780fca4d0ec9f234848ccccdba468711846a265c12108f65`.
  It records 236,897 selected ALA baseline occurrence-evidence rows, 230,027
  spatially eligible rows, 23,744 aggregate rows, exact per-scope row counts,
  and 53 contributing dataset resources.
- ALA rights: downstream release remains
  `blocked_pending_dataset_rights_resolution` for 16,753 selected records from
  `dr1097`, `dr30019`, and `dr635`. The internal counts are evidence inventory,
  not permission to display or publish the occurrence layer.
- Flickr query plan: exact deterministic Australia-known lane fingerprint
  `044e5c09d13b5e4ab7f966b46c447a0c5e29fb6f12f02e449e0672b0a27ad524`.
  It contains 1,876 definitions, 4,997 logical associations, 1,754 deduplicated
  physical requests, and 4,997 lossless links across 463 accepted species.
  Fixed parameters are `content_types=0`, `media=photos`, and `safe_search=1`.
  Every request remains `planned_not_sent`; the freeze makes zero provider
  calls and does not include the active external Flickr fetch.
- Pack: `australian-butterflies-v1`, version `v1`, 463 accepted species,
  manifest SHA-256
  `41f74251dedc53f319d22e266dc7c4d01757a5dd457a4e729a79a80b09006b5a`.
- Worker: no separate semantic package version exists, so the truthful version
  is worker tree `7503b6f7076f1b47e42675d4b2d3e23bbdddb49a` plus identity contract
  `butterflylens-worker-identity:v1.0.0`. No live identity, heartbeat, model
  configuration, MPS state, or resource observation is attached.
- Models: YOLOE remains `blocked_not_executed`; BioCLIP remains
  `skipped_unfinished_by_goal_instruction`. Both have null IDs/revisions/weight
  fingerprints and zero execution claims. The analyst is configured for
  `bounded-model`, but Submitted mode is a stored replay with no model invocation,
  no network call, and no live-model evaluation.
- Review: the CC BY-SA 4.0 Wikimedia Commons fixture is available for a local
  blind draft. The Submitted snapshot records zero stored review events, zero
  completed consensus records, zero representative or decisive reviews, zero
  human-verified media, disabled community writes, and no scientific claim.
- Map: exact internal ALA counts are retained, while the public projection is
  `scope_only_occurrences_withheld`. Displayed occurrence, cell, and admitted
  Flickr-candidate counts are null—not fabricated zeroes—and absence inference
  remains forbidden.

## Verification

- Seven focused freeze tests pass: exact rebuild, SHA/Git identity, ALA/map
  rights, Flickr plan, pack/worker/model versioning, review non-persistence, and
  fingerprint tamper rejection.
- All 583 locked Python tests pass in 21.2 seconds.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  typecheck, 119-package licence verification, media checksum, and production
  build pass. The existing 1.50 MB chunk warning remains non-blocking.
- All 10 Playwright Chromium, Firefox, WebKit, mobile, reduced-motion,
  forced-colour, and no-WebGL checks pass with the previously documented local
  WSL dependency cache.
- All 45 frozen Deno Edge tests pass; four entry points type-check and all 22
  function files pass formatting.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixture roots, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- The rights verifier covers 53 tracked provider/data/media payloads, including
  a metadata-only record for this snapshot that retains every child right and
  release block. Staged licensing covers 562 files and exact dependency
  manifests with zero model files.
- Snapshot, security, rights, licensing, JSON/JSONL, workflow YAML, shell,
  Python compilation, generated/model/media, large-file, secret, staged-scope,
  whitespace, and `git diff --check` gates are completed immediately before
  commit.

## Provenance and external-work boundary

This task depends only on already committed immutable local evidence, so no
current external fact was required and Valyu was not needed. GitHits remained
disabled by user instruction and was not called. No external implementation
was copied.

BioMiner remains at
`55b253aa7253d3001a51271e4bfd62dffa8ae83a`, with its committed TaxaLens 14.1
handoff and active uncommitted ButterflyLens handoff/model follow-on work. No
complete immutable ButterflyLens handoff exists, so no partial GBIF, Flickr, or
model data was copied. The current BioMiner SHA is a coordination observation,
not an input to the frozen snapshot. The snapshot retains only the already
committed reference-bank origin SHA it actually consumes.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, output inspection/import,
Supabase/B2 mutation, provider submission, live GPT call, YOLOE work, BioCLIP
work, scientific model call, scientific inference, or third-party media copy
occurred.

Next safe task: prepare Task 16.2's scheduler state without issuing Flickr API
calls or duplicating the already active external fetch.
