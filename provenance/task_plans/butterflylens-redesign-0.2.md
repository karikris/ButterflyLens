# ButterflyLens redesign Task 0.2 plan — screenshot defect matrix

Task ID: `butterflylens-redesign-0.2`

Objective: capture the unchanged pre-redesign public experience at the required
desktop/mobile and accessibility display states, inspect the rendered pixels,
and freeze a defect matrix with a root cause and acceptance test for every
recorded issue.

Starting local and remote SHA:
`056fe3563f6282a8bce4ea61ab1da3d96323e526`.

Capture-source application SHA:
`056fe3563f6282a8bce4ea61ab1da3d96323e526`.
Task 0.1 changed documentation only, so its web bundle remains the current
pre-redesign UI. The capture server will run locally with every non-local
request blocked.

Pre-existing user-owned untracked content remains:

- `AGENTS.md:Zone.Identifier`;
- `docs/agents/`.

Exact upstream observations at task start:

- BioMiner `bfdb4b38646f16062d7fb4a6d0f4b0674c8f01dd`, with the user confirming
  it remains in Flickr-metadata fetching only;
- TaxaLens `e845dd98493979f37b04dbb6538e0d7b8758ca11`.

This visual audit does not overlap BioMiner's active work, so it will not read,
copy, or count BioMiner output. It will make no Flickr API call. YOLOE and
BioCLIP remain unfinished.

## Capture set

Required Explore viewport states:

- 1440 × 900 light;
- 1280 × 720 light;
- 390 × 844 light/touch;
- 1280 × 720 reduced motion;
- 1280 × 720 forced colours/high contrast.

Additional 1280 × 720 section captures:

- current map;
- Verify;
- species/reference evidence;
- live operations;
- data quality;
- Community/contributor surface;
- Ask ButterflyLens analyst surface.

Every capture will record viewport, pixel size, emulation state, target
fragment, byte count, SHA-256, application source commit, Playwright version,
browser version, and zero-external-request policy in a generated manifest.

The WSL host lacks `libnspr4`, `libnss3`, and `libasound.so.2`. The exact Ubuntu
runtime packages will be downloaded and unpacked under `/tmp` and supplied
through `LD_LIBRARY_PATH`; the system package database will not be changed.

## Defect matrix

For each issue record:

- issue ID;
- route;
- viewport/state;
- severity;
- screenshot;
- observed problem;
- root cause;
- proposed fix;
- acceptance test;
- status.

The matrix will distinguish visible layout/information-architecture problems
from the already-audited persistence/scientific gaps. It will not label
unavailable evidence as zero or treat planned BioMiner/model work as present.

GitHits is unavailable and explicitly disabled by user instruction for the
remainder of the goal, so it will not be called. No external visual design or
source code will be copied.

## Verification and push

- verify manifest/image fingerprints and dimensions;
- visually inspect every capture;
- run the capture script twice and require identical image hashes;
- run focused visual/browser assertions, web tests/build, rights, licensing,
  release security, fixed completion audits, JSON/JSONL checks, and whitespace;
- commit `docs(ui): record visual defect matrix`;
- push `main` without force and verify the remote SHA.
