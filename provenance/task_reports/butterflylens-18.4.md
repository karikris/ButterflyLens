# ButterflyLens 18.4 — submitted map analyst and judge reconciliation

Status: **submitted map reconciliation complete; the overall ButterflyLens goal
and public release remain unfinished**.

Starting and remote SHA:
`982238de0f7ff438403d40b03856f330de7794fc`.

Subtask commits:

- `609433e0e765cc3ba7d1b894db44e3cd2c4381f0` — checksum-pinned map evidence
  tools in Python and the shared Supabase Edge boundary;
- `e380d2a39314a96cb4b4097a402cf90a36790484` — regenerated stored analyst
  replay and 48-case deterministic evaluation suite;
- `5f257bc2ab7e514d078db8aa76c98f8ce7c4cf17` — map-first public anchor,
  operations summary, README hero capture, and 90-second judge route.

Ending and remote SHAs: pending the containing Task 18.4 closeout commit and
non-force task push.

## Outcome

The deterministic analyst tools now admit the checksum-pinned Task 18.3 public
map as direct aggregate evidence. National, state/territory, IBRA, LGA
approximation, and H3 scope identifiers require exact matches. Tool results
include bounded coordinate-free evidence records and never expose raw centers,
polygons, or occurrence coordinates.

The national submitted result reports 213,310 rights-screened, map-eligible ALA
rows across 630 coarse H3 cells. The complete 236,897-selected-record rebuilt
ALA baseline remains authoritative; the public projection excludes all 16,753
selected rows from the three already flagged datasets. That conservative screen
is not a legal conclusion and does not grant full occurrence release.

Flickr remains unavailable in every comparison. No count difference is
calculated from one source, unavailable is never rendered as zero, and no
species-level occurrence count is invented from the non-species-granular map.

## Stored analyst evidence

The regenerated stored replay pins implementation commit
`609433e0e765cc3ba7d1b894db44e3cd2c4381f0` and map-data commit
`cfe6b5f38b687e83d2a601d381edde29fcb7a717`. The national comparison makes one
direct cited ALA aggregate claim while retaining null unavailable Flickr and
two-source-difference claims. It records zero model calls and zero network
calls and explicitly excludes BioMiner's active metadata fetch.

All 48 deterministic evaluation cases pass. Live-model status remains
`not_run`; the evaluation therefore reports
`deterministic_gate_passed_live_model_not_run`, not a live GPT-5.6 result.

## Public judge experience

The public `#live` anchor now opens the rights-screened heatmap rather than the
older historical map shell. Operational monitoring has the separate
`#operations` anchor and summarizes the same committed aggregate while keeping
the frozen Task 16 evidence snapshot unchanged.

The README and Judge Guide now demonstrate an exact selected H3 cell, its
fingerprint, and its coordinate-free provider-record sample. They label the
layer as evidence coverage rather than presence, absence, abundance,
identification, or a cross-source coverage gap.

The 960×540 eight-frame GIF is a local production-browser capture of the real
map surface. Its SHA-256 is
`2dea64aad4f960b35caf57f26309e6324b49c2a257bdd703eb0b91a65fa6b975`
and its size is 285,315 bytes. Every non-local browser request was blocked. No
third-party photograph, external tile, provider response, credential, model
output, or active-run artifact appears in it.

## Verification

- The full Python repository suite passes all 653 tests in 31.049 seconds.
- All 21 Vitest files and 100 tests plus three standalone Node tests pass.
- The production build, TypeScript check, 119-package dependency-licence
  report, and review-media checksum pass. The existing large-bundle warning
  remains non-blocking.
- All 10 Playwright browser and visual checks pass across Chromium, Firefox,
  WebKit, mobile Chromium, reduced motion, forced colours, and no WebGL.
- All 46 Deno Edge tests pass with the pinned function import map.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 625 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 601 tracked text files, and 11 explicit network
  boundary files while retaining `release_ready=false`.
- The fixed Task 18.2 completion audit still validates with
  `goal_complete=false`; JSON generation, fingerprints, compilation, and
  whitespace checks pass.

The full pass exposed three stale downstream references: demo-video evidence
checksums, navigation target discovery, and the browser's old withheld-layer
assertion. The closeout updates those references to the exact new replay,
artifact registry, map anchor, and aggregate-map state.

## Binding unfinished work

BioMiner is still fetching Flickr metadata only. Its mutable partial output was
not inspected, copied, or counted, and ButterflyLens made no Flickr API call.
The immutable Flickr handoff, ALA/Flickr comparison, YOLOE, BioCLIP, human
review, representative quality estimates, observed live worker evidence, live
GPT-5.6 evaluation, video recording, human approval, and public release remain
unfinished.

GitHits remained unavailable and was not called. No connected Supabase project,
provider, OpenAI, B2, model, image-generation, or video-generation mutation
occurred.
