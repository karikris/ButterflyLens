# ButterflyLens 17.4 — competition deck and Devpost copy

Status: **deck and copy complete and locally verified; external Devpost
submission, screenshots, human approval, and public video remain unfinished**.

Starting SHA: `6db0d3319d9309150c55e874fcaca753ded573f6`.

Ending SHA: pending the containing Task 17.4 commit.

Remote SHA: pending the containing Task 17.4 push.

BioMiner SHA: `65b98ce4bed1d8b799ef0396fea5515921621e68`.

TaxaLens SHA: `e845dd98493979f37b04dbb6538e0d7b8758ca11`.

## Outcome

`PITCH_DECK.md` is a ten-slide, 16:9, evidence-first competition narrative. It
moves from the evidence-workflow problem through the working product, journey,
architecture, community quality design, Bounded model/Codex roles, exact Submitted
measurements, current boundaries, and public ask. Every slide includes concise
on-slide copy, speaker notes, and visual/proof instructions that favour real
product footage over decorative or generated imagery.

`DEVPOST_ENTRY.md` contains paste-ready project name, tagline, category, winning
line, short description, inspiration, product journey, implementation, Bounded model
and Codex roles, challenges, accomplishments, lessons, next steps, links,
technology, credits/licences, public claims ledger, and submission preflight.
The README now links the deck, entry copy, judge guide, and video script.

The exact user-supplied winning line appears unchanged:

> “ButterflyLens brings machine screening, community expertise, and Australia’s
> national biodiversity evidence together to reveal where public imagery could
> strengthen butterfly knowledge.”

Both documents label it as the product thesis because machine screening remains
unfinished in the current Submitted snapshot.

## Evidence and claim boundaries

The deck and entry may publish only numbers bound to the canonical snapshot or
the measured release gate:

- 463 accepted species;
- 236,897 selected ALA rows, 230,027 spatially eligible rows, and 23,744
  aggregate rows as internal inventory with public occurrence display withheld;
- 1,876 Flickr query definitions and 1,754 deduplicated physical requests,
  deterministic and unsent in the frozen snapshot;
- 2,906 valid reference decodes and 0 human-verified species; and
- 610 Python tests at this task gate, plus the unchanged 92 Vitest, three Node,
  45 Deno, 10 browser, and 25-schema parity measures. The Task 17.3 deck copy
  deliberately cites its preceding 603-test release receipt; a future final
  submission update may cite the later 610 count after its containing commit is
  recorded.

The public claims ledger blocks completed Flickr totals, public occurrence and
impact cells, identity, community review/consensus, reviewer reliability,
representative quality estimates, live M5/model/analyst results, public export,
finished video, or overall release readiness.

## Verification

- Seven focused submission tests pass: exact winning-line preservation, exactly
  ten ordered complete slides, paste-ready Devpost sections, frozen artifact
  numbers, Bounded model/Codex and fail-closed language, exact public links and README
  discovery, and explicit unfinished-output boundaries.
- The combined competition-document suite passes all 26 focused README, guide,
  video-packet, deck, and entry checks.
- All 610 locked Python tests pass in 21.9 seconds.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  TypeScript, the 119-package dependency licence report, review-media checksum,
  and production build pass. The unchanged script remains 1,496.87 kB / 229.80
  kB gzip with the existing non-blocking chunk-size warning.
- All 45 frozen Deno Edge tests pass under cached Deno 2.9.3; all four entry
  points type-check and all 22 function files pass formatting.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid roots,
  21 versions, and 15 vocabularies using TypeScript 7.0.2.
- All 10 Playwright browser and visual checks pass across Chromium, Firefox,
  WebKit, mobile, reduced motion, forced colours, and no WebGL using the exact
  previously documented untracked host-library paths.
- Canonical snapshot, security, rights, licensing, JSON/JSONL, shell, tracked
  Python compilation, whitespace, staged-scope, generated-media, binary/model,
  secret, and large-file checks are run again against the final staged patch
  immediately before commit.

## Rights, privacy, provenance, and parallel work

The new artifacts are text only. No slide renderer, external template, generated
image, third-party media, private screen, active data, model output, or external
submission was used. Future deck imagery is restricted to real public product
captures and the existing rights-checked review fixture. The copy excludes
credentials, reviewer identities, sensitive locations, private worker telemetry,
and the unverified Flickr checkpoint.

Task 17.3 commit `6db0d3319d9309150c55e874fcaca753ded573f6`
was pushed at `2026-07-18T14:59:40Z`. Pages run `29649102842` built that SHA in
22 seconds, deployed it in 10 seconds, and the immutable raw script, manifest,
captions, README link, publication-null state, and served Pages base path were
verified.

GitHits remained disabled by direct user instruction and was not called. No
current Devpost field rule or mutable external fact is asserted, so Valyu was
not used. No installed deck/presentation skill exists; imagegen was not
applicable because real product evidence is required. The PR-oriented publishing
skill conflicts with the direct-`main`, exact-subject, no-PR workflow and was not
used.

BioMiner advanced to
`65b98ce4bed1d8b799ef0396fea5515921621e68` while retaining active uncommitted
Flickr estimator, keyword, query/log, and pooling-ablation work. No complete
immutable ButterflyLens handoff receipt exists, so no partial GBIF, Flickr,
review, model, or pooling output was copied. TaxaLens was not an input.

No Flickr API call, GitHits call, Supabase/B2 mutation, provider submission,
Devpost mutation, live GPT call, image/video/audio generation, public upload,
YOLOE work, BioCLIP work, scientific model call, scientific inference, or
third-party media copy occurred.

Scientific claims allowed: exact frozen artifact counts and states, exact public
routes, exact winning line as thesis, measured test/build properties, and
descriptions of implemented contracts and safeguards. Scientific claims
blocked: identity, verified occurrence, biological absence, Flickr completeness,
stored community evidence, consensus, quality estimates, geographic impact,
live worker/model state, released export, completed public video, or release
readiness.

Human work remaining: select and capture exact product visuals, review the deck
and entry for competition tone, verify all links and measurements at the final
release SHA, finish and approve the public YouTube video, paste the approved
copy into Devpost, and submit it as Kris Kari.

Next safe task: complete the Build Week provenance delta, including the primary
`/feedback` Session ID boundary and exact new/imported/human/test evidence.
