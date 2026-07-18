# Task plan — ButterflyLens 11.2

Task ID: `butterflylens-11.2`

Objective: implement the fourteen named deterministic ButterflyLens evidence
tools over the committed submitted snapshot, with strict model-facing input
schemas, validated bounded outputs, exact artifact citations, and fail-closed
privacy/evidence behavior.

Starting and remote SHA:
`f9b96814f335684cf311b70b622e2cade0188b9b`.

GitHits: disabled for the remainder of the goal by explicit user instruction;
no call is made. No external implementation is needed: the repository's
fingerprinting, quality, review, privacy, worker, geographic-impact, and
submitted-snapshot contracts are authoritative.

BioMiner coordination: Task 11.2 overlaps pipeline and worker visibility.
BioMiner was re-read at `b6d9af957d27ea0f6bb012e030be089d8435f437`
and remains dirty/ahead with active dynamic-pooling/BioCLIP and Flickr work.
No partial output, log, configuration, credential, GBIF file, or Flickr record
will be read or copied. Dynamic lanes remain explicitly unavailable.

Implementation: pin and verify every readable source artifact; define fourteen
strict OpenAI-compatible function contracts; expose a deterministic registry;
validate inputs and outputs; return only bounded scalar facts and records;
attach repository, exact commit, path, and SHA-256 citations; distinguish
observed, derived, unavailable, withheld, unfinished, conflict, and
not-applicable facts; and fingerprint every result.

Available submitted behavior: inspect the authoritative 463-species catalogue,
taxonomy/reference maturity, submitted pipeline state, and deterministic
species-level review priorities. ALA/Flickr comparison, Flickr candidates,
classification, consensus, private reviewer quality, live worker state,
geographic contribution, and authenticated impact remain unavailable when no
committed governed snapshot exists.

Privacy/science boundaries: model arguments never grant authorization. Reviewer
and contributor tools are self-scoped; no identity, expected control, precise
sensitive location, ranking, speed, probability, occurrence, or scientific
truth is inferred. Missing evidence is not zero or absence. YOLOE and BioCLIP
remain unfinished; no provider, database, browser, or OpenAI call is made.

Verification: contract inventory and strictness, semantic arguments, artifact
checksum failure, deterministic fingerprints, all fourteen available or honest
unavailable behaviors, citation completeness, output bounds, no fabricated
metrics, no secrets/provider calls, full Python suite, rights/licensing,
provenance JSONL, staged safety, whitespace, exact commit, and non-force push.

Rollback: remove the tool package, generated contracts, artifact registry,
tests, and task provenance. No live state is changed.
