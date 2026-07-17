# TaxaLens integration audit

This document records which committed TaxaLens capabilities ButterflyLens may
reuse, which boundaries must remain explicit, and which current TaxaLens claims
must not be promoted into ButterflyLens product or scientific claims.

## Audited source boundary

| Field | Evidence |
| --- | --- |
| Repository | `karikris/taxalens` |
| Audited commit | `95f9081567d6c96abdc5b5614d7e401d15ad4f03` |
| Commit subject | `build(map): add offline map rendering` |
| Commit time | `2026-07-18T00:04:43+10:00` |
| Licence at the audited commit | MIT |
| Audit time | `2026-07-17T14:08:54Z` |
| Working tree used | No |
| Hosted snapshot observed | `7d3e70c2ac935600d8f457a42a9c28c481352e74` |

The TaxaLens working tree contained unrelated user-owned changes during this
audit. Every finding below comes from an archive of the immutable audited
commit, inspected with `git show`, `git grep`, `git ls-tree`, `rg`, and focused
offline tests. No dirty or untracked upstream file is a source artifact.

The audited commit adds pinned, locally licensed MapLibre runtime dependencies
and a dependency verifier. It does not add a Geographic Impact Lens React
component. This distinction matters because a dependency decision is not an
implemented national map.

## Maturity vocabulary

- **Implemented and offline-tested** means executable code and focused tests
  exist at the audited commit. It says nothing about live provider data, human
  performance, scientific validity, or production operation.
- **Implemented for the fixture** means the public/static path operates over
  committed replay evidence and must not be described as a live service.
- **Partial** means some executable layers exist while a required UI, live
  runtime, authority boundary, or release gate is absent.
- **Contract-only** means a documented or typed interface exists without the
  corresponding end-to-end product capability.
- **Absent** means the audited tree contains no qualifying implementation.

## Required capability audit

| Capability | Maturity at the audited commit | Evidence and boundary |
| --- | --- | --- |
| Verification contracts | Implemented and offline-tested | Versioned campaign, item, sampling, provider, rights, review-requirement, private-media, and Flickr-source contracts are validated fail closed. |
| Review events | Implemented and offline-tested | Append-only event records bind reviewer round, structured decision, media and question hashes, campaign manifest, TaxaLens SHA, optional BioMiner SHA, supersession, and explicit conflict pointers. |
| Consensus | Implemented and offline-tested | Consensus is projected from each reviewer's latest effective event. Full decisive-signature agreement, uncertainty, media failure, second-review policy, and adjudication remain distinct states. |
| Conflicts | Implemented and offline-tested | Outcome, non-target category, alternative taxon, life stage, visual domain, view, and explicit-pointer disagreements retain event lineage; independent adjudication is separately validated. |
| Quality estimates | Implemented and offline-tested, current pilot estimates unavailable | Wilson simple-random intervals, stratified Hajek estimates, grouped percentile bootstrap intervals, coverage, aggregate agreement, nominal Krippendorff alpha, controls, milestones, and release gates preserve sampling and unavailable states. No current human-quality result is adopted here. |
| Geographic impact | Partial | The accepted architecture, typed sources, query builder, DuckDB-Wasm analytics, cache/controller, and bounded GeoJSON feature projection exist. The Geographic Impact Lens UI and its final hosted map bundle do not. |
| Map | Operational fixture map implemented; impact map absent | `FlickrWorkloadMap.tsx` is an accessible SVG coordinate-plane view of candidate clusters. MapLibre and a React wrapper are pinned at the newest audited commit, but no MapLibre React map component exists. |
| GPT-5.6 tools | Implemented and offline-tested; live model quality not measured | TaxaLens defines 12 general research tools and 8 verification tools, exact `gpt-5.6-sol` analyst contracts, strict structured outputs, budgets, citations, and stored replay. Its deterministic evaluation explicitly sets `liveApiCalls: false` and `modelOutputEvaluated: false`. |
| Public replay | Implemented for a static fixture | The public GitHub Pages root and build fingerprint were independently reachable on the audit date. The deployed snapshot is a credential-free, backend-free, resettable Papilio fixture, not live acquisition or inference. |

## Verification contracts

### Campaign and item identity

The root campaign contract is
`taxalens-verification-campaign:v1.0.0`. It supports Flickr target,
reference-identity, reference-route, adjudication, and quality-control
campaigns with draft through archived lifecycle states. The provider vocabulary
is Flickr, GBIF, iNaturalist, Wikimedia Commons, and a TaxaLens fixture.

