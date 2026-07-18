# ButterflyLens judge guide

**Judged mode:** Submitted replay · **current worker:** unavailable ·
**measured result:** 463 accepted Australian butterfly species.

[Open the public replay](https://karikris.github.io/ButterflyLens/) ·
[Open the Australia map](https://karikris.github.io/ButterflyLens/#live) ·
[Help verify](https://karikris.github.io/ButterflyLens/#verify)

The primary route needs no login, private key, Supabase or B2 account, GPU,
model download, or M5 availability. Refreshing the page resets the local review
draft and analyst answer. Search results remain hypotheses—not biodiversity
records.

## The 90-second route

The unavailable results below are expected fail-closed evidence, not demo
failures. Do not substitute the separately active Flickr fetch or an uncommitted
worker observation.

| Step | Time | Action | Expected evidence |
| ---: | :--- | --- | --- |
| 1 | 0:00–0:10 | **View the Australia map.** Open [Live](https://karikris.github.io/ButterflyLens/#live) and find **Committed map**. | Australia scope and map shell load. **Occurrence layer withheld** remains visible; the committed catalogue shows 463 species. |
| 2 | 0:10–0:20 | **Compare ALA and Flickr.** Open [Ask ButterflyLens](https://karikris.github.io/ButterflyLens/#ask-butterflylens), choose “Can ALA and Flickr counts be compared yet?”, then replay it. | The stored trace says the national ALA count is withheld, no immutable Flickr count is attached, and the difference is unavailable—not zero. |
| 3 | 0:20–0:30 | **Attempt to open a potential coverage-gap cell.** Return to the [map](https://karikris.github.io/ButterflyLens/#live) and inspect the scope card. | No selectable cell is exposed in Submitted mode. This is the correct rights-safe result while occurrence and cell counts are withheld; it does not imply biological absence. |
| 4 | 0:30–0:45 | **Review a butterfly image.** Open [Verify](https://karikris.github.io/ButterflyLens/#verify), choose **Can’t tell** when the image cannot support a stronger decision, then lock the draft to reveal permitted context. | The decision is blind, the integrity-checked CC BY-SA 4.0 fixture is visible, and the interface labels the decision **Draft only**. Nothing is submitted. |
| 5 | 0:45–0:55 | **Watch community evidence update.** Observe **Current contribution** change to the selected draft, then open [Contributors](https://karikris.github.io/ButterflyLens/#contributors). | Only local draft state changes. The authenticated contribution snapshot and all stored community totals remain unavailable; no consensus or occurrence is fabricated. |
| 6 | 0:55–1:05 | **Inspect quality.** Open [Quality](https://karikris.github.io/ButterflyLens/#quality). | Reviewed sample 0 and decisive reviews 0 are workflow counts, not 0% precision. Precision and agreement remain unavailable. Reference diagnostics show 463 accepted species, 2,906 valid decodes, and 0 human-verified species. |
| 7 | 1:05–1:20 | **Ask the GPT-5.6 evidence route what is missing.** Choose “Which species should receive the next reference review?” and replay it. | The deterministic gap queue names *Hypochrysops sandrae*, *Lacturnea lacturnus*, then *Charaxes andrewsi*. The footer says **Model not invoked**; this is targeted workflow order, not rarity or distribution. |
| 8 | 1:20–1:30 | **Inspect the live M5 worker.** Return to [Live](https://karikris.github.io/ButterflyLens/#live) and open operational monitoring. | **Worker status unavailable**, heartbeat unavailable, stage/queue/resource values unavailable, and YOLOE/BioCLIP unfinished. The site and Submitted artifacts remain usable. |

## What the judge should conclude

- The product works without mutable infrastructure and never turns missing
  evidence into a favourable metric.
- A Flickr hit would enter as a discovery candidate, not an occurrence.
- ALA is authoritative baseline occurrence evidence for this build, not complete
  ground truth; non-detection cannot prove absence.
- Machine screening may prioritize work, while independent human evidence and
  explicit release receipts govern stronger claims.
- GPT-5.6 is the bounded live evidence-analyst target. The Submitted judge path
  is a stored, fingerprinted, model-free replay.
- Codex built and verified the application, contracts, tests, documentation, and
  provenance; it does not supply butterfly identities or community votes.

## Expected Submitted state

| Surface | Expected value | Evidence boundary |
| --- | --- | --- |
| Canonical snapshot | `sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de` | Immutable Task 16.1 freeze sourced from commit `0e07f175fa07650e90606ca07b2286807010f1de`. |
| Australian catalogue | 463 accepted species · fingerprint `083ed290418938e1c32ee75cad5dea6d81153f529ab1c40acbb64f52beccba06` | Accepted taxonomy and source assertions; no occurrence or identity claim. |
| ALA internal inventory | 236,897 selected rows · 230,027 spatially eligible · 23,744 aggregate rows | Audit inventory only. Public occurrence and cell counts remain null. |
| Flickr plan | 1,876 query definitions · 1,754 deduplicated physical requests | Deterministic and `planned_not_sent` by the freeze. No active-fetch output is included. |
| Public Flickr display | 0 photos displayed | A workflow count caused by the blocked public display gate, not proof that Flickr has no butterfly photos. |
| Review | local draft only · 0 stored reviews · 0 decisive reviews | The demo does not write community evidence or claim consensus. |
| Quality | precision, confidence interval, agreement, and species quality unavailable | Reference coverage diagnostics are not representative quality estimates. |
| Worker | no ID · no heartbeat · no committed live replacement | Unavailable is not offline, failed, or zero; liveness was not observed. |
| Models | YOLOE blocked/not executed · BioCLIP skipped/unfinished | No revisions, weight fingerprints, scores, probabilities, or detections are claimed. |
| Analyst | three exact stored questions · model calls 0 · network calls 0 | Every answer retains exact tool output, citations, trace, and replay label. |

## Submitted versus Live

| Concern | Submitted replay now | Governed Live eligibility |
| --- | --- | --- |
| Source of truth | Bundled Git- and SHA-256-pinned artifacts | An authenticated observation may select only an explicitly committed live artifact. |
| Site availability | Worker-independent GitHub Pages build | Live status enhances the site but never gates it. |
| Map | Australia scope only; occurrence layer and counts withheld | A generalized cell becomes selectable only with rights, sensitivity, artifact, and release receipts. |
| Flickr | Unsent plan and blocked display surface | Only fully received, deduplicated, rights-eligible candidates may be displayed; they still are not occurrences. |
| Community | Local demo draft; writes blocked | Authenticated append-only reviews, independent overlap, privacy policy acceptance, and release gates are required. |
| GPT-5.6 | Stored tool trace; no model or network call | A server-side authenticated Responses run must use strict read-only tools and preserve exact citations. |
| M5 | No heartbeat, identity, batch, model fingerprint, or resource snapshot | A fresh authenticated heartbeat, worker identity, model revisions, committed batch, and recovery receipt must all validate. |
| Failure behaviour | Submitted artifacts remain queryable | A stale, malformed, or unavailable live observation falls back to Submitted. |

## Optional live-worker path

Do this only if the **Live** dashboard itself proves all prerequisites. Do not
infer them from a running process, a screenshot, the external Flickr fetch, or
operator commentary.

1. Confirm the UI says **Live snapshot**, not Submitted fallback.
2. Verify a fresh heartbeat timestamp and worker state appear together.
3. Open the worker identity and confirm its contract fingerprint, exact source
   commit, and committed artifact reference.
4. Confirm model IDs, revisions, and weight fingerprints are present before
   interpreting a stage as model-backed. For this goal, YOLOE and BioCLIP remain
   unfinished, so this prerequisite currently fails.
5. Inspect the first committed batch, queue/failure values, and recovery receipt.
   Unavailable values must remain unavailable rather than becoming zero.
6. Return to Submitted and confirm the public site, review fixture, catalogue,
   analyst replay, and export documentation still work without the worker.

Current result: stop at step 1. No authenticated live snapshot or M5 heartbeat
is attached.

## Technical route

This route verifies the evidence chain rather than repeating the visual tour.

1. Inspect the [canonical Submitted snapshot](data/submission/v1/submitted_snapshot.json)
   and recompute it:

   ```bash
   .venv/bin/python scripts/freeze_submitted_snapshot.py --check
   ```

2. Inspect the [analyst artifact registry](packages/openai/submitted-artifacts.v1.json).
   It cites commit `f9b96814f335684cf311b70b622e2cade0188b9b`;
   the repository reads the exact Git objects at that commit so later
   working-tree metadata cannot mutate the Submitted analyst view.
3. Run the guide, replay, and immutable-artifact checks:

   ```bash
   PYTHONPATH=packages/contracts/python:packages/openai/python \
     .venv/bin/python -m unittest \
       tests.test_judge_guide \
       tests.test_submitted_snapshot_freeze \
       tests.test_openai_replay
   ```

4. In the analyst result, expand **Artifact citations** and **Stored tool trace**.
   Confirm the commit, SHA-256, bounded arguments, result fingerprint, and
   “Model not invoked” footer.
5. In Quality, expand **Evidence, method, and provenance**. Confirm targeted
   failure discovery is separate from representative estimation and model votes
   are excluded.
6. In Species, expand **Species-page evidence and provenance**. Confirm the
   ButterflyLens key, reference-evidence fingerprint, catalogue fingerprint,
   ALA snapshot, and authoritative rebuilt baseline.

## Rights, privacy, and provenance

- ALA display and downstream release remain blocked pending exact rights review
  for dataset UIDs `dr1097`, `dr30019`, and `dr635`, covering 16,753 selected
  rows. Internal inventory counts do not grant publication permission.
- The review fixture retains Wikimedia Commons source attribution and CC BY-SA
  4.0 terms. Its use does not verify the pictured taxon.
- Flickr display requires source, photographer, licence, cache, privacy,
  attribution, and removal evidence. The active parallel fetch is not public
  evidence and is not inspected by the replay.
- Exact sensitive locations are not exposed. Unknown or missing sensitivity
  evidence fails closed.
- Community writes remain blocked until the prelaunch privacy and security
  prerequisites close. The demo stores no identity, review, or contribution.
- Start from the [Task 16.1 freeze report](provenance/task_reports/butterflylens-16.1.md),
  [Task 17.1 competition README report](provenance/task_reports/butterflylens-17.1.md),
  [data-rights audit](DATA_RIGHTS.md), and [release security review](SECURITY_RELEASE_REVIEW.md).

## Current limitations

- No public occurrence layer or selectable coverage-gap cell is released.
- No completed immutable Flickr candidate dataset is attached.
- No stored community review, consensus, representative audit, or quality
  estimate exists.
- No live GPT-5.6 evaluation is claimed; Submitted answers are stored replays.
- No authenticated M5 worker ID, heartbeat, model fingerprint, first committed
  batch, queue, resource observation, or recovery receipt is attached.
- YOLOE and BioCLIP remain explicitly unfinished for this goal.
- Community/data release remains blocked by privacy, rights, and unfinished-model
  prerequisites even though the static Submitted replay is verified.
