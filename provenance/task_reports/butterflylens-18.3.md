# ButterflyLens 18.3 — rights-screened submitted ALA map

Status: **submitted ALA map task complete; the overall ButterflyLens goal and
public release remain unfinished**.

Starting and remote SHA:
`c7d6efda5a122502383ae66830e7b117259e5de2`.

Subtask commits:

- `cfe6b5f38b687e83d2a601d381edde29fcb7a717` — deterministic rights-screened
  ALA projection and Parquet artifacts;
- `1c4fcf128749b25446c3ec22b62e7f5db775d42b` — accessible offline Submitted
  map, exact drilldowns, and synchronized table.

Ending and remote SHAs: pending the containing Task 18.3 closeout commit and
non-force task push.

## Outcome

The rebuilt ButterflyLens ALA baseline remains authoritative and unchanged at
236,897 selected records. A separate fail-closed public projection excludes all
16,753 selected records from the three datasets already marked
`blocked_pending_citation_rights_resolution`; this is a conservative publication
choice and not a legal conclusion. The projection contains 220,144
rights-screened selected records and maps 213,310 spatially eligible records.

The excluded datasets are:

- `dr1097`, Victorian Biodiversity Atlas: 15,268 selected and spatial records;
- `dr30019`, Natural History Museum Rotterdam - Specimens: 360 selected and
  324 spatial records;
- `dr635`, NatureShare: 1,125 selected and spatial records.

No raw occurrence coordinates are included in the browser snapshot. The public
projection contains aggregate H3 geometry and exact aggregate counts only.
Flickr, YOLOE, BioCLIP, review, human-supported-additional, and
release-ready-additional values remain unavailable with explicit reasons and
null values; none is represented as zero.

## Artifacts

- `geographic_impact_cells.parquet`: 630 H3 resolution-3 rows, 70,885 bytes,
  SHA-256
  `f6ed6f8bdaf6385ea91ed47d98b77f31817f5880c02c4d604c4d4310b3080ed0`;
- `geographic_impact_summary.parquet`: 23,484 rows, 2,542,291 bytes, SHA-256
  `c85952e63dda07003b68bd54ce8fb9c1ecc7116d8d3119868b12d28a1d5a3be3`;
- `map_manifest.json`: SHA-256
  `fe37f6c004dbed987b81293a5a5602afdac8683a59d4e85b651ca5732b3c8015`;
- browser snapshot: 1,458,054 bytes, SHA-256
  `2033dadaa67427768fde54c6f16b509bddae382bb9e38fb9cdbdbd6c9a43281e`.

The summary contains one Australia row, nine state/territory rows, 87 IBRA
rows, 532 LGA 2023 statistical-approximation rows, 630 coarse H3 rows, 4,960
regional H3 rows, and 17,265 local H3 rows. Every coarse cell validates against
the existing geographic-impact contract.

## Public experience

The Explore view uses native SVG and committed data only: no external tiles,
network calls, WebGL, or canvas. It provides a blue ALA H3 heatmap, an explicit
unavailable Flickr legend, Submitted/disabled-Live modes, selected-cell details,
coordinate-free provider samples, state/territory, IBRA, LGA, and H3
drilldowns, exact tables, rights context, keyboard access, responsive layout,
reduced-motion handling, and forced-colour support. The full 630-cell exact
table remains synchronized with map selection.

The first local browser attempt stopped before application startup because the
WSL host lacks browser runtime libraries. Reusing the existing documented
Playwright host-library cache allowed the functional suite to run. That run
identified a narrow-screen heading overflow; the flex and wrapping rules were
corrected, after which all seven functional browser variants passed.

## Verification

- Eight focused deterministic map-builder tests pass, including byte-identical
  rebuild and unavailable-layer false-claim checks.
- The corrected final Python repository suite passes all 651 tests in 30.071
  seconds.
- All 21 Vitest files and 100 tests plus three standalone Node tests pass.
- The web production build passes. Its existing large-bundle warning remains
  non-blocking.
- Seven functional Playwright variants pass across Chromium, Firefox, WebKit,
  mobile Chromium, reduced motion, forced colours, and no WebGL.
- Cross-language parity passes for 25 schemas, 21 valid roots, 21 invalid
  roots, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 623 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 599 tracked text files, and 11 explicit network
  boundary files while retaining `release_ready=false`.

The full-suite inventory exposed two deterministic closeout assumptions. The
contract-coverage inventory now registers the completion-audit and submitted-map
schemas/projection. Replaying the GBIF publisher now preserves its original
source and artifact insertion positions instead of moving those records past
later append-only map rights records.

## Binding unfinished work

BioMiner is still fetching Flickr metadata only. Its mutable partial output was
not inspected, copied, or counted, and ButterflyLens made no Flickr API call.
The immutable Flickr handoff, cross-layer map comparisons, YOLOE, BioCLIP,
human review, representative quality estimates, observed live worker evidence,
video recording, publication approval, and public release remain unfinished.
The fixed Task 18.2 completion audit remains historical and is not silently
rewritten by this follow-on task.

GitHits remained unavailable and was not called. No provider, OpenAI, Supabase,
B2, model, image-generation, or video-generation mutation occurred.
