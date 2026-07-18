# Task plan — ButterflyLens 12.4

Task ID: `butterflylens-12.4`

Objective: add deterministic, fail-closed incident and fallback behavior for M5
sleep, network outage, Flickr outage, B2 outage, Supabase outage, model crash,
corrupted checkpoint, and rate-limit exhaustion without making any provider,
storage, database, or model call.

Starting, origin, remote, and deployed SHA:
`e605864a786bf6897135ba968b320c86c87b967f`.

Deployment evidence: GitHub Pages run `29638920381` built and deployed the exact
Task 12.3 SHA. The served bundle contains all nine operational-monitoring labels
and the submitted fallback.

Behavior boundary: implement one closed incident vocabulary and deterministic
plan for each required scenario. Every plan keeps the submitted snapshot and
last committed artifact queryable, forbids duplicate work and destructive
cleanup before durable acknowledgement, prevents scientific claims, and states
exactly which stage pauses, what evidence is retained, and what condition may
resume work. No incident may authorize an immediate retry, credential rotation,
rate-limit bypass, unverified checkpoint reuse, live-data publication, or model
fallback claim.

Checkpoint boundary: independently checksum bounded regular checkpoint files.
A mismatch or unsafe file fails closed; the incident plan quarantines rather
than deletes it, reuses only separately journalled committed work, and rebuilds
only affected uncommitted work.

Simulation boundary: exercise all eight incidents with fakes and local temporary
files only. The model-crash scenario is policy simulation with model execution
explicitly false; YOLOE and BioCLIP remain unfinished. Flickr outage and budget
tests must invoke no Flickr API. Supabase and B2 outage tests must invoke no live
service or deployment workflow.

BioMiner: published SHA
`079c4d846fd434d1d10973c66662ff2ca6fab53b` remains active. Its current-state
ledger still lists live GBIF acquisition and durable admission as remaining,
and no immutable handoff is published. Do not inspect or copy active outputs.
The user-reported Flickr fetch remains external and active.

GitHits is disabled by explicit user instruction and will not be called.

Tests: exact incident vocabulary and deterministic fingerprints; all eight
scenario-specific pause/retain/resume policies; corrupt checkpoint checksum;
committed-work reuse; public site continuity; no network/model imports or calls;
full Python, Deno, web, rights, licensing, JSON/JSONL, build, secret, staged
scope, and Pages deployment gates.

Rollback: revert the incident planner, checkpoint verifier, exports,
documentation, and tests together. Task 12.3 monitoring and its submitted
fallback remain independently deployable.
