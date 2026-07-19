# Testing, release, and competition

## 1. Test layers

Maintain as relevant:

- unit tests;
- Python/TypeScript/JSON Schema contract parity;
- fixture-backed integration tests;
- database migration/RLS tests;
- fingerprint and checksum tests;
- Flickr budget simulations;
- worker interruption/resume tests;
- model smoke tests;
- review/consensus/reliability tests;
- statistical estimator tests;
- GPT-5.6 tool/evaluation tests;
- browser E2E;
- accessibility;
- visual regression;
- rights/provenance/security checks.

---

## 2. Default CI

Default CI must:

- make no live Flickr, ALA, GBIF, iNaturalist, or OpenAI calls;
- require no cloud credentials;
- download no model weights;
- use deterministic fixtures;
- validate schemas, checksums, rights, and provenance;
- avoid reliance on the M5 worker.

Live tests are opt-in, bounded, credentialed, and produce receipts.

---

## 3. Browser coverage

Test:

- Chromium full journey;
- Firefox smoke;
- WebKit smoke;
- 1280×720;
- mobile;
- keyboard;
- screen-reader semantics;
- reduced motion;
- high contrast;
- no WebGL;
- no WASM;
- worker offline;
- Submitted/Live switch.

Hero journey:

1. Open landing page.
2. Review an image.
3. See community evidence update.
4. Open map.
5. Compare ALA and Flickr.
6. Drill into a region/cell.
7. Inspect evidence.
8. Ask GPT-5.6.
9. Inspect quality.
10. Export.
11. Switch snapshots.

---

## 4. Scientific regression checks

Release tests must verify:

- candidates are not called occurrences;
- ALA absence is not called biological absence;
- provider assertions are not called human verified;
- Skip/Can’t view do not count as decisive;
- targeted failure-discovery reviews do not produce unweighted population
  estimates;
- reviewer reliability does not use model agreement as truth;
- raw scores are not called probabilities;
- unreviewed Flickr records cannot enter final export;
- sensitive coordinates remain protected;
- Submitted snapshot remains immutable.

---

## 5. Security and rights gate

Run:

- secret scan;
- dependency audit;
- licence audit;
- media-rights/attribution verifier;
- RLS tests;
- external-network audit;
- sensitive-data checks;
- large-file scan;
- generated-file inspection;
- `git diff --check`.

Block release on unresolved YOLOE/Ultralytics licensing, Flickr display
non-compliance, missing ALA/provider attribution, or unlicensed public media.

---

## 6. Performance gate

Measure before claiming:

- replay startup;
- first map render;
- drilldown/filter latency;
- API throughput;
- model load time;
- images/second;
- embedding cache hit rate;
- MPS peak memory;
- restart work avoided;
- bundle size.

Set regression thresholds from measured baselines with documented tolerances.

---

## 7. Judge replay

Primary judge path must require:

```text
No login
No private API key
No Supabase account
No B2 account
No GPU
No model download
No M5 availability
```

It must:

- be public;
- be resettable;
- use fingerprinted artifacts;
- display source/model/bundle SHAs;
- provide a guided route;
- include a static fallback;
- remain available through judging.

Live data is an enhancement, not a dependency.

---

## 8. README and judge guide

README first screen:

- ButterflyLens;
- tagline;
- map/product GIF;
- Help Verify;
- Open Map;
- Submitted Replay;
- worker state;
- one measured result;
- Codex/GPT-5.6 roles;
- concise architecture.

Judge Guide:

- 90-second route;
- technical route;
- expected states/counts;
- Submitted versus Live;
- current limitations;
- rights/provenance;
- optional live-worker path.

Do not begin the README with installation details.

---

## 9. Video and presentation

Video:

- public YouTube;
- under three minutes;
- target 2:45–2:50;
- at least two-thirds working product;
- clear audio;
- explicitly explain Codex and GPT-5.6.

Required sequence:

1. ALA baseline.
2. Flickr candidate stream.
3. M5 pipeline.
4. community review.
5. map update.
6. repeated/qualified review and quality.
7. GPT-5.6 evidence analysis.
8. export/provenance.

Every public number must come from a fingerprinted artifact or measured study.

---

## 10. Release checklist

A release is ready only when:

- root and relevant nested agent instructions were followed;
- all task commits are pushed;
- provenance and tool logs validate;
- submitted bundle fingerprints validate;
- live site works without worker;
- review and map work;
- quality states are honest;
- GPT-5.6 replay is credential-free;
- browser/a11y/security/rights gates pass;
- README/Judge Guide/video/deck are complete;
- primary `/feedback` Session ID is recorded;
- allowed and blocked scientific claims are documented.
