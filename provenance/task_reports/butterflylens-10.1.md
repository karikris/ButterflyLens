# ButterflyLens 10.1 — Public visual system

Status: **implemented locally; automated responsive/accessibility contract
verified**.

Starting SHA: `11d8d3e232d2fa96eae6cc44c5a2f5cd615ce83b`.

TaxaLens immutable source inspected:
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`.

BioMiner overlap: none. Its active GBIF evidence-database work was not
inspected, interrupted, or copied.

## Outcome

The web app now has an original, versioned ButterflyLens visual system. Its
literal palette draws on eucalypt canopy, paperbark, clay, coast, wattle, and
field charcoal, with separate semantic aliases for brand, surface, accent,
focus, danger, and evidence states. Georgia/system serif provides an editorial
display voice while the local system sans stack keeps controls and evidence
copy direct and fast; there are no remote fonts or new dependencies.

Reusable state badges pair every colour treatment with a textual label and a
visible marker. Reusable evidence notices make information, caution, and
critical boundaries consistent and opt into live-region semantics only when a
state is dynamic. The existing review photograph is the visual anchor, framed
against a neutral matte without filters, overlays, pixel changes, or a new
asset. The review and quality surfaces now use these primitives.

The `butterflylens-visual-system:v1.0.0` contract fixes the requested design
principles, exact palette, semantic evidence states, normal-text contrast pairs,
44 CSS-pixel target, 320 CSS-pixel reflow floor, 1280×720 desktop and 390×844
mobile anchors, 820/520 breakpoints, three-pixel focus outline, reduced-motion
and forced-colour support, and an explicit prohibition on image alteration.
TypeScript and Python tests bind the contract to the CSS and document theme.

## Research and originality

Official iNaturalist pages informed the observation-photography, short-action,
community-contribution emphasis. ALA and ALA Lens informed an Australian public
infrastructure voice that separates exploration from contribution. Current W3C
WCAG 2.2 guidance informed the contrast, reflow, resize, focus, and target
boundaries. GitHits and Valyu remained unavailable and were not retried; the
official primary-site fallback is recorded.

TaxaLens visual primitives were inspected from its immutable commit for
literal/semantic separation and colour-independent status precedent. No
TaxaLens or external-site name, value, source, style, component, test, image, or
runtime data was copied. The original implementation uses ButterflyLens-owned
class names, palette values, components, and tests.

## Verification

- Full Python suite — 379 tests and 69 subtests passed.
- Focused visual-system parity — 5 tests passed for exact palette projection,
  WCAG contrast, no gradient/filter, focus/motion/forced-colour/target rules,
  theme metadata, and desktop/mobile reflow anchors.
- Web suite — 18 Vitest component and visual-contract tests passed; TypeScript
  check and production build passed.
- Web production checks — 116 dependency licences and the unchanged exact
  review-media fingerprint verified; built bundle sizes were 0.60 kB HTML,
  18.67 kB CSS, and 216.44 kB JavaScript before gzip.
- Contract parity — passed unchanged (25 schemas, 21 valid, 21 invalid, 21
  versions, 15 vocabularies; TypeScript 7.0.2).
- Rights verification — passed for 52 tracked provider payloads.
- Licensing — passed for 346 staged/tracked files, 2 dependency manifests, and
  0 model files.
- Production dependency audit — 0 vulnerabilities.
- No new third-party package, font, media file, model artifact, or database
  migration was introduced.
- Staged whitespace, secret, model-file, cache, generated-bulk, and large-file
  gates passed for all 21 task files.

Automated DOM and stylesheet contracts cover semantics and responsive rules. A
standalone browser screenshot or accessibility-engine run is not claimed
because no browser runtime is installed in this environment; the production
bundle and both declared viewport layouts remain ready for that later release
gate.

No Flickr API call, BioMiner record access, YOLOE work, BioCLIP work, model
inference, or scientific result occurred. YOLOE and BioCLIP remain unfinished.

Next safe task: Task 10.2, build the public application shell and main
navigation from these primitives.
