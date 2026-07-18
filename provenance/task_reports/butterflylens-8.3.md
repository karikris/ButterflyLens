# ButterflyLens 8.3 — Repeated independent assignment

Status: **implemented locally; database integration gate unavailable in this environment**.

Starting SHA: `d30da7d3ddfc8d992533be4f902c1bc51ee63c07`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 8.3 adds a versioned, server-only assignment policy over the existing
campaign, reviewer, membership, and assignment tables:

- ordinary images require two independent reviewers;
- disagreement campaigns require a third reviewer;
- potential-gap campaigns permit three to five reviewers, defaulting to three;
- reference images require two reviewers;
- high-impact release candidates permit three to five reviewers, defaulting
  to three, with at least two verified qualifications and an expert gate.

Campaign creation fails closed when counts, qualified-review minima, or the
expert gate contradict those rules. Assignment writes retain the existing
unique campaign-item-reviewer key, use a transaction advisory lock, and require
the next monotonic round. Expired or withdrawn work no longer satisfies the
active assignment count, so a later independent reviewer can receive a new
round without deleting history.

The database derives assignment reason and required reviewer role. It checks
active project membership and profile state at assignment time. Qualified
slots require a verified qualification; the expert slot additionally requires
an expert, curator, or administrator project role. Assignment identity and
policy fields are immutable after creation.

A service-only progress function reports required, assigned, responded,
remaining, qualified, and expert-gate counts. It returns no reviewer identity
or decision, and neither guests nor authenticated reviewers can call it.
Existing RLS still lets reviewers read only their own assignment rows and
reserves mutation for curators/administrators.

## Evidence and provenance

The Supabase and Supabase Postgres best-practices skills informed the fixed
search paths, explicit grants, private schema, RLS separation, concurrency
lock, and indexed uniqueness boundary. Current official Supabase RLS and Data
API guidance was used because Valyu remained unavailable. GitHits remained
unavailable and was not retried.

TaxaLens' immutable required-independent-reviewer and consensus precedent was
inspected. No TaxaLens code or data was copied; the policy, migration, and tests
are original ButterflyLens implementation. No Flickr API call, YOLOE work,
BioCLIP work, model artifact, scientific score, or biodiversity claim was
produced.

## Verification

- Targeted Python migration/RLS suite — 21 tests passed.
- pgTAP fixture — 21 assertions defined for policy defaults, private
  privileges, and server-only progress access.
- Docker-backed pgTAP execution — unavailable because this runtime cannot
  access the Docker daemon; the fixture was not reported as executed.
- `uv run python -m unittest discover -s tests -v` — 288 passed.
- Cross-language contract parity — passed with TypeScript 7.0.2: 24 schemas,
  20 valid fixtures, 20 invalid fixtures, 20 versions, and 15 vocabularies.
- Rights verification — passed for 52 tracked provider/media payloads.
- Licence verification — passed for 280 tracked files, two dependency
  manifests, and zero model files.
- Provenance JSON/JSONL, staged whitespace, secret-pattern, and model-artifact
  gates passed.

## Privacy and scientific boundary

Assignment policy does not expose peer decisions, reviewer identities,
reliability, model outputs, or campaign progress to reviewers. Counts create
review work only; they do not establish consensus, expert approval, human
support, or release readiness. Blind-review enforcement remains Task 8.4 and
append-only decision persistence remains Task 8.5.
