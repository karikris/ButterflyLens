# ButterflyLens demonstration — 2:48 production script

**Tagline:** Discover, review, and strengthen Australia’s butterfly data.
**Target runtime:** `02:48` (`168` seconds).
**Working-product footage:** `02:40` (`95.2%`).
**Capture source:** `45fb5ac07dcd51852c9e92217667f3f5052868fe`.
**Submitted snapshot:** `sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de`.
**Submitted map:** `sha256:d39a73ae0b41677a2e557c89a72237d90d0e1e6cd2019cfbf091b41e85bae446`.

> Production status: scripted, captioned, and machine-validated; not recorded,
> narrated, reviewed as a final cut, or uploaded. There is no public YouTube URL
> yet. The final human-approved recording and public upload remain required.

This is the source of truth for the second demonstration cut. The synchronized
[v2 caption file](assets/video/butterflylens-demo.v2.en-AU.srt) and
[v2 shot manifest](assets/video/butterflylens-demo.v2.json) must travel with it.
The [v1 manifest](assets/video/butterflylens-demo.v1.json) and its caption file
remain unchanged as the historical pre-map packet.

Unavailable states are part of the product demonstration. Do not replace them
with mock live activity, partial Flickr output, simulated reviews, invented
model results, or unfinished YOLOE/BioCLIP output.

## Recording contract

- Record the actual ButterflyLens product at the pinned source commit from a
  local production build in a 1920×1080, 30 fps browser viewport. Establish the
  local URL and Submitted badge before hiding browser chrome.
- Block every request except the pinned local build. Do not open Supabase, B2,
  Flickr, BioMiner, worker, or credential screens.
- Keep the **Submitted** mode visible whenever practical. Never splice a test
  fixture that is unavailable in the pinned public build into a product shot.
- Use a human narrator speaking clear Australian English. Mix narration clearly
  above optional licence-cleared music; music is not required. Burn in or attach
  the supplied English captions.
- Record only the integrity-checked local review fixture. Do not show the active
  Flickr fetch, private imagery, reviewer identities, exact sensitive
  coordinates, credentials, or unfinished YOLOE/BioCLIP outputs.
- End at `02:48`; do not pad the cut. This script allocates `160/168` seconds to
  the working product.

## Timecoded sequence and narration

### 1. `00:00–00:18` — ALA baseline

**Product action:** Open `#live`. Frame **Rights-screened submitted map**,
**213,310** map-eligible baseline rows, **630** H3 cells, the blue aggregate
heatmap, and **Public projection, not complete truth**.

**Narration:**

> ButterflyLens starts with the authoritative rebuilt ALA baseline: 236,897
> selected occurrence-evidence rows. The Submitted public map conservatively
> exposes 213,310 map-eligible rows across 630 blue H3 cells after excluding
> three flagged datasets. It is a selected baseline, not complete biological
> truth.

**Claim source:** the canonical Submitted snapshot and rights-screened map at
the pinned source commit. The map projection is narrower than the authoritative
baseline, does not publish raw coordinates, and is not a legal conclusion.

### 2. `00:18–00:34` — Flickr candidate stream

**Product action:** Scroll to `#flickr-display-policy`. Hold on **0 Flickr photos
displayed**, **Display remains blocked**, and the notice that active partial
outputs are not public evidence.

**Narration:**

> Flickr is the live discovery stream, not a biodiversity record. This
> Submitted replay contains the deterministic request plan, but no completed,
> immutable Flickr result. The active external fetch and its partial outputs are
> never substituted into the demo.

**Truth card:** `Discovery candidate ≠ occurrence`. Do not display the
operator-reported partial photo count; it is not a fingerprinted public
artifact.

### 3. `00:34–00:48` — M5 pipeline

**Product action:** Open `#operations` and frame **Pipeline observatory**,
**Worker status unavailable**, and **YOLOE unfinished · BioCLIP unfinished**.

**Narration:**

> Governed candidates are designed to flow through the M5 pipeline. No
> authenticated heartbeat, committed batch, or model fingerprint is attached.
> YOLOE and BioCLIP remain unfinished, so the dashboard says unavailable instead
> of inventing progress.

**Truth card:** `Unavailable ≠ offline, failed, or zero`.

### 4. `00:48–01:12` — Butterfly verification

**Product action:** Open `#verify`. Show the blind-review notice, inspect the
rights-cleared local fixture, choose **Can’t tell**, lock the draft, and reveal
permitted source context. Keep **Draft only** visible.

**Narration:**

> Community expertise enters through blind review. Without enough visible
> evidence, I choose “Can’t tell” rather than force an identity. Only after the
> draft is locked do source details appear. This changes local demo state; it
> submits nothing and verifies no species.

**Interaction note:** use a deliberate pointer pace and leave the outcome
visible for two seconds before revealing context.

### 5. `01:12–01:27` — Map update boundary

