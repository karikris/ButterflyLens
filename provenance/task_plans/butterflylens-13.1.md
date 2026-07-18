# Task plan — ButterflyLens 13.1

Task ID: `butterflylens-13.1`

Objective: publish a versioned community privacy policy that addresses
pseudonymous accounts, private user IDs, review history, retained comments,
private reviewer reliability, analytics, Flickr owner data, deletion requests,
and sensitive occurrence locations without claiming a legal or operational
state the repository cannot prove.

Starting, origin, remote, and deployed SHA:
`ebba78c8a2b04aedadb57fa6a5c96a8bf19bb483`.

Policy boundary: the current site is a static submitted replay. Treat community
write access and the live analyst as prelaunch-disabled. Do not infer the legal
operator, APP-entity status, private privacy contact, production regions,
overseas recipient countries, or retention periods. Record every unresolved
production detail as a launch blocker in both the human and machine-readable
policy.

Data boundary: reflect the implemented permanent pseudonymous-account model,
private Auth UUID, self/curator-only review and reliability access, append-only
review supersession, Flickr owner provenance and removal graph, no current web
analytics/browser storage, and explicit-only OpenAI analyst boundary. Do not
make public community comments, reliability, login identity, or sensitive
coordinates.

Deletion boundary: distinguish account disabling, direct-identifier deletion
or de-identification, public pseudonym tombstoning, comment/content removal,
provider backup expiry, and the minimum de-identified integrity evidence that
may remain. Never promise silent mutation of an append-only evidence ledger or
indefinite retention.

Legal-research boundary: use current primary OAIC guidance for policy contents,
pseudonymity, security/de-identification, access, correction, and incident
response. State commitments and launch gates rather than offering a legal
conclusion. Require an automated-decision policy review before 10 December
2026.

Parallel-work boundary: the external Flickr fetch remains active and no partial
records are consumed. BioMiner remains authoritative for its active GBIF work;
inspect only the published handoff state if overlap requires it. GitHits is
disabled. Make no Flickr API, Supabase, B2, YOLOE, or BioCLIP call.

Tests: policy/manifest version parity, fail-closed launch blockers, required
privacy subjects, current browser/analyst boundaries, schema-backed identity
and evidence controls, deletion semantics, public links, full Python/web/Deno,
rights, licensing, JSON/JSONL, build, secret, staged-scope, and Pages gates.

Rollback: revert the policy, manifest, public links, tests, plan, report, and
provenance receipt together. Community writes and live analyst remain disabled.
