# ButterflyLens — Devpost entry copy

> Submission status: copy-ready, but not ready to submit as complete. The final
> public YouTube demonstration, human approval, and unresolved release gates are
> still outstanding.

## Project name

ButterflyLens

## Tagline

Discover, review, and strengthen Australia’s butterfly data.

## Category

Work and Productivity

## Winning line

> “ButterflyLens brings machine screening, community expertise, and Australia’s
> national biodiversity evidence together to reveal where public imagery could
> strengthen butterfly knowledge.”

This is the product thesis. In the current Submitted snapshot, the machine
screening and live-data stages remain explicitly unfinished.

## Short description

ButterflyLens is a public evidence workspace that brings Australia’s rebuilt
ALA butterfly baseline, Flickr discovery candidates, optional M5 screening,
blind community review, quality estimation, geographic impact, and Bounded model
evidence analysis into one inspectable workflow. It keeps every search result a
hypothesis until rights, independent review, provenance, and release evidence
support a stronger claim.

**Search results are hypotheses—not biodiversity records.**

## Inspiration

Australia already has extraordinary national biodiversity evidence through the
Atlas of Living Australia, while people share vast numbers of nature photos in
public. The interesting question is not “How many photos can we find?” It is:
where could public imagery strengthen butterfly knowledge, and what work is
required before any candidate deserves to be treated as occurrence evidence?

That is a productivity problem for evidence. Discovery, review, quality,
geography, rights, model output, and export are often split across tools or
blurred into one confidence score. ButterflyLens makes those stages visible and
gives communities a careful path through them.

## What it does

ButterflyLens lets a judge or contributor:

1. inspect the Australia-scoped Submitted map and authoritative rebuilt ALA
   evidence boundary;
2. see how Flickr discovery is separated from public display and occurrence
   release;
3. review a rights-checked butterfly fixture blind, including an honest “Can’t
   tell” outcome;
4. distinguish a local draft from a stored community review;
5. inspect repeated-review, contributor, and representative-quality
   requirements;
6. ask the stored analyst replay what the fingerprinted evidence supports and
   inspect exact citations and tool traces;
7. see how optional M5 compute can add live status without gating the site; and
8. inspect occurrence-release and Darwin Core export contracts.

The Submitted route is public, resettable, credential-free, and independent of
Supabase, B2, OpenAI availability, a GPU, model downloads, and the M5 worker.
Missing evidence remains unavailable rather than becoming a favourable zero.

## How we built it

The public product is a TypeScript/React application built with Vite and served
from GitHub Pages. Python builds and validates the taxonomy, ALA baseline,
reference, review, quality, worker, and export evidence contracts. Deno Edge
Functions define strict live boundaries for the Bounded model analyst, private object
access, public monitoring, and governed control actions. Supabase and B2 are
live-service boundaries, not dependencies of the Submitted judge replay.

The scientific path is:

```text
authoritative rebuilt ALA evidence + Flickr discovery candidates
        → fingerprinted contracts
        → optional M5 screening
        → blind independent human review
        → representative quality + safe geographic impact
        → governed Darwin Core / ALA contribution export
```

BioMiner is the scientific evidence engine. ButterflyLens accepts only complete
immutable handoffs, so active or partial BioMiner/Flickr work cannot silently
become public product evidence. TaxaLens supplied a versioned verification
precedent and the attributed local review fixture through already recorded
upstream provenance.

## How we used Bounded model

Bounded model is designed as a bounded evidence analyst, not a species oracle. Its
strict read-only tools return small deterministic records. Completed claims
must cite the current tool output; refusal and incomplete states are first-class
results. The model may explain what evidence is missing or what workflow review
should happen next, but it cannot identify a butterfly from memory, override a
release gate, or turn a candidate into an occurrence.

For judging, the public product uses three stored, fingerprinted replays with
exact artifact citations and tool traces. The interface explicitly says **Model
not invoked**. No live provider call is disguised as part of the Submitted
experience.

## How we used Codex

Codex worked across the new ButterflyLens repository to design and implement
the product shell, deterministic evidence contracts, privacy/security/rights
boundaries, worker-independent replay, blind review, map, quality and analyst
surfaces, tests, documentation, and append-only provenance.

At the current verified gate, the repository passes 603 Python tests, 92 Vitest
tests plus three Node tests, 45 frozen Deno Edge tests, 10 real-browser and
visual checks, and Python/TypeScript parity for 25 schemas. Codex does not
supply butterfly identities, reviewer decisions, model results, or scientific
ground truth.

## Challenges we ran into

### Keeping discovery separate from occurrence

A Flickr label, comment, or search hit may be useful for discovery but is not a
biodiversity record. The product and contracts keep candidate, review,
consensus, quality, and release states distinct.

### Making unavailable evidence useful

It is tempting to fill an empty dashboard with zeros or simulated activity.
ButterflyLens instead makes unavailable, unfinished, withheld, and blocked
states visible and gives each one an exact next receipt.

### Rights and sensitivity across combined evidence

The rebuilt ALA inventory includes dataset-level rights that still need exact
review, Flickr media needs owner/licence/cache/removal evidence, and sensitive
locations need governed generalization. Those gates block public occurrence
layers and exports even when internal processing artifacts exist.

### Keeping the public product independent of live compute

The M5 worker can add optional screening and status, but it cannot be the public
server or sole source of truth. The immutable Submitted replay remains usable
with no heartbeat, model, database, or provider connection.

## Accomplishments we are proud of

- A public working replay with no login or private infrastructure dependency.
- An accepted Australian butterfly catalogue of **463 species**, bound to a
  canonical Submitted fingerprint.
