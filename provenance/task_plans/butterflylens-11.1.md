# Task plan — ButterflyLens 11.1

Task ID: `butterflylens-11.1`

Objective: verify and freeze the current official OpenAI requirements for the
ButterflyLens Bounded model evidence analyst before implementing tools or transport.

Starting and remote SHA:
`e83cdd2711f7b22415b60c1c4e0c7eeef1f7ec38`.

Skill: OpenAI Docs. Local integration surfaces are inventoried first, then the
official OpenAI Developer Docs MCP and `/v1/responses` OpenAPI endpoint are used.
Only official OpenAI documentation is authoritative for current API/model
claims.

GitHits: disabled for the remainder of the goal by explicit user instruction;
no call is made.

Expected files: versioned machine-readable requirements, human implementation
guide with official citations, static contract tests, prior-task commit/push
receipt, OpenAI Docs/model provenance, and task report. No SDK dependency,
server route, key, model call, tool implementation, or evaluation run is added.

Requirements to resolve: exact model slug and alias; Responses API request and
tool loop; strict function and final-output schemas; bounded tools, loops,
output, retries and timeouts; server-only secret; privacy-preserving safety
identifier; explicit storage policy; evidence/artifact citations; refusal,
incomplete and error handling; no model-memory biodiversity facts; replay
semantics; observability and at least 40 representative evaluation cases.

Scientific/privacy boundaries: the model is a bounded analyst over deterministic
read-only tools, never a taxonomic authority. Unsupported/missing evidence is
reported, not guessed. Reviewer/control/sensitive-location data remains governed.
No browser key or direct database/provider/model action is permitted.

Verification: JSON shape and exact constants, official-source allowlist,
strict-schema rules, budgets, privacy and citation boundaries, local-inventory
claims, no dependency/runtime addition, full Python suite, rights/licensing,
provenance JSONL, staged safety, and whitespace.

Rollback: remove the requirements document/artifact/tests and task provenance.
No external state or live API data is changed.
