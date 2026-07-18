# ButterflyLens 10.5 — Flickr public-display policy

Status: **implemented locally; fail-closed policy and release boundaries
verified**.

Starting SHA: `f053c27d877fba07df841e2825618d9f705b2333`.

## Outcome

ButterflyLens now has one versioned Flickr public-display policy enforced in
Python, TypeScript/React, and a Supabase/Postgres migration. The submitted site
shows the policy and displays zero Flickr photos because application approval,
commercial-use determination, privacy disclosure, and admitted current public
thumbnail evidence are not recorded. The active fetch and its partial outputs
are explicitly not public evidence.

An eligible page is capped at 30 unique photos. Every item requires a current
public source record, allowed display and redistribution rights, a committed
public thumbnail served through an internal path, the exact Flickr photo link,
photographer, owner identity, licence and licence link, complete attribution,
three evidence fingerprints, an unexpired cache, visibility/licence
revalidation within 24 hours, and no removal case. One invalid item blocks the
whole page.

The exact public notice is always rendered: “This product uses the Flickr API
but is not endorsed or certified by SmugMug, Inc.” No Flickr logo, remote Flickr
thumbnail, private image, or essential-experience imitation is used.

## Durable database and removal boundary

The migration adds service-only application-approval, public-display-asset,
removal-case, and append-only removal-event tables. Every table has RLS; browser
roles cannot publish or mutate provider evidence; authenticated curators have
read-only project-scoped visibility; and anonymous roles have no access. The
service projection uses `security_invoker` and remains service-only.

Display admission validates current Flickr source and governed public-thumbnail
rows, active application approval, exact source/licence/fingerprints, rights,
visibility, attribution, and cache state. An admitted owner/rights/provider
removal case immediately quarantines the public projection, media object, and
source rights state before downstream traversal. Cases are insert-only;
fingerprinted dependency events retain quarantine, purge, invalidation,
completion, and appeal evidence. The owner deadline and display-cache maximum
are both 24 hours.

The Supabase and Postgres skills led to explicit grants, RLS on all new exposed-
schema tables, `security_invoker` projection semantics, foreign-key and partial
indexes, and the absence of `security definer` code. Supabase's April 2026 Data
API exposure change is handled with explicit service/authenticated grants and
explicit anonymous revocation.

## Active parallel work

Task 10.4 remains unfinished. The user reported an active Flickr fetch with
50,000 unique images and about 20 hours remaining. No Flickr API call, partial
output read, copy, display, or metric claim occurred here. The supplied GBIF
Parquet handoff also remains deferred until BioMiner publishes it safely. YOLOE
and BioCLIP remain unfinished and were not run.

## Verification

- Full Python suite — 394 tests passed.
- Focused Flickr policy suite — 6 tests passed, including policy, page,
  attribution, application/privacy, cache/removal, and SQL boundaries.
- Web suite — 43 Vitest parser/component tests passed; TypeScript check and
  production build passed.
- Production bundle — 0.60 kB HTML, 32.93 kB CSS, and 1,418.00 kB JavaScript
  before gzip; JavaScript is 212.98 kB after gzip. The existing raw chunk-size
  advisory remains driven by the full local species catalogue.
- Repository rights and licensing verification passed (52 tracked provider
  payloads and 362 tracked files). Build verification checked 116 dependency
  licences and the unchanged review-media SHA-256.
- Twenty-eight pgTAP assertions define the database gate. They were not run
  against a live/local Postgres instance because the Supabase CLI is absent.
- Supabase MCP OAuth succeeded for project `ujfsrohgsrmssmfqgdsp`; the already-
  running MCP client retained its pre-auth handshake and requires a session
  reload, so no live database mutation or advisor result is claimed.
- Visual tests include the Flickr stylesheet and continue to enforce contrast,
  focus, responsive behavior, no gradients, and no scientific-image filters.

No Flickr API, GitHits, YOLOE, BioCLIP, or scientific model call occurred. No
Flickr credential, provider photo, partial run output, or live database row was
introduced.

Next safe task: Task 10.6, contributors experience, while Task 10.4 and the GBIF
handoff remain deferred behind active BioMiner work.
