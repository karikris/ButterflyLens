# Architecture and upstream boundaries

## 1. Product boundaries

### BioMiner

Owns the scientific engine:

- registry compilation;
- name trust;
- Flickr query planning/polling;
- geographic normalization;
- reference admission;
- YOLOE routing;
- full-frame inputs;
- BioCLIP embeddings;
- candidate scoring;
- calibration/evaluation;
- incremental reruns;
- durable model artifacts.

### TaxaLens

May supply stable precedent/contracts for:

- campaigns;
- append-only reviews;
- consensus/conflicts;
- quality estimates;
- geographic impact;
- evidence facade;
- Bounded model tools;
- deterministic replay.

### ButterflyLens

Owns:

- Australian public/community product;
- Australian butterfly pack;
- ALA/Flickr live map;
- community accounts and moderation;
- repeated review;
- reviewer reliability;
- species pages;
- live M5 worker presentation;
- submitted/live snapshots;
- stored evidence replay tools;
- contributor experience.

Do not duplicate upstream scientific algorithms unless no stable artifact,
schema, command, or package can satisfy the need.

---

## 2. High-level architecture

```text
Public web application
    ├── Explore map
    ├── Verify
    ├── Species
    ├── Live
    ├── Quality
    ├── Contributors
    └── About

Supabase PostgreSQL/Auth/RLS
    ├── projects/runs/work items
    ├── review campaigns/events/consensus
    ├── worker heartbeat
    ├── quality snapshots
    └── map summaries

Backblaze B2
    ├── immutable Parquet
    ├── manifests
    ├── permitted media
    ├── full-frame inputs
    ├── embeddings
    └── submitted snapshots

M5 Pro worker
    ├── Flickr scheduler
    ├── media validation/dedup
    ├── YOLOE
    ├── BioCLIP
    ├── Parquet commit
    └── map materialization
```

The web application must continue working when the M5 worker is offline.

---

## 3. Submitted versus live

### Submitted

- immutable;
- exact code SHA;
- exact data/model fingerprints;
- credential-free;
- deterministic;
- source for video and competition claims.

### Live

- append-only updates;
- current heartbeat;
- current processing state;
- timestamped;
- may change after submission.

The UI must clearly label the mode and never overwrite the submitted snapshot.

---

## 4. M5 worker

The M5 is a compute worker, not the public host.

Persist:

- worker ID;
- machine/software/model fingerprints;
- MPS availability;
- memory/disk;
- current lease/stage;
- heartbeat;
- last committed artifact.

Worker rules:

- persistent models;
- bounded queues by items and bytes;
- one model process per accelerator by default;
- automatic batch reduction on memory pressure;
- checkpoint before cleanup;
- no repeated committed request/download/embedding;
- resumable leases;
- website independence.

Use `launchd` or the later native app host for restartable operation.

---

## 5. Storage roles

### PostgreSQL

Mutable control state:

- projects/runs;
- work leases;
- API budget;
- heartbeats;
- review assignments/events;
- current consensus;
- user roles;
- quality snapshots;
- current map summaries;
- release projections.

### B2

Immutable evidence:

- Parquet;
- manifests;
- snapshots;
- permitted media;
- transformations;
- embeddings;
- reports;
- submitted bundle.

### Local cache

Temporary:

- model weights;
- source downloads;
- decode cache;
- working shards.

Delete only after durable commit.

---

## 6. Parquet and manifests

- immutable parts;
- Zstandard compression;
- versioned schemas;
- stable IDs/fingerprints;
- projection/predicate pushdown;
- bounded part sizes;
- row/byte/checksum inventory;
- manifest written last;
- deterministic sort and canonicalization.

Do not store large analytical matrices in PostgreSQL.

---

## 7. Fingerprint chain

Fingerprint at minimum:

- taxon concept;
- name assertion;
- query definition;
- physical API request and response;
- logical query association;
- Flickr source record;
- media content;
- duplicate group;
- YOLOE route;
- full-frame input;
- embedding;
- reference bank/prototype;
- candidate score;
- review event;
- consensus;
- quality snapshot;
- map cell;
- release candidate;
- export.

A downstream artifact must retain the upstream fingerprints needed to explain
its derivation.

---

## 8. Public map architecture

Recommended scopes:

```text
Australia
state/territory
IBRA
LGA
H3/spatial cell
record
```

National view should use aggregated H3/hex data; lower levels may use bubbles
and individual points.

The judge replay must not require external tiles, fonts, or map credentials.
Bundle compatible boundaries/styles or provide an offline fallback.

Always provide a synchronized table.

---

## 9. Live API scheduler

Use one Flickr API ledger/token bucket across every method.

Persist:

- window;
- budget;
- reserve;
- request fingerprint;
- method;
- query/partition;
- response hash;
- retries;
- quota status.

Search planning should prioritize unique/geotagged/butterfly-positive yield,
coverage gaps, species readiness, and review capacity. Low-yield terms may cool
down. Search terms remain provenance, not labels.

---

## 10. OpenAI boundary

Bounded model receives typed evidence through bounded tools. It may plan, inspect,
compare, explain, and report.

It does not own:

- work leases;
- pipeline state;
- queue checkpoints;
- model inference;
- statistical calculations;
- consensus;
- release decisions.

The deterministic orchestrator continues when bounded inference contracts are no longer active.

---

## 11. Security boundary

- Browser receives user-scoped credentials only.
- Service-role, B2, Flickr secret, and OpenAI credentials remain server-side or
  in the worker’s secure secret store.
- RLS protects exposed tables.
- B2 access uses constrained signed URLs.
- Review events and scientific evidence are append-only.
- Sensitive coordinates are generalized before public exposure.
