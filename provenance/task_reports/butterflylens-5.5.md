# ButterflyLens 5.5 — interruption, resume, and offline behavior

Status: implementation and gates complete; task commit and non-force push
follow this report.

Starting SHA and remote SHA:
`dcf1490589b92fc21e9a94e239f0fbb0f5fe1125`. The ending commit and verified
push SHA are recorded in the next append-only commit receipt because a commit
cannot contain its own SHA.

The worker now reconstructs a private, append-only committed-work journal on
restart. Semantic identities cover API calls, downloads, embeddings, and
artifact commits. A resume plan is fingerprinted against both the admitted
lease and checkpoint; committed identities are reused, while interrupted work
without a durable commit remains explicitly executable. Exact persistence
acknowledgements are mandatory. Journal tampering, broad permissions, invalid
records, conflicting outputs, duplicate inventory, and duplicate append races
fail closed.

The public offline projection separates site availability from M5 liveness. It
keeps the submitted snapshot immutable and queryable, and serves the latest
committed live snapshot as current-but-stale after heartbeat expiry. This is a
tested domain contract, not a web deployment or remote persistence test.

No provider transport was invoked, no media was downloaded, and no Flickr API
call occurred. The embedding path is identity/idempotency metadata only:
YOLOE, full-frame inputs, BioCLIP, embeddings, and scoring remain unfinished
and were not loaded, computed, benchmarked, or fabricated. BioMiner still
reports incomplete live GBIF/media/scientific quality work, so no data or
source was copied.

Scientific claims allowed: none. Operational restart safety and query
availability do not establish evidence maturity, taxonomy, classification, or
release readiness.

Next: mark model-dependent Phase 6 work unfinished where required by the user,
then move to the next model-independent subtask.
