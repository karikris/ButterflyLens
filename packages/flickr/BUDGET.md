# Flickr global hourly API budget

ButterflyLens uses one project-wide token bucket across every Flickr method and
one credential fingerprint. The provider ceiling is 3,600 calls per clock
hour per key; ButterflyLens stops at 3,500, leaving 100 calls unused as a hard
safety remainder. Normal work may reserve at most 3,000 calls and explicitly
classified reserve work at most 500.

The durable ledger is keyed by `(project_id, UTC window start)` and has one
allowed credential fingerprint. A second key, a second process-local bucket,
or method-specific accounting is rejected; keys must never be rotated or
pooled to evade the provider ceiling. Distributed workers reserve through the
same fenced server-side ledger before attempting a request.

Every HTTP attempt has a stable request ID, method, purpose, lane, reservation
time, and settlement. Searches, info lookups, comments, retries, manual calls,
and judge calls all use the same counter. A retry is a new attempt and consumes
another token. `not_sent` is the only settlement that releases a reservation,
and it is allowed only when transport proves no request left the process.
Timeouts, disconnects after send, ambiguous provider responses, lost receipts,
or any disagreement between workers settle as `uncertain`: the token remains
consumed and the entire UTC window freezes for reconciliation.

The ledger never rolls forward implicitly. A new UTC hour creates a new durable
row; late events remain attached to the hour in which the request was reserved.
Planning stops when the normal lane, reserve lane, total envelope, fencing
lease, credential identity, or accounting certainty gate fails.

This contract performs no Flickr API call and contains no credential.
