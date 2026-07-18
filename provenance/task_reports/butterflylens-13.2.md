# ButterflyLens 13.2 — Community moderation workflow

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`f031c5300c04434eb71157513db7a6955eedb235`.

## Outcome

ButterflyLens now has a versioned, authenticated moderation workflow for
reporting a review comment, hiding or restoring abusive content, suspending or
reinstating a reviewer, opening and completing a review audit, submitting and
resolving an appeal, adding private curator notes, and closing a case.

The workflow is implemented as an immutable case plus append-only reports,
events, appeals, and curator notes. Every event records one contiguous
case-local sequence, actor, bounded reason, sorted unique evidence
fingerprints, exact visibility and membership effects, an event fingerprint,
and `scientific_claim_allowed = false`. Closed cases reject later events.

## Privacy and authority

An active project member can report a non-empty comment once. The party-visible
case contains only a controlled reason category and server-generated generic
summary. Reporter identity and detailed report remain in a separate private
table. Appeal rationale is self/curator-only. Curator note text is
curator/administrator-only; parties can see that a note event exists but not
its content.

Exact fixed-search-path security-definer RPCs enforce caller authority. Active
membership is required to report; only the affected reviewer can appeal; and
only an active project curator or administrator can enforce, audit, resolve an
appeal, or add a note. Browser roles can select only through RLS and cannot
insert, update, or delete moderation ledger rows directly. Guests receive no
case, event, appeal, note, comment, or RPC access.

## Evidence and dignity boundary

Hiding nulls comment text only in the moderated authenticated projection. It
does not update or delete the retained review event, comment, decision,
fingerprint, correction chain, or dissent. Earlier evidence remains available
to its author and authorized curators under the existing review RLS.

Suspension pauses only the affected reviewer/expert membership in the current
project. The workflow refuses curator or administrator targets and curator
self-moderation. An affected reviewer can appeal without active membership. An
upheld appeal restores a current hide and/or reinstates the paused membership
inside the same database transaction; a denied appeal changes neither.

Review-audit completion requires an exact audit-evidence fingerprint.
Moderation never writes reviewer reliability, consensus, quality, or release
state; never erases minority evidence; and cannot approve an occurrence or
create scientific authority.

## Verification

- 503 locked Python tests pass, including ten focused moderation workflow and
  pgTAP-contract tests.
- The complete migration passes PostgreSQL statement parsing. All five public
  PL/pgSQL RPC bodies also pass the independent PL/pgSQL parser. The four small
  trigger/helper bodies follow existing repository patterns; the parser's JSON
  renderer cannot serialize trigger pseudorecord output in this environment.
- The 55-assertion pgTAP contract covers tables, private reporter storage,
  RLS, triggers, fixed-search-path RPCs, anonymous denial, authenticated RPC
  grants, direct-mutation denial, foreign-key lineage, the moderated view, and
  immutable review events. Runtime pgTAP remains unavailable because the local
  Docker socket is not accessible and no local PostgreSQL server is running.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass.
  Web typecheck, dependency audit, media checksum, and `/ButterflyLens/`
  production build pass with the existing non-blocking chunk-size warning.
- All 45 frozen Deno tests pass; four Edge entry points type-check and all 22
  function files pass formatting.
- Rights verification covers 52 tracked provider payloads. Staged licensing
  covers 501 tracked files and zero model files.

## Deployment and external boundaries

Task 13.1 Pages run `29639790266` succeeded at the exact starting SHA and the
served bundle links the canonical privacy policy. This task adds a public
community-safeguards link; its deployment is verified after push.

No live Supabase migration, B2 action, Flickr API call, Flickr import,
production workflow dispatch, model call, YOLOE work, BioCLIP work, or
scientific inference occurred. GitHits remained disabled and was not called.
BioMiner remains active at published SHA
`4da369ef5bbb88e32af516716b1afe8544205ca0`; no active or partial output was
read or copied. The user-reported Flickr fetch remains external and active from
its 50,000-image checkpoint.
