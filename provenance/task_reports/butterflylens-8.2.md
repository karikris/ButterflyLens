# ButterflyLens 8.2 — Review-first landing experience

Status: **review-first web surface implemented with one rights-cleared credential-free fixture**.

Starting SHA: `ec71f15ffbdce76e84e320ef9900b4bef3dc8c4e`

TaxaLens SHA inspected: `c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`

BioMiner overlap: none; no BioMiner data was read or copied.

## Outcome

Task 8.2 establishes the first ButterflyLens web application as an exact-version
Vite/React static bundle. Its landing route leads directly with one review item
and includes:

- Yes, No, Can’t tell, Can’t view, and Skip;
- an optional comment;
- an alternative-taxon field enabled only for qualified reviewers;
- a credential-free, offline Australia map preview with explicit unavailable
  location state;
- a live current-contribution summary;
- a clear distinction between a local draft and a stored review;
- responsive layout, keyboard focus treatment, reduced-motion handling,
  forced-colour borders, semantic headings, fieldsets, labels, and status text.

The submitted replay uses one 180,698-byte Wikimedia Commons JPEG copied
byte-for-byte from immutable TaxaLens commit
`c5e87ead4fdb26d5c5624bbb8d8d67e46d8eddbc`. Its SHA-256, byte count,
source, creator, attribution, CC BY-SA 4.0 licence, and no-scientific-claim
boundary are checked before every build. Yes, No, and Can’t tell become
available only after that integrity-checked image successfully loads; Can’t
view and Skip remain available if it fails. This is an intentional scientific
gate, not a zero or negative classification. The generic question does not
expose the provider’s species label, and the page displays no model label,
model score, Flickr query term, source comment, majority vote, or peer decision.

The current-contribution panel is deliberately a draft projection. Review event
persistence remains Task 8.5 and is not claimed here.

## Architecture and provenance

TaxaLens’ immutable verification controls, media-readiness precedent, and
rights-cleared Wikimedia fixture were inspected. ButterflyLens uses original
components, styling, tests, and page data. No TaxaLens code, campaign bundle,
review history, measurement, generated data, model, build, runtime artifact,
or dirty working-tree content was copied. The one accepted image was extracted
from the immutable commit, renamed without changing its bytes, and recorded in
the migration and data-rights manifests.

The package versions match the proven sibling stack and were independently
resolved from the official npm registry. The exact lockfile, a deterministic
116-package licence report, and a production React-family MIT notice are
committed. The production build has no external font, map-tile, model, or API
dependency; its single local image has visible attribution and fingerprinted
rights evidence.

GitHits remained unavailable and was not retried. Valyu was unavailable, so
official npm registry, Wikimedia Commons, Creative Commons, and installed
package metadata were used directly. No Flickr API call, YOLOE work, BioCLIP
work, model artifact, scientific score, or biodiversity claim was produced.

## Verification

- `npm test` — five component/interaction tests passed.
- `npm run media:check` — exact SHA-256, byte count, rights fields, provider
  assertion, non-representative state, and no-scientific-claim state passed.
- `npm run check` — strict TypeScript check passed.
- `npm run build` — production build passed; 199.26 kB JavaScript and 7.87 kB
  CSS before gzip, with the production third-party notice bundled.
- `npm run licenses:check` — 116 exact packages and nine reviewed licence
  identifiers passed.
- `npm audit --audit-level=high` — zero vulnerabilities reported.
- 1280×720 Playwright visual smoke — unavailable because the installed browser
  cannot load host library `libnspr4.so`; no screenshot or visual-pass claim is
  made.
- `uv run python -m unittest discover -s tests -v` — 282 passed.
- Cross-language contract parity — passed with the pinned TypeScript 7.0.2:
  24 schemas, 20 valid fixtures, 20 invalid fixtures, 20 versions, and 15
  vocabularies. The first root invocation lacked an explicit compiler path;
  rerunning with `apps/web/node_modules/.bin/tsc` passed.
- Rights verification — passed for 52 tracked provider/media payloads.
- Licence verification — passed for 276 tracked files, two dependency
  manifests, and zero model files.
- Provenance JSON/JSONL, staged whitespace, secret-pattern, and unexpected
  binary/model-artifact gates passed. The only staged binary is the exact
  rights-verified JPEG.

## Rights, privacy, and claims

The page contains one attributed source-media fixture and no personal data,
Auth ID, raw coordinate, or signed URL. The provider identity is not a verified
taxonomic decision, the fixture is not representative, and the schematic map
makes no occurrence claim. No outcome is called submitted, community reviewed,
human supported, expert reviewed, or release ready. Real candidate media and
persistence remain required before the full review journey can be called
complete.
