# ButterflyLens redesign 0.1.1 — current public-route audit

Status: complete at committed and deployed source
`3d6486da87f32136c35e29aeed6cb6291da66a17`.

Date: 2026-07-19

## Routing model

ButterflyLens currently has one public document at `/ButterflyLens/`. It has no
route library or path resolver. `App.tsx` mounts every public surface in one
long document and `PublicShell.tsx` exposes eight fragment links. The Explore
link is permanently marked `aria-current="page"`; route state is not derived
from the URL. Fragment deep links work as browser anchors, but there is no
page-level loading, title, current-navigation, or back/forward state for the
individual product surfaces.

The deployed document order is:

`#explore` introduction → `#live` submitted map → `#verify` review draft →
`#species` catalogue → `#operations` observatory → `#flickr-display-policy` →
`#quality` → `#contributors` → `#ask-butterflylens` → `#about` footer.

## Route inventory and disposition

| Current route | Component | Purpose | Current committed data | Scientific maturity | Decision |
| --- | --- | --- | --- | --- | --- |
| `/ButterflyLens/#explore` | inline `App` introduction | Product promise and evidence-state summary | Static copy only | Correctly says candidate evidence and active release gates, but is Australia-only and does not expose impact | **Keep and rebuild** as the Explore page hero immediately followed by the global evidence map |
| `/ButterflyLens/#live` | `SubmittedEvidenceMap` | Browse baseline evidence by H3 cell and named aggregate scope | Rights-screened rebuilt ALA snapshot: 236,897 selected, 220,144 rights-screened, 213,310 map-eligible records, 630 H3 cells; fingerprint `d39a73…ae446` | Provider occurrence assertions only; not identity verification, completeness, absence, abundance, or release evidence; Flickr and human-review layers unavailable | **Keep and move** into Explore; retain `#live` as an alias while replacing the Australia SVG with the required global evidence map and adding only committed candidate/review layers |
| `/ButterflyLens/#verify` | `ReviewLanding` | Demonstrate blind human assessment of one image | One rights-cleared Wikimedia fixture plus React draft state | Integrity-checked media is displayable, but the page explicitly stores nothing and creates no scientific review event | **Keep and rebuild** as the second public page with durable append-only review, receipt, immediate record state, set progress, and map/community projection |
| `/ButterflyLens/#species` | `SpeciesDirectory` | Inspect accepted taxonomy, source names, conservative crosswalks, and reference coverage | Submitted catalogue of 463 accepted species and diagnostic candidate/decode counts | Taxonomy snapshot and source assertions are inspectable; provider media and crosswalks are not human identity or distribution claims; human-verified species count is zero | **Move under More** to Model and reference evidence, with `#species` preserved as a deep link |
| `/ButterflyLens/#operations` | `OperationsDashboard` | Separate live worker observation from immutable committed fallbacks | Strict submitted operations snapshot plus optional monitoring URL | Site/map/review fallback availability is proven; worker state and current monitoring may remain unavailable; not scientific maturity | **Move under More** to Live operations and preserve `#operations` |
| `/ButterflyLens/#flickr-display-policy` | `FlickrDisplayBoundary` | Expose Flickr display and attribution release gates | Policy plus empty/blocked submitted context; application approval is not recorded | No Flickr image is publicly eligible and no candidate scientific claim is made | **Move under More** to Rights and attribution and preserve the fragment; later candidates must remain link/metadata-only until every display gate passes |
| `/ButterflyLens/#quality` | `QualityDashboard` | Show review quality, diagnostics, and release blockers | Submitted quality projection: reviewed sample 0, accepted species 463, valid decodes 2,906, all quality estimates unavailable | Reference diagnostics exist; representative review quality, reviewer agreement, species quality, and release evidence do not | **Move under More** to Data quality; keep concise milestone truth on Community and preserve `#quality` |
| `/ButterflyLens/#contributors` | `ContributorExperience` | Show the current visitor's private contribution trace | Submitted self-only projection with every metric unavailable and no source fingerprint | No stored contributor evidence; rankings and speed metrics are correctly forbidden | **Replace at top level** with Community: shared milestone, completed 20-image sets, species/areas reviewed, unresolved conflicts, needs, and current visitor contribution; keep private metrics private and preserve `#contributors` |
| `/ButterflyLens/#ask-butterflylens` | `AskButterflyLens` | Present a stored replay or optional live bounded analyst | Fingerprinted stored replay catalog; submitted mode claims zero model/network calls; a Supabase live client also exists in runtime source | This is an explanatory analyst surface, not butterfly evidence; it conflicts with the required no-chat product boundary | **Remove deliberately** from runtime, navigation, deploy, tests, and current product claims; preserve historical provenance instead of preserving a public deep link |
| `/ButterflyLens/#about` | `PublicShell` footer | Explain evidence stages and link governance policies | Static project and policy links | Wording correctly separates hypotheses, review, quality, and release | **Move and retain**: product explanation belongs on How it works; governance links belong under More and the footer; preserve `#about` |

## Required destination architecture

The first four public destinations must be exactly:

1. Explore
2. Verify
3. How it works
4. Community

Technical surfaces move under a single More disclosure/navigation group:
Evidence Lens; Model and reference evidence; Data quality; Data governance;
Rights and attribution; Provenance; Live operations; Exports; Research methods.

The implementation must preserve useful fragments while introducing real
page state. A compatibility resolver should map current fragments to their new
destinations before scrolling to the relevant subsection. Removed analyst
fragments should land on How it works with a concise deliberate-removal notice,
not recreate the analyst interface.

## Primary defects established by this audit

- The product opens with prose, not the evidence map or contribution impact.
- Eight equal-weight primary links expose implementation/governance structure
  before the visitor understands the four-step product loop.
- Explore and Live are split even though the map is the core Explore surface.
- Verify has no durable effect, receipt, map update, or community update.
- Community is a private unavailable snapshot rather than shared progress.
- The Ask route implies a general interaction mode that the redesigned product
  explicitly does not ship.
- All surfaces load eagerly in one document; advanced content cannot be
  progressively disclosed or route-split.
- Navigation current state is incorrect for every fragment except Explore.

## Evidence boundary

This report changes no runtime. The rebuilt ALA baseline remains authoritative.
BioMiner is still fetching Flickr metadata, so Flickr candidates remain
unavailable and no partial artifact was read or copied. YOLOE and BioCLIP are
unfinished. No Flickr API, model, provider, Supabase-project, or deployment
call occurred.
