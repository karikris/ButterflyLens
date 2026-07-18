# Task 18.4 plan — reconcile submitted analyst and judge map evidence

Task ID: `butterflylens-18.4`

Objective: make the deterministic Ask ButterflyLens evidence tools, stored judge
replay, README hero, and 90-second judge route consume the real rights-screened
ALA map added in Task 18.3, while retaining the incomplete Flickr comparison as
explicitly unavailable rather than zero.

Competition criteria improved: deterministic evidence tools and artifact
citations (74–80), blue ALA map and national/lower-scope drilldowns (61, 63–68),
worker-independent map behavior (72), working public map/judge route (96 and
98), and artifact-backed displayed metrics (99).

Starting and remote SHA:
`982238de0f7ff438403d40b03856f330de7794fc`.

Source goal SHA-256:
`898dbe5ec3520d1425bf5d0f891c49d6f7615318ed28b35b16f7513684a3fa40`.

BioMiner boundary: BioMiner is still fetching Flickr metadata only. This task
does not overlap its active work, so its mutable record will not be inspected
or copied. No Flickr API call will be made. A complete immutable handoff is
still required before the amber layer or any ALA/Flickr difference is admitted.

TaxaLens boundary: no TaxaLens source or artifact is needed; the existing local
ButterflyLens tool contracts and Task 18.3 map are authoritative inputs.

Agent files read: root `AGENTS.md`, `docs/agents/README.md`,
`TOOLS.md`, `GIT_AND_PROVENANCE.md`, `SCIENCE_AND_DATA.md`,
`ARCHITECTURE.md`, `TESTING_AND_RELEASE.md`, and `TASK_TEMPLATE.md`.

Skills used: Headroom, to retain the exact long-form goal under receipt
`898dbe5ec3520d1425bf5d0f`; and the Supabase skill, to keep the shared Edge
Function path aligned with current official Deno testing guidance without a
connected-project mutation.

GitHits: unavailable and disabled by direct user instruction for the remainder
of the goal; it will not be called. The implementation is derived from the
existing repository contracts and tests.

Valyu/current official documentation: the Supabase skill requires a current
changelog and Edge Function test-contract check. Official Supabase sources were
used only to confirm that this pure shared Deno evidence projection has no
relevant breaking change and should remain locally unit-tested. No external API
behavior, provider term, licence, project state, or deployment is changed.

Rights and scientific boundary: the full 236,897-row rebuilt ALA baseline
remains authoritative and preserved. The public map is the separate 213,310-row
aggregate projection that excludes three already flagged datasets. Exclusion is
a conservative publication decision, not a legal conclusion. Provider labels
remain assertions, no raw coordinates enter analyst output, and missing Flickr,
review, model, or release evidence remains unavailable.

Security/privacy boundary: tools remain read-only, checksum-pinned, bounded,
credential-free, and exact-scope only. The public capture may contain only the
offline application and committed aggregate evidence; no provider request,
secret, signed URL, source photograph, or active-worker observation may enter.

## Subtask 18.4.1 — ground the analyst map tools

- Move the submitted analyst artifact registry to the exact Task 18.3 map-data
  commit and add the browser map snapshot as a checksum-pinned artifact.
- Validate and index national/state/IBRA/LGA/H3 scopes from the pinned snapshot.
- Return exact rights-screened ALA aggregate counts and fingerprints while
  keeping Flickr counts and two-source differences null and unavailable.
- Accept exact percent-encoded scope IDs, fail closed for missing scopes, and
  retain species-granularity abstention when the map has no species projection.
- Regenerate strict tool contracts and add focused positive, negative,
  immutability, coordinate-safety, and bounded-output tests.

Commit: `feat(openai): ground map tools in submitted ALA evidence`.

## Subtask 18.4.2 — refresh replay and evaluation

- Pin the deterministic tool implementation to the 18.4.1 commit.
- Regenerate the three stored judge replays so the ALA/Flickr answer cites the
  public map count while refusing a Flickr count or difference.
- Regenerate the representative offline evaluation suite and strict schemas;
  preserve zero live/model/network calls and null live metrics.
- Update replay/evaluation tests and the analyst package documentation.

Commit: `data(openai): refresh submitted analyst replay`.

## Subtask 18.4.3 — refresh public competition materials

- Update the README first screen, judge route, expected-state tables, rights
  boundary, and limitations to match the real submitted ALA map.
- Replace the stale withheld-map GIF with an eight-frame capture of the actual
  offline national heatmap and drilldown surface; block every non-local request.
- Update exact GIF/map tests and public analyst component expectations.

Commit: `docs(submission): align judge route with submitted map`.

## Task closeout

- Run focused analyst/replay/judge tests, full Python and web gates, production
  build, browser functional/visual coverage, contract parity, rights,
  licensing, security, JSON/JSONL, compilation, whitespace, and staged-scope
  checks.
- Record model usage, disabled GitHits/not-needed Valyu status, commit receipts,
  task report, allowed claims, and remaining external/user-deferred blockers.
- Push `main` once for Task 18.4 without force and verify the exact remote SHA.

Commit: `docs(provenance): close submitted map reconciliation`.