**Product action:** Show **Current contribution**, then return to `#live`.
Select **H3 coarse cells**, filter `838c23fffffffff`, and frame **224** ALA
baseline records, the full evidence fingerprint, and the coordinate-free
provider-record sample.

**Narration:**

> One local draft cannot update this map. H3 cell 838c23fffffffff links 224 ALA
> baseline rows to a fingerprint and coordinate-free source sample. A future
> Flickr or review layer needs its own committed, rights-cleared evidence.

**Truth card:** `Draft review ≠ stored evidence ≠ map release`.

### 6. `01:27–01:43` — Repeated reviewers

**Product action:** Open `#contributors`. Frame **Contribution snapshot
unavailable**, **No contribution totals are claimed**, and **Evidence, not
speed**.

**Narration:**

> Stronger evidence requires repeated, independent reviewers and an explicit
> consensus policy. This replay contains no stored community review or reviewer
> identity. Contributor totals stay unavailable; agreement with a model or a
> majority is never treated as truth.

### 7. `01:43–01:59` — Quality interval

**Product action:** Open `#quality`. Pan across **Precision estimate —
Unavailable** and **Reviewer agreement — Unavailable**, then show **2,906**
valid decoded images and **0** human-verified species. Expand **Evidence,
method, and provenance**.

**Narration:**

> Quality needs a representative audit, not a convenient sample. No such sample
> exists yet, so precision and its interval are unavailable—not zero. The 2,906
> valid decodes are reference diagnostics, and zero species are human-verified
> in this snapshot.

### 8. `01:59–02:20` — Bounded model analysis

**Product action:** Open the local submitted replay artifact view (submitted
replay is model-free and detached from live routes), choose **Can ALA and Flickr
counts be compared yet?**, and replay. Show the 213,310-row cited ALA claim,
the unavailable Flickr count and difference, stored tool trace, artifact
citations, and **Model not invoked** footer.

**Narration:**

> Bounded model is the bounded live analyst target: it can explain deterministic
> evidence through read-only tools, never identify from memory. The model-free
> Submitted replay cites the ALA aggregate, refuses a Flickr difference without
> evidence, and preserves its tool trace. The footer proves no model ran here.

### 9. `02:20–02:31` — Geographic impact

**Product action:** Return to `#live`. Move through **State / territory**,
**IBRA v7**, **LGA approximation**, and **H3 coarse cells**; finish on **Flickr
candidates — Unavailable—not zero**.

**Narration:**

> The Submitted map drills from national ALA evidence into state, IBRA, LGA,
> and H3 counts. Cross-source geographic impact remains unavailable until an
> immutable Flickr layer arrives; missing coverage is not biological absence.

### 10. `02:31–02:40` — Evidence export

**Product action:** Scroll to the footer; point to **Occurrence release** and
**Darwin Core export** without leaving the product.

**Narration:**

> Export is governed too. ButterflyLens exposes the release contract, not a
> pretend download. Unreviewed Flickr candidates can never enter the final
> occurrence archive.

### 11. `02:40–02:48` — Codex provenance

**Product action:** Cut once to a clean end card listing the exact source
commit, both snapshot fingerprints, Bounded model role, and Codex role. Do not obscure
the identifiers.

**Narration:**

> Codex built and tested the product and its provenance. It supplied no
> butterfly identity, community vote, or scientific ground truth.

## End card copy

```text
ButterflyLens
Discover, review, and strengthen Australia’s butterfly data.

Submitted source  45fb5ac07dcd51852c9e92217667f3f5052868fe
Snapshot          sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de
Map               sha256:d39a73ae0b41677a2e557c89a72237d90d0e1e6cd2019cfbf091b41e85bae446
Bounded model           bounded live evidence analyst target; model-free Submitted replay
Codex             product, contracts, tests, documentation, and provenance

Search results are hypotheses—not biodiversity records.
```

## Recording and publication checklist

Before recording:

- verify the checked-out source is exactly the manifest commit;
- run `npm ci`, the production build, and
  `uv run python -m unittest tests.test_demo_video -v`;
- capture from the local production server with all non-local requests blocked;
- turn off notifications, password managers, browser autofill, and recording
  overlays that can disclose private information;
- rehearse every click against the supplied timestamps; and
- confirm the review fixture attribution and integrity check are visible.

Before publication:

- confirm the final runtime is between `02:45` and `02:50` and under three
  minutes;
- confirm working product occupies at least `01:52`; this plan requires
  `02:40`;
- listen on speakers and headphones, check caption timing, and inspect the
  1080p upload rather than only the local master;
- have Kris Kari approve the scientific wording, rights/privacy framing,
  product state, audio, captions, and public upload; and
- publish to public YouTube and replace the null URL in the v2 manifest only in
  a later, separately verified commit.

## Hard stops

Stop the recording or edit if any shot shows a credential, private worker
observation, partial Flickr output, unapproved media, exact sensitive location,
invented community activity, simulated model result, or a value that differs
from the pinned artifact. Do not label the script, captions, a silent screen
capture, or an unlisted upload as the completed public video.
