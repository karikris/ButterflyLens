# Task 18.1 plan — fingerprinted GBIF occurrence evidence

Task ID: `butterflylens-18.1`

Objective: acquire the operator-supplied GBIF Australian Papilionoidea download,
freeze its exact receipt, convert the Darwin Core occurrence and multimedia
members to deterministic rights-preserving Parquet, and integrate the evidence
pack without replacing the rebuilt ButterflyLens ALA baseline.

Competition criterion improved: reproducible Australian butterfly occurrence
evidence with immutable source identity, exact attribution, explicit quality and
sensitivity boundaries, and offline replay.

Starting SHA: `51e3dc3d84978432b3b1991a5a375a581684b64d`

Remote main SHA: `51e3dc3d84978432b3b1991a5a375a581684b64d`

BioMiner SHA inspected for coordination:
`19fd744b1104c09dde75367bafb6b531ef4239a4`. BioMiner is still fetching
Flickr metadata and has no complete immutable GBIF handoff, so no partial
upstream output will be copied.

Relevant agent files read: `AGENTS.md` and the complete `docs/agents/` policy
pack. The updated instructions are acknowledged and govern this task.

Relevant skill: Headroom. It compressed the 2,611-line goal file under receipt
`898dbe5ec3520d1425bf5d0f` and protected the focused ALA builder/test sources
under receipt `70c0caae115eb0066a82175e`; exact source reads remain authoritative.

GitHits needed: no call. It is unavailable and disabled for the rest of the
goal by direct operator instruction.

External sources needed: yes. Only the official GBIF occurrence download API,
the exact supplied archive, and official GBIF technical documentation are used.

## Source contract

- Download key: `0004170-260715120105164`.
- DOI: `10.15468/dl.7uut3k`.
- Citation: `GBIF.org (18 July 2026) GBIF Occurrence Download
  https://doi.org/10.15468/dl.7uut3k`.
- Scope: country `AU` and Catalogue of Life Papilionoidea taxon key `5G9`.
- Expected records: 571,755 from 126 constituent datasets.
- Raw archive: 261,743,165 bytes, SHA-256
  `7807622f6c2539ac536cb5f06d17087da3ecdd83b13a0dec54764e3800ff8f2b`.

The raw 261.7 MB archive is verified outside Git and will not be committed.
Acquisition and build are separate commands so default tests remain offline.

## Evidence and rights policy

GBIF rows are processed provider occurrence assertions, not human verification,
ground truth, proof of presence at present, or proof of absence. Exact provider
licence, rights-holder, attribution, information-withheld, generalisation,
coordinate-uncertainty, issue, and geospatial-quality fields must be preserved.
The download-level licence is CC BY-NC 4.0; constituent rights include CC BY
4.0, CC BY-NC 4.0, and CC0. Public release remains blocked pending the existing
rights and human-review gates.

The independently rebuilt ButterflyLens ALA baseline remains authoritative.
This GBIF pack is complementary evidence for occurrence comparison, provenance,
taxonomy reconciliation, and future keyword/reference analysis.

## Patch plan

1. Freeze the official download/API receipt, archive member fingerprints,
   citation, constituent-rights distribution, scope, authority boundary, and
   provenance. Commit as an independently reviewable subtask.
2. Add an explicit acquire/verify command and a deterministic offline
   DWCA-to-Parquet builder with closed schemas, semantic row fingerprints,
   stable ordering, exact rights preservation, negative tests, and byte-stable
   rebuild coverage. Commit as an independently reviewable subtask.
3. Build and admit occurrence, multimedia, and dataset/citation Parquet files;
   publish a manifest with physical and semantic fingerprints; update the pack
   inventory while retaining ALA authority. Commit as an independently
   reviewable subtask.
4. Run proportional and repository gates, push the task commits to direct
   `main`, verify remote identity, and report all still-unfinished live Flickr,
   YOLOE, BioCLIP, M5, community-review, and release work.

## Security, privacy, and scientific risks

- Never persist credentials, notification email addresses, private endpoints,
  signed URLs, or worker telemetry.
- Never reconstruct or increase the precision of withheld/generalised
  locations; preserve only GBIF-processed public values and warnings.
- Never infer biological absence from missing records or identify a butterfly
  from an occurrence/provider label.
- Never silently merge GBIF records into the authoritative ALA baseline.
- Never download media or call Flickr as part of this task.

## Verification

Focused receipt/schema/fingerprint tests; ZIP integrity and exact archive hash;
expected row, dataset, and media counts; deterministic Parquet rebuilds;
physical/semantic manifest reconciliation; rights/sensitivity preservation;
JSON/JSONL validation; security, rights, licensing, snapshot, staged-scope,
large-file, secret, and relevant full-suite gates.

Rollback: remove the additive `gbif/` evidence directory, builder/tests, pack
inventory references, and this task's append-only provenance entries. The ALA
baseline and all existing submitted artifacts remain unchanged.
