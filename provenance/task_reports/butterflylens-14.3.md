# ButterflyLens 14.3 — ALA contribution preparation

Status: **implemented and locally verified; publication pending the task
commit**.

Starting SHA:
`6ac859c96bfd40392815ff3ffb7c914c2ed3f130`.

## Outcome

ButterflyLens now prepares a deterministic offline ALA contribution archive
from an exact, verified Task 14.2 Darwin Core evidence archive. The final
archive preserves every source member byte-for-byte and adds all six requested
preparation artifacts: EML dataset metadata, dataset licence, attribution,
provider-agreement checklist, quality report, and final evidence manifest.

The source archive's physical SHA-256 and semantic package fingerprint are
mandatory inputs. Preparation verifies its exact member order, paths,
encryption state, checksums, canonical manifest fingerprint, policy and
non-publication states, record/release receipt inventory, dataset identity, and
representative quality receipt before adding anything. Unknown fields and
tampering fail closed.

The generated EML contains the current mandatory ALA metadata: title,
description, licence, administrative contact name/email, creator, citation, and
provider URL. It also records purpose, methods, keywords, and geographic,
taxonomic, and temporal scope. The selected dataset-record licence is one of
ALA's preferred Creative Commons families; individual media licence, creator,
rights-holder, attribution, and source fields remain authoritative and are not
overwritten.

The final manifest binds both source identities, all inherited and generated
file checksums, record count, exact artifact paths, code SHA, preparation
gates, privacy properties, member order, and canonical package fingerprint.
Fixed ZIP timestamps, permissions, compression, and order plus atomic final
write make identical governed input byte-identical.

## Human and provider boundary

The ordered provider checklist covers Data Provider Agreement execution,
authority to provide occurrence data, dataset licence, attribution,
sensitive-data review, administrative contact, update/removal process, and
third-party media terms. A passed check requires a valid SHA-256 evidence URN;
an unreferenced boolean cannot claim approval.

Preparation states are explicit:

- `blocked_quality_review` when representative review is incomplete or has a
  declared blocker;
- `blocked_pending_provider_requirements` when quality passes but a provider
  requirement remains pending; and
- `ready_for_human_submission` only when both evidence sets pass.

Even the ready state remains `prepared_not_published`, `not_submitted`, and
`human_submission_required`. The contract and CLI import no HTTP, socket,
email, or submission client and expose no submit flag. No ALA email, issue,
upload, agreement action, acceptance, or occurrence publication occurred.

## Scientific, privacy, and quality boundary

The quality report derives record count, release-receipt count, and exact
representative-audit fingerprints from the verified source. It explicitly
rejects targeted failure discovery as a population metric, model scores as
probabilities, no detection as absence, and provider/ALA acceptance as a
quality conclusion. It contains declared limitations rather than invented
precision or performance values.

Because ALA requires an administrative contact, the final manifest marks the
archive `private_operator_handoff` and
`contains_administrative_contact: true`. It is not a public-site artifact. The
inherited biodiversity evidence still contains only governed generalized H3
locations, fingerprint-only review evidence, and media metadata: no raw
coordinates, reviewer identity, or media bytes.

No live release receipt exists in this repository, so no production ALA
package was built or committed. The deterministic fixture uses an `.invalid`
contact and is software evidence only.

## Current-source decision

Current official ALA sharing guidance prefers Darwin Core Archive and lists
the mandatory metadata and occurrence fields. Current ALA terms say detailed
or extensive datasets should have a Data Provider Agreement. Current ALA
licensing guidance prefers CC0, CC BY, and CC BY-NC and requires suitable
provider rights. Those facts and the offline human-gate inference are frozen in
`provenance/valyu.jsonl`; the public policy links the primary sources.

GitHits remained disabled by explicit user instruction and was not called. No
external implementation was copied.

## Verification

- 556 locked Python tests pass, including eleven new fixture-backed ALA
  archive, EML, licence, attribution, provider-checklist, quality, source
  tamper, privacy, deterministic atomic-write, exact parser/CLI, and no-network
  tests.
- The one-record blocked software fixture is 12,244 bytes, has archive SHA-256
  `ceb6b5a3327c4734756954f548592d2b0cbd6f59e593a4d006d8e5bbfeb8e6e5`,
  semantic package fingerprint
  `c71fd3f14bb419d17cb0d545784172a416226202dc27becf0382cb2cf782c5c7`,
  and state `blocked_pending_provider_requirements`. These are software-fixture
  identities, not biodiversity or production performance results.
- All 18 Vitest files and 91 tests plus three standalone Node tests pass. Web
  typecheck, the 116-package dependency audit, media checksum, and the
  `/ButterflyLens/` production build pass. The existing chunk-size warning is
  unchanged and non-blocking.
- All 45 frozen Deno Edge tests pass; four Edge entry points type-check and all
  22 function files pass formatting. The cached Deno 2.9.3 executable was run
  via `npx --no-install` from the function config directory.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixtures, 21 versions, and 15 vocabularies using TypeScript 7.0.2.
- Rights verification covers 52 tracked provider payloads. Repository
  licensing, JSON/JSONL, workflow YAML, shell syntax, Python compilation,
  whitespace, staged scope, secret-safety, model/media/archive-file, and
  large-file checks are completed immediately before commit.

## External-work boundary

BioMiner was inspected only through Git state and its published
`docs/agents/CURRENT_STATE.md` coordination record. It advanced during this
task to `515d581cf9ad3404e027aecf67ecea39a2561028` and remains active with dirty
dynamic-pooling/Flickr work. Its authoritative remaining-work ledger still
names live current-policy GBIF acquisition and durable-media admission, live
BioCLIP/Flickr scoring, representative Flickr reviews, and a sufficient-sample
audit. It supplies no immutable GBIF handoff, so no active data or partial
output was copied. The rebuilt ButterflyLens ALA baseline remains
authoritative.

TaxaLens remained at
`e845dd98493979f37b04dbb6538e0d7b8758ca11`; its dirty user work was untouched.
The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, Flickr result import, Supabase or
B2 mutation, provider submission, media copy, production workflow dispatch,
YOLOE work, BioCLIP work, scientific model call, or scientific inference
occurred.

Known limitation: producing a real contribution requires immutable release
receipts, approved private administrative contact, provider-rights evidence,
executed ALA provider agreement, and explicit human submission authorization.

Next safe task: broaden cross-contract coverage in Task 15.1 after this exact
commit is pushed and its GitHub Pages deployment is verified.
