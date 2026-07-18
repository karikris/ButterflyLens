# Task 18.8 plan — configure the Supabase MCP OAuth boundary

Task ID: `butterflylens-18.8`

Objective: add the missing project-local hosted Supabase MCP declaration so a
reloaded MCP-aware client can open browser OAuth, while constraining later tool
access to the recorded ButterflyLens project, read-only database queries, and
official documentation.

Competition criterion improved: operational evidence for criteria 82, 83, 90,
and 97 becomes reachable through a least-privilege inspection path. This setup
does not satisfy any live criterion, authenticate the current session, or
authorize a project mutation.

Starting and remote SHA:
`6630862c7abc497c11c8a6c957277a91fe0b2faf`.

BioMiner boundary: BioMiner is still only fetching Flickr metadata according
to the user. This MCP configuration does not overlap that active work, so its
record, worktree, partial output, and API activity will not be inspected,
copied, or counted. No Flickr API call will occur.

Agent files read: root `AGENTS.md`, `docs/agents/TOOLS.md`,
`GIT_AND_PROVENANCE.md`, `ARCHITECTURE.md`, `TESTING_AND_RELEASE.md`, and
`TASK_TEMPLATE.md`.

Skills used: Supabase for the official hosted-MCP configuration and
authentication workflow; Headroom for the exact source goal under receipt
`898dbe5ec3520d1425bf5d0f`.

GitHits: unavailable and disabled by direct user instruction for the rest of
the goal. No call will be made; the exact disabled status will be recorded.

Valyu: unavailable as a dedicated tool. Current official Supabase MCP
documentation and the official remote-MCP changelog were inspected through the
authoritative web fallback on 19 July 2026 (Australia/Sydney).

## Subtask 18.8.1 — declare a least-privilege hosted MCP client

- Add the exact official hosted HTTP endpoint in `.mcp.json`.
- Scope it to recorded project `ujfsrohgsrmssmfqgdsp`.
- Require `read_only=true` and limit features to `database,docs`.
- Commit no token, header, secret, command, environment value, or client cache.
- Document browser OAuth, manual tool approval, production-data prohibition,
  reload requirements, and the distinction between authentication and action
  authorization.
- Prove the URL, query constraints, secret-free shape, and honest current-state
  language with deterministic tests.

Files: `.mcp.json`, `SUPABASE_MCP.md`, focused tests, and provenance ledgers.

Contracts affected: operator tooling only. Application runtime, submitted
replay, schema, migrations, Edge Functions, provider data, worker state, and
public claims remain unchanged.

Security/privacy: the project reference is non-secret; all OAuth material stays
in the client. The configuration must fail closed to one project, read-only
queries, and database/docs feature groups. A later operator must confirm the
project contains development or obfuscated data before authenticating.

Tests: focused config tests; release-security and licensing verifiers; JSON and
JSONL parsing; secret-pattern scan; full Python suite; `git diff --check`; clean
staged-scope inspection.

Rollback: remove `.mcp.json`, its operator guide, and the focused tests. Revoke
the OAuth grant in Supabase separately if a later client completes it; this
task itself creates no grant or token.

Commit: `chore(supabase): configure MCP OAuth boundary`.
