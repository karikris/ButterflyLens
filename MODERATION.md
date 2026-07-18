# ButterflyLens Community Safeguards

Policy version: `butterflylens-community-moderation:v1.0.0`

Status: normative prelaunch policy. Community writes remain blocked until the
privacy, retention, consent, operator-contact, and overseas-processing launch
gates are closed.

ButterflyLens exists to strengthen evidence through careful collaboration. Community participation must be safe, scientifically useful, accessible, and respectful of people, knowledge authorities, media owners, and sensitive species.

## Reviewer dignity

- Never publicly shame, grade, or label a reviewer as bad, inaccurate, slow, or unreliable.
- Never publish reviewer-reliability estimates. Reliability evidence is private, domain-specific, uncertainty-aware, and available only to authorized quality and adjudication workflows.
- Never use a speed leaderboard or reward decisions per minute. Contributor recognition may celebrate coverage, care, conflict resolution, controls completed, regions helped, or expertise shared without ranking speed.
- Preserve good-faith minority dissent. Disagreement is evidence to resolve, not misconduct.
- Provide an appeal route for moderation and reviewer-status decisions.

## Independent evidence

- Assign the same item to multiple independent reviewers under the configured campaign contract.
- When blindness is required, hide model output, Flickr query terms, source comments, majority state, and other reviewer decisions until the reviewer submits a decision.
- Never infer reviewer reliability from agreement with BioCLIP, YOLOE, or another model.
- Never infer reliability from majority agreement alone.
- Never count model output as a community vote or use model agreement to manufacture consensus.
- Treat **Skip** and **Can’t view** as non-decisive workflow events.
- Preserve conflicts and route configured cases to qualified or expert adjudication.

## Scientific release

- Never release an unreviewed discovery candidate as a scientific occurrence.
- Guests may browse and contribute only within the authorization contract; they cannot release scientific records.
- A human-supported candidate remains a candidate until every configured identity, coordinate, date, duplicate-independence, rights, provenance, quality, conflict, and expert gate passes.
- Public copy must use ButterflyLens evidence-maturity language and must not turn potential contribution into an occurrence or range claim.

## First Nations knowledge and names

ButterflyLens follows the people- and purpose-oriented [CARE Principles for Indigenous Data Governance](https://www.gida-global.org/careprinciples).

The enforceable name workflow is defined in [First Nations Language-Name Governance](FIRST_NATIONS_NAMES.md).

- Never invent, machine-translate, generalize, or place a name in a generic “Aboriginal name” field.
- Every assertion must identify the language, stable language identifier where available, Country/community, source, cultural authority or publication, permitted use, attribution, and review state.
- A name is not eligible for a Flickr query, public label, or export until its use has been reviewed and authorized for that purpose.
- Removal, correction, attribution, and future-use restrictions from the relevant authority take priority over cache or convenience.

## Sensitive locations

- Retain and enforce provider sensitivity flags, coordinate uncertainty, generalization state, and applicable jurisdictional rules.
- Do not display or export coordinates at finer resolution than ALA, Flickr, a data provider, a rights holder, or a configured sensitive-species policy permits.
- Derive public map cells from the permitted generalized location, never from a private precise coordinate.
- Review comments must not reveal hidden sensitive locations.

The [ALA Sensitive Data Service](https://sds.ala.org.au/) is a baseline source for Australian sensitivity handling, not permission to reverse generalization.

## Reports, removal, and enforcement

Every public comment and eligible media item must provide a report or rights-request route. Authorized moderators may:

1. hide abusive or rights-disputed public content without deleting the append-only audit event;
2. restrict a reviewer while preserving prior evidence and appeal state;
3. quarantine media and its derivatives from public display and future processing;
4. record a takedown, correction, licence change, or attribution change against the immutable source identity;
5. invalidate affected caches, thumbnails, embeddings, evidence packets, and exports through a traceable removal job;
6. notify downstream release workflows that earlier evidence is no longer eligible.

Removal actions require an actor, timestamp, reason category, affected fingerprints, visibility effect, downstream effect, and resolution or appeal state. Public explanations must minimize personal information and never expose private reviewer-quality data.

## Moderation workflow

The versioned database workflow separates moderation from the immutable review
event. It supports the following audited actions:

1. An active project member may report a non-empty review comment once per
   comment. The public case retains only a bounded reason category and a
   server-generated generic summary;
   reporter identity and detailed report remain in a private table.
2. An active curator or administrator may hide or restore comment text through
   the moderated projection. Hiding never updates or deletes the underlying
   review decision, comment, fingerprint, dissent, or supersession lineage.
3. A curator may suspend a reviewer or expert by pausing only that project
   membership. Other project memberships and all earlier evidence remain
   intact. This workflow cannot suspend a curator or administrator and cannot
   be used by a curator against their own membership.
4. A curator may open and complete a review audit. Completion requires an exact
   audit-evidence fingerprint. An audit is not a reliability estimate,
   scientific decision, or automatic misconduct finding.
5. The affected reviewer may appeal an active hide or suspension even while
   the membership is paused. An upheld appeal restores hidden content and/or
   reinstates the paused membership in the same transaction where applicable;
   a denied appeal changes neither. One exact appeal fingerprint is retained.
6. Curators may add append-only notes. Note text is visible only to authorized
   project curators and administrators; reporters and affected reviewers can
   see that a note event occurred but not its content.

Cases, events, appeals, reporter records, and curator notes are append-only.
Every event has a contiguous per-case sequence, actor, bounded reason, sorted
unique evidence fingerprints, explicit visibility and membership effects, and
its own fingerprint. Closed cases reject further actions. Browser roles cannot
insert, update, or delete ledger rows directly; exact authenticated RPCs enforce
reporter, affected-reviewer, and curator authority.

Moderation is not scientific truth. It must not alter reviewer reliability,
manufacture consensus, erase minority dissent, approve an occurrence, or grant
scientific authority. Evidence exclusion or release correction requires the
separate governed audit, consensus, quality, and release workflows.

## Accessibility and conduct

- Review and moderation controls must be keyboard accessible, clearly labelled, usable without colour alone, and compatible with reduced motion and assistive technology.
- Harassment, hate, threats, doxxing, deliberate coordinate disclosure, rights abuse, impersonation, and manipulation of independent review are prohibited.
- Ambiguity and honest mistakes should be resolved with education and evidence before punitive action where safety permits.
