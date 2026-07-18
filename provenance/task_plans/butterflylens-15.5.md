# ButterflyLens Task 15.5 plan

Task: Security and compliance.

Commit: `chore(security): verify ButterflyLens release`

## Objective and judging criterion

Run and preserve one credential-free release-security gate covering RLS,
secrets, dependency integrity, licences, provider/media rights, privacy,
rate-limit behavior, abuse boundaries, external-network inventory, and staged
diff safety. Improve judge confidence by distinguishing a verified static
submitted replay from production/community/data release readiness.

## Files and contracts

- Harden the local Supabase Auth configuration so the versioned prelaunch
  privacy block cannot accidentally permit sign-up.
- Add an offline release-security verifier and exact regression tests for all
  public-table RLS, security-invoker views, fixed-path security definers,
  high-signal secrets, and allowlisted external-network boundaries.
- Add a human-readable release review that records passing controls and keeps
  every unresolved privacy, data-rights, YOLOE, and BioCLIP block explicit.
- Record the Task 15.4 commit/push/Pages receipt and Task 15.5 tool/model
  provenance.

## Verification

- Focused RLS/schema tests and every tracked pgTAP definition; static fallback
  is explicit because Docker access, Supabase CLI, and session-visible MCP
  tools are unavailable.
- High-signal tracked-file and staged secret scans.
- Exact npm and Deno dependency/lock audits, licence and rights verifiers.
- Privacy manifest/config review, Flickr hourly/retry simulations, Edge abuse
  tests, external-network inventory, full repository regressions, and
  `git diff --check`.

## Risks, rights, and external work

- A passing control verifier must not be represented as permission to enable
  community writes, run a live analyst, publish rights-conflicted ALA rows, or
  execute skipped model work.
- The rebuilt ButterflyLens ALA baseline remains authoritative, while its three
  dataset citation-rights conflicts continue to block downstream public-product
  release.
- GitHits remains disabled. Current official Supabase security, RLS, API, npm,
  and changelog guidance is used through primary documentation.
- BioMiner remains active without an immutable complete ButterflyLens handoff;
  no partial artifact is copied. No Flickr API, YOLOE, or BioCLIP work occurs.
