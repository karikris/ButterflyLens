# ButterflyLens 18.2 — evidence-backed completion boundary

Status: **completion audit and false-claim guard complete; ButterflyLens remains
not complete and not release-ready**.

Starting and fixed audit SHA:
7a2c2eba61cd10034096e006cdb04fd5018a2b10.

Fixed audit tree:
fc29c3de542b63cb3905ab4059e16a2d81548138.

Subtask 18.2.1 commit:
88e97d13d85f98b84af0220dc286cd6a30bd6a33.

Ending and remote SHAs: pending the containing Task 18.2 commit and non-force
task push.

## Outcome

The repository now has one exact completion boundary instead of relying on task
names or implementation volume as evidence of overall completion.
provenance/completion_audit.v1.json records the exact 100 final acceptance
criteria and 46 minimum required artifacts from the source goal. At the fixed
Task 18.1 tree:

- 70 criteria are satisfied;
- 9 are partial;
- 7 are blocked_by_user_instruction;
- 14 are blocked_external;
- 11 minimum artifacts are present under the requested name;
- 7 are present as named semantic equivalents;
- 5 model artifacts are explicitly deferred; and
- 23 live or downstream artifacts are externally blocked.

COMPLETION_STATUS.md turns the machine audit into a concise public boundary. It
explicitly retains the rebuilt ButterflyLens ALA baseline as authoritative,
keeps the GBIF Parquet pack separate and complementary, and blocks any inference
from provider inclusion or search output to human verification or a
release-ready occurrence.

## False-completion guard

scripts/verify_completion_audit.py is a no-network fail-closed verifier. It
requires:

- the exact audited commit, tree, goal hash, session, model, and effort;
- criterion IDs 1 through 100 in exact order with exact source text;
- the fixed evidence status for every criterion;
- all 46 artifact names and fixed statuses;
- non-empty rationales and next actions for every non-satisfied criterion;
- safe unique evidence paths present in the fixed Git tree;
- exact summary counts and authority-boundary language; and
- goal_complete=false unless every criterion is satisfied and every required
  artifact is present or an explicitly accepted equivalent.

The JSON Schema closes structural fields and collection sizes. Regression tests
reject missing criteria, a status upgrade at the fixed boundary, a false
completion flag, summary drift, unsafe paths, and evidence first added after the
audit boundary. The release-security verifier now invokes this guard before
reporting its own pass and still emits release_ready=false.

## Binding unfinished work

1. BioMiner remains at
   ae6a18509b7be48da5c6ca69ab0caacf4632cc70 and is still fetching Flickr
   metadata. No partial output, counter, log, checkpoint, or active record was
   copied. No Flickr API call was made.
2. YOLOE and BioCLIP remain unfinished_not_run by explicit user direction.
   Routes, full-frame inputs, embeddings, prototypes, scores, persistent model
   workers, and cache-hit evidence remain incomplete.
3. The public impact map and its national/state/IBRA/LGA/H3 interactions remain
   blocked by missing Flickr/model/review cells and unresolved ALA
   public-product rights.
4. The bounded Bounded model server path and deterministic tools exist, but no
   credentialed live model evaluation is claimed. The stored judge replay
   remains explicitly labelled Model not invoked.
5. M5 heartbeat, restart, and append-only live update contracts are tested, but
   no observed live receipt is attached and judges cannot inspect a live worker.
6. The exact 2:48 video packet exists, but human recording, voiceover, approval,
   upload, and public URL remain unfinished.

## Skill and service safety

Headroom preserved the exact long-form goal under receipt
898dbe5ec3520d1425bf5d0f while the audit retained exact criterion and artifact
text. The Supabase safety instructions were applied to the read-only inspection
of local migrations and RLS evidence: no connected project, schema, Auth state,
Storage object, Edge Function, or database row was changed. A local contract or
migration was not counted as observed live Supabase operation.

GitHits remains unavailable and disabled by user instruction. It was not called;
append-only records retain disabled_by_user_unavailable_not_called.

## Verification

- The focused completion and release-security suites pass: 12 tests.
- The corrected full repository command passes all 643 Python tests in 22.41
  seconds with the four package roots configured in PYTHONPATH.
- The first full-suite attempt incorrectly supplied -t . to Python 3.14
  discovery even though tests/ is not an importable package. It failed before
  running tests; removing that inappropriate flag produced the passing full
  result above.
- The audit passes its Draft 2020-12 JSON Schema and deterministic CLI verifier,
  which reports goal_complete=false.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  TypeScript and the production build pass; the existing 1,496.87 kB script
  retains its non-blocking chunk-size warning.
- Rights verification passes for 62 tracked provider/data/media payloads.
  Licensing passes for 605 tracked files, two dependency manifests, and zero
  model files.
- Release security passes across 50 RLS tables, 11 security-invoker views, 60
  security-definer functions, 583 tracked text files, and 11 explicit network
  boundary files while retaining release_ready=false.
- All tracked JSON and provenance JSONL parse, tracked Python compiles, and
  whitespace checks pass.

No provider, Flickr, OpenAI, Supabase, B2, GitHits, YOLOE, BioCLIP, image, or
video generation call occurred. The only sibling-repository action was the
read-only BioMiner coordination check required by the operator.
