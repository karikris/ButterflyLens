# ButterflyLens 7.5 — Live / Submitted map switch

Status: **domain contract complete; public map switch unfinished**.

The model-independent offline projection already keeps the immutable submitted
snapshot and latest committed live snapshot distinct, fingerprinted, and
queryable. It marks stale live data when the worker is offline and never hosts
the site from the M5. Seven restart/offline tests remain green.

No public map UI exists because Tasks 7.1–7.4 remain blocked by upstream
evidence and ALA public-product rights gates. Therefore no visual switch,
displayed fixed counts, or live update time is claimed. No model or Flickr API
call occurred. Task 7.5 remains unfinished at the UI level.
