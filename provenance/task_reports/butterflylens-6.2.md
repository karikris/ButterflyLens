# ButterflyLens 6.2 — global out-of-range index

Status: **deferred; authoritative upstream still active**.

- Global butterfly species not currently known from Australia —
  `blocked_pending_authoritative_global_source`
- Lower default priority — contract available as Tier 5; no real index rows
- Strict provenance — admission contract available; no source snapshot admitted
- `novel_presence_hypothesis` state — `unfinished_not_run`
- No automatic scoring exclusion solely due to geography — policy preserved;
  scoring remains unfinished

The existing fail-closed global lane accepts only species-rank, authoritative,
fingerprinted assertions compared against the rebuilt ButterflyLens Australian
baseline. It treats “not currently known from Australia” as checklist
comparison, never biological absence, and its fixture tests remain green.

The real-data status remains
`blocked_pending_authoritative_global_source`, with zero admitted species.
BioMiner at `c7eaa9bf3696a25a0c8229837819dccec4fb9d66` contains current
uncommitted global/local pool provenance and its live current-policy GBIF
quality work is not complete. Per user direction, that active overlap was
acknowledged and left untouched. No data or source was copied, no synthetic
global species were created, and no Flickr API call occurred.

Task 6.3 is next and remains unfinished because it explicitly requires YOLOE
routing and BioCLIP embeddings.
