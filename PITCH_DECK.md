# ButterflyLens competition deck

**Format:** 10 slides · 16:9 · evidence-first · use only real product captures.

**Design direction:** deep eucalyptus green, warm paper, restrained amber for
caution, and the product's existing type and evidence badges. Prefer a clean
browser crop or the repository's real map GIF over decorative butterfly
imagery. Every number shown on a slide must retain the source note below.

## Slide 1 — Look closer

### On slide

# ButterflyLens

**Discover, review, and strengthen Australia’s butterfly data.**

> “ButterflyLens brings machine screening, community expertise, and Australia’s
> national biodiversity evidence together to reveal where public imagery could
> strengthen butterfly knowledge.”

`Work and Productivity` · [Open the working Submitted replay](https://karikris.github.io/ButterflyLens/)

### Speaker note

ButterflyLens is an evidence workspace for finding where public imagery could
strengthen Australian butterfly knowledge—without turning a search result into
a biodiversity record. The winning line describes the governed end-to-end
product thesis; the current Submitted snapshot keeps machine screening and live
data stages explicitly unfinished.

### Visual and proof

Use the real `assets/readme/butterflylens-live-map.gif` beside the title. Do not
add a generated butterfly or third-party photo.

## Slide 2 — The evidence gap is a workflow problem

### On slide

- ALA provides the authoritative occurrence-evidence baseline for this build,
  but not complete biological ground truth.
- Public imagery can reveal candidate evidence that deserves a closer look.
- Search labels, comments, geography, and model scores cannot verify a species.
- The missing layer is a productive path from **discovery → review → quality →
  release**.

**Search results are hypotheses—not biodiversity records.**

### Speaker note

The opportunity is not to fill a map with internet photos. It is to make the
work of checking evidence legible, repeatable, and safe. A missing ALA record
does not prove biological absence, and a Flickr hit does not prove occurrence.

### Visual and proof

Use a four-stage horizontal flow with an explicit gate between every stage.
Avoid a heat map implying released occurrence or absence data.

## Slide 3 — One workspace, one inspectable journey

### On slide

1. Explore the Australian baseline and committed map state.
2. Discover Flickr candidates behind a rights-aware display gate.
3. Route eligible imagery through optional M5 screening.
4. Review an image blind; choose uncertainty when evidence is weak.
5. Require repeated, independent review before stronger claims.
6. Inspect representative quality and geographic impact.
7. Ask GPT-5.6 to explain what the artifacts support.
8. Export only reviewed, rights-cleared occurrence evidence.

[Follow the 90-second judge route](JUDGE_GUIDE.md)

### Speaker note

The interface brings the entire evidence journey together. The Submitted replay
works without credentials or mutable infrastructure and shows unavailable
stages as unavailable rather than quietly converting them to zero.

### Visual and proof

Use eight compact frames from the actual public product. Keep the **Submitted
replay** badge in the first and last frame.

## Slide 4 — The working product fails closed

### On slide

| Product surface | Submitted evidence now |
| --- | --- |
| Australian catalogue | **463 accepted species** |
| Map | Australia scope; occurrence layer withheld |
| Review | Rights-checked fixture; local draft only |
| Quality | Diagnostics visible; representative estimates unavailable |
| Analyst | Three stored evidence replays; model calls **0** |
| Worker | Status and heartbeat unavailable |

**No login · no private key · no GPU · no M5 dependency**

### Speaker note

This is not a mock. Judges can open the public product, make a local blind-review
draft, inspect the immutable catalogue and map boundary, expand quality
provenance, and replay exact cited analyst traces. The product remains useful
when every live dependency is absent.

### Visual and proof

Capture the public product at Submitted source
`c6037ca37871c3db819f7fd780158ef352e85e51` or a later verified commit that has
not changed the cited values. Source: canonical snapshot fingerprint
`sha256:27a256934a1ac1a9fb0d27b75a0fe805bf12224df42d7e6b7d235991d26fb9de`.

## Slide 5 — Architecture: evidence before inference

### On slide

```text
Authoritative rebuilt ALA baseline ─┐
                                   ├─ fingerprinted evidence contracts
Flickr discovery candidates ───────┘              │
                                                  ├─ optional M5 screening
                                                  ├─ blind independent review
                                                  ├─ quality + geographic impact
                                                  └─ governed export

GPT-5.6 ─ read-only evidence explanation
Codex   ─ product + contracts + tests + provenance
```

**GitHub Pages:** immutable worker-independent replay
**Supabase/B2:** governed live boundaries; not required for judging
**BioMiner:** scientific evidence engine; only immutable handoffs are eligible

### Speaker note

Every layer preserves source, licence, fingerprint, uncertainty, and release
state. The M5 worker is optional compute, never the web server or sole source of
truth. Partial BioMiner or Flickr activity cannot cross into the public product
without a complete immutable handoff.

### Visual and proof

Use the architecture exactly as drawn. Do not show Supabase, B2, BioMiner, or
the M5 as currently supplying live public data.

## Slide 6 — Community expertise earns stronger claims

### On slide

**Blind first**

- Hide source comments, query terms, peer decisions, and model output.
- Let reviewers say Skip, Can’t view, or Can’t tell.

**Independent and repeated**

- Separate repeated reviewers, qualified review, conflict, and adjudication.
- Never score reviewer reliability from model or majority agreement alone.

**Representative quality**

- Keep targeted failure discovery separate from representative audit samples.
- Publish an interval only when the versioned estimator has eligible evidence.

### Speaker note

Community review is not a gamified vote. ButterflyLens is designed to preserve
independence, uncertainty, and conflict so the product can say how much evidence
exists without pretending that consensus is truth.

### Visual and proof

Use the actual blind-review and Quality surfaces. The current replay contains no
stored reviews, consensus, reviewer reliability, or representative interval.

## Slide 7 — GPT-5.6 explains; Codex makes the system inspectable

### On slide

| GPT-5.6 live target | Codex Build Week role |
| --- | --- |
| Strict read-only evidence tools | Product architecture and implementation |
| Claims bound to current tool output | Versioned schemas and fail-closed contracts |
| Exact artifact citations | Deterministic fixtures and replay |
| Refusal and incomplete states | 603 Python, 92 web, 45 Edge, 10 browser tests |
| Never identifies from model memory | Rights, privacy, security, and provenance gates |

**Submitted judging path:** stored, fingerprinted analyst replay · **Model not
invoked**

### Speaker note

GPT-5.6 is the bounded evidence analyst target, not a butterfly oracle. Codex
built the surrounding product and verification system. Neither supplies human
review or scientific ground truth. The replay lets judges inspect exact traces
without credentials or a provider call.

### Visual and proof

Show the actual analyst answer with artifact citations and stored tool trace
expanded, then show the test/provenance receipt. Test counts are measured at the
Task 17.3 release gate.

## Slide 8 — Measured Submitted evidence

### On slide

| Measured artifact | Value | What it means |
| --- | ---: | --- |
| Accepted Australian butterfly catalogue | **463 species** | Taxonomy scope, not occurrence completeness |
| Rebuilt ALA inventory | **236,897 selected rows** | Internal evidence inventory; public count withheld |
| Spatially eligible ALA inventory | **230,027 rows** | Internal generalized-workflow input |
| ALA aggregate inventory | **23,744 rows** | Internal cell/taxon aggregates |
| Flickr query plan | **1,876 definitions / 1,754 physical requests** | Deterministic and unsent in the frozen snapshot |
| Reference diagnostics | **2,906 valid decodes / 0 human-verified species** | Coverage diagnostics, not quality estimates |

### Speaker note

These are the only headline data numbers in the submission because each resolves
to the frozen snapshot or a cited derived artifact. The active external Flickr
fetch is deliberately absent until a complete immutable handoff exists.

### Visual and proof

Source every row to the canonical Submitted snapshot and the exact projections
named in `JUDGE_GUIDE.md`. Do not add the operator-reported partial Flickr count.

## Slide 9 — What is real, and what remains to earn

### On slide

**Real now**

- public credential-free Submitted product;
- immutable catalogue, map shell, local blind review, quality diagnostics;
- stored analyst traces with exact citations;
- rights, privacy, release, worker, and model gates that fail closed.

**Still unfinished**

- public occurrence layer and selectable geographic-impact cells;
- complete immutable Flickr candidate handoff;
- stored community reviews, consensus, and representative quality interval;
- authenticated live M5 receipt;
- YOLOE and BioCLIP work;
- recorded, approved, public YouTube demonstration;
- overall release readiness.

### Speaker note

This boundary is a feature of trustworthy evidence work. ButterflyLens shows
exactly where the proof ends and what receipt must exist before the next stage
can appear.

### Visual and proof

Use two plain columns with Submitted and Unfinished badges. Do not use a progress
percentage.

## Slide 10 — Make biodiversity evidence work visible

### On slide

> “ButterflyLens brings machine screening, community expertise, and Australia’s
> national biodiversity evidence together to reveal where public imagery could
> strengthen butterfly knowledge.”

[Open ButterflyLens](https://karikris.github.io/ButterflyLens/) ·
[Help verify](https://karikris.github.io/ButterflyLens/#verify) ·
[Open the map](https://karikris.github.io/ButterflyLens/#live) ·
[Judge guide](JUDGE_GUIDE.md) ·
[Source](https://github.com/karikris/ButterflyLens)

**Ask:** judge the working replay, inspect the boundaries, and help turn the next
eligible image into evidence worth reviewing.

### Speaker note

ButterflyLens makes careful evidence work productive: one place to discover,
review, measure, explain, and—only when the evidence earns it—export. The next
milestone is a governed immutable Flickr handoff followed by independent review,
not a larger unreviewed candidate count.

### Visual and proof

Return to the real product GIF and exact public links. The video link remains
absent until an approved public YouTube upload exists.

## Presenter preflight

- Replace no unavailable value with zero, a progress percentage, or a simulated
  success.
- Keep the winning line word-for-word and explain that it is the product thesis,
  not a claim that unfinished machine screening has run.
- Use only the exact metrics on Slides 4, 7, and 8.
- Call Flickr results discovery candidates, never occurrences.
- Call ALA authoritative baseline evidence for this build, never complete ground
  truth.
- State that the submitted analyst is a model-free replay and GPT-5.6 is the
  bounded live target.
- State that the public video is unfinished until recorded, approved, and
  uploaded to public YouTube.
- Finish on the working product and public judge route, not an architecture
  diagram.
