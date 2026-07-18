# ButterflyLens 15.3 — community journey E2E

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`7ee83b75870af56e67965a272193e177cf07e4e0`.

## Outcome

ButterflyLens now has one credential-free end-to-end community journey that
renders the exact assembled submitted `App` and follows all eight Task 15.3
judge steps in order. It does not replace production surfaces with test-only
component doubles, and it installs a failing `fetch` boundary so any accidental
network dependency fails the route.

The route opens the landing page and confirms the submitted experience,
authoritative rebuilt baseline, and candidate-evidence release boundary. It
loads the existing integrity-checked, rights-attributed review image, waits
until scientific choices are enabled, records an explicitly uncertain local
draft with a visible reason, locks that draft, and only then reveals the
allowlisted post-decision context and Wikimedia Commons source.

The review remains explicitly local and not submitted. The route proves it
cannot fabricate a public map update: the review map retains unavailable
location evidence, while the operations map remains tied to the exact
committed submitted refresh at `2026-07-17T19:14:01Z` and keeps the occurrence
layer withheld.

The route then searches all 463 accepted species for `Acraea andromacha`, opens
that exact species page, and inspects its submitted evidence. Human-verified
media remains zero as a workflow count, and unfinished YOLOE/BioCLIP state
remains visible rather than being converted into a negative identity result.

## Live, GPT, quality, and export steps

The pipeline step verifies the worker-independent map shell, committed species
snapshot link, submitted monitoring fallback, unavailable worker status, and
unfinished model state. No worker or monitoring endpoint is required.

The analyst step chooses the exact stored Acraea question, replays it, opens
the one-call `inspect_species` trace, verifies its result fingerprint, and
opens all three pinned artifact citations. The rendered result states that no
model was invoked, and the test confirms no fetch occurred.

The quality step distinguishes the zero reviewed workflow sample from an
unavailable precision estimate, opens the exact method/provenance disclosure,
and checks the rebuilt baseline plus model-vote exclusion boundary.

The final step reaches the governed Darwin Core export and ALA contribution
preparation policies. Because the submitted repository has no public
release-ready occurrence archive, the route explicitly proves that no download
link is invented. This is the honest evidence-export state, not a successful
provider submission or publication claim.

## Verification

- The focused eight-step journey passes in 0.45 seconds with zero fetch calls.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- The complete locked Python suite passes all 572 tests in 20.0 seconds.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixtures, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing passes for 541 pre-stage tracked files and 544 files after staging
  the exact Task 15.3 scope, with zero model files.

## Scope and external-work boundary

This is a component end-to-end journey in Vitest/jsdom. It proves assembled
React state and interaction linkage, but it does not claim Chromium, Firefox,
WebKit, viewport, reduced-motion, high-contrast, pixel, or real-navigation
coverage. Those are Task 15.4.

GitHits remained disabled by explicit user instruction and was not called.
Valyu was not needed because the exact versioned submitted experience is the
test subject. No external implementation was copied, and the existing
rights-cleared review media was not changed.

BioMiner advanced to
`5635dfcc9f6a0019cd00bb56fcc02ad5e2b48053` with an intermediate TaxaLens
pooling-evidence exporter. That commit contains implementation and tests, not a
complete immutable ButterflyLens data handoff. Its worktree remains active on
follow-on quality/handoff code, so no partial artifact was copied. The rebuilt
ButterflyLens ALA baseline remains authoritative.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, external result import, Supabase
or B2 mutation, provider submission, archive generation, media copy, live GPT
call, YOLOE work, BioCLIP work, scientific model call, or scientific inference
occurred.

Next safe task: add Task 15.4 real-browser and visual public-experience
coverage after this exact commit is pushed and its Pages deployment is
verified.
