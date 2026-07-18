# Task plan — ButterflyLens 12.3

Task ID: `butterflylens-12.3`

Objective: add privacy-safe operational monitoring for heartbeat freshness, API
budget, stage health, queue depth, failures, artifacts, map refresh, models, and
disk/memory state without making live telemetry a site dependency.

Starting, origin, remote, and deployed SHA:
`5432772619bceebd9f5a4762993c53e84abd4de7`.

Deployment evidence: GitHub Pages run `29638070094` built and deployed the
worker-independent site successfully. The served asset contains the committed
operations heading, unavailable-worker state, withheld occurrence layer,
bundled review route, and always-bundled snapshot.

BioMiner: published SHA
`c462c848c9e9cb18c4efc86fa22bbae01af05a3b` remains active and dirty with no
immutable GBIF handoff. Do not read live counters or copy partial outputs.
Monitoring defaults must use unavailable values rather than importing active
BioMiner state. The user-reported Flickr fetch remains external and active; do
not call it or expose partial counts as ButterflyLens telemetry.

Supabase boundary: add an append-only, service-write-only monitoring snapshot
table with typed nullable metrics, RLS, indexed foreign keys, exact states, and
no identities, raw queues, failure messages, coordinates, secrets, or URLs.
Add a public read-only Edge Function using `@supabase/server` `auth: none`; it
selects only the configured public project's latest allowlisted row through the
admin client, returns `no-store`, and permits only the configured Pages origin.
Keep `verify_jwt = false` only for this non-personal public status endpoint.

Browser boundary: bundle a complete submitted monitoring snapshot so every
metric always renders with an explicit submitted, unavailable, or unfinished
state. An optional HTTPS endpoint may refresh the exact live contract with a
small response/time budget, no credentials, no referrer, and no cache. Any
invalid response, outage, timeout, or missing endpoint retains the bundled
snapshot and the Task 12.2 site surfaces.

Model boundary: YOLOE and BioCLIP remain `unfinished`; no model is loaded or
called. Model telemetry cannot be interpreted as scientific quality.

Tests: database constraints, RLS, append-only behavior and indexes; Edge
method/origin/config/not-found/error/success responses; exact monitoring parser
and null/value invariants; transport URL/body/time/credential limits; component
rendering and live refresh fallback; full Python, Deno, web, rights, licensing,
JSON/JSONL, build, staged-scope, secret and Pages deployment checks.

Rollback: remove the optional monitoring URL variable and client loader,
undeploy the public status function, then apply a forward migration revoking and
dropping its append-only table. The submitted monitoring snapshot and all Task
12.2 static content remain independently revertible.
