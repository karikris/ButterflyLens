# ButterflyLens 10.6 — Contributor experience

Status: **implemented locally; evidence, privacy, and no-speed boundaries
verified**.

Starting SHA: `2f83ce9b7df6cc1f8bc90946c1e6bb6fe55cb87d`.

## Outcome

The Contributors navigation now opens a complete responsive experience rather
than a scheduled preview. It celebrates reviewed images, independently
resolved conflicts, accepted species helped, generalised public regions helped,
aggregate control coverage, and eligible work performed under a verified
expert role.

The submitted replay claims no totals: every value is null and rendered as an
unavailable dash because no authenticated, fingerprinted contributor snapshot
is bundled. A strict TypeScript parser rejects invented zeroes, unexpected
fields, rankings, speed metrics, scientific authority, incomplete evidence, or
public visibility.

## Evidence and database contract

The deterministic Python compiler counts unique effective stored-review media,
append-only resolved conflicts, distinct accepted species and region IDs,
distinct governed control fingerprints, and exact expert-eligible events. It
rejects malformed or duplicated lineage, excludes superseded/non-effective
events, sorts source fingerprints, and calculates stable RFC 8785 SHA-256
source and projection fingerprints.

The migration stores append-only contribution snapshots with explicit null
unavailable states. RLS exposes rows only to the active contributor with an
active project membership. Writes remain service-only; anonymous access is
revoked; the latest-self view uses `security_invoker`; foreign keys and latest
lookups are indexed; and expert totals require a currently verified expert,
curator, or administrator profile. No security-definer function is added.

Control identities, expected answers, exact region IDs, Auth IDs, reliability
weights, durations, rates, rankings, and person-to-person comparisons are not
projected. Recognition cannot approve an identity, consensus, expert gate,
quality estimate, release candidate, or publication.

The Supabase and Postgres skills led to self-only RLS, explicit grants,
service-only writes, security-invoker view semantics, indexed foreign keys,
append-only storage, and the absence of browser-controlled aggregation.

## Parallel work

BioMiner was inspected at `746e5259922c057e0f7864643a861844c8fdf03f`
and remains dirty/active with no completed Flickr or GBIF handoff. No partial
output, log, credential, configuration, or runtime artifact was read or copied.
Task 10.4 and the GBIF Parquet copy remain deferred. BioCLIP and YOLOE remain
unfinished and were not run. No Flickr API or GitHits call occurred.

## Verification

- Full Python suite: 400 tests passed.
- Focused contributor Python suite: 6 tests passed.
- Web suite: 49 Vitest parser/component tests passed across 12 files.
- TypeScript check and production build passed.
- Production bundle: 0.60 kB HTML, 35.25 kB CSS, and 1,424.16 kB JavaScript
  before gzip; JavaScript is 214.60 kB after gzip. The existing raw chunk-size
  advisory remains driven by the full local species catalogue.
- Rights verification passed for 52 tracked provider payloads.
- Licence verification passed for 389 tracked files, two dependency manifests,
  and zero model files; 116 web dependency licences were verified.
- Production dependency audit found zero vulnerabilities.
- Twenty-four pgTAP assertions define the database gate. They were not run
  against a live/local Postgres instance; no database mutation is claimed.
- Visual tests cover the contributor stylesheet and retain contrast, focus,
  reflow, forced-colour, reduced-motion, no-gradient, and no-image-filter gates.

No external data, media, identity, profile, contribution row, credential,
provider output, or active-run artifact was introduced.
