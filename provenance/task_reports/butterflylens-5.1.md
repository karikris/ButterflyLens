# ButterflyLens 5.1 — worker identity and heartbeat

Status: implementation and task gates complete; task commit and non-force main
push follow this report.

Starting SHA and remote SHA: `7171193892fb420f310e80395c094c4dfa5287af`.
The ending commit and verified push SHA are recorded in the next append-only
`provenance/commits.jsonl` receipt because a commit cannot contain its own SHA.

BioMiner was inspected at
`c7eaa9bf3696a25a0c8229837819dccec4fb9d66`; TaxaLens was inspected at
`16242d1e97b4b7cee6823ed604232ebcc4436daf`. BioMiner still reports live
current-policy GBIF acquisition and scientific quality evidence as pending.
No relevant worker process was active, no incomplete BioMiner artifact was
copied, and dirty upstream worktrees were not changed.

The new runtime provides:

- a stable, private, atomic local registration reused across restarts;
- directly observed platform, architecture, chip, memory, MPS, RSS, and free
  disk fields;
- canonical worker-identity and heartbeat fingerprints;
- monotonic heartbeat sequence and observation time;
- one attached fenced lease with expiry-driven degraded health;
- exact append-only heartbeat persistence acknowledgement;
- graceful drain that blocks new lease/stage work;
- exact persisted lease-release acknowledgement before final shutdown;
- schema-valid empty configured/current model lists.

The synthetic M5 profile exists only as a test fixture. This WSL environment
does not establish that the target M5 worker is online. YOLOE and BioCLIP remain
explicitly unfinished, were not loaded or executed, and produced no artifacts.
The worker runtime contains no Flickr or other provider transport.

Verification:

- `uv run python -m unittest tests.test_worker_identity_heartbeat -v` — 9
  passed;
- `uv run python -m unittest discover -s tests -v` — 250 passed;
- Python compilation for the worker package and focused tests — passed;
- Python/TypeScript/JSON Schema contract parity — passed;
- rights verifier — passed with 51 tracked provider payloads;
- licence verifier — passed with 214 tracked files, one dependency manifest,
  and zero model files;
- provenance JSONL and `git diff --check` — passed.

Scientific claims allowed: the runtime can report directly observed operational
identity and health through fingerprinted records. Scientific claims blocked:
worker health does not establish evidence maturity, model readiness, provider
acquisition, accuracy, or release readiness.

Next safe task: 5.2, a development `launchd` service and secret-safe lifecycle
around this runtime. Task 5.4 remains unfinished by explicit user direction and
must be skipped when reached.
