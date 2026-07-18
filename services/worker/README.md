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

## Development launchd agent

On the target Mac, create the pinned `.venv` first, then run:

```sh
services/worker/launchd/install.sh
```

The installer renders a mode-`0600` plist into the current user's
`Library/LaunchAgents`, validates it with `plutil`, and uses `launchctl
bootstrap`, `enable`, and `kickstart`. It writes stdout/stderr under
`~/Library/Logs/ButterflyLens` and private registration/heartbeat state under
`~/Library/Application Support/ButterflyLens/worker`.

`KeepAlive.SuccessfulExit=false` restarts crashes but does not relaunch a clean
graceful exit. The worker stays in the foreground and converts `SIGTERM` into a
final draining heartbeat. `ThrottleInterval=30` limits crash-loop churn and
`ExitTimeOut=60` bounds the drain before launchd may force termination.

`worker.env` is parsed as data, never sourced as shell. It accepts only the four
documented numeric tuning fields and rejects secret-like names, unknown keys,
shell metacharacters, symlinks, and group/world permissions. Provider secrets
belong in macOS Keychain. `KeychainSecretProvider` retrieves a specifically
named generic-password item on demand with `/usr/bin/security`, without a
shell, plist entry, environment variable, command-line secret, or log value.
Use Keychain Access to create and control those items; the current heartbeat
service does not request any secret.

Uninstall with:

```sh
services/worker/launchd/uninstall.sh
```

Uninstalling boots out the exact user agent and removes only its rendered plist.
It retains state, non-secret configuration, and logs for recovery/audit.

This is an unsigned development LaunchAgent. A distributable production helper
must move into a signed app bundle and use Apple's Service Management path; this
script does not claim production signing or notarization.

## Bounded media admission

`media_pipeline.py` accepts local caller-supplied media only. Each stage queue
has independent record and byte ceilings; metadata is flushed into bounded
Zstandard Parquet parts. Exact durable acknowledgements are required for every
unique source object, Parquet part, and checkpoint manifest before any input
cache path is removed. Failed or incomplete acknowledgements preserve all
source paths.

Rolling prefetch is disabled until an M5 measurement demonstrates a useful
bounded setting. YOLOE, full-frame model inputs, BioCLIP, and scoring are
recorded only as `unfinished_not_run`; no placeholder model evidence is made.

## Interruption and offline behavior

`restart.py` reconstructs a private append-only committed-work journal before
resuming a lease/checkpoint pair. API calls, downloads, embeddings, and
artifact commits use semantic input fingerprints: acknowledged committed work
is reused, while interrupted work with no commit remains executable. The
journal is fingerprint-checked, mode-`0600`, symlink-rejecting, and locked while
appending; identical artifact recommits are idempotent and conflicting outputs
fail closed.

Public availability is independent of worker liveness. The offline projection
keeps the immutable submitted snapshot queryable and continues serving the
latest committed live snapshot as current-but-stale when heartbeats expire.
This module defines and tests that domain contract; it does not deploy the web
host or a remote journal, contact a provider, download media, or run a model.
