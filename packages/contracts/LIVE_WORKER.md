# Live worker contract

The ButterflyLens API and the persistent evidence worker communicate through
versioned, idempotent records. The browser never launches BioMiner, holds a
worker credential, submits an arbitrary command, or trusts a worker artifact
without admission checks.

## Authority split

- The API authorizes projects and runs, queues work, issues fenced leases and
  bounded commands, records heartbeats, admits artifacts, and projects live
  status.
- The worker runs pinned BioMiner commands, maintains bounded queues, loads
  approved local models, checkpoints durable work, and reports evidence.
- BioMiner remains the evidence engine. A worker event or healthy heartbeat
  does not lift scientific maturity.
- The public site reads an allowlisted projection. It receives no provider,
  object-storage, database, OpenAI, model-distribution, or worker secret.

## Identity and health

Worker identity is stable and fingerprints the machine/capability declaration.
It reports the actual platform, architecture, chip label, unified memory, MPS
availability and runtime, supported stages, queue limits, and configured model
identities. A configured model is not necessarily loaded or healthy; each
heartbeat reports current model health separately.

The intended M5/MPS deployment is not asserted merely because these fields
exist. Hardware, runtime, model, throughput, memory, and latency claims require
a directly observed heartbeat or run artifact from that exact worker.

## Lease and command safety

- One run stage is protected by a time-bounded lease, monotonically increasing
  revision, and opaque fencing token.
- A stale worker cannot commit after a newer lease revision is active.
- Commands are a closed vocabulary with typed payloads. There is no shell,
  environment, URL, token, or free-form executable field.
- Every command has a stable idempotency key and expiry.
- Cancellation is cooperative and append-only: stop acquiring work, finish or
  safely checkpoint the in-flight unit, report state, then release the lease.
- Graceful shutdown drains admitted work and records a final checkpoint and
  heartbeat when possible.

## Restart and committed evidence

Checkpoints and artifact commits are content-addressed. A restarted worker
resumes from the admitted checkpoint and does not repeat a committed provider
request, download, embedding, or artifact commit. Temporary cache cleanup must
never delete the sole copy before durable commit verification succeeds.

The API derives `offline` or `stale` when the latest heartbeat exceeds the
configured threshold or lease expiry; a worker cannot self-certify future
availability. The website, reviews, submitted snapshot, and last committed live
projection remain available when the M5 worker is offline.