The sampling plan preserves:

- purpose and design;
- whether selection is representative and blind;
- inclusion probabilities and population weights;
- strata and grouping keys;
- leakage controls;
- a separate quality-estimation eligibility decision; and
- explicit unavailable or incomplete fields.

The campaign also binds question, manifest, TaxaLens, and BioMiner identities,
declares whether it is a public replay, and carries
`scientificClaimAllowed`. A ButterflyLens adapter must retain these fields and
must reject unsupported schema versions rather than filling defaults.

### Append-only review events

`taxalens-verification-event:v1.3.0` represents Yes, No, Can't tell,
Can't view, and Skip. It can retain an alternative accepted taxon, a structured
non-target category, corrected life stage, visual domain and view, media
quality, duplicate or captive/cultivated concerns, confidence, duration, and
comments.

The validator blocks scientific annotations on non-scientific outcomes, binds
each event to the exact displayed image and question, and requires appropriate
No-category detail for Flickr target review. Ledger validation enforces unique
event IDs, contiguous reviewer rounds, and valid non-repeated supersession.
Current state is a projection; history is not overwritten.

### Consensus, conflicts, and adjudication

`taxalens-verification-consensus:v1.0.0` preserves these states:

- pending;
- complete agreement;
- unresolved disagreement;
- uncertain only;
- media failure;
- deferred; and
- adjudicated.

Consensus does not use a model vote. It does not convert majority agreement or
a single decisive review into truth. A conflict retains the fields and event
IDs that disagree. An adjudicator must be independent of the conflicting
reviewers and must resolve against the exact canonical lineage.

Support eligibility (`not_applicable`, `blocked`, or
`prepared_for_biominer_resolution`) is separate from final-test eligibility.
ButterflyLens must preserve that separation when adding community review and
private reliability weights.

## Quality estimation

TaxaLens provides deterministic estimators rather than a current quality
claim:

- `taxalens-target-precision-estimate:v1.0.0` includes simple-random Wilson,
  stratified Hajek, and grouped percentile bootstrap paths;
- missing inclusion probabilities, incomplete strata, grouping errors, or
  insufficient samples produce blockers or unavailable output;
- weighted estimates retain effective sample size and represented versus
  missing strata;
- `taxalens-reviewer-reliability:v1.0.0` provides aggregate anonymous
  pairwise agreement, nominal Krippendorff alpha, and pre-reviewed control-set
  performance; and
- `taxalens-verification-quality-snapshot:v1.1.0` combines coverage,
  precision, agreement, conflict, controls, references, fingerprints, leakage,
  milestones, and release policy without treating targeted failure discovery
  as a representative audit.

This upstream reviewer-reliability module is an aggregate campaign-quality
surface. It is not an individual, domain-specific, uncertainty-shrunk reviewer
weighting system. ButterflyLens therefore may reuse the aggregate contracts
but owns any private assignment and reliability model.

The TaxaLens README reports zero human participants and an unavailable target
precision interval. Its scripted interaction comparison is not human time
saved, productivity, or scientific-quality evidence. ButterflyLens imports
none of those fixture measurements as a product metric.

## Geographic impact and map

The Geographic Impact architecture correctly separates:

- conservatively deduplicated baseline occurrence evidence;
- Flickr discovery candidates;
- reviewed positive, non-target, uncertain, media-failure, and deferred states;
- human-supported candidates from release-ready occurrence candidates;
- grid resolution from administrative scope; and
- missing baseline evidence from biological absence.

The provider-union contract prevents GBIF-delivered iNaturalist observations
from being blindly added to a direct iNaturalist snapshot. A direct snapshot
that does not exist is unavailable, not zero. H3 resolutions are artifact
identity, not universal constants. Coordinate precision may roll a cell up but
may not invent a finer child cell.

Executable TypeScript exists for source verification, scoped queries,
DuckDB-Wasm analytics, cache and cancellation, and bounded feature collections.
The source tree contains no `GeographicImpact*.tsx` component. The visible
`FlickrWorkloadMap.tsx` instead draws operational cluster centroids in SVG and
explicitly says it is separate from Geographic Impact.

At the audited commit, `maplibre-gl@5.24.0` and
`@vis.gl/react-maplibre@8.1.1` are pinned with a local-only dependency policy:
no remote styles, tiles, fonts, sprites, GeoJSON, tokens, telemetry, or
renderer-side clustering that obscures evidence state. This is a useful design
constraint, not evidence that the proposed impact map has been rendered or
deployed.

