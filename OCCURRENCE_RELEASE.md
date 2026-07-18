# ButterflyLens occurrence release policy

Policy version: `butterflylens-occurrence-release:v1.0.0`

Last reviewed: 18 July 2026

## Meaning of release-ready

A **release-ready occurrence candidate** has passed every gate below with exact
fingerprinted evidence. It is still not a published occurrence, an ALA record,
or proof that a butterfly was present or absent. Publication and provider
submission are later, separately authorised actions.

Missing, stale, unverifiable, unrelated, or unknown evidence blocks release.
Machine scores, provider labels, query terms, geography, and majority vote
cannot substitute for a required human or evidence gate.

## Required gates

Every release-ready candidate requires:

1. **Human-supported identity.** The latest append-only community evidence for
   the exact campaign, media object, and taxon supports the identity. Provider
   assertion and machine screening are not human support.
2. **Qualified consensus.** The latest qualified layer supports the identity.
   Disagreement or uncertainty remains blocked until exact independent
   adjudication is incorporated; weighting alone cannot resolve conflict.
3. **Expert review when configured.** A configured expert gate requires a
   current positive review by an active, verified expert, curator, or
   administrator. An unconfigured expert gate passes only as not applicable,
   not as a claim that expert review occurred.
4. **Coordinate and date validity.** The occurrence date is present and valid,
   and the public cell matches a validated sensitive-location receipt. No raw
   or more precise coordinate is authorized by this gate.
5. **Duplicate independence.** A fingerprinted assessment shows that the
   evidence is independent or that the configured duplicate grouping and
   statistical treatment prevents duplicate support.
6. **Rights and provenance.** The exact media and candidate rights lineage is
   allowed, no removal request applies, all provider terms and attribution are
   preserved, and unknown is blocking.
7. **Quality threshold.** A blind representative audit—not targeted failure
   discovery—produces an allowed population estimate and passes the versioned
   release threshold with its exact snapshot and threshold fingerprints.
8. **No unresolved conflict.** Every recorded conflict for the exact campaign
   and media object has an independent adjudication event. Minority evidence
   remains retained.
9. **Complete evidence packet.** The candidate has an immutable packet
   fingerprint covering the evidence required to explain and reproduce its
   release assessment.

The database validates these relationships and stores an immutable receipt.
The anonymous release projection additionally requires the current sensitive-
location receipt and absence of a media takedown. A nominally approved or
exported row without all three controls remains invisible.

## Current project boundary

The repository currently contains no release receipt and claims no new
published occurrence. The rebuilt ButterflyLens ALA baseline remains baseline
occurrence evidence; it is not converted into human verification. BioMiner's
active GBIF and Flickr work is not admitted until an immutable governed handoff
exists. YOLOE and BioCLIP remain unfinished in this goal and cannot contribute
a release claim.
