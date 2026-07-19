# ButterflyLens Task 1.1.1 — audit runtime analyst dependencies

Status: complete.

Starting SHA: `5209ff7f5da564965419870c7a4703b86bafd6a8`

Ending SHA: `3d8370d779f68aeaffc209964103f053dc366541`

Remote SHA: `3d8370d779f68aeaffc209964103f053dc366541`

Task ID: `butterflylens-1.1.1`

Primary model: `gpt-5.6-sol`

Reasoning effort: `xhigh`

Codex session: not started in this environment session

GitHits records:
- unavailable (user-directed) in `provenance/githits.jsonl`

Valyu records:
- not needed for this task

Files changed:
- `provenance/task_plans/butterflylens-1.1.1.md`
- `docs/reports/butterflylens_redesign_1_1_1_openai_runtime_audit.md`
- `provenance/githits.jsonl`

Contract boundaries:
- runtime analyst modules inventoried for full removal
- shared openai provenance/evaluation artifacts preserved

Scientific claims:
- no candidate/occurrence claims added in this task
- no science logic changed

Tests run:
- audit-only task; no runtime test command executed

Task results:
- confirmed all live analyst runtime artifacts currently present in web, shell, and
  Supabase layers
- confirmed OpenAI runtime dependency chain remains active in Edge runtime path
- confirmed shared provenance/evaluation packages and scripts must be preserved in
  order to keep Codex development evidence intact
