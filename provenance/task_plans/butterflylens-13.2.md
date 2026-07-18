# Task plan — ButterflyLens 13.2

Task ID: `butterflylens-13.2`

Objective: add an authenticated, project-scoped, append-only moderation
workflow for comment reports, abusive-content hiding, reviewer suspension,
review audit, appeal, and private curator notes without changing scientific
review evidence or reviewer reliability.

Starting, origin, remote, and deployed SHA:
`f031c5300c04434eb71157513db7a6955eedb235`.

Deployment evidence: GitHub Pages run `29639790266` built and deployed the exact
Task 13.1 SHA. The served bundle links the canonical versioned privacy policy.

Privacy boundary: keep reporter identity and detailed reports separate from the
public case, keep appeal rationale self/curator-only, and make curator note text
curator-only. Expose no moderation data to guests. Community writes remain
prelaunch-disabled under Task 13.1 even though the server contract is complete.

Evidence boundary: never update or delete a review event. Hide comment text only
in the moderated projection while retaining the event fingerprint. Moderation
cannot update reliability, consensus, quality, or release state and never grants
scientific authority.

Authority boundary: exact security-definer RPCs with empty search paths enforce
active project membership for reporters, target identity for appeals, and active
curator/administrator roles for enforcement, audits, and notes. Browser roles
receive read access under RLS but no direct ledger mutation privilege.

Suspension boundary: pause only the target reviewer/expert membership in the
affected project, retain every prior event, forbid self-moderation, and exclude
curator/administrator suspension from this workflow. An upheld appeal restores
the active hide and/or suspension effect transactionally.

Audit boundary: cases, reports, events, appeals, and notes are append-only.
Events use contiguous case-local sequence numbers, exact actors, bounded
reasons, sorted unique evidence fingerprints, explicit visibility/membership
effects, and unique event fingerprints. Curator audit completion requires a
separate evidence fingerprint.

External-work boundary: GitHits is disabled. BioMiner and the external Flickr
fetch remain active; inspect only BioMiner's published current-state record and
copy no partial data. Make no Flickr API, Supabase, B2, YOLOE, or BioCLIP call.

Tests: static workflow and policy tests, pgTAP schema/authority contract, public
link tests, all Python/web/Deno gates, staged rights/licensing, JSON/JSONL,
whitespace, secrets, staged scope, and Pages deployment verification.

Rollback: revert the moderation migration, pgTAP contract, policy/link updates,
tests, plan, report, and provenance together. Existing privacy and immutable
review evidence remain independently valid.
