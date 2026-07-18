# ButterflyLens integration test coverage

Task 15.2 is covered by `tests/test_butterflylens_integrations.py`. The suite
crosses production component boundaries with deterministic repository artifacts,
temporary local files, in-memory durable-store acknowledgements, and an injected
synthetic Flickr transport. It never opens a provider connection.

| Required flow | Integrated boundary | Fail-closed assertion |
| --- | --- | --- |
| ALA pack | Pack manifest -> artifact bytes -> submitted species catalogue -> operations map -> pinned GPT repository | Dataset-rights withholding keeps the occurrence layer hidden and forbids scientific claims. |
| Flickr scheduler | Authoritative name assertion -> logical query -> physical request -> adaptive schedule -> Australia partition -> hourly budget -> injected response checkpoint | The request starts `planned_not_sent`; unfinished model metrics stay missing; no credential is persisted and no built-in HTTP client is used. |
| M5 worker | Caller-supplied media -> bounded queues -> durable acknowledgements -> Parquet/checkpoint -> restart journal -> offline projection | Cache cleanup follows durable commits, restart reuses committed work, model stages are unfinished, and the public site remains queryable when the worker is offline. |
| Model flow | Worker unfinished-stage state -> classification-maturity contract | YOLOE and BioCLIP are unavailable rather than negative; no probability, release, or scientific claim is created. |
| Review flow | Human review events -> layered consensus -> representative dataset-quality audit -> contributor-impact projection | Agreement alone is not release readiness; model votes are excluded; contributor speed, ranking, and scientific claims stay forbidden. |
| Map updates | Evidenced occurrence release gates -> submitted operations map -> database location/release receipt policy | A failed rights gate blocks the candidate and the public occurrence layer; publication still requires exact location and occurrence receipts. |
| GPT tools | Pinned submitted artifact repository -> local evidence toolbox invocations | Withheld, unfinished, and submitted-only states remain explicit; tools claim neither live state nor inferred probability. |
| Exports | Release-receipt-backed candidate -> Darwin Core archive -> ALA preparation archive | Preparation preserves record rights and lineage but remains not submitted, not published, and human-operated. |

## External-work boundaries

- BioMiner remains the authority for its active GBIF/Flickr acquisition work.
  No partial handoff is imported by this suite.
- Flickr behavior is exercised only through a synthetic callback. No Flickr API
  call, credential, or provider response is used.
- YOLOE and BioCLIP remain unfinished and are not executed.
- GitHits remains disabled and is not called.
- ALA contribution packaging prepares an operator handoff only; it cannot submit.
