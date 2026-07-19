# ButterflyLens 18.5 — current immutable completion audit

Status: **completion evidence refreshed; the overall ButterflyLens goal and
public release remain unfinished**.

Starting and remote SHA:
`45fb5ac07dcd51852c9e92217667f3f5052868fe`.

Audited boundary:

- commit `45fb5ac07dcd51852c9e92217667f3f5052868fe`;
- tree `aa93a6abf058d15c0ef80c7bde241a3355cfe024`;
- audit ID `butterflylens-18.5.1`.

Subtask commit:

- `f893b84e47468446db717db9982056c7aaf81057` — deterministic current audit,
  fixed-boundary verifier, release-security integration, and mutation tests.

Ending and remote SHAs: pending the containing Task 18.5 closeout commit and
non-force task push.

## Outcome

`provenance/completion_audit.v2.json` is now the current immutable completion
account. It retains all 100 criteria and all 46 named minimum artifacts from
the source goal, fixes the evidence boundary to the already-pushed Task 18.4
tree, and derives `goal_complete=false`.

The historical v1 audit is preserved byte-for-byte at its original Task 18.2
boundary. The v2 builder derives from that inventory and has only a closed,
verifier-enforced transition set. Unchanged rows must remain identical to v1,
and future worktree paths cannot be credited as past evidence.

The current criterion summary is 80 satisfied, eight partial, seven blocked by
user instruction, and five blocked externally. The artifact summary is 14
present, seven present equivalents, five blocked by user instruction, and 20
blocked externally.

## Exact evidence changes

Only criteria 19, 61, 63, 64, 65, 66, 67, 68, 72, and 96 were upgraded. These
changes credit the checksum-pinned rights-screened ALA aggregate map, national
heatmap, record bubbles and totals, state/territory, IBRA, LGA statistical
approximation, H3 drilldowns, credential-free static operation, and public
judge route.

Only these three minimum artifacts were upgraded to present:

- `geographic_impact_cells.parquet`;
- `geographic_impact_summary.parquet`;
- `map_manifest.json`.

Criterion 62 remains blocked externally because Flickr is unavailable.
Criterion 69 remains partial because a real two-source maturity comparison is
not available. No map evidence is treated as biological completeness,
presence, absence, abundance, identification accuracy, or a legal rights
conclusion.

## Verification

- The full Python repository suite passes all 661 tests in 31.608 seconds.
- The 28 focused historical/current audit, contract-coverage, and
  release-security tests pass.
- Both fixed-boundary verifiers pass. The historical audit remains at 70
  satisfied and false; the current audit records 80 satisfied and false.
- The checked-in v2 audit exactly matches deterministic generator output.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for 631 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 607 tracked text files, and 11 explicit network
  boundary files while retaining `release_ready=false`.
- JSON and JSONL parsing, Python compilation, whitespace, and staged-scope
  checks pass.

## Provenance and boundaries

The exact source goal was reviewed under Headroom receipt
`898dbe5ec3520d1425bf5d0f`; the updated agent pack was reviewed under receipt
`68f877e2154683642274c51a`. GitHits remained unavailable and was not called.
Valyu was not needed because the audit depends only on immutable local Git
objects and contracts.

BioMiner is still fetching Flickr metadata only. This task did not overlap
that active work, so no mutable BioMiner record or partial output was
inspected, copied, or counted. ButterflyLens made no Flickr API call. No live
model, connected Supabase project, provider, B2, image-generation, or
video-generation mutation occurred.

## Binding unfinished work

The immutable completed Flickr handoff and ALA/Flickr comparison remain
external blockers. YOLOE and BioCLIP remain explicitly unfinished by user
instruction. Human review, representative quality estimates, observed live
worker evidence, representative live Bounded model evaluation, real community
evidence, video recording, human approval, and public release are also
unfinished.

The next safe overlapping action is to wait for BioMiner to publish a complete,
immutable Flickr metadata handoff, then inspect and copy that finished data in
a new numbered task without running any Flickr API calls here.
