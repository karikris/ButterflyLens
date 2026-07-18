# ButterflyLens security and compliance release review

Review date: 18 July 2026

Decision: **the credential-free static Submitted replay passes its release
security verification; community, live-service, and downstream data release
remain blocked**.

This decision is intentionally narrower than a production approval. The
security verifier exits successfully when the controls are internally
consistent, while its machine-readable result keeps `release_ready` false and
lists every unresolved release blocker.

## Control matrix

| Goal control | Evidence | Result |
| --- | --- | --- |
| RLS tests | Static migration inventory, focused Python policy tests, and the tracked pgTAP policy definitions cover 50 public tables, 11 security-invoker views, and 60 fixed-search-path security-definer functions. | Pass for versioned SQL; live-database execution unavailable in this session. |
| Secret scan | `scripts/verify_release_security.py` scans every tracked text file for high-signal private-key, JWT, OpenAI, Supabase, GitHub, and AWS credential patterns. The staged release gate repeats the scan. | Pass. |
| Dependency audit | Web lock installation/audit reports zero known vulnerabilities. npm 12 verifies 119 registry signatures and 45 attestations. Deno resolves every dependency through the exact lock. | Pass with the npm 9 expired-registry-key note below. |
| Licence audit | Python/provider licence verification, staged-file licensing, the generated web dependency report, and the Deno lock inventory are checked. | Pass for the static replay; YOLOE remains unfinished and blocked. |
| Rights audit | The rights verifier covers 52 provider records and preserves restrictive or unknown rights as blockers. | Pass as a verifier; downstream data release blocked on ALA dataset records `dr1097`, `dr30019`, and `dr635`. |
| Privacy review | The versioned policy and Supabase local Auth configuration fail closed: sign-up, anonymous Auth, community writes, and the live analyst are disabled. | Static replay pass; community/live release blocked. |
| Rate-limit simulation | Flickr budget tests exercise the 3,500-call hard hourly envelope, 3,000 normal calls plus 500 reserve, 100-call provider safety remainder, multi-key rejection, retry bounds, and uncertain-send freeze behavior through injected transports. | Pass; no Flickr API call made. |
| Abuse tests | Moderation, takedown, role, review, RPC, origin, payload, and rate-boundary tests run against deterministic fixtures. | Pass. |
| External-network audit | The exact allowlist contains four opt-in Python acquisition scripts, two browser transports, and four Supabase Edge entry points. The Flickr contract has no built-in transport. Browser tests fail on external requests. | Pass; 10 boundary files. |
| `git diff --check` | Whitespace and staged-scope gates run immediately before commit. | Required to pass before release commit. |

## RLS verification scope

Every migration-created `public` table has an explicit RLS enable statement.
Every public view is declared with `security_invoker = true`. Security-definer
functions use an empty `search_path`; public functions also have an explicit
default privilege revoke. The verifier rejects authorization through
deprecated `auth.role()` calls or user-editable metadata.

This session could not execute the pgTAP definitions against a live local or
remote project: the Supabase MCP server was reachable but still required a
client reload after OAuth, Supabase CLI was absent, and the installed Docker
daemon denied access. The static SQL inventory and deterministic policy tests
therefore prove the versioned contract, not the deployed database state. A
production release still requires the same tests against the target project.

The controls follow current Supabase guidance that exposed tables need RLS,
raw-SQL tables need explicit RLS and grants, policies should target roles and
prefer `(select auth.uid())`, views should use `security_invoker`, service keys
must stay out of browsers, and security-definer functions require particular
care:

- [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [Securing your API](https://supabase.com/docs/guides/api/securing-your-api)
- [Product security](https://supabase.com/docs/guides/security/product-security)

The local Auth configuration is additionally fail-closed for this prelaunch
state: global and email sign-up are disabled, anonymous sign-in is disabled,
email confirmations and secure password changes are required, and passwords
must contain lower- and uppercase letters, digits, and symbols with at least
12 characters. These settings do not claim to mutate or verify the remote
Supabase project.

## Dependency-integrity note

The host npm 9.2.0 `npm audit signatures` command reported
`EEXPIREDSIGNATUREKEY` for `bidi-js@1.0.3` because the registry signing key
expired on 29 January 2025. Repeating the documented check with exact npm
12.0.1 verified all 119 installed package signatures and 45 attestations. npm
12 warned that its supported Node floor is 22.22.2 while this host provides
22.22.1, but it completed the signature and attestation verification. The
package lock remains authoritative; the standard vulnerability audit is a
separate required pass. See Supabase's current
[npm security guidance](https://supabase.com/docs/guides/security/npm-security).

## Privacy decision

The repository identifies the categories and purposes of information that a
future community service may handle, but it does not invent a legal operator,
private contact channel, production regions, overseas recipient locations, or
category-specific retention schedule. Versioned participant acceptance and
production moderation/removal workflows also remain unresolved. Those six
items keep account creation, community writes, and the live analyst disabled.

This fail-closed decision follows current OAIC guidance:

- [APP 1](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-1-app-1-open-and-transparent-management-of-personal-information)
  requires a clearly expressed and current policy describing purposes,
  access/correction procedures, and a usable contact path.
- [APP 11](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information)
  requires reasonable technical and organisational protection and active
  destruction or de-identification when personal information is no longer
  needed.
- [OAIC's privacy-policy guide](https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/more-guidance/guide-to-developing-an-app-privacy-policy)
  recommends category-specific archiving, destruction, or de-identification
  periods and stable contact details.

OAIC also states that from 10 December 2026 APP entities using personal
information in automated decisions that may significantly affect a person's
rights or interests will have additional privacy-policy disclosures. The
policy already records that review date, but the live analyst is not enabled
and ButterflyLens makes no claim that it presently falls within that future
rule. See the official
[automated-decision consultation](https://www.oaic.gov.au/engage-with-us/consultations/consultation-on-guidance-for-transparency-in-automated-decision-making).

## Release blockers

- Community privacy: legal operator identity, a private privacy contact,
  overseas recipient countries or regions, a category retention schedule,
  versioned participant acceptance, and production moderation/removal
  workflows.
- ALA dataset rights: `dr1097`, `dr30019`, and `dr635` require resolution
  before downstream public-product release. The rebuilt ButterflyLens ALA
  baseline remains authoritative; passing the verifier does not clear those
  records.
- YOLOE: `blocked_not_executed`; unfinished by goal instruction.
- BioCLIP: `skipped_unfinished_by_goal_instruction`; unfinished by goal
  instruction.
- Deployment: the static verification does not attest the live Supabase RLS
  state, remote Auth settings, B2 policy, provider contracts, or production
  regions.

BioMiner remains active and has not supplied a complete immutable ButterflyLens
handoff. No partial GBIF/Flickr artifact is copied. The user-reported Flickr
fetch remains external and active from its 50,000-unique-image checkpoint; no
Flickr API call or inspection occurs in this task. GitHits remains disabled and
is not called.
