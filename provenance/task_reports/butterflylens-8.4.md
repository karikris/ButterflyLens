# ButterflyLens 8.4 — Blind community review

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `c731df6dbc97f756337eae2088d394d049cd5d40`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 8.4 turns the existing blind-review flags into an enforceable data and UI
boundary. Every community campaign must keep model label, model score, Flickr
query term, source comment, and peer-decision blinding enabled.

The assigned-review projection is a security-invoker view over existing RLS.
It exposes only assignment/campaign IDs, question, assignment status,
blind-payload fingerprint, checksum, byte count, media type/dimensions, rights
fingerprint, and a false scientific-claim flag. It never selects private
storage keys, campaign names, assignment reasons or sequence, model evidence,
Flickr query definitions, source comments, peer decisions, Auth IDs, or
reviewer profile IDs. Media rows are available only to
their assigned reviewer and only when committed, valid, rights-allowed, and
display-permitted.

Post-decision context uses a separate allowlisted disclosure table. A composite
foreign key binds each disclosure to the same assignment's append-only review
event. Respondent RLS also requires that assignment to be `responded` and that
its reviewer match the current Auth user. Guests cannot read disclosures and
reviewers cannot create them. Model context is banded rather than a raw score;
peer context is counts without identities; source-comment excerpts require an
explicit display permission; every disclosure forbids scientific claims.

In the credential-free page, all six required context classes are listed as
withheld. The complete Commons title/source link is also withheld because it
contains the provider taxon label; creator and licence remain visible. After a
reviewer chooses an outcome, they may lock the local draft and reveal only the
allowlisted context. Controls remain locked after reveal. Starting a new draft
clears the decision, comment, and alternative taxon and restores the blind
state. The replay disclosure truthfully reports model, Flickr, comment, and
peer evidence unavailable.

## Evidence and provenance

The Supabase and Supabase Postgres best-practices skills informed the use of
column grants, RLS, security-invoker views, fixed allowlists, foreign keys, and
indexed access paths. Current official Supabase RLS and Data API guidance was
used because Valyu remained unavailable. GitHits remained unavailable and was
not retried.

TaxaLens' immutable blind-disclosure pattern was inspected. No TaxaLens code,
data, or stored disclosure was copied; the migration, components, styling, and
tests are original ButterflyLens implementation. No Flickr API call, YOLOE
work, BioCLIP work, model artifact, scientific score, or biodiversity claim
was produced.

## Verification

- `npm test` — six component/interaction tests passed.
- `npm run check` — strict TypeScript check passed.
- `npm run build` — production build passed; 201.89 kB JavaScript and 9.05 kB
  CSS before gzip.
- Targeted blind-review/RLS/database suite — 20 tests passed.
- pgTAP fixture — 18 assertions defined for views, RLS, grants, and hidden
  base-table fields.
- Docker-backed pgTAP execution — unavailable because this runtime cannot
  access the Docker daemon; the fixture was not reported as executed.
- `uv run python -m unittest discover -s tests -v` — 293 passed.
- Cross-language contract parity — passed with TypeScript 7.0.2: 24 schemas,
  20 valid fixtures, 20 invalid fixtures, 20 versions, and 15 vocabularies.
- Rights verification — passed for 52 tracked provider/media payloads.
- Licence verification — passed for 285 tracked files, two dependency
  manifests, and zero model files.
- `npm audit --audit-level=high` — zero vulnerabilities reported.
- Provenance JSON/JSONL, staged whitespace, secret-pattern, and model-artifact
  gates passed.

## Privacy and scientific boundary

A local locked draft is not a persisted review event; Task 8.5 owns append-only
submission and duration/source-version evidence. The fixture's source metadata
is bundled in a static artifact and therefore is not a secure production blind
payload; the database projection is the production authority boundary. Reveal
does not turn model output, provider labels, query terms, comments, majority,
or peer counts into scientific truth, consensus, or release readiness.
