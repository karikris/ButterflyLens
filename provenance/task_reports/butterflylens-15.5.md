# ButterflyLens 15.5 — security and compliance

Status: **implemented and locally verified; production/community/data release
remains blocked; publication pending the task commit**.

Starting SHA:
`01b3241a91acfbefbfb28ed831fbeb5453f77d1c`.

## Outcome

ButterflyLens now has one deterministic, credential-free release-security
verifier and an explicit human-readable release decision. The verifier proves
the versioned database and application boundary is internally closed while
refusing to convert a passing security check into scientific, provider,
privacy, or production authority.

The exact machine-readable result inventories 50 public RLS tables, 11 public
security-invoker views, 60 fixed-search-path security-definer functions, and 10
allowlisted external-network boundary files. It finds no high-signal credential
pattern in tracked text, confirms that community writes and the live analyst
are disabled, returns `release_ready: false`, and names all 11 blockers.

The local Supabase Auth configuration now matches the versioned
`prelaunch_blocked` policy: global and email sign-up and anonymous sign-in are
disabled; email confirmation and secure password changes are required; and a
12-character lower/upper/digit/symbol password policy is declared. This is a
versioned local and deployment-input control, not a claim that the remote
project was changed.

The Supabase and Supabase Postgres best-practice skills materially shaped the
implementation: the verifier requires RLS on every public table,
security-invoker public views, empty-search-path security-definer functions,
explicit default privilege revocation for public definers, role-safe
authorization, and no user-editable Auth metadata in policy logic.

## Security and compliance gate

- RLS/schema: 40 focused Python tests pass. Every one of 50 public tables has
  an explicit RLS enable statement; 11 public views are security invokers; 60
  security-definer functions have an empty search path and public definers have
  explicit default privilege revocation.
- Runtime RLS limitation: all tracked pgTAP definitions remain covered by
  exact parser/plan assertions, but they could not be executed against a live
  database in this session. The Supabase MCP endpoint remained OAuth-gated
  until a client reload, Supabase CLI was absent, and Docker daemon access was
  denied. Production must rerun them against the target project.
- Secret scan: the release verifier scans every tracked text file for
  high-signal private-key, JWT, OpenAI, Supabase, GitHub, and AWS credential
  shapes. The final staged scan repeats the check.
- Dependency audit: `npm audit --audit-level=high` reports zero known
  vulnerabilities. Exact npm 12.0.1 verifies 119 registry signatures and 45
  attestations. Exact Deno lock resolution succeeds for all four Edge entry
  points.
- npm signature note: host npm 9.2.0 first returned
  `EEXPIREDSIGNATUREKEY` for `bidi-js@1.0.3` because the registry key expired
  on 29 January 2025. npm 12.0.1 completed the verification but warned that
  Node 22.22.1 is one patch below its supported 22.22.2 floor. The separate
  vulnerability and lock checks pass.
- Licence audit: the web report verifies 119 installed packages; the
  repository licence verifier covers all staged tracked files and exact Python,
  npm, and Deno dependency manifests with zero model files.
- Rights audit: all 52 tracked provider payloads pass the verifier. This proves
  correct fail-closed handling, not rights clearance; ALA records `dr1097`,
  `dr30019`, and `dr635` still block downstream data release.
- Privacy review: current OAIC APP 1 and APP 11 guidance confirms that the
  unidentified operator/contact, production processing locations, overseas
  recipients, and absent category-retention schedule cannot be guessed. The
  existing versioned six-item community launch block remains correct.
- Rate-limit and abuse behavior: 61 focused Flickr budget, rate, retry, search
  execution, resilience, privacy, moderation, and takedown tests pass. Exact
  simulations cover the 3,500-call hard envelope, 3,000 normal plus 500 reserve,
  100 provider-safety remainder, multi-key block, and uncertain-send freeze.
- External network: the allowlist contains four opt-in Python acquisition
  scripts, two browser transports, and four Supabase Edge entry points. The
  Flickr contract has no built-in HTTP transport. All 10 real-browser tests
  fail on any external request and pass without one.

## Full repository verification

- All 576 locked Python tests pass in 20.6 seconds.
- All 19 Vitest files and 92 tests plus three standalone Node tests pass. Web
  typecheck, dependency licences, media checksum, and the production build
  pass. The existing 1.50 MB chunk warning remains non-blocking.
- Playwright 1.61.1 passes all 10 Chromium, Firefox, WebKit, mobile,
  reduced-motion, forced-colour, and no-WebGL browser/visual checks. The same
  previously documented untracked local browser-library cache is used because
  this WSL host lacks sudo-installed Playwright dependencies.
- All 45 frozen Deno Edge tests pass, the four Edge entry points type-check,
  and all 22 function files pass formatting.
- Python/TypeScript parity passes for 25 schemas, 21 valid and 21 invalid
  fixture roots, 21 versions, and 15 vocabularies with TypeScript 7.0.2.
- Rights, licensing, JSON/JSONL, workflow YAML, shell syntax, Python
  compilation, generated/model/media, large-file, secret, staged-scope,
  whitespace, and `git diff --check` gates are completed immediately before
  the commit.

## Release decision

`SECURITY_RELEASE_REVIEW.md` is the durable decision record. Only the public,
credential-free Submitted replay passes this task. These remain blocked:

- community accounts and writes;
- the live analyst and remote service claim;
- downstream public release of the ALA data while three dataset-rights
  conflicts remain;
- YOLOE, which remains `blocked_not_executed` and unfinished;
- BioCLIP, which remains `skipped_unfinished_by_goal_instruction` and
  unfinished;
- any claim that the target Supabase RLS/Auth, B2, contracts, region, or
  retention controls were deployed or remotely verified.

## Research and external-work boundary

Current official Supabase RLS, API security, product security, npm security,
and breaking-change documentation was used together with current official OAIC
APP 1, APP 11, privacy-policy, and automated-decision guidance. GitHits remained
disabled by user instruction and was not called. No external implementation
was copied.

BioMiner is now at
`55b253aa7253d3001a51271e4bfd62dffa8ae83a`, with a complete committed TaxaLens
Task 14.1 handoff but active uncommitted ButterflyLens handoff/model follow-on
work. It does not yet provide a complete immutable ButterflyLens GBIF/Flickr
handoff, so no partial artifact was copied. The rebuilt ButterflyLens ALA
baseline remains authoritative.

The user-reported Flickr fetch remains external and active from its 50,000
unique-image checkpoint. No Flickr API call, Flickr output inspection/import,
Supabase or B2 mutation, provider submission, live GPT call, YOLOE work,
BioCLIP work, scientific model call, scientific inference, or third-party
media copy occurred.

Next safe task: freeze the exact Task 16.1 submitted snapshot after this task
commit is pushed and its Pages deployment is verified.
