# Git, commits, pushes, and provenance

## 1. Default workflow

Unless the user explicitly overrides it:

- Work directly on `main`.
- Do not create feature branches.
- Do not open pull requests.
- Do not merge branches.
- Do not force-push.
- One numbered subtask equals one focused commit.
- Push `main` after each completed task.

The purpose of pushing after a task rather than each subtask is to preserve
small commits while avoiding excessive remote churn.

---

## 2. Before every task

```bash
git switch main
git status --short
git branch --show-current
git rev-parse HEAD
git pull --ff-only origin main
```

Record:

- starting SHA;
- dirty files;
- untracked files;
- branch;
- remote state.

Do not discard or overwrite pre-existing user work.

For upstream integration:

```bash
git -C ../BioMiner status --short
git -C ../BioMiner branch --show-current
git -C ../BioMiner rev-parse HEAD

git -C ../taxalens status --short
git -C ../taxalens branch --show-current
git -C ../taxalens rev-parse HEAD
```

Use only committed upstream content.

Prefer:

```bash
git show <sha>:<path>
git archive <sha>
```

over copying from a working tree.

---

## 3. Subtask commit

Before commit:

1. Run targeted tests.
2. Run relevant lint/type checks.
3. Run `git diff --check`.
4. Inspect the staged diff.
5. Confirm no secrets, model weights, source-image collections, caches, or
   generated bulk data are staged.
6. Update:
   - GitHits/Valyu logs;
   - upstream migration manifests;
   - model usage;
   - human decisions when applicable.

Commit only the subtask.

Use conventional messages:

```text
feat(map): add Australian H3 impact cells
fix(review): require verified media before decision
test(worker): cover MPS resume behavior
docs(rights): record Flickr display policy
```

---

## 4. Required trailers

```text
AI-Assistance: OpenAI Codex
AI-Primary-Model: exact_model_id
AI-Reasoning-Effort: exact_value
AI-Reasoning-Mode: standard | pro
AI-Supporting-Models: exact_ids_or_none
AI-Session: exact_session_id
Build-Week-Scope: new | modified-existing
Origin-Repository: karikris/BioMiner | karikris/taxalens | none
Origin-Commit: full_sha | none
GitHits-Log: provenance/githits.jsonl#task-id | not-needed
Valyu-Log: provenance/valyu.jsonl#task-id | not-needed
Human-Decision: concise description
Human-Reviewed-By: Kris Kari
Tests: exact commands
```

Rules:

- Do not use AI as Git co-author.
- Do not invent unavailable model/session IDs.
- Do not claim human review before it occurred.
- If historical provenance is unknown, add a separate attestation rather than
  rewriting pushed history.

---

## 5. Task push

After all task subtasks are committed:

1. Run the task-level test gate.
2. Run relevant rights, provenance, bundle, and replay verifiers.
3. Inspect `git status --short`.
4. Push:

```bash
git push origin main
```

5. Verify remote SHA.
6. Record the push in the task report and `provenance/commits.jsonl`.

If rejected because remote `main` advanced:

- do not force-push;
- do not create a branch;
- do not rewrite pushed history;
- stop and report:
  - local SHA;
  - remote SHA;
  - commits not pushed;
  - conflicting files when known.

---

## 6. Upstream provenance

Maintain:

```text
UPSTREAM_BIOMINER.md
UPSTREAM_TAXALENS.md
provenance/biominer_migration_manifest.yaml
provenance/taxalens_migration_manifest.yaml
```

Each imported/adapted component records:

```yaml
component_id: string
source_repository: string
source_commit: full_sha
source_path: path
destination_path: path
migration_kind: artifact_contract | adapter | dependency | extracted | copied
reason: string
build_week_scope: new | modified_existing
source_license: string
changes:
  - string
tests:
  - string
status: planned | migrated | verified | superseded
```

Integration preference:

1. committed artifact;
2. versioned schema;
3. thin adapter;
4. stable command;
5. small shared package;
6. copied source only when every prior option is unsuitable.

Do not bulk-copy BioMiner or TaxaLens.

---

## 7. Build Week provenance

Maintain:

```text
BUILD_WEEK_BASELINE.md
BUILD_WEEK_DELTA.md
CODEX_COLLABORATION.md
HUMAN_DECISIONS.md
provenance/commits.jsonl
provenance/model_usage.jsonl
provenance/githits.jsonl
provenance/valyu.jsonl
provenance/review_attestations.yaml
provenance/sessions/
```

Before submission:

- run `/feedback` in the primary GPT-5.6 Codex session;
- record the exact Session ID;
- separate pre-existing BioMiner/TaxaLens work from ButterflyLens work;
- list imported contracts and origin SHAs;
- record tests and human decisions.

---

## 8. Prohibited operations

Do not:

- force-push;
- rewrite pushed history;
- amend pushed commits;
- silently rebase after remote divergence;
- commit secrets;
- commit unrestricted model weights;
- commit source-image collections;
- commit generated caches;
- commit unlicensed media;
- fabricate provenance;
- represent copied upstream work as new ButterflyLens work.
