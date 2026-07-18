# ButterflyLens 6.4 — per-image evidence maturity

Status: implementation and gates complete; task commit and non-force push
follow this report.

Starting SHA and remote SHA:
`51b4cb9f54a5f6949c132b21cee6c35b2ce5a8cb`. The ending commit and verified
push SHA are recorded in the next append-only commit receipt because a commit
cannot contain its own SHA.

Butterfly detection, species-candidate availability, community review, quality
estimate availability, expert review, and release readiness now have an exact
per-image JSON Schema plus matching Python and TypeScript declarations. Each
fact independently distinguishes an evidence-backed boolean from unavailable
evidence. Available states require one or more fingerprints; unavailable states
require a reason and null value. Duplicate evidence, unknown states, malformed
identities/times, noncanonical ordering, and fingerprint tampering fail closed.

The deterministic worker-side builder performs no provider or scientific-model
execution. With YOLOE/BioCLIP unfinished, their states are unavailable rather
than false. Release readiness may be true only when all five preceding states
are explicitly available and true. The projection itself cannot authorize a
scientific claim.

No database migration or remote deployment was required: existing review,
quality, and release tables retain their stronger persistence/RLS gates, while
this task adds the missing cross-service per-image projection. No BioMiner data
or source was copied and no Flickr API call occurred.

Next: Task 6.5, a model-independent species-progress scheduler that must treat
unfinished reference/model factors as unavailable rather than zero.
