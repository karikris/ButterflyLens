# ButterflyLens 8.1 — Community authentication

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `5b6659eb2e483810085a150301c2d0e9ca082f77`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

The existing Supabase schema already provided guest-safe public projections,
pseudonymous reviewer profiles, and project-scoped reviewer, expert, curator,
and administrator roles. This task adds the missing low-friction onboarding
boundary for a registered reviewer:

- unauthenticated guests continue to browse through the `anon` projections;
- a permanent Supabase Auth user may idempotently create one pseudonymous
  profile and one active base-reviewer membership;
- an anonymous Supabase Auth user is rejected even though Supabase maps that
  user to the `authenticated` Postgres role;
- the browser cannot request expert, curator, or administrator authority;
- public identifiers are generated inside the database and are distinct from
  the private Auth user ID;
- pseudonyms cannot contain email-like or HTTP contact details;
- paused, suspended, invited, or revoked identities require curator action and
  are never silently reactivated.

The registration function is a fixed-search-path `SECURITY DEFINER` RPC with
explicit `anon` revocation and a narrow `authenticated` execute grant. It does
not read `user_metadata`, expose a service credential, or grant direct table
inserts to browser roles.

## Evidence and provenance

The Supabase and Supabase Postgres best-practices skills were used. Current
official Supabase Auth, anonymous-sign-in, RLS, changelog, and Data API exposure
documentation was retrieved on 2026-07-18. Valyu was unavailable, so the
official documentation was fetched directly. GitHits remained unavailable and
was not retried. TaxaLens was inspected at its immutable commit; no code or
asset was copied from its dirty working tree.

No Flickr API call, YOLOE work, BioCLIP work, model artifact, scientific score,
or biodiversity claim was produced.

## Verification

- `uv run python -m unittest tests.test_community_auth_schema tests.test_rls_role_policies tests.test_review_database_schema -v` — 21 passed.
- pgTAP fixture — 15 assertions defined for function security, privileges,
  idempotency, role ceiling, and anonymous-user rejection.
- `npx --yes supabase status --output json` — unavailable because this runtime
  cannot access the Docker daemon; the pgTAP fixture could not be executed.
- `uv run python -m unittest discover -s tests -v` — 282 passed.
- Cross-language contract parity — passed: 24 schemas, 20 valid fixtures, 20
  invalid fixtures, 20 versions, and 15 vocabularies.
- Rights verification — passed for 51 tracked provider payloads while retaining
  the existing ALA public-product block.
- Licence verification — passed for 252 tracked files, one dependency manifest,
  and zero model files.
- Provenance JSONL validation and `git diff --check` — passed.

## Rights, privacy, and claims

No source media or occurrence data changed. Private Auth IDs remain confined to
RLS-protected tables and are not returned by the registration RPC. The task
supports account and role state only; it does not claim that any reviewer is an
expert or that any evidence has been human verified.
