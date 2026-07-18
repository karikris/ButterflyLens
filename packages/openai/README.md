# ButterflyLens deterministic analyst tools

This package is the read-only evidence boundary for the Ask ButterflyLens
analyst. It does not contain an OpenAI client, browser transport, database
credential, provider client, or live-workstore reader.

`tool_contracts.json` contains the fourteen strict Responses API function
definitions generated from `python/butterflylens_openai/catalog.py`. Rebuild it
with:

```bash
uv run --locked python3 scripts/build_openai_tool_contracts.py
```

The generator is deterministic and tests require its output to equal the
tracked artifact exactly. Every function is strict, read-only, and bounded.
Objects reject additional properties and require every field; optional model
arguments are required nullable values with separate semantic checks.

## Submitted evidence boundary

`submitted-artifacts.v1.json` pins every readable evidence artifact to the
published Task 11.1 commit and exact SHA-256. `SubmittedEvidenceRepository`
verifies every byte before making any artifact available. Tool citations always
include artifact ID, `karikris/ButterflyLens`, the exact commit, repository path,
and SHA-256 fingerprint.

The submitted tools can inspect the 463 accepted-species catalogue, source and
crosswalk state, provisional reference diagnostics, committed pipeline stages,
and deterministic species-level workflow priorities. They preserve the ALA
rights boundary and distinguish targeted review priorities from representative
quality sampling.

No completed immutable Flickr candidate/map snapshot, classification, review
consensus, private reviewer-quality snapshot, worker heartbeat, geographic
contribution snapshot, or authenticated impact snapshot is bundled. Those
tools return cited `unavailable` or `withheld` results with null values; they do
not return fabricated zeroes, infer absence, inspect BioMiner's active work,
call Flickr, or guess from model memory.

## Result contract

Each invocation returns one validated and fingerprinted envelope containing:

- validated query selectors;
- bounded scalar facts with `observed`, `derived`, `unavailable`, `withheld`,
  `unfinished`, `conflict`, or `not_applicable` state;
- at most 20 bounded records;
- allowlisted artifact citations;
- explicit limitations; and
- an RFC 8785 SHA-256 result fingerprint.

Reviewer and contributor tools are model-facing `self` operations. Later
server transport must supply and enforce authorization independently; model
arguments can never grant access or select another person. Results do not
expose private controls, expected answers, exact sensitive locations, reviewer
weights, rankings, speed metrics, probabilities, or scientific authority.

## Credential-free stored replay

`submitted-replays.v1.json` contains three exact single-turn judge questions
with their complete deterministic tool calls and output envelopes. It is
generated with:

```bash
uv run --locked python scripts/build_openai_replay.py
```

`replay-catalog.schema.json` is the strict generated Draft 2020-12 contract.
Tests rebuild both files, invoke every stored call again, and require
byte-identical outputs, exact response citations, and RFC 8785 SHA-256 result,
trace, and catalogue fingerprints.

The catalogue is labelled `replayed`, records zero network and Responses calls,
and says `model_invoked: false`. Its response shape deliberately has no model
identity field: GPT-5.6 did not author these stored answers. The public replay
only matches the three exact questions and never falls through to live
inference, re-executes a tool, or simulates a conversation.
