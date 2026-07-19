# ButterflyLens screenshot defect matrix

Task: `butterflylens-redesign-0.2`

Audit date: 19 July 2026

Application source: `056fe3563f6282a8bce4ea61ab1da3d96323e526`

Capture manifest: [task-0.2/manifest.json](../assets/redesign-baseline/task-0.2/manifest.json)

## Outcome

The submitted baseline is visually coherent and its unavailable states are
careful, but it is not yet the intended impact-first product. The highest-risk
defects are the one-document information architecture, the map being below the
first viewport and limited to the Australian ALA replay, the draft-only Verify
flow, the unavailable personal-only Community surface, and the retained public
analyst.

BioMiner is still fetching Flickr metadata. This audit did not read or copy its
partial outputs and made no Flickr API calls. Candidate imagery and BioCLIP
labels therefore remain unavailable rather than being represented as zero or
inferred from query terms. YOLOE and BioCLIP product work remains unfinished.

Severity meanings:

- **Critical:** blocks the required public journey or contradicts a binding
  product boundary;
- **High:** makes a primary journey unavailable, misleading, or materially
  difficult;
- **Medium:** degrades comprehension or visual priority without blocking the
  journey.

## Capture coverage

| State | Evidence |
|---|---|
| Explore, 1440 × 900 | [explore-desktop-1440x900.png](../assets/redesign-baseline/task-0.2/explore-desktop-1440x900.png) |
| Explore, 1280 × 720 | [explore-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/explore-desktop-1280x720.png) |
| Explore, 390 × 844 touch/mobile | [explore-mobile-390x844.png](../assets/redesign-baseline/task-0.2/explore-mobile-390x844.png) |
| Explore, reduced motion | [explore-reduced-motion-1280x720.png](../assets/redesign-baseline/task-0.2/explore-reduced-motion-1280x720.png) |
| Explore, forced colours/high contrast | [explore-forced-colors-1280x720.png](../assets/redesign-baseline/task-0.2/explore-forced-colors-1280x720.png) |
| Submitted map | [map-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/map-desktop-1280x720.png) |
| Verify | [verify-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/verify-desktop-1280x720.png) |
| Species/reference evidence | [species-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/species-desktop-1280x720.png) |
| Live operations | [operations-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/operations-desktop-1280x720.png) |
| Data quality | [quality-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/quality-desktop-1280x720.png) |
| Community/contributor surface | [community-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/community-desktop-1280x720.png) |
| Ask ButterflyLens | [analyst-desktop-1280x720.png](../assets/redesign-baseline/task-0.2/analyst-desktop-1280x720.png) |

The captures used Chromium `149.0.7827.55`, Playwright `1.61.1`, `en-AU`,
Australia/Sydney, a device scale factor of one, and a local build. Every
non-application origin was blocked; the manifest records zero external
requests for all 12 captures.

## Defect matrix

