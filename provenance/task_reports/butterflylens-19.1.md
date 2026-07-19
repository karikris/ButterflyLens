# ButterflyLens 19.1 — implementation uplift and legacy cleanup

Status: **repository-owned uplift complete; external data, live-service,
human-production, and model work remains explicitly unfinished**.

Starting and remote SHA:
`b86d32334476f6497a7ac187472c2d2cb53e80a9`.

Implementation commit:

- `282f940190a0b1351e268d393355828fa6e29e84` — remove the unused
  evidence-fingerprint v1.0 compatibility island and make v1.1 the only
  admitted contract.

Ending and remote SHAs: pending this closeout commit and the required
non-force task push.

## Audit outcome

The implementation inventory covered 644 tracked files, the Python and
TypeScript contract/runtime surfaces, 92 Python test modules, all tracked JSON
Schemas, the SQL and Edge-function surfaces, scripts, submitted artifacts,
and exact Git history. Searches combined path/reference inventory, duplicate
body and export checks, contract/test ownership, and history rather than
assuming that a low lexical reference count meant dead code.

One compatibility layer was proven redundant. Fingerprint v1.0 was created at
`9fd6137596613eb19d87f537e37c5be140e27122` and superseded by v1.1 at
`690592cb8b2ff31da22734504b69dcda04b86c19` during the same 18 July uplift.
It had no admitted record, submitted artifact, runtime consumer, or exact
committed TaxaLens/BioMiner consumer. Its remaining footprint consisted only
of its schema, a second vocabulary, parallel types, a compatibility union,
validator branches, exports, parity roots, and positive compatibility tests.

The implementation commit therefore:

- deletes the v1.0 JSON Schema and legacy Python/TypeScript declarations;
- replaces the compatibility union with the concrete current fingerprint type
  throughout the TypeScript lineage graph;
- makes both validators accept only v1.1 and reject v1.0 before vocabulary or
  digest processing;
- removes compatibility-positive fixtures and tests while adding explicit
  negative version rejection in runtime and JSON-Schema parity gates;
- preserves the negative `api_response` vocabulary test; and
- reconciles the governed inventory from 42 to 41 tracked schemas and from 25
  to 24 cross-language schemas. The previous documentation's claim of 36
  tracked schemas was stale and is corrected to the enforced total.

This removes 317 lines while adding 52 implementation/test/documentation lines
before provenance. No migration adapter is retained because there is nothing
persisted to migrate.

## Retained implementation boundaries

The audit did not collapse useful ports merely because their declarations are
small:

- `SearchPageTransport` isolates provider I/O from deterministic planning,
  retry, and budget tests;
- `EvidenceLedgerStore` and `LogicalAssociationLedgerStore` encode append-only
  persistence behavior independently of a concrete backend;
- `DurableArtifactStore` keeps worker checkpoint/commit semantics testable and
  prevents storage implementation details from entering scientific routing;
- `HeartbeatSink` separates worker liveness reporting from work execution; and
- `KeychainSecretProvider` is the explicit macOS credential boundary and is
  directly exercised for success and failure behavior.

Removing these would couple network, persistence, heartbeat, or secret access
to domain logic and weaken existing fail-closed tests. They are ports, not
unused wrapper layers.

Repeated short helpers were also reviewed. The similarly named
`canonical_json`, `write_json`, `write_parquet`, `sha256_file`, `_digest`,
`_utc_text`, `_text`, `_identifier`, `_https_url`, and `_strict_kwargs`
functions do not form one safe generic abstraction: they differ in I-JSON/JCS
rules, newline and encoding policy, explicit Parquet schemas and metadata,
atomic replacement behavior, type/domain limits, and error ownership. Moving
them behind a new cross-domain utility or factory would introduce coupling and
make scientific artifact builders less auditable. Their local ownership is
retained. No unreferenced factory or configuration layer was found that could
be removed without changing a provider, security, storage, or contract
boundary.

Positive contract tests outside the retired v1.0 island remain valuable: they
assert fail-closed rights, human-authority, scientific-language, privacy,
lineage, restart, and submitted/live boundaries. They were not removed as
"legacy" based on age alone.

