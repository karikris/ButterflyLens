# Scientific, community, and data rules

## 1. Evidence maturity

Use explicit stages:

```text
discovery_candidate
butterfly_image_candidate
species_candidate
community_reviewed
human_supported
expert_reviewed
release_ready_occurrence_candidate
published_occurrence
```

Never skip a stage in public language.

A release-ready candidate is still not a published occurrence.

---

## 2. Discovery and taxonomy

- Query terms explain retrieval, not identity.
- Retain every logical query association after physical-request deduplication.
- Scientific names, synonyms, common names, genera, families, and order terms
  do not label returned photos.
- Higher-rank evidence must not catastrophically prune species candidates.
- The target and eligible competitor union remain scoreable.

Taxonomic concepts must preserve:

- accepted key;
- source IDs;
- accepted name;
- rank;
- parent path;
- taxonomic status;
- source version;
- conflicts.

Do not silently merge incompatible concepts.

---

## 3. Name assertions

Every name assertion records:

- taxon key;
- name;
- language;
- region;
- source;
- trust tier;
- query eligibility;
- homonym risk;
- review state;
- retrieval date.

### First Nations language names

Do not use a generic “Aboriginal name” field.

Require:

- language name/identifier;
- Country/community;
- source;
- cultural authority or publication;
- permitted use;
- attribution;
- review state;
- query eligibility.

No machine translation, invention, pan-community generalization, or public
query use without evidence and authorization.

---

## 4. ALA baseline

Use:

```text
ALA baseline occurrence evidence
```

Do not call it complete truth or official ground truth.

Every snapshot records:

- taxon scope;
- query;
- retrieval date;
- snapshot ID;
- source datasets;
- licences;
- attribution;
- coordinate policy;
- basis-of-record policy;
- sensitive-data policy;
- fingerprint.

Distinguish:

- eligible field observations;
- machine observations;
- specimens;
- fossils;
- historical records;
- coordinate uncertainty;
- geospatial issues;
- data-deficient cells.

Do not infer biological absence from missing ALA evidence.

Preserve provider-specific terms and sensitive-coordinate generalization.

---

## 5. Flickr

### Evidence

A Flickr record is a candidate until release gates pass.

Public claim:

> All butterfly candidate images discoverable through the published
> ButterflyLens Flickr search plan.

Never claim all Australian butterfly photos on Flickr.

### API budget

Current repository policy:

```text
hourly envelope:        3,500
normal planned maximum: 3,000
reserve:                  500
safety remainder:         100
```

One ledger covers search, metadata, geo, licences, comments, retries, and manual
calls. Do not evade limits with multiple keys.

Partition searches that approach provider result ceilings. Persist request,
response, partition, page/cursor, and logical-association fingerprints.

### Display

Apply current Flickr terms. At minimum:

- no more than the permitted number of Flickr photos per public page;
- photographer/source link;
- licence and attribution;
- required non-endorsement notice;
- removal workflow;
- no public exposure of private/research-only caches.

Verify current terms with Valyu before changing the implementation or public
copy.

---

## 6. Reference images

Provider-asserted GBIF/ALA/iNaturalist images may enter provisional support only
under an explicit admission policy.

Label them:

```text
provider-asserted provisional support
```

Do not call them human verified, expert confirmed, or ground truth.

Required automated gates should cover:

- accepted taxon reconciliation;
- source/provider identity;
- media type and decode;
- checksum;
- licence/use policy;
- attribution;
- canonical duplicate status;
- observation/photographer diversity;
- YOLOE route/domain compatibility;
- subject visibility;
- full-frame input generation.

Human rejection overrides provider assertion.

Separate adult, larval, pupal, specimen, and artifact banks.

Provider-asserted support must not become calibration or final-test truth without
the configured human-review policy.

---

## 7. Models

### YOLOE

YOLOE is a gate/router. It may identify:

- adult butterfly;
- caterpillar;
- pupa/chrysalis;
- specimen;
- moth/other insect;
- artifact;
- no organism;
- ambiguous visual domain.

It does not decide species.

### BioCLIP

- Run locally from fingerprinted Hugging Face weights by default.
- Do not upload Flickr images to Hugging Face by default.
- Load once per persistent worker.
- Use full-frame inputs for target-aware production:
  - raw;
  - focused;
  - masked;
  - multi-object.
