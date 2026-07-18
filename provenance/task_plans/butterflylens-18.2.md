# Task 18.2 plan — evidence-backed completion boundary

Task ID: `butterflylens-18.2`

Objective: close the current Codex work window with an exact, machine-readable
audit of all 100 final acceptance criteria and all 46 minimum required
artifacts, then add a deterministic fail-closed verifier that prevents an
overall completion claim while any criterion is partial or blocked.

Starting and remote SHA:
`7a2c2eba61cd10034096e006cdb04fd5018a2b10`.

Fixed audit tree:
`fc29c3de542b63cb3905ab4059e16a2d81548138`.

Source goal SHA-256:
`898dbe5ec3520d1425bf5d0f891c49d6f7615318ed28b35b16f7513684a3fa40`.

BioMiner coordination SHA:
`ae6a18509b7be48da5c6ca69ab0caacf4632cc70`. BioMiner is still fetching
Flickr metadata. Its partial output, logs, query counters, and uncommitted files
remain outside ButterflyLens; no Flickr API call will be made here.

Authoritative data boundary: the rebuilt ButterflyLens ALA baseline remains
authoritative. The separately fingerprinted GBIF occurrence evidence is
complementary and does not replace or silently merge into that baseline.

Explicit exclusions: YOLOE and BioCLIP remain `unfinished_not_run` by user
direction. No model weight, model output, embedding, prototype, candidate score,
or inferred completion state will be created.

GitHits: unavailable and disabled by direct user instruction. It will not be
called. Append-only provenance records will retain that status without
inventing search results.

Skills used:

- Headroom, to audit the complete 2,611-line goal while retaining exact
  acceptance criteria and artifact names under receipt
  `898dbe5ec3520d1425bf5d0f`.
- Supabase, for the read-only safety boundary around existing local migrations,
  RLS evidence, worker status, and live-service claims. No connected project,
  schema, authentication state, Storage object, or Edge Function is mutated.

## Subtask 18.2.1 — freeze the audit

- Record the exact 100 criterion texts and evidence status.
- Inventory every minimum required artifact, including exact, equivalent,
  externally blocked, and user-deferred states.
- Publish a short human-readable completion statement.
- Keep `goal_complete` false unless all 100 criteria are `satisfied`.

Commit: `docs(provenance): audit completion evidence`.

## Subtask 18.2.2 — enforce the audit

- Add a no-network verifier for the audit schema, fixed Git boundary, evidence
  paths, exact criteria, summary counts, artifact inventory, and completion
  rule.
- Add focused regression tests that reject missing criteria, false completion,
  invalid evidence paths, and drifted counts.
- Run proportionate repository gates, publish the task report, commit, and
  non-force push `main` once for Task 18.2.

Commit: `test(provenance): prevent false completion claims`.
