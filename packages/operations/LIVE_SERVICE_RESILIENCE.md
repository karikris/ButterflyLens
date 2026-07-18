# Live-service resilience boundary

Version: `butterflylens-incident-plan:v1.0.0`

Task 12.4 defines fallback decisions; it does not perform provider, storage,
database, or model recovery. Every decision is deterministic and fingerprinted.
The submitted snapshot and last committed artifact remain queryable throughout.
Uncommitted work is never promoted, separately journalled committed work is
never repeated, and local inputs are never deleted before a durable
acknowledgement.

| Incident | Immediate stage action | Evidence required to resume |
| --- | --- | --- |
| M5 sleep | Pause every worker stage | Fresh fenced lease after wake and a verified checkpoint |
| Network outage | Pause network-dependent stages | Bounded scheduled health probe after backoff |
| Flickr outage | Pause Flickr stages | Provider recovery and available governed budget |
| B2 outage | Pause artifact commit and publication; retain local sources | Durable B2 write acknowledgement |
| Supabase outage | Pause remote control and telemetry persistence | Database health re-established |
| Model crash | Pause model stages and mark model state unavailable | Operator-verified runtime and checkpoint |
| Corrupted checkpoint | Quarantine without deletion; rebuild affected uncommitted work | Verified inputs and a new checkpoint |
| Rate-limit exhaustion | Pause Flickr stages | New UTC window and a fresh budget ledger |

An incident plan executes no side effect and authorizes no immediate retry.
Flickr requests, ambiguous B2 retry, fabricated Supabase acknowledgement,
credential rotation, budget bypass, unverified checkpoint reuse, model evidence
publication, and fallback identity claims are explicitly blocked in the
relevant plans. YOLOE and BioCLIP remain unfinished; the model-crash test is a
policy simulation and loads no model. No operational outcome authorizes a
scientific claim.
