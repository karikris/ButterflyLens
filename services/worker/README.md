# ButterflyLens persistent worker

This package implements local worker identity, observed machine/resource
profiles, append-only heartbeat records, lease-expiry reporting, and graceful
shutdown state. It does not start BioMiner, contact Flickr, load a model, or
claim that an M5/MPS worker exists merely because the contract supports one.

The deployment supplies a private writable registration path outside the
repository. `load_or_create_registration` atomically creates a mode-`0600`
record and reuses its worker ID and registration time on restart. Identity and
heartbeat payloads are canonically fingerprinted before a heartbeat sink can
persist them.

A worker that receives a shutdown request enters `draining`, stops accepting
leases or stages, checkpoints and releases any attached lease, emits a final
heartbeat, and then closes its emitter. Clearing a lease requires an exact
persisted release acknowledgement. An expired lease forces a `degraded`
heartbeat and explicitly tells the worker to stop fenced work.

YOLOE and BioCLIP are unfinished and skipped for the current goal. Keep
`configured_models` and heartbeat model health empty until separately approved,
fingerprinted model artifacts actually exist; this task performs no model work.
