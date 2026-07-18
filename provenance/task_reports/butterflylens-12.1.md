# ButterflyLens 12.1 — Public service infrastructure

Status: **deployment definitions and security boundaries implemented; static
deployment ready; credentialed Supabase and B2 application pending**.

Starting SHA:
`0d4dc889dd6a08f79736f168ef988baf25988aca`.

## Outcome

ButterflyLens now has a pinned GitHub Pages deployment for the static React
application, with the repository-site `/ButterflyLens/` base injected only at
build time. The submitted, credential-free replay remains usable independently
of every live service.

The Supabase deployment adds authenticated `sign-b2-object` and
`control-butterflylens` Edge Functions alongside the existing authenticated
GPT-5.6 analyst route. B2 signing authorizes through caller-scoped RLS before a
service-only storage lookup, admits only committed and rights-displayable
objects, signs only `GET` or `HEAD` for 300 seconds by default and at most 900
seconds, and records a URL-free append-only receipt. The server-action boundary
accepts only pause, resume, and cancel with an expected run revision. A
transaction-scoped advisory lock and database trigger verify active project
authority and apply the transition with its append-only receipt atomically.

The B2 contract separates private originals from public thumbnails, requires
SSE-B2, configures the exact Pages origin CORS policy, rejects bucket ACL drift,
and intentionally omits lifecycle deletion and Object Lock. A manually gated
production workflow can apply migrations, secrets, Edge Functions, and bucket
configuration through a protected `production` environment without putting a
credential in the browser or repository.

## Verification

- 464 locked Python tests passed, including eight deployment-structure tests.
- 39 Deno Edge tests passed; all three Edge entry points type-check and all 19
  TypeScript files pass the formatter check.
- A separately calculated Python HMAC reference matches the frozen AWS SigV4
  signature produced by the TypeScript signer.
- All 67 Vitest tests, web typecheck, production Pages-base build, 116-package
  dependency report, and media verifier pass. The unchanged client bundle is
  1,468.09 kB (222.76 kB gzip) and retains its existing chunk-size warning.
- The uv lock, frozen environment, eight-package compatibility check, rights
  verification for 52 tracked provider payloads, licence verification for 441
  tracked files, workflow YAML, shell syntax, JSON/JSONL, whitespace, and
  secret-pattern checks pass.
- The pgTAP file declares and contains 38 assertions over tables, roles,
  indexes, RLS, authority, transitions, compare-and-swap, signing TTLs, and
  append-only behavior. It was not executed: Docker socket access is denied and
  this process has no authenticated live-project database connection.

## Live deployment state

The Supabase MCP OAuth grant completed for project
`ujfsrohgsrmssmfqgdsp`, but this already-running client does not expose the new
MCP tools until it is reloaded. The CLI has no access token, the inherited
`SUPABASE_URL` contains a publishable key rather than a URL, the project host is
not resolving from this shell, and no B2 credentials are present. Consequently
no migration, Auth setting, secret, Edge Function, B2 bucket, object, or key was
changed and this report makes no live Supabase/B2 claim. The production-services
workflow remains manual and cannot run without protected environment secrets.

The GitHub Pages workflow is designed to deploy from the task commit after it
reaches `main`; activation and remote workflow evidence are checked as the
final publication step.

## Parallel work and exclusions

The user-reported Flickr fetch remains active with 50,000 unique images and an
approximately 20-hour completion estimate. No Flickr API call or partial Flickr
output was made or consumed. BioMiner's last inspected record remained active
without an immutable GBIF handoff, and this infrastructure task did not overlap
its acquisition work, so no partial BioMiner output was inspected or copied.
The supplied GBIF download remains queued for authoritative Parquet admission
after that handoff. GitHits remained disabled. YOLOE and BioCLIP remain
explicitly unfinished and were not run.
