# Reviewer reliability policy

Policy version: `butterflylens-reviewer-reliability-policy:v1.0.0`

Status: normative policy; estimation and consensus implementations remain
separate tasks.

## Purpose and boundary

Reliability evidence may reduce the influence of demonstrably noisy review in
a narrowly matched domain. It must not become a public ranking, a shortcut to
taxonomic truth, or a mechanism for excluding dissent. A weight describes the
uncertain evidence available for one reviewer-domain cell at one versioned
time; it does not describe a person.

## Normative rules

1. **Equal-weight start.** Every eligible reviewer begins at weight `1.0` in
   every domain. Missing, sparse, stale, or invalid evidence resolves to equal
   weight—not zero weight and not an inferred score.
2. **Minimum evidence before weighting.** A non-unit weight is prohibited
   until the exact domain cell contains at least 20 scorable control attempts,
   at least 5 positive and 5 negative controls, at least 10 independently
   overlapping items, and at least 5 overlaps with an independent adjudication.
   Sensitivity or specificity is unavailable unless its relevant class has at
   least 10 scorable controls. Thresholds apply after exclusions.
3. **Domain-specific only.** Each estimate is keyed by butterfly family, life
   stage, and visual domain. Evidence must not be silently pooled across a
   family, stage, or domain boundary. A sparse cell falls back to weight `1.0`.
4. **Shrink toward equal weight.** The versioned estimator must shrink every
   eligible estimate toward `1.0`, report its uncertainty interval, and apply
   more shrinkage to smaller or less diverse samples. Task 9.3 must publish the
   exact estimator and deterministic fixtures before any weight is used.
5. **Cap influence.** Applied weights are clamped to `[0.5, 2.0]` after
   shrinkage. No reviewer can veto or dictate consensus through weight alone.
6. **No model-derived reliability.** Agreement with BioCLIP, YOLOE, another
   classifier, a model score, or a model-generated label is never control
   truth and never contributes to reviewer reliability.
7. **No majority-as-truth shortcut.** Agreement with a majority is an
   agreement measure only. It cannot define correctness, ground truth, or a
   reliability target. Control truth requires governed evidence; conflicts
   require independent adjudication.
8. **Preserve minority dissent.** Weighting never deletes, rewrites, hides, or
   marks a review event as invalid. Consensus must retain every effective event
   fingerprint, minority count, conflict, adjudication link, method version,
   and both weighted and unweighted summaries.
9. **Keep reliability private.** Individual control attempts, estimates,
   intervals, weights, and domain cells are visible only to that reviewer and
   authorized curators/administrators for support and governance. They are not
   included in public profiles, leaderboards, exports, maps, badges, or APIs.
10. **Protect reviewer dignity.** ButterflyLens never labels a person “bad,”
    “inaccurate,” “unreliable,” or an equivalent public judgement. Private
    messages describe evidence limits and actionable training or appeal paths,
    never personal worth or intent.

## Evidence eligibility

Only append-only review events linked to an active, fingerprinted control item
or to independently adjudicated overlap may enter an estimate. The control
definition must predate the attempt, remain hidden until the attempt is
committed, match the campaign/item/image/question fingerprints, and carry a
governed evidence citation. Superseded attempts remain in the audit ledger but
only the current effective event is scored.

The estimator excludes withdrawn assignments, leaked controls, rights- or
integrity-invalid media, unmatched domains, self-adjudication, unresolved
conflicts, synthetic attempts not declared as such, and any record whose
lineage cannot be recomputed. Exclusions and unavailable metrics are reported
as explicit reason codes, not silently dropped.

## Use in consensus

Community evidence remains available as an unweighted human summary. A weight
may affect only the separately labelled qualified-consensus layer after all
minimum-evidence and independence gates pass. Release consensus still requires
its own expert, rights, provenance, conflict, quality, and authorization gates;
reviewer weight alone never authorizes publication.

Every weighted projection records the reliability snapshot fingerprint,
policy/estimator versions, evidence cutoff, applied caps, equal-weight
fallbacks, unweighted result, weighted result, and retained dissent. A later
correction creates a new snapshot and consensus revision; it never mutates the
old evidence.

## Review, correction, and appeal

Reviewers can see a plain-language private explanation of evidence counts,
uncertainty, exclusions, and domain scope, and can request correction or
appeal. A curator must resolve an appeal through append-only evidence and a
versioned decision. Suspension or moderation is governed separately and must
not be inferred automatically from a reliability estimate.

This policy must be reviewed before thresholds, domains, estimator method,
caps, visibility, or consensus use changes. Such a change requires a new
policy version; existing snapshots retain their original version.
