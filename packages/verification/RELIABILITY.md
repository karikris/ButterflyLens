# Reviewer reliability estimator

`butterflylens-reliability-estimator:v1.0.0` implements the private reliability
policy in `policies/reviewer-reliability.md`. It accepts only governed human
control outcomes, independent reviewer overlaps, and exact adjudication lineage
for one family × source provider × life stage × visual-domain cell. Model output
and majority agreement are never truth inputs.

## Metrics

- Control accuracy is correct governed controls divided by all governed controls.
- Sensitivity and specificity are reported only when the relevant positive or
  negative class has at least 10 controls.
- Pairwise agreement is the target reviewer's agreement with every independent
  peer rating divided by the number of those reviewer-peer pairs.
- Nominal Krippendorff alpha uses all reviewer labels on each overlap item and
  the standard observed-versus-expected disagreement calculation. It is absent
  when fewer than two overlapping items or no label variation make it undefined.
- Adjudicated overlap is agreement between the target reviewer and an independent
  adjudicator over items whose adjudication cites every exact source event.

Controls and overlap items must be disjoint. Duplicate item identifiers,
duplicate control or event fingerprints (including reuse across items), unknown
control kinds or response labels, control-kind/answer mismatches, self-review,
repeated peers, non-independent adjudicators, and incomplete adjudication
lineage fail closed.

## Estimate and uncertainty

The evidence gate requires at least 20 controls, including 5 positive and 5
negative controls, 10 independent overlap items, and 5 adjudicated overlaps. If
any threshold fails, the estimate and interval remain unavailable and storage
preserves the equal weight of 1 with explicit blockers.

For eligible evidence, let `s` be correct controls plus adjudicator agreements
and let `n` be controls plus adjudicated overlaps. The estimator uses the
predeclared prior `Beta(15, 5)`:

```text
posterior = Beta(15 + s, 5 + n - s)
estimate = (15 + s) / (20 + n)
shrinkage_fraction = 20 / (20 + n)
```

The 95% uncertainty interval is the posterior mean plus or minus 1.95996
posterior standard deviations, clipped to `[0, 1]`. Accuracy maps monotonically
to the operational weight by `1 + (accuracy - 0.75) / 0.25`, capped to
`[0.5, 2]`. The same transform maps interval bounds before database admission.

Canonical RFC 8785 JSON is SHA-256 fingerprinted after stable input sorting.
The database stores private, append-only, monotonically superseding snapshots;
reviewers may see their own estimate and authorized curators may govern it, but
public ranking and scientific claims remain prohibited.
