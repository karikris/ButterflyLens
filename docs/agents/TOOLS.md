# Tool, MCP, research, and skill routing

## 1. General rule

Inspect local code first. Use the smallest tool set that resolves the unknowns.
Tool output is evidence, not authority.

Priority:

1. Local code, tests, schemas, manifests, and git history.
2. A matching installed skill.
3. Official/current external sources through Valyu.
4. Open-source implementation patterns through GitHits.
5. Other tools only when they add necessary evidence.

Do not browse or search simply to decorate a task report.

---

## 2. Skills

When a task matches an installed skill:

1. Locate the skill.
2. Read its `SKILL.md` before acting.
3. Follow its workflow and constraints.
4. Record the skill used in the task report.

Typical routing:

| Task | Skill |
|---|---|
| General GitHub repository/PR/issue context | GitHub skill |
| Address review comments | `gh-address-comments` |
| Diagnose GitHub Actions | `gh-fix-ci` |
| Commit, push, publish changes | `yeet`, only if compatible with the current direct-main instruction |
| Document/presentation/spreadsheet artifact | Matching artifact skill |
| Repository-specific skill | Nearest repository `SKILL.md` |

A skill does not override the user’s direct-main, scientific, rights, or
provenance instructions unless the user explicitly changes them.

---

## 3. GitHits MCP

### Use GitHits for

- open-source implementation patterns;
- architecture comparisons;
- React/TypeScript component patterns;
- Polars, DuckDB, Parquet, H3, MapLibre, Supabase, B2, or MPS examples;
- test harnesses;
- resumable workers;
- append-only review systems;
- accessible visualization patterns.

### Required use

Run GitHits for each non-trivial numbered implementation, architecture,
data-model, UI, testing, deployment, or performance task/subtask.

GitHits may be marked `not-needed` for:

- pure status reports;
- a deterministic typo/formatting fix;
- exact renames with no behavior change;
- provenance updates that introduce no implementation choice.

Record why it was not needed.

### Workflow

1. Inspect local code.
2. Write a focused query.
3. Review at least two approaches when practical.
4. Note source licences.
5. Record adopted and rejected patterns.
6. Implement a native solution; do not copy wholesale.
7. Append one log record.

Log:

```text
provenance/githits.jsonl
```

Record shape:

```json
{
  "task_id": "butterflylens-4.2.3",
  "timestamp": "ISO-8601",
  "queries": ["focused query"],
  "repositories_reviewed": ["owner/repository"],
  "patterns_adopted": ["pattern"],
  "patterns_rejected": ["pattern"],
  "reason": "why this design fits ButterflyLens",
  "license_notes": ["licence and copying implications"],
  "solution_id": null,
  "githits_status": "used"
}
```

### Query quality

Good:

```text
Polars lazy anti join immutable parquet work queue
MapLibre local GeoJSON dual bubble layers accessibility
Supabase append-only review events RLS
PyTorch MPS persistent model worker memory pressure
```

Bad:

```text
best dashboard
AI butterfly app
cool map
```

### Failure

If unavailable:

1. Record one failed attempt.
2. Do not retry repeatedly.
3. Use local evidence and authoritative documentation.
4. Set `githits_status: unavailable`.
5. Do not invent repositories or solution IDs.

---

## 4. Valyu MCP

### Use Valyu for current external truth

Use Valyu when the task depends on information that may change or requires
authoritative external evidence:

- API contracts and quotas;
- provider terms and licences;
- current OpenAI models and APIs;
- ALA, Flickr, GBIF, iNaturalist, Supabase, B2, Hugging Face, PyTorch, or
  Ultralytics documentation;
- scientific papers;
- standards such as Darwin Core;
- sensitive-data or Indigenous data-governance guidance;
- current software compatibility.

Prefer primary sources:

1. Official documentation.
2. Official repositories/model cards.
3. Peer-reviewed papers.
4. Trusted standards bodies.
5. Secondary sources only when primary material is unavailable.

### Mandatory use

Use Valyu when:

- an external URL, API, model, law, term, licence, or paper is referenced;
- a fact may have changed;
- scientific or provider behavior is uncertain;
- a user asks for current verification;
- the task changes public claims based on external data.

### Workflow

1. State the exact external question.
2. Search narrowly.
3. Open the primary source.
4. Record retrieval date, source URL, and relevant version/date.
5. Separate sourced facts from inference.
6. Update a policy/ADR when the finding changes architecture or release rules.
7. Append one log record.

Log:

```text
provenance/valyu.jsonl
```

Record shape:

```json
{
  "task_id": "butterflylens-0.3.2",
  "timestamp": "ISO-8601",
  "questions": ["What is Flickr's current whole-key hourly limit?"],
  "sources": [
    {
      "url": "official source",
      "title": "source title",
      "retrieved_at": "ISO-8601",
      "version_or_date": "when available"
    }
  ],
  "facts_used": ["concise fact"],
  "inferences": ["clearly marked inference"],
  "valyu_status": "used"
}
```

### OpenAI work

For OpenAI:

1. Verify current behavior through official OpenAI documentation with Valyu.
2. Use GitHits only for implementation examples.
3. Record exact model ID, API, reasoning mode, tool version, and evaluation.

### Failure

If Valyu is unavailable:

- record the outage;
- use another authoritative-search mechanism if available;
- do not answer mutable external questions from memory;
- block the decision if current verification is essential.

---

## 5. When to use both

Use both when a task has two distinct needs:

- Valyu: “What is the current official contract?”
- GitHits: “How have strong open-source projects implemented it?”

Examples:

- current OpenAI Responses API + practical tool-calling architecture;
- current Flickr quota/terms + resilient scheduler patterns;
- current MapLibre API + accessible React map examples;
- current Supabase RLS behavior + append-only review schema examples.

Do not mix source roles. GitHits examples do not override official terms.

---

## 6. Other MCP/tool routing

- Morph: semantic local code exploration and targeted edits.
- Headroom: compress long logs/context, then retrieve exact source before edit.
- GitHub connector/skill: repository, issue, PR, and metadata operations.
- Local `git`/`gh`: current branch, Actions logs, commits, and pushes when needed.
- Python/Polars/DuckDB: deterministic analysis and artifact validation.

If a non-essential MCP service fails, record it once and continue safely. Never
fabricate tool output.
