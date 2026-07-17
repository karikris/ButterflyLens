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
