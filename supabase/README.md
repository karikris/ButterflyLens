# ButterflyLens Supabase database

The database is built as ordered Supabase migrations. Task 3.1.1 establishes
the typed `projects` and `runs` control-state tables. Task 3.1.2 adds species
and name projections, logical query definitions and associations, deduplicated
physical API requests, and versioned Flickr source records. The remaining 3.1
migrations add model-evidence, review, map-impact, and user-role/RLS storage.

The discovery schema performs no provider call and stores no credential.
Logical species/name associations remain separate from physical request rows,
query terms are structurally forbidden from becoming labels, and unknown media
rights block download, inference, display, and redistribution.

The model-evidence schema adds content-addressed media, duplicate-group
membership, typed pipeline stages, fenced worker leases, append-only
heartbeats, and raw model-evidence state. YOLOE and BioCLIP stage values exist
only so their blocked or `skipped_unfinished` state can be represented. This
migration does not acquire model weights or produce routes, embeddings,
prototypes, scores, or human-verification claims.

The review schema separates pseudonymous profiles, blind campaigns,
independent assignments, append-only review events, layered consensus, private
domain-specific reliability estimates, and quality snapshots. Review
corrections supersede earlier events, reliability cannot use BioCLIP or
majority agreement as truth, and release consensus requires an expert gate.

The map-impact schema stores immutable submitted/live comparisons against the
authoritative rebuilt ButterflyLens ALA baseline. Every count and flag carries
an availability state so missing Flickr, YOLOE, or BioCLIP evidence cannot
become a misleading zero. Release candidates are append-only, blocked by
default, coordinate-coarsened, and require every scientific gate plus qualified
authorization before approval.

The role migration adds project-scoped reviewer, expert, curator, and
administrator memberships. Anonymous access is restricted to explicitly
public projections. Reviewers can read their own assignments and append a
decision only to their own open assignment; consensus stays blind until they
respond. Curators receive project-scoped inspection and campaign-management
policies, while raw evidence and scientific releases remain server-written.

The community-account migration adds an idempotent registration RPC for
permanent Supabase Auth users. It creates only a pseudonymous base reviewer and
self-service membership in an active project. Anonymous Auth users cannot
register, and expert, curator, or administrator authority still requires a
trusted server-controlled path. Guest browsing continues through the `anon`
public projections without creating an Auth account.

Every public table has row-level security. The `anon` role can read only safe
columns through four security-invoker public views. Authenticated access is
further constrained by self, assignment, and project-role policies; raw writes
and scientific releases remain server-only. The `service_role` credential must
never enter a browser or committed configuration.

Create migration filenames through the CLI:

```bash
npx --yes supabase migration new descriptive_name --yes
```

Run the local migration and pgTAP suite:

```bash
npx --yes supabase start --yes
npx --yes supabase db reset --local --no-seed
npx --yes supabase test db --local supabase/tests/database
```

The first migration targets PostgreSQL 17, matching the current generated
Supabase configuration and avoiding deprecated PostgreSQL 14 support.

## Ask ButterflyLens Edge Function

`ask-butterflylens` is an authenticated, read-only OpenAI Responses API
boundary. It uses `@supabase/server` user authentication behind the platform
JWT gate, and it does not use a service-role client or write to Postgres. The
browser may send only a Supabase publishable key and the signed-in user's
access token. `OPENAI_API_KEY` is read only inside the Edge Function.

The committed Deno import map pins `@supabase/server` 1.4.0 and `openai`
6.48.0 exactly. `deno.lock` and `dependency-licenses.json` cover the complete
12-package npm tree. Use frozen dependency resolution for every check:

```bash
npx deno test --config=supabase/functions/deno.json --frozen=true supabase/functions/tests
npx deno check --config=supabase/functions/deno.json --frozen=true supabase/functions/ask-butterflylens/index.ts
```

For local manual testing only, put the secret in an ignored file such as
`supabase/functions/.env.local` and serve the function through the local
Supabase gateway:

```bash
npx --yes supabase functions serve ask-butterflylens --env-file supabase/functions/.env.local
```

The file must contain `OPENAI_API_KEY`; never prefix that secret with `VITE_`,
place it in browser configuration, commit it, print it, or paste it into a test
fixture. Invocation requires a real user JWT. A publishable key by itself is
not authorization.

Production setup is an explicit operator action: set `OPENAI_API_KEY` through
Supabase Edge Function secrets, deploy `ask-butterflylens`, and retain
`verify_jwt = true`. The submitted static experience intentionally injects no
live client and performs no model call. Task 11.4 owns the separately labelled
credential-free stored replay.

## Production service boundaries

Task 12.1 adds two more authenticated functions:

- `sign-b2-object` first proves that the caller can read the media row through
  RLS, rechecks committed/decode/rights/display/removal state through the
  server client, signs only `GET` or `HEAD` for at most 900 seconds, and
  records a URL-free receipt before returning access.
- `control-butterflylens` accepts only `pause_run`, `resume_run`, and
  `cancel_run`. A database trigger independently checks active
  curator/administrator membership and the expected run revision, changes the
  run, and freezes the receipt in one transaction.

The manually gated production workflow applies migrations without seed data,
sets Edge secrets, and deploys the exact three functions. It requires the
`production` GitHub environment plus the secret and variable names declared
in `infra/supabase/production.v1.json`. Supabase Auth production site and
redirect URLs must match that file; local `config.toml` Auth settings are not
deployed by the CLI.

B2 deployment is defined in `infra/b2/buckets.v1.json`. Provisioning requires
an account-level key only for bucket administration. The Edge signer must use
a separate read-only, private-bucket, `butterflylens/v1/`-prefix key. No
credential, signed URL, query string, or private storage key belongs in GitHub
variables, browser configuration, logs, fingerprints, or database receipts.
