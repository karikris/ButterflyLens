# ButterflyLens community privacy policy

Policy version: `butterflylens-community-privacy:v1.0.0`

Last reviewed: 18 July 2026

Status: **prelaunch policy; community account creation and write access are
blocked**.

## Scope and operator status

This policy explains how the ButterflyLens project is designed to handle
personal information when people browse the public site, create a pseudonymous
account, review candidate evidence, or make a privacy request. It is a project
commitment whether or not the eventual operator is required to comply with the
Australian Privacy Act 1988. It does not assert that an unidentified future
operator is, or is not, an APP entity.

The current public site is a static, read-only submitted replay. It does not
offer account creation, review submission, or a live AI analyst. The repository
does not yet identify the legal operator or a private privacy-contact channel.
ButterflyLens must not enable community writes until both are displayed here,
along with the approved retention schedule and the countries or regions in
which service providers process project data. Do not put identity documents,
private contact details, or sensitive location information in a public GitHub
issue.

The policy structure follows the Office of the Australian Information
Commissioner's guidance on an accessible privacy policy, anonymity and
pseudonymity, security, access, and correction:
[APP 1](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-1-app-1-open-and-transparent-management-of-personal-information),
[APP 2](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-2-app-2-anonymity-and-pseudonymity),
[APP 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information),
[APP 12](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-12-app-12-access-to-personal-information),
and [APP 13](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-13-app-13-correction-of-personal-information).

## What ButterflyLens handles and why

ButterflyLens minimises personal information and separates private identity
from public evidence. Depending on the feature used, the project may handle:

- **Pseudonymous accounts and user IDs.** Browsing does not require an account.
  Contributing requires a permanent Supabase Auth account so reviews can be
  attributed, corrected, audited, protected from abuse, and assigned without
  duplicate work. A contributor chooses a public pseudonym; a real name is not
  required. The stable Auth UUID and login identifiers are private and are
  never part of a public profile or scientific export.
- **Review history and retained comments.** Review decisions, confidence,
  comments, timestamps, assignment context, evidence fingerprints, and
  supersession links form an append-only integrity record. A correction adds a
  new event rather than silently rewriting history. Comments are not licensed
  for public reuse or publicly displayed by default. Contributors must not put
  contact details, information about another person, or sensitive occurrence
  locations in comments.
- **Reviewer reliability and contribution summaries.** Domain-specific
  reliability evidence is visible only to the reviewer and authorised
  curators or administrators. It is not a public score, leaderboard, badge,
  map field, or export. Self-visible contribution totals do not measure pace,
  personal worth, or scientific authority.
- **Flickr source and owner data.** Candidate-source records may retain the
  Flickr photo ID, owner NSID, displayed owner name, source URL, title,
  description, licence statement, and provider timestamps. These public-source
  fields are used only for discovery provenance, attribution, deduplication,
  rights checks, and owner, rights-holder, provider, legal, or privacy removal
  requests. They do not become a ButterflyLens account and must not be used to
  build owner profiles or infer private characteristics.
- **Service and security metadata.** Hosting, authentication, database,
  storage, and server boundaries may process IP address, user agent, request
  time, authentication and security events, and bounded operational logs. The
  purposes are delivery, access control, abuse prevention, incident response,
  debugging, and service reliability—not advertising or behavioural profiling.
- **Explicit Ask ButterflyLens requests.** If the live analyst is later
  enabled, invoking it sends the question, relevant conversation history, and
  deterministic evidence-tool results to OpenAI. The application requests
  `store: false` and sends a one-way, truncated hash derived from the Auth UUID
  as a safety identifier; it does not send the raw UUID or store the generated
  answer in ButterflyLens. Provider processing remains governed by the
  published provider terms and this policy. No live analyst is deployed now.
- **Privacy, correction, complaint, and removal requests.** The project keeps
  the minimum requester contact and verification evidence, request scope,
  case events, decision, appeal state, affected fingerprints, and completion
  evidence needed to resolve and prove the request. Verification must use the
  minimum information reasonably needed for the risk.

ButterflyLens does not sell personal information. It does not use personal
information for advertising, unrelated people-search, face recognition, or to
infer sensitive characteristics.

## Anonymous browsing and analytics

The ButterflyLens web application currently sets no application cookie, uses
no browser local or session storage, and includes no product analytics,
advertising pixel, or behavioural tracker. Hosting and network providers may
still receive ordinary request metadata under their own service terms.
Supabase's local operational analytics configuration is infrastructure
telemetry, not a browser product-analytics integration.

Any future product analytics must be off by default until this policy names the
provider, data, purpose, retention, location, consent or opt-out mechanism, and
public configuration change. Analytics must not receive review comments,
precise occurrence coordinates, raw Auth UUIDs, reviewer reliability, or
Flickr owner profiles.

## Who can see the data

Row-level access controls are designed so a reviewer can see their own profile,
assignments, reviews, private reliability evidence, and contribution summary.
Authorised project curators or administrators can access the records needed to
operate review, investigate integrity or safety issues, answer requests, and
maintain evidence lineage. Service-role access is confined to governed server
operations. Public projections must exclude login identity, Auth UUIDs,
reliability evidence, private storage fields, and review material not expressly
approved for display.

