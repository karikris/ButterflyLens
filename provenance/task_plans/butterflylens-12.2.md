# Task plan — ButterflyLens 12.2

Task ID: `butterflylens-12.2`

Objective: make the public website operationally independent of the M5 worker
while keeping worker availability honest and visible.

Competition criterion improved: the public judge experience remains useful and
inspectable through worker interruption, network failure, absent credentials,
or an unavailable live status service.

Starting, origin, and remote SHA:
`68fdc1c4dd45a245f40a2ea28d9640a0c560de3e`.

Deployment baseline: GitHub Pages run `29637562893` built and deployed this SHA
successfully to `https://karikris.github.io/ButterflyLens/`. HTTPS is enforced.
The repository `production` environment is restricted to the `main` branch.
The credentialed Supabase/B2 workflow has not been dispatched.

BioMiner overlap check: published SHA
`c462c848c9e9cb18c4efc86fa22bbae01af05a3b` remains active and dirty. Its
published current-state record still lists live current-policy GBIF acquisition
and durable-media admission as unfinished and publishes no immutable GBIF
handoff. Do not inspect or copy partial output; use only ButterflyLens committed
artifacts.

Artifacts: add an exact, immutable public operations snapshot referencing the
committed 463-species catalogue, rebuilt ALA snapshot, and submitted review
fixture. Add a strict parser and pure freshness reducer that can distinguish a
fresh worker, a stale/offline worker, and unavailable live evidence without
changing the current committed snapshot. Replace the scheduled Live placeholder
with an accessible operations dashboard whose scope map, review route, and
submitted snapshot render entirely from the bundle.

Failure behavior: malformed, absent, future-dated, or missing heartbeat evidence
must never remove or replace static content. No heartbeat means unavailable,
not inferred offline. A stale observed heartbeat is visibly offline. A live
snapshot may be selected only when it is explicitly committed and exactly
validated; otherwise the submitted snapshot remains current.

Tests: parser exactness; fresh/stale/absent/future heartbeat cases; static and
offline component rendering; map, review, and submitted-snapshot availability;
16-file web regression, standalone Node licence tests, typecheck, both build
bases, full Python, rights, licence, JSON/JSONL, media, whitespace, staged
secret/scope checks, Pages deployment, and three-SHA verification.

Rights/privacy: publish no occurrence coordinate, dataset-restricted count,
heartbeat identity, queue content, reviewer identity, provider credential, or
signed URL. The committed map renders Australia scope only and keeps ALA
occurrence layers withheld behind the existing dataset-rights gate.

Rollback: revert the one Task 12.2 commit. The existing submitted Verify,
Species, Quality, Contributor, and Ask surfaces remain independent components;
rollback restores only the previous Live placeholder.
