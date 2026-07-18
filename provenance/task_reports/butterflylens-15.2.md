# ButterflyLens 15.2 — integration coverage

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`95ff299b598ced7890b74cf5bbcc280dac62ab53`.

## Outcome

ButterflyLens now has eight deterministic cross-component integration tests,
one for every flow required by Task 15.2. The tests exercise production
contracts and committed submitted artifacts while substituting only private
temporary files, in-memory durable acknowledgements, and one injected local
Flickr callback.

The ALA path recomputes every artifact checksum in the authoritative pack and
then follows the pack manifest into the 463-species submitted catalogue,
operations map, and checksum-verified GPT artifact repository. It proves that
the rebuilt baseline remains authoritative and that its unresolved dataset
rights state keeps ALA occurrence evidence withheld and the public occurrence
layer hidden.

The Flickr path begins with an eligible authoritative name assertion, compiles
its logical definition, binds its taxon association, deduplicates a physical
request, and schedules that request through the adaptive Australia lane. It
then creates one state/time partition and one page checkpoint, reserves exactly
one unit of the one-key hourly budget, and checkpoints a one-photo response
from a local callback. The callback is software-fixture code, not an HTTP
client or Flickr API call. The credential stays separate and is absent from
the persisted execution result.

The M5 path admits caller-supplied JPEG bytes through bounded queues, verifies
their checksum and type, requires durable source/Parquet/checkpoint
acknowledgements, deletes cache only afterward, journals the immutable
checkpoint, and proves a restarted worker reuses it. A stale heartbeat then
projects the worker offline while keeping the submitted and committed live
snapshots queryable.

## Scientific and community boundary

The model path carries the worker's explicit `unfinished_not_run` YOLOE and
BioCLIP states into classification maturity. Missing model evidence remains
unavailable rather than false; it produces no score, probability, identity,
release, or scientific claim.

The review path carries two independent human review events through unweighted
community and qualified consensus, a stratified representative quality audit,
and self-only contributor impact. Complete agreement still reports
`not_release_ready` without the remaining gates. The quality estimate excludes
model votes, and contributor impact exposes neither speed nor rankings.

The map path supplies all nine occurrence-release gates but deliberately fails
the rights gate. The deterministic decision stays blocked and never claims a
published occurrence. The public operations snapshot remains hidden, while
the RLS policy independently requires both a publishable location receipt and
an occurrence release receipt before map visibility.

## GPT and export boundary

The GPT path invokes local deterministic tools against their exact pinned
submitted repository. It retrieves the accepted species count while retaining
withheld ALA counts, unfinished YOLOE/BioCLIP states, absent probability, and
submitted-only pipeline state. It makes no Responses, model, provider, or
database call.

The export path carries one synthetic release-receipt-backed candidate through
the deterministic Darwin Core archive and then the private ALA contribution
preparation archive. Record-specific media rights and lineage survive, but the
pending Data Provider Agreement keeps the archive
`blocked_pending_provider_requirements`, `not_submitted`, and
`prepared_not_published`. No automatic submission capability is introduced.

## Verification

- All eight focused Task 15.2 integration tests pass in 0.12 seconds.
- The complete locked Python suite passes all 572 tests in 19.5 seconds.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixtures, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing passes for 537 pre-stage tracked files and 541 files after staging
  the exact Task 15.2 scope, with zero model files.
- The first raw Python discovery command omitted the existing ALA test's
  required package path, and the first parity command used an obsolete test
  path. Both runner commands were corrected to the documented package paths;
  the complete gates then passed without implementation changes.

## Research and external-work boundary

The task depends only on versioned local code, committed evidence artifacts,
and deterministic fixtures. Valyu is logged not needed. GitHits remained
disabled by explicit user instruction and was not called. No external
implementation was copied.

BioMiner was inspected only through Git state and its complete published
`docs/agents/CURRENT_STATE.md` coordination record. It advanced to
`900301dfb33a818dffaebc2a59bd4d1e86f34cd7` and began active Phase 14 handoff
work with dirty Flickr/TaxaLens-related files. It still supplies no immutable
ButterflyLens handoff, so no active data or partial output was copied. The
rebuilt ButterflyLens ALA baseline remains authoritative.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No external Flickr result was inspected or imported.
No Flickr API call, GitHits call, Supabase or B2 mutation, provider submission,
media copy, production workflow dispatch, YOLOE work, BioCLIP work, scientific
model call, or scientific inference occurred.

Known limitation: these integration fixtures prove current contract linkage
and fail-closed behavior, not live provider availability, production database
deployment, real human review, provider acceptance, or biological accuracy.

Next safe task: implement the Task 15.3 browser community journey after this
exact commit is pushed and its Pages deployment is verified.