- Encode each content/input/model fingerprint once.
- Reuse embeddings.

### Scores

The following are not probabilities:

- cosine similarity;
- nearest-reference similarity;
- prototype similarity;
- detector score;
- SVM margin;
- geographic evidence score.

A calibrated probability requires reviewed labels, leakage-safe groups, an
independent calibrator, and a versioned evaluation.

---

## 8. Geography and map semantics

Map colors:

- blue: ALA baseline occurrence evidence;
- amber: Flickr evidence.

Maturity must also use fill/stroke/shape:

- hollow: unreviewed;
- light fill: community reviewed;
- solid: human supported;
- dark outline: release ready;
- dashed: uncertain.

Use:

- potential coverage-gap cell;
- human-supported additional cell;
- release-ready additional cell;
- candidate range extension;
- data-deficient baseline.

Do not use:

- new occurrence;
- new range;
- species absent from Australia.

Recommended drilldown:

```text
Australia
→ state/territory
→ IBRA
→ LGA
→ H3/spatial cell
→ record
```

Every map requires an exact-count accessible table and non-color semantics.

---

## 9. Human verification

Separate campaigns for:

- butterfly/non-butterfly;
- Flickr identity;
- reference identity;
- geographic-gap candidates;
- conflict/adjudication;
- reviewer controls.

Outcomes:

- Yes;
- No;
- Can’t tell;
- Can’t view;
- Skip;
- optional comment;
- optional alternative taxon where qualified.

Yes, No, and Can’t tell require displayed, integrity-checked media.

Skip and Can’t view are not decisive.

Review events are append-only and bind:

- reviewer;
- campaign/item;
- question version;
- image hash;
- outcome;
- time/duration;
- source/model versions;
- superseded event.

### Blind review

Hide model output, search term, comments, majority vote, other reviewers, and
novelty framing when the campaign policy requires blindness.

### Consensus layers

Separate:

- community evidence;
- qualified consensus;
- release consensus.

A community click must not directly release a record.

---

## 10. Reviewer reliability

Principles:

1. Equal initial weight.
2. No weighting without sufficient controls and overlap.
3. Domain-specific reliability.
4. Shrink estimates toward equal weight.
5. Cap individual influence.
6. Preserve uncertainty and minority dissent.
7. Never use agreement with BioCLIP as truth.
8. Never use majority agreement alone as truth.
9. Keep reliability private.
10. Do not publicly shame reviewers.
11. Do not use speed leaderboards.

Valid evidence may include:

- adjudicated control items;
- independently resolved overlap;
- sensitivity/specificity;
- agreement statistics;
- uncertainty interval;
- domain sample size.

---

## 11. Statistical quality

Maintain two distinct queues:

### Audit

- probability/stratified sample;
- known inclusion probabilities;
- representative geography/species/score/query tiers;
- grouping by duplicate, observation, owner, and geography;
- used for population-quality estimates.

### Failure discovery

- low margins;
- unusual geography;
- small subjects;
- model disagreement;
- comment conflict;
- reference shortfall;
- used to find errors, not unweighted population estimates.

Where valid, calculate:

- review coverage;
- viewability;
- precision/recall;
- false-positive/negative rates;
- coverage/abstention;
- confidence intervals;
- effective sample size;
- agreement/conflict.

Return unavailable when assumptions or samples are insufficient.

Do not claim that more votes automatically guarantee accuracy.

---

## 12. Rights, privacy, and sensitive data

Every displayed media asset records:

- creator;
- source;
- licence;
- licence URI;
- attribution;
- use scope;
- checksum;
- removal policy.

Never expose:

- private source caches;
- secrets;
- signed URLs beyond their intended scope;
- sensitive coordinates;
- private reviewer reliability.

Preserve ALA coordinate generalization and equivalent controls for Flickr-derived
records.

Maintain a takedown/removal workflow and moderation audit trail.

---

## 13. Release gate

A Flickr record may enter a final export only when the configured policy passes,
including as applicable:

- decisive human identity review;
- qualified consensus;
- expert review;
- coordinate/date quality;
- duplicate independence;
- rights and provenance;
- representative quality gate;
- no unresolved conflict;
- complete evidence packet.

A released record is a projection from immutable evidence, not a mutable status
on the source Flickr row.