| ID | Route | Viewport/state | Severity | Screenshot | Observed problem | Root cause | Proposed fix | Acceptance test | Status |
|---|---|---|---|---|---|---|---|---|---|
| UI-001 | All/public shell | 1440 × 900 and 390 × 844 | High | [desktop](../assets/redesign-baseline/task-0.2/explore-desktop-1440x900.png), [mobile](../assets/redesign-baseline/task-0.2/explore-mobile-390x844.png) | Eight equal-weight links compete in the primary navigation. On mobile only Explore through Quality are visible; later destinations are off-screen without an obvious disclosure control. The labels also omit required **How it works** and rename **Community** to Contributors. | [`primaryNavigation`](../../apps/web/src/shell/PublicShell.tsx) hard-codes eight fragment links, while horizontal overflow in [`publicShell.css`](../../apps/web/src/shell/publicShell.css) is the only small-screen accommodation. | Make the first four destinations Explore, Verify, How it works, Community. Place advanced destinations under one accessible **More** disclosure. | At 390 × 844, a Playwright test finds all four primary links and More without horizontal scrolling; opening More exposes every advanced destination and Escape returns focus to its trigger. | Open |
| UI-002 | Explore (`#explore`) | 1440 × 900 and 1280 × 720 | Critical | [1440 × 900](../assets/redesign-baseline/task-0.2/explore-desktop-1440x900.png), [1280 × 720](../assets/redesign-baseline/task-0.2/explore-desktop-1280x720.png) | The initial viewport is dominated by a slogan and technical replay facts. At 1280 × 720 no map content is visible; at 1440 × 900 only the next section heading begins. Geographic impact is not the entry point. | [`App.tsx`](../../apps/web/src/App.tsx) renders the large `shell-intro` before `SubmittedEvidenceMap`; display-scale type and up to six rem vertical padding amplify it. | Make the global evidence map the Explore hero. Keep a concise purpose statement, primary **Help verify** action, current state, and real counts adjacent to—not before—the map. | At both desktop viewports, the screenshot contains the map canvas, blue baseline legend, amber candidate legend, taxon control, and a Help verify action without scrolling. | Open |
| UI-003 | Explore (`#explore`) | 390 × 844 | High | [mobile](../assets/redesign-baseline/task-0.2/explore-mobile-390x844.png) | The slogan, lede, and replay-facts card consume the entire first mobile viewport. The map is not visible and its heading is clipped at the bottom, so there is no immediate action or geographic context. | The single-column breakpoint stacks the unchanged desktop hero and its three-row facts card ahead of the map. | Use a compact mobile map-first composition, move detailed replay metadata into progressive disclosure, and keep one clear verification action above the fold. | At 390 × 844, visual and locator assertions show a usable map region and primary action in the first viewport; no heading is clipped and no horizontal page overflow exists. | Open |
| UI-004 | All | Desktop and mobile | Critical | [Explore](../assets/redesign-baseline/task-0.2/explore-desktop-1440x900.png), [Verify](../assets/redesign-baseline/task-0.2/verify-desktop-1280x720.png) | Navigation changes scroll position inside one very long document rather than opening four distinct public pages. A user entering a deep fragment loses the persistent header and page context in the captured viewport. | [`App.tsx`](../../apps/web/src/App.tsx) eagerly mounts every product surface and [`PublicShell.tsx`](../../apps/web/src/shell/PublicShell.tsx) uses only hash anchors; there is no route boundary. | Introduce route-level Explore, Verify, How it works, and Community pages, lazy-load advanced More destinations, and preserve a consistent shell/current-page state. | Direct navigation and reload of each route renders the correct page, title, landmark and `aria-current`; the initial route bundle does not contain every advanced surface. | Open |
| UI-005 | Explore map (`#live`) | 1280 × 720 | Critical | [map](../assets/redesign-baseline/task-0.2/map-desktop-1280x720.png) | The map is an Australia-only submitted ALA replay with aggregate H3 counts. It cannot present the required global, taxon-neutral GBIF-led impact view. | [`SubmittedEvidenceMap.tsx`](../../apps/web/src/map/SubmittedEvidenceMap.tsx) is bound to the rebuilt Australian ALA snapshot and an SVG Australia projection. | Build the scalable global map contract with the rebuilt authoritative baselines, taxonomic/geographic filters, maturity filters, and no-external-tile fallback. Preserve ALA as governed supporting evidence where it passes project quality gates. | With Geography=Global and a selected accepted taxon, the map renders fingerprinted GBIF baseline evidence and exposes baseline/Flickr/both controls; changing family, genus, species, region, time or maturity updates the visible projection without reloading. | Open |
| UI-006 | Explore map (`#live`) | 1280 × 720 | Critical | [map](../assets/redesign-baseline/task-0.2/map-desktop-1280x720.png) | There are no amber Flickr candidates, no personal/community maturity state, and no candidate side sheet. The disabled live mode cannot start the required map → image → review journey. | The submitted map explicitly marks its Flickr layer unavailable, and no committed authoritative BioMiner candidate/model handoff is present. BioMiner's active metadata fetch is not consumable partial evidence. | After BioMiner completes and commits a governed handoff, copy only validated fingerprinted data. Render candidates as candidates—not occurrences—and open a rights-aware side sheet with BioCLIP evidence only when authoritative. Do not run Flickr calls from this goal. | A fixture backed by the final handoff displays hollow amber candidates; selecting one opens the side sheet. Regression coverage proves a Flickr query term cannot become the public taxon label and unavailable model evidence stays unavailable. | Deferred — BioMiner active; YOLOE/BioCLIP unfinished |
| UI-007 | Verify (`#verify`) | 1280 × 720 | Critical | [Verify](../assets/redesign-baseline/task-0.2/verify-desktop-1280x720.png) | The surface presents one fixture as “1 image awaiting review,” but decisions remain local component state and the page later states that it does not submit or claim a stored review. There is no authoritative receipt or cross-surface update. | [`ReviewLanding.tsx`](../../apps/web/src/review/ReviewLanding.tsx) owns draft state in React and prevents form submission; it does not call the existing secure RPC or a public replay repository. | Adapt the audited repository boundary: append-only IndexedDB events and projections for submitted replay; authenticated Supabase RPC plus authoritative receipt and Realtime refresh for live mode. | A review returns `review_event_id`, `event_fingerprint`, `assignment_id`, and `item_id`; reload retains it; map, Verify, set progress and Community update without a page reload. Replay copy says **Stored on this device** and never claims Supabase storage. | Open |
| UI-008 | Verify (`#verify`) | 1280 × 720 | High | [Verify](../assets/redesign-baseline/task-0.2/verify-desktop-1280x720.png) | Introductory copy, a queue counter and a large evidence notice occupy most of the viewport. Only a strip of the image is visible, so the image is not the hero and review controls are below the fold. | The `review-intro` and notice precede the two-column review grid; the page uses display-scale headings designed for a report rather than a rapid 20-image workflow. | Lead with the large rights-eligible image, simple decision controls, concise context, and visible `n / 20` progress. Collapse evidence/provenance below it. | At 1280 × 720 and 390 × 844, the current image, permitted candidate label, all five decisions, save state and set progress are operable in or immediately adjacent to the first viewport. | Open |
| UI-009 | Verify | All | Critical | [Verify](../assets/redesign-baseline/task-0.2/verify-desktop-1280x720.png) | There is no 20-image review-set experience, resumption state, bounded media prefetch, or set completion outcome. | The current model supplies a single `submittedReviewItem`; no review-set repository or progress projection is connected to the UI. | Implement the versioned review-set contract with default size 20, assignment ordering, resumable progress and bounded current/next/previous prefetch. | Contract and browser tests create a 20-item set, persist progress, resume after reload, advance after a stored receipt, and never preload all full-resolution images. | Open |
| UI-010 | Community (`#contributors`) | 1280 × 720 | Critical | [Community](../assets/redesign-baseline/task-0.2/community-desktop-1280x720.png) | The destination is a personal contribution dashboard whose snapshot is unavailable. It shows no collective review progress, next milestone, completed review sets, species/regions helped, or current review needs. | [`ContributorExperience.tsx`](../../apps/web/src/community/ContributorExperience.tsx) consumes only an authenticated/fingerprinted contributor snapshot and deliberately withholds totals when it is absent. | Create a public Community projection with transparent denominators and milestone rules, then layer optional private contributor impact beneath it. | With a deterministic fixture, Community displays collective progress, exact next milestone, completed sets, species/regions helped and current needs; unavailable values are labelled unavailable, never zero. A stored review updates the projection without reload. | Open |
| UI-011 | Community (`#contributors`) | 1280 × 720 | Medium | [Community](../assets/redesign-baseline/task-0.2/community-desktop-1280x720.png) | The display heading wraps into three widely separated lines and consumes more than half of the viewport before any useful community metric. | The contributor heading inherits a very large display token with a narrow text column and generous section spacing. | Use a compact community headline and make milestone/progress content the visual anchor; constrain responsive type and whitespace with container-aware rules. | The 1280 × 720 and 390 × 844 snapshots show the headline and at least one meaningful milestone/progress block without awkward orphan lines or clipped content. | Open |
| UI-012 | Quality and Live operations | 1280 × 720 | High | [Quality](../assets/redesign-baseline/task-0.2/quality-desktop-1280x720.png), [operations](../assets/redesign-baseline/task-0.2/operations-desktop-1280x720.png) | Unavailable worker state and unavailable quality estimates are promoted as primary public destinations. They are honest but read as operational/research dashboards rather than the simple first-time journey. | Quality and Live are equal primary anchors and eagerly rendered in `App`; the detailed evidence boundary is not progressively disclosed. | Move quality, governance, provenance, live operations, exports and research methods under More/Evidence Lens. Summarise only decision-relevant state on primary pages. | Primary navigation has no Quality or Live item. Keyboard users can open each advanced route from More, and no advanced dashboard is included in the first Explore render tree. | Open |
| UI-013 | Ask ButterflyLens (`#ask-butterflylens`) | 1280 × 720 | Critical | [analyst](../assets/redesign-baseline/task-0.2/analyst-desktop-1280x720.png) | A large analyst composer, suggested-question workflow and stored replay remain a visible public product surface, contrary to the decision not to ship a general-purpose chat interface. | [`AskButterflyLens.tsx`](../../apps/web/src/analyst/AskButterflyLens.tsx), its clients/replays and the primary navigation entry remain mounted. | Audit shared contracts, then remove the runtime analyst UI, clients, Edge Function, OpenAI-only configuration/dependencies and product claims while preserving immutable development provenance. | Production source/build scans find no Ask ButterflyLens route, composer, analyst Edge Function, Responses API path, runtime OpenAI secret or analyst-only dependency. The required Codex-development statement remains in documentation. | Open |
| UI-014 | All fragment destinations | Keyboard/screen reader | High | [Explore](../assets/redesign-baseline/task-0.2/explore-desktop-1280x720.png) | Explore remains visually and semantically marked current even after a user navigates to Verify, Community or another fragment, so location feedback is false. | `current: true` is static on the Explore item and `aria-current="page"` is never derived from location or route state in [`PublicShell.tsx`](../../apps/web/src/shell/PublicShell.tsx). | Derive current navigation state from the real route; do not use page semantics for inactive hash targets. Announce page titles at route changes and restore deliberate focus. | For every direct route and client navigation, exactly one primary link has `aria-current="page"`, its label matches the visible page, and the page heading receives expected screen-reader/focus treatment. | Open |

## Accessibility-state observations

The forced-colour capture remains legible: headings, links, the selected
navigation state, status boundary and fact-card separators retain visible
structure without relying on the original palette. No forced-colour-only
defect was found in this first viewport. The reduced-motion capture is
pixel-identical to the ordinary 1280 × 720 Explore capture, as expected for
this static state; the current stylesheet also disables smooth scrolling and
transitions when reduced motion is requested.

These observations do not close any issue above. Each redesigned route still
requires keyboard, screen-reader, forced-colour and reduced-motion regression
coverage when Phase 10 applies fixes and captures after states.

## Capture reproducibility

[`capture-redesign-baseline.mjs`](../../apps/web/scripts/capture-redesign-baseline.mjs)
requires an exact application SHA and normalized capture instant. It fixes the
browser context, viewport, locale, timezone, colour scheme and device scale;
blocks service workers and every non-local request; disables screenshot
animations; and fingerprints each PNG. Fragment captures explicitly disable
smooth scrolling before positioning, preventing a transitional scroll frame
from being mistaken for a route baseline.
