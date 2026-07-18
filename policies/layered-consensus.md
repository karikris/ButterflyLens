# Layered consensus policy

Policy version: `butterflylens-layered-consensus-policy:v1.0.0`

Method version: `butterflylens-layered-consensus:v1.0.0`

## Purpose

Consensus summarizes human evidence without turning a vote, reviewer weight,
provider assertion, or model output into biological truth. Every revision is
append-only and fingerprinted. Superseded review events remain in their source
ledger; every current effective event, conflict, adjudication link, and minority
dissent count remains visible in the consensus snapshot.

## Layers

1. **Community evidence** is an unweighted count of every effective human
   review. It reports support, opposition, uncertainty, media failure, deferred
   reviews, and dissent. It never consumes reviewer reliability.
2. **Qualified consensus** uses only reviewers whose qualification is governed
   outside the calculation. Missing or unavailable reliability uses equal
   weight 1. An eligible, exact-domain private reliability snapshot may alter
   the separately labelled support and opposition totals. A weighted majority
   never resolves disagreement, deletes dissent, or becomes correctness.
3. **Release consensus** never adds votes. It projects the qualified outcome
   through explicit rights, provenance, conflict-resolution, quality, expert,
   and release-authorization gates. Only a supported qualified outcome with all
   six gates may become `release_ready`. A release-ready candidate is still not
   a published occurrence.

## Conflict and adjudication

Yes/no disagreement remains unresolved regardless of raw or weighted majority.
Resolution requires an independent qualified adjudicator whose append-only
event cites every exact conflicting decisive event fingerprint. Adjudication may
resolve qualified consensus but does not rewrite the unweighted community
layer: that layer remains blocked with its source dissent retained.

`Can't tell` is uncertainty, `Can't view` is media failure, and `Skip` is
deferred. None is a decisive positive or negative. A correction may supersede
only an earlier event by the same reviewer, must not predate it, and cannot
create a cycle or multiple current events.

## Reliability boundary

Reliability must match the exact family, source provider, life stage, and visual
domain. It must be private, estimated by the versioned control-calibrated
method, blocker-free, and capped to the policy range. Missing or sparse evidence
falls back to equal weight. Model agreement and majority agreement never enter
reliability or consensus truth.

## Release and privacy

The calculated conflict state is authoritative: an external gate cannot mark
unresolved human evidence as resolved. Release-ready state additionally
requires rights, provenance, quality, expert, and authorization evidence.
Individual reliability snapshots remain private even when their composite
fingerprint is attached to qualified consensus. Public surfaces may show layer
summaries and dissent but never individual reviewer scores or rankings.