The required synchronized table, keyboard interaction, non-colour state cues,
exact counts, and non-WebGL path are accepted architecture. Their presence in
the architecture document does not establish end-to-end UI conformance.

## GPT-5.6 analyst boundary

TaxaLens exposes two read-only tool sets:

1. Twelve general evidence tools resolve a taxon, inspect query coverage and
   stages, estimate a mission, trace lineage, compare candidates, explain a
   decision, inspect reference and prototype state, and export evidence.
2. Eight verification tools inspect campaigns, coverage, quality, conflicts,
   reference readiness, and sampling; recommend a next review batch; and
   explain a quality change.

The verification tool packet is
`taxalens-verification-tool-evidence:v1.2.0`, results are
`taxalens-verification-tool-result:v1.1.0`, and citations are
`taxalens-verification-artifact-citation:v1.0.0`. Inputs and outputs use strict
schemas, bounded arrays, exact artifact IDs and SHA-256 values, and source
repository, commit, and path citations. Tool results always carry
`scientificClaimAllowed: false`.

The verification analyst contract names exact model `gpt-5.6-sol`, output and
run version `v1.2.0`, bounded response turns and tool calls, no external
actions, unsupported-claim rejection, and no causal claim for quality-change
explanations. The default judge path replays checksum-bound stored output. The
committed evaluation checks deterministic tools and policy; it explicitly does
not evaluate a live model response. ButterflyLens may adapt this evidence-tool
shape, but it must independently implement and evaluate its own agents.

## Public replay check

On `2026-07-17T14:05:48Z`, an independent HTTPS request to
`https://karikris.github.io/taxalens/` returned HTTP 200. The simultaneously
retrieved `build-fingerprint.json` declared:

- deployment schema `taxalens-static-deployment/v1`;
- source SHA `7d3e70c2ac935600d8f457a42a9c28c481352e74`;
- public `true`;
- login, backend, and credentials required `false`;
- resettable `true`;
- three checksum-addressed review-media fixtures; and
- build-fingerprint SHA-256
  `0af07ea4afa3a7c26a6585931b5dff4a64c12960307a34e9f93d9f164d8de5d5`.

The public deployment therefore lagged the audited source commit by one
dependency-only commit. It is a static, single-target Papilio replay with local
IndexedDB review events. It does not establish community accounts, a live
database, live GPT calls, a live M5 model worker, or the proposed Geographic
Impact map.

The upstream hosted verifier completed its HTTP, manifest, media checksum, and
fallback checks before the audit host reached the browser step. The independent
Chromium step was unavailable because the audit host lacks `libnspr4.so`.
Accordingly, this audit does not claim a new incognito interaction, export, or
reset result; it relies only on the directly observed HTTP/fingerprint facts
and labels the browser recheck unavailable.

## Reuse decision

ButterflyLens will prefer versioned contract extraction and adapters over
application copying. The candidate order is:

1. shared verification and geographic JSON Schema contracts with Python and
   TypeScript parity;
2. append-only event and consensus adapters that retain upstream lineage;
3. quality-estimation fixtures and algorithms only after component-level
   provenance and parity tests;
4. an evidence-facade pattern over ButterflyLens-owned storage and live-worker
   contracts; and
5. read-only analyst tool patterns whose outputs remain evidence-bound.

ButterflyLens will not import the TaxaLens React shell, Papilio judge bundle,
fixture measurements, local IndexedDB repository, static deployment identity,
or broad source directories. Every accepted component remains `planned` in
`provenance/taxalens_migration_manifest.yaml` until a later focused commit
records an exact destination, copied or adapted content, licence handling, and
tests.

## Verification performed

An archive of the immutable audited commit was tested outside the TaxaLens
working tree. Twenty-three focused Vitest files passed with 111 tests covering
verification contracts, events, consensus, adjudication, coverage, quality,
release policy, schema/export validation, dashboard projection, the operational
map, geographic analytics/query/cache/controller/source layers, both analyst
surfaces, and both tool sets.

The first isolated attempt used an external dependency symlink; Vite denied a
DuckDB worker URL outside the temporary root after 108 tests had passed. A
temporary physical dependency copy removed that isolation limitation, and the
same pinned source then passed all 111 tests. The failed infrastructure attempt
is not counted as a product failure or hidden as a successful run.

No TaxaLens source, data, media, model, build output, or runtime artifact was
copied into ButterflyLens during this audit.
