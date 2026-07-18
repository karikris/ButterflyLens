# Task plan — ButterflyLens 12.1

Task ID: `butterflylens-12.1`

Objective: provision the public ButterflyLens service boundary using Supabase
PostgreSQL/Auth/RLS, authenticated Supabase Edge Functions for the GPT-5.6
analyst, rights-gated short-lived B2 URLs, narrow audited run controls, and a
static React deployment.

Competition criterion improved: a public, reproducible deployment path whose
browser contains no provider or service credential and whose submitted replay
remains available independently of live services.

Starting and remote SHA:
`0d4dc889dd6a08f79736f168ef988baf25988aca`.

BioMiner: last observed at
`990640e1f1a27da1c459f54eaa43c55736846500`, active and dirty with no immutable
GBIF handoff. Infrastructure work does not overlap the active BioMiner record,
so no partial output will be inspected or copied.

TaxaLens: observed at
`e845dd98493979f37b04dbb6538e0d7b8758ca11`; its unrelated dirty files will not
be read or changed.

Relevant instructions: root `AGENTS.md`; `docs/agents/ARCHITECTURE.md`,
`TESTING_AND_RELEASE.md`, `TOOLS.md`, `GIT_AND_PROVENANCE.md`, and
`TASK_TEMPLATE.md`; the Supabase and Supabase Postgres best-practices skills.
GitHits is disabled by user direction. Current official Supabase, Backblaze,
GitHub Pages, and Vite deployment guidance is recorded in
`provenance/valyu.jsonl` through the official-source fallback.

Artifacts: add one migration for append-only B2 signing receipts and
compare-and-swap run-control receipts; add authenticated `sign-b2-object` and
`control-butterflylens` Edge Functions; retain the authenticated
`ask-butterflylens` GPT-5.6 boundary; add a credential-free B2 provisioning
contract and a manually gated production-services workflow; add a pinned
GitHub Pages workflow and configure the Vite base path.

Database boundary: every new table has RLS, indexed foreign keys, least-
privilege grants, and append-only mutation rejection. Browser users never
receive service credentials or a private storage key. A trigger applies only
the closed `pause_run`, `resume_run`, and `cancel_run` action set atomically,
checks an active curator/administrator membership for the verified actor, and
requires the expected run revision.

B2 boundary: sign only exact committed, decoded, display-authorized,
non-removed B2 objects already visible through caller-scoped RLS. Allow only
`GET` and `HEAD`, default to 300 seconds, cap at 900 seconds, validate the B2
endpoint and content-addressed object prefix, return `no-store`, and persist a
receipt without the URL, query string, storage key, or credential. Private and
public bucket credentials remain separately scoped operator secrets.

Live-state constraint: the Supabase MCP OAuth grant is configured for project
`ujfsrohgsrmssmfqgdsp`, but this already-running client has no MCP tool until a
reload. The Supabase CLI has no access token, the project hostname currently
does not resolve from the shell, inherited `SUPABASE_URL` is misassigned to a
publishable key, and no B2 credentials are present. Do not claim or attempt a
Supabase/B2 deployment without those prerequisites. The public static site may
be deployed through the already-authorized GitHub repository after its build
and workflow are committed.

Tests: pgTAP schema/role/transition tests; deterministic SigV4 test vectors;
Edge request/auth/rights/error tests; frozen Deno lock/type/format; full web
tests/typecheck/build with the Pages base; full Python, rights, licensing,
JSON/JSONL, secret/model/media/large-file, whitespace, workflow syntax, Pages
deployment, and remote-SHA verification.

Rights/privacy: introduce no provider data, image, model output, account key,
signed URL fixture, private reviewer record, or precise coordinate. This task
makes no Flickr API, GPT-5.6, YOLOE, BioCLIP, or scientific-model call.

Rollback: disable GitHub Pages, remove the two deployment workflows and Vite
base configuration, undeploy the two new Edge Functions, remove their secrets,
and apply a forward Supabase migration that revokes/drops the new trigger,
functions, policies, and tables. Delete B2 buckets only after an operator
proves they are empty and no manifest references them.