## GitHits and upstream alignment

GitHits solution `f19c0cc1-02b7-44e2-9bc6-0bff36544b17` was used under strict
licensing. MIT-licensed examples from `peterbussch/pageledger`,
`surya17495/centri-v0`, and `MyButtermilk/Scriber` supported the general
current-only validator plus retired-version negative-test pattern. No external
code was copied. Positive feedback was submitted after the pattern passed the
ButterflyLens cross-language gates. The query, sources, adopted/rejected
patterns, licensing, and feedback state are recorded in
`provenance/githits.jsonl#butterflylens-19.1.1`.

Only exact committed upstream objects were considered:

- BioMiner `ae6a18509b7be48da5c6ca69ab0caacf4632cc70`;
- TaxaLens `e845dd98493979f37b04dbb6538e0d7b8758ca11`.

Neither has a committed fingerprint-v1.0 consumer. Their dirty worktrees were
preserved. TaxaLens alignment remains contract-based and the rebuilt ALA
baseline remains authoritative. BioMiner is still fetching Flickr metadata
only according to the user; no BioMiner data exists for this handoff, no
partial record was inspected or copied, and ButterflyLens made no Flickr API
call.

## Verification

- 670 Python tests pass in 34.818 seconds.
- Focused fingerprint and governed-contract tests pass: 13 tests.
- Python/TypeScript/JSON-Schema parity passes with 24 schemas, 20 positive
  documents, 22 negative documents, 20 version checks, 14 vocabulary checks,
  and TypeScript 7.0.2.
- The contracts TypeScript surface passes strict compilation.
- 100 Vitest tests and three standalone Node tests pass.
- Web dependency-licence, media, production build, and type checks pass; the
  generated production bundle is unchanged by this contract-only task.
- 49 Deno Edge tests pass; formatting covers 23 files and all four Edge entry
  points type-check against the frozen lockfile.
- Rights verification passes for 66 tracked provider/data/media payloads.
- Licensing passes for the final closeout boundary's 645 tracked files, two
  dependency manifests, and zero model files.
- Release security passes across 50 public-RLS tables, 11 security-invoker
  views, 60 security-definer functions, 621 tracked text files, and 12
  explicitly inventoried network-boundary files. `release_ready=false` remains
  binding.
- Both fixed completion audits pass. The current audit remains 80 satisfied,
  eight partial, seven blocked by user instruction, and five externally
  blocked; `goal_complete=false`.
- JSON and JSONL parsing, Python compilation through the full suite, and
  whitespace/staged-scope checks pass.

The Playwright command rebuilt the site successfully but all ten browser
launches were unavailable on this WSL host because required system libraries
are absent (`libnspr4.so`, `libasound.so.2`, and WebKit runtime dependencies).
No product assertion failed and the preceding task boundary recorded all ten
browser checks passing. System packages were not installed as part of this
contract cleanup. Generated failure traces were removed after the diagnostic.

## Binding unfinished work

The repository-owned cleanup and alignment requested by Task 19.1 is complete.
The broader product/release state is intentionally not upgraded:

- BioMiner's Flickr metadata fetch is still active, so there is no completed
  immutable handoff to copy; do not ingest its mutable output mid-run;
- no Flickr API call or image fetch may be started from ButterflyLens;
- YOLOE and BioCLIP execution remain skipped and unfinished by user
  instruction;
- the representative live Bounded model evaluation remains `not_run` and requires a
  separately authorized credentialed run, cost acceptance, and human review;
- Supabase OAuth approval, client reload, and read-only remote comparison
  remain external operator work; configuration is not remote evidence;
- the demonstration packet is not a narrated, human-reviewed, approved, or
  uploaded public video; and
- live community review, production privacy operations, remaining ALA rights
  decisions, live worker/provider evidence, and public release remain blocked
  by the existing completion and release-security gates.

No additional repository-owned task can honestly resolve those states without
new completed upstream data, operator authorization, model authorization, or
human work. The safe next action after BioMiner finishes is to inspect its
exact committed completion record and copy only the versioned, checksum-backed
handoff artifacts that meet ButterflyLens rights and contract gates.
