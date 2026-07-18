# Supabase MCP operator boundary

ButterflyLens declares the hosted Supabase MCP server in `.mcp.json` for
operator-only development and verification. It is not an application runtime
dependency and the credential-free Submitted replay never uses it.

The checked-in URL is deliberately constrained:

- `project_ref=ujfsrohgsrmssmfqgdsp` limits access to the ButterflyLens project
  recorded in `HUMAN_DECISIONS.md` and disables account-management tools;
- `read_only=true` executes database queries through Supabase's read-only
  Postgres role; and
- `features=database,docs` excludes every tool group except database inspection
  and Supabase documentation.

The project reference is an identifier, not a credential. The repository must
never contain an OAuth token, personal access token, service key, refresh token,
authorization header, or MCP client cache.

## Authenticate after a client reload

1. Confirm that the target is a development project with non-production or
   obfuscated data. Do not connect Supabase MCP to production data.
2. Restart or reload the MCP-aware client so that it discovers `.mcp.json`.
3. Select the `supabase` MCP server and choose its authentication action.
4. Complete browser OAuth for the organization that owns the exact project.
5. Keep manual approval enabled for every tool call.
6. Verify that only database and documentation tools appear and make a
   read-only inspection before recording any live-state claim.

Hosted Supabase MCP uses dynamic browser OAuth by default, so a personal access
token is neither needed nor permitted for this interactive repository setup.
Authentication grants tool access only; it does not authorize a migration,
Edge Function deployment, secret read, database write, Auth change, Storage
operation, or release claim.

## Current state

The remote endpoint is reachable and the project-local configuration is
versioned. This already-running Codex session did not discover a Supabase MCP
tool and did not complete OAuth after the configuration was added. A client
reload and explicit operator browser approval remain required. No Supabase
project read or mutation is evidenced by this file.

Official references:

- [Supabase MCP Server](https://supabase.com/docs/guides/ai-tools/mcp)
- [Supabase Remote MCP server changelog](https://supabase.com/changelog/39434-supabase-remote-mcp-server)
