# ButterflyLens 18.7 — submitted-map video production packet

Status: **map-aligned production packet complete; the final recording, human
review, public video, overall ButterflyLens goal, and release remain
unfinished**.

Starting and remote SHA:
`27a37f078006436d387b3e07242ca5a29d84668e`.

Subtask commit:

- `f534c6bb88dae54472ea56922153a0a9598a4831` — versioned v2 script,
  captions, shot manifest, artifact-derived claims, and fail-closed validator.

Ending and remote SHAs: pending the containing Task 18.7 closeout commit and
non-force task push.

## Outcome

The current 2:48 production script now records the real rights-screened
Submitted ALA map rather than the stale pre-map shell. Its first shot derives
the authoritative 236,897 selected-row baseline and the conservative public
213,310 map-eligible-row, 630-cell projection from fixed artifacts. It states
that the projection excludes all selected rows from three flagged datasets,
publishes no raw coordinates, is not a legal conclusion, and is not complete
biological truth.

The map-update shot selects exact H3 scope `h3:3:838c23fffffffff`, shows its 224
ALA baseline rows, binds them to evidence fingerprint
`ddac9c308e2bf80d3ee45d777359cfbdcdca8bfb10b22c9cdd88e2fff77dd233`,
and uses the coordinate-free provider-record sample. The geographic-impact
shot now demonstrates the available state/territory, IBRA, LGA approximation,
and H3 drilldowns while retaining unavailable Flickr and cross-source impact.

The Bounded model shot now uses the map-grounded stored question “Can ALA and Flickr
counts be compared yet?”. Its deterministic replay cites the 213,310-row ALA
aggregate, preserves a null Flickr count and null difference, records zero
model calls, and explicitly excludes active BioMiner output.

## Versioned packet and validation

`assets/video/butterflylens-demo.v2.json` pins capture source
`45fb5ac07dcd51852c9e92217667f3f5052868fe`, the canonical Submitted snapshot,
the submitted map snapshot, ten evidence-source checksums, measured claims,
and the exact source paths required for every shot. The validator checks both
the current bytes and the pinned Git bytes, so later drift fails closed.

The v2 caption file remains contiguous from 00:00 to 02:48, contains 22 cues,
and keeps every cue at or below 3.2 words per second. Working-product footage is
160 of 168 seconds, or 95.2 percent.

The historical v1 manifest and caption file remain byte-identical at SHA-256
`851cec43a9ed5da0e25a0046becb5daf91cbdb6a171a1ee9ad6e0fe170ca9b52` and
`dccdcc81bfaf1df7374160dd085b8129ed0bc4abb053fc04014291cb67998e48`.
They are retained as the pre-map record and are no longer the current recording
instructions.

## Verification

- The corrected complete Python repository command passes all 666 tests with
  `PYTHONPATH=packages/contracts/python`.
- The focused video, README, and judge-guide suite passes all 23 tests; 12 are
  direct v2 video-packet checks.
- All 21 Vitest files and 100 tests plus three standalone Node tests pass.
- The production build, TypeScript check, 119-package dependency-licence
  report, and review-media checksum pass. The existing large-bundle warning is
  unchanged and non-blocking.
- All ten Playwright browser and visual checks pass across Chromium, Firefox,
  WebKit, mobile Chromium, reduced motion, forced colours, and no WebGL. The
  documented untracked host-library cache and host-validation skip were needed
  on this WSL host.
- All 49 Deno Edge tests pass. Deno formatting passes for 24 files, and the
  recorder plus four Edge entry points type-check against the pinned config.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 639 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 615 tracked text files, and 12 explicit network
  boundary files while retaining `release_ready=false`.
- The current completion audit still validates at 80 satisfied criteria with
  `goal_complete=false`; the historical audit remains valid.
- JSON, JSONL, Python compilation, whitespace, and clean staged-scope checks
  pass.

The first raw Python discovery command omitted the local contracts package and
reported its already-documented import error; the corrected project command
passed all 666 tests. The first raw Playwright command lacked the documented
untracked host-library environment; the corrected full ten-test command passed.

## Binding unfinished work

No video was recorded, narrated, mixed, reviewed as a final cut, approved, or
uploaded. There is no public YouTube URL. Criteria 93 and 94 remain external
human/publication work and were not upgraded by this production packet.

BioMiner is still fetching Flickr metadata only. This non-overlapping task did
not inspect, copy, or count its mutable record and made no Flickr API call.
YOLOE and BioCLIP remain unfinished by user instruction. No OpenAI Responses
request, connected Supabase action, provider call, B2 action, image generation,
video generation, or public release occurred.

GitHits remained unavailable and was not called. Headroom receipt
`898dbe5ec3520d1425bf5d0f` covers the exact source goal. The updated
`AGENTS.md`, untracked `docs/agents/` pack, and user-owned Zone.Identifier were
read or preserved as instructed and were not staged.

The next completion step for this packet is human production: record the pinned
local build, add clear narration and captions, review scientific/right/privacy
accuracy, obtain Kris Kari's approval, publish the sub-three-minute video to
public YouTube, and commit the final URL and media receipt. That work requires
human recording and publication authority, so the repository can safely move
to the next independent unfinished task while BioMiner continues.
