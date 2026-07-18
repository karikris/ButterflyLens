# Representative audit and dataset-quality policy

Policy version: `butterflylens-representative-audit-policy:v1.0.0`

## Purpose

ButterflyLens estimates dataset precision only from a blind probability sample whose sampling frame, inclusion probabilities, strata, and dependence groups are recorded. A targeted failure-discovery queue is useful for finding defects, but it is not representative and must never be reported as a population-quality estimate.

## Separated audit lanes

`representative_audit` is the only lane eligible for a population estimate. It requires a probability design (`simple_random`, `stratified_random`, or `clustered_random`), an immutable sampling-frame fingerprint, the exact `hajek_inverse_inclusion_probability_v1` method, and both `owner_id` and `observation_id` grouping keys.

`targeted_failure_discovery` may prioritize suspected errors, rare cases, or operational anomalies. It reports reviewed, decisive, supported, failure, and unresolved counts. Its precision estimate, interval, and effective sample size are always null, and `population_estimate_allowed` is always false.

## Estimator

Only `supported` and `not_supported` outcomes backed by complete agreement or exact independent adjudication are decisive. `uncertain`, `media_failure`, and `deferred` remain explicit but do not enter the estimate.

Within each declared stratum, records receive inverse-inclusion-probability weights. The estimator normalizes those weights within stratum and combines stratum estimates using declared population weights, or population counts when all weights are absent. Mixed or incomplete population weights fail closed.

The point estimate is a Hájek weighted proportion. Effective sample size is the Kish weight-inequality diagnostic `(sum(w)^2 / sum(w^2))`; it does not claim to capture dependence. Dependence is handled separately by the grouped interval.

## Dependence and confidence interval

Rows sharing an owner or observation identifier form one connected resampling group. A group that crosses strata invalidates the audit because stratified resampling would no longer preserve the sampling design. Every stratum requires at least two decisive groups.

The 95% confidence interval is a deterministic percentile bootstrap with 2,000 replicates by default. Connected owner/observation groups are sampled with replacement within each stratum. The persisted seed is a SHA-256 fingerprint, not the secret or operational seed value. Algorithm and interval method versions are stored with every snapshot.

Each snapshot retains the sampled record, inclusion probability, stratum, outcome, consensus state, and exact review/consensus fingerprints. Raw owner and observation identifiers are replaced with sampling-frame-scoped group fingerprints. A composite audit-evidence fingerprint binds the ordered manifest without enabling cross-frame owner tracking.

## Fail-closed rules

Missing strata, invalid inclusion probabilities, non-blind review, missing group identifiers, unsupported methods, insufficient groups, or incomplete population weights produce `availability: unavailable`, explicit blockers, and null estimate fields. They never produce zero-valued substitute evidence.

Model output is never an audit vote. YOLOE and BioCLIP remain unfinished and cannot influence this estimator. Quality snapshots are append-only; corrections create a new serialized revision linked to the superseded snapshot.

## Interpretation

The estimated quantity is the proportion of decisive sampled records supported by governed human evidence under the recorded sampling design. It is not species prevalence, model accuracy, or proof that every record is correct. Release still requires the separate rights, provenance, conflict, quality, expert, and authorization gates.
