# ButterflyLens demonstration — 2:48 production script

**Tagline:** Discover, review, and strengthen Australia’s butterfly data.
**Target runtime:** `02:48` (`168` seconds).
**Working-product footage:** `02:40` (`95.2%`).
**Capture source:** `c6037ca37871c3db819f7fd780158ef352e85e51`.
**Submitted snapshot:** `sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de`.

> Production status: scripted, captioned, and machine-validated; not recorded,
> narrated, reviewed as a final cut, or uploaded. There is no public YouTube URL
> yet. The final human-approved recording and public upload remain required.

This is the source of truth for the demonstration cut. The synchronized
[caption file](assets/video/butterflylens-demo.en-AU.srt) and
[shot manifest](assets/video/butterflylens-demo.v1.json) must travel with it.
The unavailable states are part of the product demonstration: do not replace
them with mock live activity, partial Flickr output, simulated reviews, or
invented model results.

## Recording contract

- Record the actual ButterflyLens product at the pinned source commit in a
  1920×1080, 30 fps browser viewport. Hide browser chrome only after the URL and
  Submitted badge are established.
- Block every network request except the pinned local build or public
  ButterflyLens static site. Do not open Supabase, B2, Flickr, BioMiner, worker,
  or credential screens.
- Keep the **Submitted replay** badge visible whenever practical. Never splice a
  test fixture that is unavailable in the public build into a product shot.
- Use a human narrator speaking clear Australian English. Mix narration clearly
  above any optional, licence-cleared music; music is not required. Burn in or
  attach the supplied English captions.
- Record only the integrity-checked local review fixture. Do not show the active
  Flickr fetch, private imagery, reviewer identities, exact sensitive
  coordinates, credentials, or unfinished YOLOE/BioCLIP outputs.
- End at `02:48`; do not pad the cut. At least two-thirds must show working
  product. This script allocates `160/168` seconds to the product.

## Timecoded sequence and narration

### 1. `00:00–00:18` — ALA baseline

**Product action:** Open the public replay at `#live`. Start wide enough to show
the ButterflyLens name and Submitted replay badge, then frame **Committed map**,
**Submitted Australian butterfly catalogue**, **463 species**, and
**Occurrence layer withheld**.

**Narration:**

> ButterflyLens brings Australia’s rebuilt ALA baseline into one inspectable
> evidence workspace. The catalogue has 463 accepted butterfly species. The
> public occurrence layer stays withheld while provider rights remain
> unresolved—that boundary is intentional.

**Claim source:** canonical Submitted snapshot, operations projection, and
accepted taxonomy catalogue at the pinned source commit. The 463 count is a
taxonomy count, not a public ALA occurrence total.

### 2. `00:18–00:34` — Flickr live stream

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

**Product action:** Return to `#live` and frame **Pipeline observatory**,
**Worker status unavailable**, and **YOLOE unfinished · BioCLIP unfinished**.

**Narration:**

> Governed candidates are designed to flow through the M5 pipeline. Today no
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

### 5. `01:12–01:27` — Map update

**Product action:** Show **Current contribution**, then return to `#live`. Frame
**Worker-independent evidence** and **No committed live replacement is
attached**.

**Narration:**

> The map does not change from one local draft. A public update needs
> independent review, rights and sensitivity checks, and a fingerprinted
> committed artifact. Until then, the worker-independent Submitted map remains
> current.

**Truth card:** `Draft review ≠ stored evidence ≠ map release`.

### 6. `01:27–01:43` — Repeated reviewers

**Product action:** Open `#contributors`. Frame **Contributor evidence
unavailable** and the explanation that no authenticated contribution snapshot
is attached.

**Narration:**

> Stronger evidence requires repeated, independent reviewers and an explicit
> consensus policy. This replay contains no stored community review or reviewer
> identity. Unavailable contributor totals stay unavailable; agreement with a
> model or majority is never treated as truth.

### 7. `01:43–01:59` — Quality interval

**Product action:** Open `#quality`. Pan across **Precision unavailable** and
**Agreement unavailable**, then show **2,906 valid decodes** and **0
human-verified species**. Expand **Evidence, method, and provenance**.

**Narration:**

> Quality needs a representative audit, not a convenient sample. No such sample
> exists yet, so precision and its interval are unavailable—not zero. The 2,906
> valid decodes are reference diagnostics, and zero species are human-verified
> in this snapshot.

### 8. `01:59–02:20` — GPT-5.6 analysis

**Product action:** Open `#ask-butterflylens`, choose **Which species should
receive the next reference review?**, and replay. Show the three-species queue,
artifact citations, stored tool trace, and **Model not invoked** footer.

**Narration:**

> GPT-5.6 is the bounded live analyst target: it can explain deterministic
> evidence through read-only tools, never identify from memory. For judging,
> this stored replay names the next reference-review queue and preserves exact
> citations and tool output. The footer proves no model ran here.

**Truth card:** the queue starts *Hypochrysops sandrae*, *Lacturnea lacturnus*,
then *Charaxes andrewsi*. It is workflow priority, not a rarity or distribution
claim.

### 9. `02:20–02:31` — Geographic impact

**Product action:** Return to `#live`. Trace the Australia scope, then hold on
**Occurrence layer withheld** and the unavailable geographic-impact values.

**Narration:**

> Geographic impact will compare reviewed imagery with the ALA baseline at safe
> resolution. No selectable impact cell is released yet. Withheld coverage does
> not mean biological absence.

### 10. `02:31–02:40` — Evidence export

**Product action:** Scroll to `#about`; point to **Occurrence release** and
**Darwin Core export** without leaving the product.

**Narration:**

> Export is governed too. ButterflyLens exposes the release contract, not a
> pretend download. Unreviewed Flickr candidates can never enter the final
> occurrence archive.

### 11. `02:40–02:48` — Codex provenance

**Product action:** Cut once to a clean end card listing the exact source commit,
snapshot fingerprint, test receipt, GPT-5.6 role, and Codex role. No marketing
claim may obscure the identifiers.

**Narration:**

> Codex built and tested the product and its provenance. It supplied no
> butterfly identity, community vote, or scientific ground truth.

## End card copy

```text
ButterflyLens
Discover, review, and strengthen Australia’s butterfly data.

Submitted source  c6037ca37871c3db819f7fd780158ef352e85e51
Snapshot          sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de
GPT-5.6           bounded live evidence analyst target; model-free Submitted replay
Codex             product, contracts, tests, documentation, and provenance

Search results are hypotheses—not biodiversity records.
```

## Recording and publication checklist

Before recording:

- verify the checked-out source is exactly the manifest commit;
- run `npm ci`, the production build, and the focused video validator;
- turn off notifications, password managers, browser autofill, and recording
  overlays that can disclose private information;
- rehearse every click against the supplied timestamps;
- confirm the review fixture attribution and integrity check are visible.

Before publication:

- confirm the final runtime is between `02:45` and `02:50` and under three
  minutes;
- confirm working product occupies at least `01:52`; this plan requires
  `02:40`;
- listen on speakers and headphones, check caption timing, and inspect the
  1080p upload rather than only the local master;
- have Kris Kari approve the scientific wording, rights/privacy framing,
  product state, audio, captions, and public upload;
- publish to public YouTube and replace the null URL in the shot manifest only
  in a later, separately verified commit.

## Hard stops

Stop the recording or edit if any shot shows a credential, private worker
observation, partial Flickr output, unapproved media, exact sensitive location,
invented community activity, simulated model result, or a value that differs
from the pinned artifact. Do not label the script, captions, a silent screen
capture, or an unlisted upload as the completed public video.
