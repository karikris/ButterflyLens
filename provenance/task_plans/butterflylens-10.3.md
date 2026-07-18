# Task plan — ButterflyLens 10.3

Task ID: `butterflylens-10.3`

Objective: add searchable Australian butterfly species pages derived from the
authoritative rebuilt ButterflyLens taxonomy, sourced-name, crosswalk, rights,
and provisional reference artifacts.

Competition criterion improved: a public, evidence-disciplined national species
catalogue that keeps authority, source assertions, provider conflicts, missing
media, provisional references, and unavailable occurrence evidence distinct.

Starting and remote SHA:
`9128a2757ad3dbab35df92aa610cae76894181ca`.

BioMiner overlap: the user-supplied GBIF occurrence archive overlaps BioMiner's
active fingerprinted evidence-database build. Its root instructions and current
agent record were inspected. The work remained active at observed commit
`b372ce18d6be62c1b66025b700d5c4e4a884428c`, so no duplicate download,
conversion, mutation, or copy is permitted in this task. Recheck after the task
boundary and copy only a completed published handoff.

Relevant agent files read: root `AGENTS.md`; the complete `docs/agents/` folder;
BioMiner root `AGENTS.md`; and BioMiner `docs/agents/CURRENT_STATE.md`.

Relevant skill: none. This task is a local code-and-fingerprinted-data projection
and does not require an available specialized skill.

GitHits: disabled for the rest of the goal by explicit user instruction because
the service is unavailable. It is not called.

Valyu needed: no. Frozen local manifests, exact fingerprints, provider rights,
and user governance decisions are authoritative for this projection.

Expected files: deterministic catalogue builder and generated JSON, strict web
model, searchable directory and species profile, responsive styles, component
and source-reconciliation tests, application composition, human decision
record, model/tool ledgers, prior-task commit receipt, and task report.

Contracts affected: the credential-free public species catalogue projection.
Database, API, review, consensus, and scientific-release contracts are
unchanged.

Data/rights implications: project only artifacts already admitted for display
and redistribution in `provenance/data_rights_manifest.json`. Reuse the one
existing rights-cleared review fixture only for its provider-labelled taxon and
retain its nonrepresentative, non-verification notice. Add no remote media.

Scientific risks: treating English names or provider matches as reviewed truth;
resolving identifier conflicts automatically; turning reference counts into
identity evidence; publishing rights-blocked ALA occurrence counts; treating
missing names, media, or records as absence; or implying skipped model results.

Security/privacy risks: browser-bundled private evidence, remote requests,
unstable identifiers, or unsafe source links. The public projection must contain
only admitted aggregate/factual evidence and immutable source fingerprints.

Tests: deterministic rebuild, catalogue fingerprint, 463 unique species and
hierarchy coverage, conservative identifiers and names, empty cultural-name
gate, withheld ALA count, unfinished model and zero-human-review state, search,
family filter, selected profiles, conflicts, missing-media handling, visual
system rules, full Python/web suites, typecheck/build, rights/licensing,
provenance, staged safety, and whitespace.

Rollback/recovery: remove the species component, generated projection, builder,
styles, and tests and restore the scheduled shell preview. No source pack,
database, provider archive, BioMiner state, or existing media bytes are mutated.