- An authoritative rebuilt ALA inventory of **236,897 selected rows**, with
  public occurrence counts and layers still rights-withheld.
- A deterministic Submitted Flickr plan with **1,876 query definitions** and
  **1,754 deduplicated physical requests**, frozen as planned and unsent.
- Reference coverage diagnostics with **2,906 valid decodes**, while preserving
  the honest value of **0 human-verified species**.
- A blind-review interface that supports uncertainty and remains explicitly a
  local draft.
- Exact, model-free analyst replays whose claims retain artifact citations and
  stored tool traces.
- Release tests that keep unreviewed candidates out of final occurrence export
  and preserve sensitive, rights, privacy, and provenance boundaries.

These are artifact measurements and workflow properties—not claims of
biological completeness, species verification, representative quality, or
release readiness.

## What we learned

The strongest product choice was not a larger model or a larger candidate
count. It was an evidence contract that lets every stage say “not yet” precisely.
That makes the workflow more productive: reviewers see only what they should,
analysts can cite exact artifacts, live compute can fail without taking down the
product, and future updates have a clear receipt to earn.

We also learned that targeted failure discovery and representative quality
estimation must be different workflows. A queue designed to find hard cases can
improve the system, but it cannot produce an unweighted population precision
claim.

## What is next

1. Accept a complete immutable BioMiner handoff for the separately active Flickr
   work; do not ingest partial output.
2. Add the user-supplied GBIF occurrence download as fingerprinted Parquet only
   through the completed authoritative handoff path.
3. Finish the explicitly skipped YOLOE and BioCLIP stages in a later goal with
   exact licences, revisions, weight fingerprints, and independent evaluation.
4. Complete the three outstanding ALA dataset-rights reviews and community
   privacy/operator prerequisites.
5. Run authenticated independent and qualified review campaigns, then produce
   representative quality intervals and safe geographic-impact artifacts.
6. Attach a governed M5 heartbeat and committed batch without making the worker
   a site dependency.
7. Record, approve, caption, and upload the scripted 2:48 demonstration to
   public YouTube.

No Flickr API call is part of this goal; the separately active fetch remains
external until its immutable handoff is complete.

## Public links

- Working product: https://karikris.github.io/ButterflyLens/
- Help verify: https://karikris.github.io/ButterflyLens/#verify
- Australia map and worker state: https://karikris.github.io/ButterflyLens/#explore
- Bounded model Submitted replay artifact: https://karikris.github.io/ButterflyLens/
- Judge guide: https://github.com/karikris/ButterflyLens/blob/main/JUDGE_GUIDE.md
- Source: https://github.com/karikris/ButterflyLens
- Demonstration video: **not yet available — public YouTube upload required**

## Technology

TypeScript · React · Vite · Python · Deno · JSON Schema · Parquet · ALA ·
Flickr discovery planning · GitHub Pages · Supabase contracts · Backblaze B2
boundary · OpenAI Responses architecture · Bounded model analyst target · Apple M5
worker contracts · BioMiner evidence engine · Codex

The technology list describes implemented code and governed boundaries; it does
not claim a live public database, object store, provider call, model run, or
worker receipt where none is attached.

## Credits, data, and licences

ButterflyLens code and configuration are AGPL-3.0-only. Data, media, models,
community content, and dependencies retain their own terms. ALA provides the
authoritative baseline evidence for this build. Flickr is a discovery source,
not an occurrence authority. The local review fixture retains its exact
Wikimedia Commons attribution and CC BY-SA 4.0 terms. BioMiner and TaxaLens
origins are recorded at exact commits in repository provenance.

See `DATA_RIGHTS.md`, `MEDIA_RIGHTS.md`, `THIRD_PARTY_LICENSES.md`,
`PRIVACY.md`, `SENSITIVE_LOCATIONS.md`, `OCCURRENCE_RELEASE.md`, and
`BUILD_WEEK_DELTA.md` before publication.

## Public claims ledger

### Safe to publish now

- the exact winning line as the product thesis;
- the public credential-free Submitted replay and its routes;
- 463 accepted species;
- the cited internal ALA inventory counts with explicit rights-withheld public
  boundary;
- the 1,876-definition / 1,754-request deterministic unsent Flickr plan;
- 2,906 valid reference decodes and 0 human-verified species;
- measured test, schema, browser, and build results from the current release
  gate;
- the exact Bounded model target role, model-free replay state, and Codex engineering
  role; and
- current unavailable, unfinished, withheld, and release-blocked states.

### Do not publish as achieved

- a completed Flickr candidate count, Flickr completeness, or any partial-fetch
  count;
- a public occurrence layer, coverage-gap cell, or geographic-impact result;
- butterfly identity, human verification, consensus, reviewer reliability, or
  community impact;
- precision, agreement, confidence interval, or species-quality estimate;
- M5 liveness, throughput, queue, recovery, committed live artifact, YOLOE
  result, or BioCLIP result;
- a live Bounded model run in the Submitted replay;
- a downloadable released occurrence archive;
- a completed public video or YouTube URL; or
- overall scientific/data release readiness.

## Submission preflight

- Paste the winning line unchanged.
- Confirm every number still matches the canonical Submitted snapshot and the
  exact release test receipt.
- Open every public link in a private browser window.
- Keep the video field empty until the approved public YouTube upload exists.
- Do not paste an operator update, screenshot, partial Flickr count, or private
  M5 observation into the entry.
- Have Kris Kari review and approve the final copy, screenshots, credits,
  licences, video, and public submission.
