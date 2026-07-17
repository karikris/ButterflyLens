# ButterflyLens Supabase database

The database is built as ordered Supabase migrations. Task 3.1.1 establishes
the typed `projects` and `runs` control-state tables only. Later 3.1 subtasks
add discovery, model-evidence, review, map-impact, and user-role/RLS policy
tables.

Both current public tables have row-level security enabled immediately. The
`anon` and `authenticated` roles have no table or sequence privileges until
Task 3.1.6 defines project membership and least-privilege policies. The
server-only `service_role` has explicit access; its credential must never enter
a browser or committed configuration.

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
