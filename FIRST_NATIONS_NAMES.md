# First Nations Language-Name Governance

Status: active policy; approved assertions in the current pack: **0**

ButterflyLens may preserve a First Nations language name only as a
community-specific, purpose-specific assertion. It must never create a generic
“Aboriginal name” field, infer a name from geography, or treat public
availability as permission for reuse.

This policy applies to collection, storage, private review, public display,
search-query use, attribution, redistribution, export, correction, and
withdrawal. It does not certify any person or institution as the cultural
authority for a language or name.

## Governing principles

ButterflyLens applies:

- the [AIATSIS Code of Ethics for Aboriginal and Torres Strait Islander
  Research](https://aiatsis.gov.au/research/ethical-research/code-ethics),
  including Indigenous self-determination, Indigenous leadership, impact and
  value, and sustainability and accountability;
- the [CARE Principles for Indigenous Data
  Governance](https://www.gida-global.org/careprinciples): Collective Benefit,
  Authority to Control, Responsibility, and Ethics;
- [AustLang](https://aiatsis.gov.au/research/languages/austlang) as the preferred
  stable language identifier when the relevant authority agrees that its code
  represents the asserted language variety; and
- community-supplied [Local Contexts Labels and
  Notices](https://localcontexts.org/labels/about-the-labels/) when applicable.
  ButterflyLens does not select, customize, or apply a community Label on a
  community’s behalf.

These references guide the workflow; they do not replace direct engagement
with the relevant people or grant permission to use knowledge.

## Required assertion record

Every proposed assertion must bind all of the following:

- stable assertion ID and ButterflyLens taxon key;
- exact name as supplied, including orthography and diacritics;
- language display name and an AustLang code or another stable language
  identifier, with source and version;
- Country/community, using the authority’s preferred self-description;
- source citation, source URL or controlled-access reference, retrieval date,
  and source fingerprint where storage is permitted;
- named cultural authority, authorized publication, or documented delegated
  decision process;
- evidence of who may grant the relevant permission and the scope of that
  authority;
- permitted use, expressed as separate permissions for private storage, public
  display, search-query use, redistribution, research export, and future
  derived use;
- required attribution and any community protocol, Local Contexts identifier,
  audience restriction, sensitivity, embargo, expiry, or review date;
- query eligibility, homonym risk, taxon-link rationale, and scientific review
  state;
- cultural review state, decision date, permission version, decision evidence,
  and a correction/withdrawal contact held privately; and
- source, policy, pack, and decision fingerprints needed to audit later use.

An unknown, missing, expired, disputed, or inaccessible required value blocks
public display, query use, redistribution, and export. It is never interpreted
as permission.

## Independent permissions

The following are distinct decisions:

| Permission | Default | Meaning |
| --- | --- | --- |
| Private metadata storage | blocked | Store the proposed assertion for controlled review. |
| Public display | blocked | Show the name and approved attribution to public users. |
| Search-query use | blocked | Submit the exact approved term to an external discovery provider. |
| Redistribution | blocked | Include the assertion in a downloadable pack or mirror. |
| Research export | blocked | Include the assertion in evidence or contribution packages. |
| Derived/model use | blocked | Use the assertion in embeddings, training, evaluation, or generated content. |

Approval for one purpose does not approve another. A publication that can be
read publicly is a source candidate, not blanket permission for database,
query, export, or model use. Open-data defaults do not override Indigenous
authority.

## Review states

The review ledger is append-only and uses these states:

1. `proposed` — recorded outside the public pack; all uses blocked.
2. `source_review` — source, exact wording, taxon link, and rights are checked.
3. `authority_contact_pending` — the relevant authority and decision process
   have not been established.
4. `authority_review` — purpose-specific permission is being considered.
5. `authorized_limited` — only explicitly listed uses are permitted.
6. `authorized_public` — public display is permitted; query/export still
   require their own affirmative values.
7. `suspended` — all affected uses stop while evidence or authority is
   disputed, expired, or under correction.
8. `withdrawn` or `rejected` — the assertion is absent from public/query/export
   projections; a minimal non-content audit tombstone may remain where allowed.

No transition is inferred from elapsed time, a model, a contributor vote, an
ALA/GBIF/iNaturalist field, or publication frequency. A curator may administer
the workflow but may not substitute for the cultural authority.

## Admission and query gate

A First Nations language-name assertion enters the public pack only when:

1. the taxon link and source are reproducible;
2. language and Country/community are specific and not generalized;
3. the authority or authorized publication and decision scope are documented;
4. public display and redistribution are affirmatively permitted;
5. exact attribution and protocols can be shown;
6. the permission has not expired, been superseded, or been withdrawn; and
7. rights, privacy, cultural-sensitivity, homonym, and pack-integrity tests pass.

Query use additionally requires an affirmative `query_use` permission for the
named external provider and purpose, a current `query_eligible` decision, and
no unresolved cross-taxon or cross-community conflict. A query term remains a
retrieval explanation and never becomes a species label for returned media.

## Prohibited actions

ButterflyLens must not:

- invent, autocomplete, transliterate without authority, or machine-translate
  a First Nations language name;
- collapse distinct languages, dialects, Countries, communities, clans, or
  islands into a pan-Aboriginal or pan-Indigenous label;
- infer Country/community or authority from a postcode, state, ALA coordinate,
  the AIATSIS map, or another approximate boundary;
- scrape a dictionary, museum label, publication, social-media post, or oral
  recording and publish the result without the required permission evidence;
- let model output, majority review, popularity, or provider repetition stand
  in for cultural authority;
- expose private authority contact details, restricted knowledge, sensitive
  location information, or decision evidence; or
- keep using a name after its approved purpose expires or the relevant
  authority requests suspension, correction, or withdrawal.

The AIATSIS Map of Indigenous Australia is not used to assign an assertion. It
shows general, sometimes contested groupings, is not an exact boundary source,
and does not identify who can authorize a particular language-name use.

## Conflict, correction, and withdrawal

Conflicting spellings or authorities remain separate assertions with their own
provenance and states. ButterflyLens does not select a winner by vote. The
affected public/query projection is suspended when authority, scope, or
permission is unresolved.

An authorized correction or withdrawal creates a new decision event and
invalidates affected public pages, query definitions, caches, exports,
snapshots, and downstream artifacts. Public content is removed promptly. The
audit ledger retains only the minimum non-content tombstone allowed by the
authority, policy, and law.

## Current pack position

The current First Nations language-name assertion dataset is intentionally
empty. No authorized source and purpose-specific approval has been supplied to
ButterflyLens. Zero approved assertions is a governance result, not missing
work to be filled from model memory or an unsupervised web search.
