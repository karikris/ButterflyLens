# Task 17.3 plan — three-minute demonstration script

Task ID: `butterflylens-17.3`
Objective: produce a truth-safe, production-ready 2:48 demonstration script,
caption file, and shot manifest for the public ButterflyLens video.
Competition criterion improved: sub-three-minute product demonstration with an
explicit Codex/GPT-5.6 explanation and artifact-backed public claims.
Starting SHA: `c6037ca37871c3db819f7fd780158ef352e85e51`
Remote main SHA: `c6037ca37871c3db819f7fd780158ef352e85e51`
BioMiner SHA: `143687e6ced5d4a65de80601042cc4ba79bec721`
TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`

Relevant agent files read: `AGENTS.md`, `docs/agents/TOOLS.md`,
`docs/agents/GIT_AND_PROVENANCE.md`, `docs/agents/TESTING_AND_RELEASE.md`, and
`docs/agents/TASK_TEMPLATE.md`.
Relevant skill: none installed for video/presentation artifacts. The imagegen
skill is not applicable because the recording must show the real product. The
GitHub yeet skill is incompatible with the user-required direct-main,
exact-subject, no-PR workflow.
GitHits needed: unavailable and disabled for the rest of the goal by direct
user instruction.
Valyu needed: no. The script is derived only from versioned local product and
Submitted evidence; no mutable external claim is introduced.

Files expected:

- `DEMO_VIDEO.md`
- `assets/video/butterflylens-demo.en-AU.srt`
- `assets/video/butterflylens-demo.v1.json`
- `tests/test_demo_video.py`
- Task plan/report and append-only provenance/tool logs

Contracts affected: a documentation-only `butterflylens-demo-video/v1` shot
manifest; no runtime, API, data, or database contract changes.
Data/rights implications: record only the existing public Submitted replay and
its rights-cleared local fixture; do not show or quote the active external
Flickr fetch, private data, exact sensitive locations, or unfinished model
output.
Scientific risks: a fast demo could turn missing values into zeros, call
Flickr candidates occurrences, imply a local draft updates evidence, describe
the replay as a live GPT call, or imply geographic absence. Each shot must name
the actual fail-closed boundary.
Security/privacy risks: no credentials, Supabase/B2 consoles, private worker
telemetry, reviewer identities, or source-image collections may appear.
Tests: focused manifest/caption/script unit tests; full Python/web/Deno/browser
and contract gates; snapshot, security, rights, licensing, JSON/JSONL,
compilation, staged-scope, large-file, shell, and whitespace checks.
Rollback/recovery: remove the documentation packet and its focused test; the
runtime and Submitted snapshot remain unchanged.

## Patch plan

1. Pin every required shot to a real public product surface at the starting
   commit and allocate an exact, contiguous 168-second timeline.
2. Script narration that distinguishes Submitted from Live, candidates from
   occurrences, local drafts from stored reviews, unavailable intervals from
   zero, replay from model invocation, and documentation from export release.
3. Add synchronized captions and a machine-readable manifest that proves the
   sequence, duration, product-footage share, evidence sources, and publication
   status.
4. Validate the packet and all release boundaries, then commit and push with
   the exact requested subject.

## Parallel-work boundary

BioMiner advanced to `143687e6ced5d4a65de80601042cc4ba79bec721`
while retaining uncommitted Flickr estimator, keyword, query, and log work. No
complete immutable ButterflyLens data handoff receipt was found, so no active
or partial output will be copied. The separately active Flickr fetch is not
inspected or called. YOLOE and BioCLIP remain unfinished and will be shown only
as unavailable states already present in the Submitted application.
