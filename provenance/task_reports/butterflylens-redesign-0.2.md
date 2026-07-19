# ButterflyLens redesign Task 0.2 — screenshot defect matrix

Status: **complete and pushed; runtime unchanged**.

Date: 2026-07-19

Starting and capture-source ButterflyLens SHA:
`056fe3563f6282a8bce4ea61ab1da3d96323e526`.

Task implementation and verified remote SHA:
`da6207453edc667da9e70316d1d845ce1a841e25`.

Exact BioMiner committed boundary:
`bfdb4b38646f16062d7fb4a6d0f4b0674c8f01dd`.

The user confirms BioMiner is still fetching Flickr metadata only. No mutable
BioMiner output was read, counted, or copied, and no Flickr API call occurred.
The rebuilt ButterflyLens baseline remains authoritative. YOLOE and BioCLIP
remain unfinished.

## Delivered

- `docs/reports/ui_screenshot_defect_matrix.md` records 14 issues: eight
  critical, five high, and one medium. Each includes route, viewport, severity,
  screenshot, observed problem, source-backed root cause, proposed fix,
  acceptance test, and status.
- `docs/assets/redesign-baseline/task-0.2/` contains 12 baseline PNGs plus a
  manifest covering 1440 × 900, 1280 × 720, 390 × 844, reduced motion, forced
  colours, the current map, Verify, Species, Operations, Quality, Community,
  and Ask ButterflyLens.
- `apps/web/scripts/capture-redesign-baseline.mjs` freezes the application SHA,
  capture instant, browser context, viewport and accessibility state; blocks
  every non-local origin and service worker; fingerprints each image; and
  positions fragment captures without recording an in-progress smooth scroll.
- Positive observations are explicit: no first-viewport forced-colour-only
  readability defect was found, and reduced motion produced the same static
  Explore pixels as ordinary 1280 × 720.

The critical defects are the map not being the first public experience, the
one-document fragment architecture, the Australia-only ALA map, absent Flickr
candidate journey, draft-only review flow, absent 20-image sets, unavailable
personal-only Community view, and retained public analyst. BioMiner-dependent
candidate/model remediation is deferred without inventing evidence.

## Task gate

| Check | Result |
|---|---|
| Deterministic recapture | 12 PNG SHA-256 values and the manifest reproduced byte-for-byte |
| Required dimensions | Ten 1280 × 720, one 1440 × 900, and one 390 × 844 RGB PNG verified |
| Network boundary | All 12 manifest records report zero external requests |
| Visual inspection | Every capture inspected; 14 defects and accessibility-state observations recorded |
| Focused browser/visual suite | Eight Chromium checks passed across desktop, mobile, reduced motion, forced colours, and no-WebGL |
| Full Python suite | 670 passed in 32.356 seconds |
| Full web suite | 21 files and 100 Vitest tests passed; three Node licence tests passed |
| Web production gate | 119 dependency licences, review-media fingerprint, TypeScript, and Vite production build passed |
| Deno Edge suite | 49 passed; 23 files formatted; four frozen entry points checked |
| Python/TypeScript/JSON Schema parity | 24 schemas, 20 valid, 22 invalid, 20 versions, 14 vocabularies; TypeScript 7.0.2 |
| Rights and licensing | 66 provider payloads and 666 tracked files passed after staging |
| Release security | 50 public-RLS tables, 11 security-invoker views, 60 security-definer functions, 626 text files, and 12 network-boundary files passed; `release_ready=false` |
| Fixed completion audits | Historical and current audits passed; `goal_complete=false` remains binding |
| JSON, JSONL, JavaScript and whitespace | Passed |

The first Python command used system Python, which lacked the repository's
locked scientific packages; the corrected `.venv` command ran all 670 tests.
The first Deno command used an absent shell-path executable; the exact cached
Deno binary then passed the full Edge gate. The first deterministic-hash
command used a repository-root-relative path while running from `apps/web` and
was corrected before the successful two-run comparison. These were
toolchain/path corrections, not product failures.

Chromium initially required WSL runtime libraries absent from the host. Exact
Ubuntu packages were unpacked under `/tmp` and supplied through
`LD_LIBRARY_PATH`; no system package was installed. The capture script was also
corrected before final generation so Explore starts at the document header and
fragment captures cannot stop midway through the app's smooth-scroll motion.

## Push and unfinished boundary

The exact task commit was pushed directly from local `main` to `origin/main`
without force. Both returned
`da6207453edc667da9e70316d1d845ce1a841e25` after the push.

Pre-existing untracked `AGENTS.md:Zone.Identifier` and `docs/agents/` content
remain unstaged and unchanged. GitHits was not called. Phase 1 runtime-analyst
removal and all later redesign phases remain unstarted in this run; the user
requested wrap-up after Task 0.2 rather than continuation into the next phase.
