# ButterflyLens 10.2 — Public application shell

Status: **implemented locally; exact navigation and repository contracts
verified**.

Starting SHA: `38f4d36369a46352373b2c29c1834fce996a4e2d`.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. Its active GBIF evidence-database work was not
inspected, interrupted, or copied.

## Outcome

The public app now has one semantic primary navigation with the exact requested
order: Explore, Verify, Species, Live, Quality, Contributors, Ask ButterflyLens,
and About. The header exposes project identity and submitted-replay state; a
skip link moves keyboard users to a focusable main landmark; the footer is the
real About destination.

Every navigation link resolves to a real document landmark. Explore introduces
the credential-free submitted replay and authoritative rebuilt baseline. The
existing Verify and Quality implementations retain their evidence semantics.
Species, Live, Contributors, and Ask ButterflyLens resolve to visibly labelled
`Surface scheduled` previews, so this shell does not claim completion of later
tasks. About explains the candidate, review, quality, and release separation.

The same navigation serves desktop and mobile. At narrow widths it remains a
44-pixel-target horizontal strip contained within the header instead of creating
a duplicate mobile landmark or hiding the primary journey behind a scripted
menu. Current state remains visible in forced-colour mode, and the established
820/520 reflow anchors are preserved.

## Originality and boundaries

The immutable TaxaLens shell was inspected for one-navigation, focus-target,
truthful-static-state, keyboard, and narrow-viewport precedent. No TaxaLens
source, labels, routes, styles, tests, or data were copied. ButterflyLens uses
its own exact product navigation, evidence vocabulary, component structure,
visual tokens, CSS, and tests.

No new public data, dependency, remote font, media, model artifact, database
migration, or external request was introduced. The existing rights-cleared
review photograph remains byte-identical.

## Verification

- Full Python suite — 383 tests and 69 subtests passed.
- Focused public-shell and visual-system suite — 9 tests passed, including exact
  order, real targets, one navigation, focus, 44-pixel targets, mobile reflow,
  palette/contrast, motion, forced-colour, and image-integrity boundaries.
- Web suite — 21 Vitest component tests passed; TypeScript check and production
  build passed.
- Production bundle — 0.60 kB HTML, 21.79 kB CSS, and 219.78 kB JavaScript
  before gzip; 116 dependency licences and the exact review-media fingerprint
  were verified during the build.
- Contract parity — passed unchanged (25 schemas, 21 valid, 21 invalid, 21
  versions, 15 vocabularies; TypeScript 7.0.2).
- Rights and licensing verification passed; production dependency audit found
  zero vulnerabilities.
- Whitespace and provenance JSONL checks passed before commit.

Automated DOM and stylesheet contracts cover semantic structure, exact links,
focusability, and responsive rules. A standalone browser screenshot or
accessibility-engine run is not claimed because no browser runtime is installed
in this environment.

No scientific claim was newly authorized. Candidate evidence remains separate
from human review, quality estimation, and scientific release.

No Flickr API call, BioMiner record access, YOLOE work, BioCLIP work, model
inference, or scientific result occurred. YOLOE and BioCLIP remain unfinished.

Next safe task: Task 10.3, build species pages from the authoritative rebuilt
ButterflyLens taxonomy and name artifacts.
