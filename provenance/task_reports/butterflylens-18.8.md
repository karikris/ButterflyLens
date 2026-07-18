# ButterflyLens 18.8 — Supabase MCP OAuth boundary

Status: **least-privilege MCP configuration complete and browser OAuth launched;
operator approval, client tool discovery, live evidence, overall ButterflyLens
goal, and release remain unfinished**.

Starting and remote SHA:
`6630862c7abc497c11c8a6c957277a91fe0b2faf`.

Subtask commit:

- `49c39561881ad5960744ebb774604954db65318d` — project-scoped,
  read-only, database/docs-only hosted Supabase MCP declaration, operator guide,
  deterministic tests, and provenance.

Ending and remote SHAs: pending this Task 18.8 closeout commit and non-force
task push.

## Outcome

The repository now declares the official hosted HTTP MCP endpoint in
`.mcp.json` for exact project `ujfsrohgsrmssmfqgdsp`. Its URL combines
`project_ref`, `read_only=true`, and `features=database,docs`; the configuration
has no header, token, command, environment value, or client cache.

`SUPABASE_MCP.md` records the operator workflow and hard boundaries: confirm
non-production or obfuscated data, reload the MCP-aware client, complete browser
OAuth, retain manual approval for every call, and verify only read-only database
and documentation tools. Authentication does not authorize a migration, Edge
Function deployment, secret read, database write, Auth or Storage change, or
release claim.

The installed Codex CLI already contained a project-scoped Supabase entry. It
was updated through `codex mcp add` to the same read-only database/docs URL. The
CLI detected OAuth, launched one browser authorization flow, and retained a
localhost callback listener. Operator approval was still pending at the
closeout boundary. No OAuth URL, state, challenge, authorization code, token,
or client cache was copied into the repository or task report.

The current agent process cannot hot-load the newly configured server and still
exposes no Supabase MCP tools. A later client reload is required even if the
browser approval completes. Configuration and an open callback are not project
evidence, so no live criterion or release status was upgraded.

## Official contract

Current official Supabase documentation confirms the hosted endpoint, the
`.mcp.json` shape, browser OAuth without a personal access token, project
scoping, read-only mode, feature-group restriction, manual call approval, and
possible post-authorization client restart. The official remote-MCP changelog
also identifies the hosted HTTP endpoint and browser OAuth as the supported
replacement for manually committed tokens.

The exact sources and retrieval time are recorded in
`provenance/valyu.jsonl#butterflylens-18.8.1`. Valyu was unavailable as a
dedicated tool, so the authoritative official-web fallback was used. GitHits
remained unavailable and disabled by direct user instruction and was not
called. The Supabase skill determined the configuration and authentication
sequence; Headroom receipt `898dbe5ec3520d1425bf5d0f` covers the exact source
goal.

## Verification

- The complete repository suite passes all 670 Python tests in 32.210 seconds
  under the existing `.venv` and contracts-package path.
- Four focused Supabase MCP tests prove the exact HTTPS host/path, one-project
  scope, read-only flag, database/docs feature restriction, credential-free
  shape, and honest current-state guide.
- The focused MCP and release-security matrix passes all eight tests.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 644 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 620 tracked text files, and 12 explicitly
  inventoried external-network boundary files. `release_ready=false` remains
  binding.
- Historical and current completion audits remain valid; the current audit
  retains 80 satisfied criteria and `goal_complete=false`.
- Staged secret scanning passes for all seven implementation files. JSON,
  JSONL, Python compilation, whitespace, and staged-scope checks pass.

The first raw full-suite command used host Python 3.14 without the repository's
installed `rfc8785` and `pyarrow` packages and therefore produced dependency
import errors. The exact same suite passed with the existing `.venv`; no code
change was made in response to the environment-only failure.

## Binding unfinished work

The OAuth browser flow still requires operator approval, followed by a client
reload and a manual, read-only tool inspection. Until that happens, there is no
evidence of the remote database schema, migrations, RLS, functions, heartbeat,
append-only updates, or live worker. No Supabase project read, secret access,
query, mutation, or deployment occurred in this task.

BioMiner is still only fetching Flickr metadata according to the user. This
non-overlapping task did not inspect, copy, or count its mutable record and made
no Flickr API call. YOLOE and BioCLIP remain unfinished by user instruction. No
OpenAI Responses request, provider call, B2 action, model execution, or public
release occurred.

After OAuth approval and client reload, the next safe action is a manually
approved read-only inventory of the exact project followed by comparison
against the versioned migrations. If no client tool becomes available, do not
loop browser authorization; preserve the local deterministic product and
report the external authentication boundary.
