# ButterflyLens 13.1 — Community privacy policy

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`ebba78c8a2b04aedadb57fa6a5c96a8bf19bb483`.

## Outcome

ButterflyLens now has a canonical, versioned community privacy policy and a
machine-readable launch gate. The policy covers pseudonymous accounts, private
user IDs, review history, retained comments, reviewer reliability, anonymous
browsing and analytics, service logs, explicit live-analyst requests, Flickr
owner data, access/correction/deletion/complaints, removal propagation,
sensitive occurrence locations, security, data breaches, and material policy
changes.

The public README and deployed site footer link the policy. The document is
written as a project commitment, not a conclusion about whether an unknown
future operator is an APP entity.

## Fail-closed prelaunch boundary

The policy does not invent a legal operator, private privacy contact,
production Supabase or B2 region, overseas recipient country, or retention
period. The companion manifest records each missing detail as null and blocks
community writes and the live analyst until the operator publishes those
details, approves category retention, records versioned participant acceptance,
and completes moderation/removal workflows.

The static submitted replay remains available without an account. The current
browser code uses no application cookie, local/session storage, product
analytics, advertising pixel, or behavioural tracker. Ordinary hosting and
network request metadata remains explicitly possible.

## Identity, evidence, and deletion

The policy matches the implemented permanent Supabase Auth identity boundary:
a public pseudonym is chosen, a real name is not required, and Auth UUIDs and
login identifiers remain private. Row-level controls restrict personal review
and reliability evidence to the reviewer and authorised curators or
administrators. Reliability is never a public rank, profile field, map value,
or export.

Review corrections supersede rather than rewrite append-only events. Approved
account deletion disables the account, deletes or de-identifies direct
identifiers, tombstones the public pseudonym, removes personal content no
longer needed, and may retain only proportionate de-identified events,
non-content tombstones, and fingerprints needed for integrity. A response must
explain deletion, de-identification, retention, backups, and any limitation.

Flickr owner source fields are purpose-limited to discovery provenance,
attribution, deduplication, rights checks, and removal. Removal propagates
through every public and downstream projection. Precise sensitive occurrence
locations are excluded from public maps, comments, analytics, logs, AI context,
downloads, and screenshots beyond an approved generalisation and rights policy.

## Primary-source review

Current OAIC guidance informed policy contents, anonymity and pseudonymity,
security and de-identification, access, correction, and breach response. The
policy also requires a review before 10 December 2026 for the commencement of
privacy-policy transparency obligations applying to certain substantially
automated decisions. Source URLs and the exact facts and inferences used are
recorded in `provenance/valyu.jsonl`.

## Verification

- 493 locked Python tests pass, including seven new privacy-policy tests and
  four adjacent public-shell tests.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass.
- Web typecheck, dependency audit, review-media checksum, and the
  `/ButterflyLens/` production build pass. The existing bundle-size warning
  remains non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Staged licensing
  covers 496 tracked files and zero model files.
- JSON/JSONL parsing and `git diff --check` pass.

## External and parallel-work boundary

No Flickr API call, Flickr record import, Supabase mutation, B2 operation,
production workflow dispatch, model call, YOLOE work, BioCLIP work, or
scientific inference occurred. GitHits remained disabled and was not called.

BioMiner's published current-state record is now at
`4da369ef5bbb88e32af516716b1afe8544205ca0`, while its worktree contains active
untracked run material. The published record still lists live current-policy
GBIF acquisition and durable-media admission as unfinished and contains no
immutable GBIF handoff. No active or partial BioMiner output was inspected or
copied. The user-reported Flickr fetch remains external and active from its
50,000-image checkpoint; no partial Flickr data was consumed.
