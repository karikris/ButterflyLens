# ButterflyLens 6.5 — species-progress scheduler

Status: **deferred; overlapping BioMiner work is active**.

BioMiner advanced to `00f987f6f23acba7135b0b349412a2e7248e933f` while this
task was reached. Its new global/local reference-pooling baseline and current
pooling audit files/tests were modified during the current work window. Those
artifacts directly affect reference readiness and compute-cost inputs.

Per user direction, the active overlap was acknowledged and left untouched.
No BioMiner source or data was copied. The species-progress scheduler was not
implemented, and its candidate-backlog, reference-readiness, ALA-gap, expected
map-impact, review-capacity, statistical-shortfall, and compute-cost selection
remain unfinished.

The existing discovery scheduler still verifies the relevant fail-closed
principle: unavailable model-derived inputs are missing, not zero. The rebuilt
ButterflyLens ALA baseline remains authoritative. No model or Flickr API call
occurred. Work advances to Task 7.1.