Access does not itself grant a right to reuse the content. Curators must use
personal information only for the purposes in this policy and must not disclose
it through public issues, logs, demonstrations, or research exports.

## Service providers and overseas processing

The intended service boundaries are GitHub Pages for static hosting, Supabase
for authentication, database and Edge Functions, Backblaze B2 for governed
media storage, and OpenAI only for an explicitly invoked live analyst. These
providers may engage subprocessors and may process data outside Australia.

The production project region, B2 bucket region, exact overseas recipient
countries or regions, operator contracts, and private request channel are not
recorded in this repository. This is a launch blocker: community writes and the
live analyst must stay disabled until the deployed policy publishes those
details and the operator completes its cross-border assessment. A later
provider or region change requires a policy and configuration review before
personal information moves through the new boundary.

## Retention, correction, deletion, and de-identification

ButterflyLens keeps personal information only for an approved purpose and an
approved retention period. The final category-by-category retention schedule
has not yet been approved, so community writes remain blocked. Security and
backup procedures must cover every controlled copy and must delete or
de-identify information that is no longer needed, subject to a documented
legal or integrity need.

Review evidence is append-only while it is needed for scientific integrity:
corrections supersede earlier events, and the effective view uses the current
event. Append-only does not mean indefinite public identification. When an
account deletion request is approved, ButterflyLens must disable the account,
remove or de-identify direct login identifiers from controlled application
data, replace the public pseudonym with a neutral tombstone, and remove comments
or personal content that is no longer needed. The project may retain the
minimum de-identified event, decision, non-content tombstone, and cryptographic
fingerprints needed to prevent duplicate evidence and explain a released
result. Those remnants must not be used to re-identify the person.

Provider backups or security logs may expire on a controlled deletion cycle
rather than immediately. The response must state what was deleted,
de-identified, retained and why, the applicable backup horizon, and any
downstream action. ButterflyLens does not promise erasure where retention is
required by law, needed to establish or defend a legal claim, or necessary to
preserve a proportionate de-identified integrity record; it must explain any
refusal or limitation and the review path.

## Access, correction, complaints, and removal

After the private privacy channel is published, a person may ask to:

- access the personal information ButterflyLens controls about them;
- correct inaccurate, out-of-date, incomplete, irrelevant, or misleading
  information, or have a correction statement associated if correction is
  refused;
- delete or de-identify an account and eligible personal content;
- challenge a private reliability record or moderation decision; or
- remove Flickr-owner material on an owner, rights, provider, legal, or privacy
  basis.

The operator must acknowledge a request, verify authority proportionately,
search controlled systems and downstream projections, and answer in writing
within the period required by applicable law. Access and correction are not
charged. Any refusal must give reasons where lawful and explain internal review
and complaint options. A person may then complain to the OAIC where that body
has jurisdiction. Until a private channel and operator are published, no
community write path may collect information that would require this workflow.

Flickr removals quarantine public display first and propagate through source
cache, signed URLs, derivatives, review queues, maps, quality outputs, release
packets, exports and mirrors. Audit history retains only the minimum lawful
non-content tombstone; copyright or private content is not kept public merely
to preserve history.

## Sensitive occurrence locations

Exact or highly precise locations for threatened species, culturally sensitive
places, private property, or vulnerable populations can create harm. Public
maps, comments, analytics, logs, AI context, downloads, and screenshots must
not expose sensitive coordinates beyond the approved rights and
generalisation policy. Exact coordinates, when lawfully held, require
need-to-know access, purpose limitation, audit, and a separately approved
retention period. ButterflyLens must not combine locations with owner or
reviewer data to re-identify, contact, profile, or surveil a person.

## Security and data incidents

ButterflyLens uses pseudonym separation, row-level access controls, server-only
provider credentials, bounded logs, append-only evidence, checksums, and
removal propagation as defence-in-depth controls. Access is revoked when no
longer needed, secrets must never enter the public client or repository, and
production changes require auditable review.

Suspected loss, unauthorised access, disclosure, alteration, or misuse must be
contained, investigated, documented, and remediated. The operator must assess
whether the event is an eligible data breach and notify affected people and the
OAIC when required. The response procedure follows the OAIC's
[data breach response guidance](https://www.oaic.gov.au/about-the-OAIC/our-corporate-information/plans-policies-and-procedures/data-breach-response-plan).

## Policy changes and automated decisions

The accepted policy version must be recorded with each participant's consent.
A material change to identity handling, purposes, visibility, analytics,
providers, countries, retention, research use, or public licensing requires a
new policy version and renewed notice or consent before the new use begins.
Historical evidence retains the policy version under which it was collected.

Automated screening and reliability estimates do not by themselves decide a
person's account rights, moderation state, or access to essential services.
Because Australian privacy-policy obligations for certain substantially
automated decisions commence on 10 December 2026, the operator must review and,
if applicable, update this policy before that date and before enabling any
automated decision that could significantly affect a person's rights or
interests.
