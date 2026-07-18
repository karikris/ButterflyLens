# ButterflyLens 9.2 — Reviewer reliability policy

Status: **policy defined; estimator and weighted consensus remain unfinished**.

Starting SHA: `9d8501cbb22dff3d1c9ffac6489f923be1a315fd`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

The versioned policy makes equal weight the fail-safe default and prohibits a
non-unit weight until an exact family/life-stage/visual-domain cell has 20
scorable controls, positive/negative class minima, 10 independent overlaps,
and 5 independently adjudicated overlaps. It requires shrinkage toward 1.0,
uncertainty, and a 0.5–2.0 cap.

Model agreement and majority agreement cannot define truth. Every effective
event, minority dissent, conflict, method version, unweighted summary, and
weighted summary must remain available. Individual estimates stay private;
public rankings and demeaning labels are forbidden. Reviewers receive private
evidence explanations, correction, and appeal paths.

The policy does not claim an estimator, estimate, score, weighted consensus,
or release decision. Those remain later tasks.

## Verification and provenance

- Five focused policy tests cover all ten rules, thresholds, domains,
  shrinkage, cap, prohibited shortcuts, privacy, dissent, dignity, and the
  explicit non-implementation boundary.
- Full Python suite — 316 tests passed.
- Contract parity — passed (24 schemas, 20 valid, 20 invalid, 20 versions,
  15 vocabularies; TypeScript 7.0.2).
- Rights verification — passed for 52 tracked provider payloads.
- Licence verification — passed for 300 tracked files, 2 dependency
  manifests, and 0 model files.
- Provenance JSONL and staged whitespace validation — passed.
- GitHits remained unavailable and was not retried. No external source was
  required for this human governance decision.
- No Flickr API call, YOLOE work, BioCLIP work, model artifact, scientific
  score, or biodiversity claim was produced.
