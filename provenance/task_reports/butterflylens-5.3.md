# ButterflyLens 5.3 — bounded model-free media pipeline

Status: implementation and gates complete; commit and non-force push follow.

Starting SHA: `054f37f97d9c1872831114643ae5b48e33aa4107`.
The next append-only receipt records the ending/push SHA.

The pipeline accepts local caller-supplied media only. Metadata, download
receipt, validation, deduplication, artifact commit, and cleanup queues enforce
both record and byte ceilings. Media bytes are checksum/type validated,
deduplicated, and committed with bounded Zstandard Parquet parts and a manifest
written last. All unique sources, parts, and the manifest require exact durable
acknowledgements before any cache path is removed.

Rolling prefetch is disabled until measured useful on the target M5. YOLOE,
full-frame model inputs, BioCLIP, and scoring are `unfinished_not_run`; no model
or provider call occurred. BioMiner remained scientifically incomplete and no
data/source was copied.

Scientific claims remain blocked: validated bytes and durable storage do not
establish butterfly identity, species, occurrence, or release readiness.

Next: skip Task 5.4 as explicitly unfinished, then implement Task 5.5 restart
and idempotency tests around committed provider/download/artifact identities.
