alter table public.api_requests
drop constraint api_requests_run_fingerprint_key;

alter table public.api_requests
add constraint api_requests_run_fingerprint_attempt_key
unique (run_pk, request_fingerprint, retry_count);

alter table public.api_requests
add constraint api_requests_retry_lineage_check
check (
  (retry_count = 0 and retry_of_request_pk is null)
  or (retry_count > 0 and retry_of_request_pk is not null)
);

comment on constraint api_requests_retry_lineage_check on public.api_requests is
  'Initial sends have no parent; every numbered retry references a prior API request and remains a distinct budgeted attempt.';
