# ButterflyLens 2.4 — provisional reference bank

Status: completed with YOLOE and BioCLIP explicitly unfinished by user
instruction.

The rebuilt ButterflyLens taxonomy and ALA baseline remain authoritative. The
older `alascraper` and `butterfly-dashboard` repositories did not contain a raw
ALA occurrence artifact with sufficient source, rights, sensitivity, and
fingerprint lineage, so none of their data was imported.

The provisional bank contains 12,980 provider-labelled observations and
24,329 media candidates. Conservative rights, exact-taxon, mirror-conflict,
host, diversity, download, and decode gates selected 2,910 iNaturalist media
rows. Of these, 2,906 decoded and four permanent HTTP 404 outcomes remain
quarantined. All labels remain unreviewed provider assertions, source-image
bytes remain outside Git, and zero media are human verified.

YOLOE produced zero routes and BioCLIP produced zero embeddings or prototypes.
Both are marked unfinished. The current BioMiner GBIF fast-start record was
inspected: implementation was complete, but live GBIF acquisition and the
durable support bank were pending and no active build or copyable live artifact
was present. No fixture data was copied. No Flickr API call was made.

Reference-quality diagnostics cover all 463 accepted species. Valid provisional
decodes cover 237 species; 126 have no imported candidate media and 100 have no
automated-gate-eligible media. The diagnostics contain categorical evidence and
blockers only—no fabricated quality score, accuracy estimate, or absence claim.

Published bank fingerprint:
`6f23e1ec04d0297797439973aea98d9b45bc989ce9ec61db35064824621bdc3d`.

Release remains blocked by absent human review, unfinished YOLOE and BioCLIP,
incomplete species coverage, and pending durable private storage for permitted
source media.
