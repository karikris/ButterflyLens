# ButterflyLens 17.1 — competition README

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`dc0dbe8b11a3621b6494e8fe43d15aebfcc00e9d`.

## Outcome

The README now opens with the ButterflyLens name, evidence-safe live-map
tagline, real working-product GIF, Help Verify, Open Live Map, and Submitted
Replay actions, current unavailable worker state, the frozen measured result of
463 accepted species, explicit GPT-5.6 and Codex roles, and compact architecture.
The 960×540 source GIF is displayed at 560 pixels wide so the complete hero
remains compact; its eight frames and 327,789 bytes are pinned by SHA-256
`223e3f21d0a82b41d801ef470edfe31b999ff21457d1949885ab56f5444ebc1d`.

The page then gives a credential-free judge route, canonical snapshot
fingerprint and measured inventory, Submitted-versus-Live boundary, detailed
architecture, governance links, and the offline development path. It never
turns the named “Live Map” route into a claim that live occurrence data, a
worker, community writes, model results, or the external Flickr fetch are
attached.

## Real capture and rights

The GIF was captured from the local production build's actual `#live` surface
with Playwright 1.61.1, resized with temporary Sharp 0.35.3 tooling, and encoded
with temporary gifenc 1.0.3 tooling. The capture route blocked every non-local
origin. It contains only the project-owned map shell, submitted catalogue card,
fingerprint, species count, and evidence-boundary copy; the attributed review
photograph is not present. No external request, provider payload, credential,
live status, scientific model output, or active-run artifact entered the GIF.

## Submitted-artifact integration repair

The first full gate after Task 16.1 made its newly tracked submitted snapshot
visible to the exhaustive contract inventory. This task registers that artifact
with positive reproducibility and negative tamper coverage.

It also exposed two pre-existing mutable-worktree assumptions. The public
catalogue is the immutable Task 10.3 artifact, so its deterministic test now
loads the data-rights manifest from the catalogue's recorded source commit
instead of rebuilding against unrelated later metadata. Likewise, the analyst
repository now reads and verifies every artifact from the exact Git commit its
citations name. A test proves that Task 16.1's later working-tree rights record
cannot silently alter the older Submitted analyst view. No catalogue, replay,
evaluation, measured count, or registry fingerprint was rewritten.

## Verification

- All five focused README tests pass: first-screen content, public action links,
  measured state, architecture boundaries, and GIF version, dimensions, frame
  count, byte count, size ceiling, and fingerprint.
- All 589 locked Python tests pass in 20.6 seconds, including submitted-freeze,
  catalogue reconstruction, contract inventory, immutable analyst repository,
  replay, integration, privacy, and policy-link coverage.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  typecheck, the 119-package licence report, media checksum, and production
  build pass. The unchanged built script is 1,496.87 kB / 229.80 kB gzip and
  retains the existing non-blocking chunk-size warning.
- All 10 Playwright browser and visual checks pass across Chromium, Firefox,
  WebKit, mobile, reduced motion, forced colours, and no WebGL. The same exact
  untracked extracted host libraries documented in Task 15.4 were supplied; the
  validator was skipped only because its `ldconfig` probe cannot see those
  directories, while all engines actually launched and completed assertions.
- All 45 frozen Deno Edge tests pass; four entry points type-check and all 22
  function files pass formatting.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid roots,
  21 versions, and 15 vocabularies with TypeScript 7.0.2.
- Release security scans 548 tracked text files and retains all 11 explicit
  blockers; rights verification covers 53 provider/data/media payloads and
  staged licensing covers 567 files with zero model files.
- Snapshot, security, rights, licensing, JSON/JSONL, workflow YAML, shell,
  Python compilation, generated/model/media, large-file, secret, staged-scope,
  whitespace, and `git diff --check` gates are completed immediately before
  commit.

## Provenance and external-work boundary

Task 16.1 commit `dc0dbe8b11a3621b6494e8fe43d15aebfcc00e9d`
was pushed at `2026-07-18T13:51:48Z`; Pages run `29646935783`
successfully built and deployed that exact SHA. This normal next-task receipt
avoids circular self-SHA metadata.

GitHits remained disabled by user instruction and was not called. No current
external fact was required, so Valyu was not needed. BioMiner is currently at
`088bd99cd1b0efafba5c553a6a65a4772ac2012d` with committed follow-on handoff
code and active uncommitted work, but no complete immutable ButterflyLens data
receipt; nothing was copied. TaxaLens was not an input to this task.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, fetch-output inspection or import,
Supabase/B2 mutation, provider submission, live GPT call, YOLOE work, BioCLIP
work, scientific model call, scientific inference, or third-party media copy
occurred.

Scientific claims allowed: exact frozen artifact counts, fingerprints, states,
and locally measured build/test/GIF properties. Scientific claims blocked:
butterfly identity, occurrence verification, Flickr completeness, ALA absence,
public occurrence display, model quality, community consensus, worker liveness,
or release readiness.

Next safe task: write the 90-second judge guide from this exact Submitted hero
and route without presenting unfinished live tasks as complete.
