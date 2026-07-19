# ButterflyLens redesign Task 0.1 plan — audit routes and product state

Task ID: `butterflylens-redesign-0.1`

Objective: establish the exact public-route, review-persistence, and pinned
TaxaLens precedent boundary before changing the ButterflyLens runtime. This is
a read-only product audit. It makes no scientific, data, runtime, or deployment
claim.

Starting local, tracked remote, and hosted source SHA:
`3d6486da87f32136c35e29aeed6cb6291da66a17`.

Hosted URL: `https://karikris.github.io/ButterflyLens/`.

Hosted response fingerprint observed at task start:
`sha256:7874616540577dcae09810f7b412a3ca43263cb640820069c3bb1fd82ea3df87`.
The successful GitHub Pages workflow run `29673265255` names the same source
SHA. No hosted mutation is authorized by this audit.

Exact upstream boundaries:

- TaxaLens `e845dd98493979f37b04dbb6538e0d7b8758ca11`;
- BioMiner `7452e196e95cb3a91fc3f08efcb294a0d1849fd0`.

Only committed Git objects will be inspected. Both sibling worktrees contain
user-owned work. BioMiner is still fetching Flickr metadata only, so no
mutable output will be inspected, counted, or copied and ButterflyLens will
make no Flickr API call. The rebuilt ButterflyLens baseline is authoritative.
YOLOE and BioCLIP remain unfinished and are outside this audit.

Pre-existing ButterflyLens worktree state:

- untracked `AGENTS.md:Zone.Identifier`;
- untracked `docs/agents/` instruction pack and related `docs/` content.

Those files are user-owned. The task adds only the explicitly requested audit
reports under `docs/reports/` and stages each path individually.

## Subtask 0.1.1 — inventory current public routes

- Trace the deployed entry point, navigation anchors, mounted components, and
  footer route.
- Record purpose, exact committed data source, scientific maturity, and the
  keep/remove/move decision for every public surface.
- Freeze the required navigation direction: Explore, Verify, How it works,
  Community, then advanced pages under More with existing deep links retained.

Commit: `docs(ui): audit public routes`.

## Subtask 0.1.2 — audit current review persistence

- Trace draft state, local persistence, RPC return, assignment transition,
  consensus, map/community consumers, and missing projection links.
- Check current Supabase and browser-platform primary documentation.
- Make no migration or runtime change.

Commit: `docs(review): audit persistence and projections`.

## Subtask 0.1.3 — audit TaxaLens implementation

- Inspect only the pinned Git object for its repository contract, IndexedDB
  ledger, same-tab/cross-tab notification, map maturity, candidate selection,
  verification workspace, reset behavior, offline sync, and Supabase adapter.
- Adopt architectural precedents selectively; copy no broad source.

Commit: `docs(upstream): audit TaxaLens interaction precedent`.

## Evidence, research, and safety

GitHits produced no result in the single bounded attempt and timed out. The
user has directed that GitHits not be called again for the rest of the goal;
every subtask records that binding state. Current official Supabase and MDN
documentation is used for platform facts. Headroom compressed the full
2,008-line redesign brief under receipt
`de308114ae4b77a0d5a229b2` before the audit began.

No external source code, credential, model output, provider media, bulk data,
or active-run artifact will be added. Rollback is documentation-only: revert
the relevant focused audit commit.

## Task gate and push

Run relevant current tests plus documentation, JSON/JSONL, licensing, rights,
release-security, completion, and whitespace gates. Push all three focused
commits directly to `origin/main` without force, then verify the exact remote
SHA.
