-- ButterflyLens 12.1: audited B2 signing and narrow server-run controls.
-- Edge Functions authenticate users; only the service role writes receipts.

create table public.b2_signing_receipts (
  id bigint generated always as identity primary key,
  signing_receipt_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  auth_user_id uuid not null references auth.users (id) on delete restrict,
  method text not null,
  ttl_seconds integer not null,
  issued_at timestamptz not null,
  expires_at timestamptz not null,
  request_fingerprint text not null,
  constraint b2_signing_receipts_id_check
    check (
        signing_receipt_id ~
        '^b2sign:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    ),
  constraint b2_signing_receipts_method_check check (method in ('GET', 'HEAD')),
  constraint b2_signing_receipts_ttl_check check (ttl_seconds between 1 and 900),
  constraint b2_signing_receipts_expiry_check
    check (expires_at = issued_at + make_interval(secs => ttl_seconds)),
  constraint b2_signing_receipts_fingerprint_check
    check (request_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint b2_signing_receipts_id_key unique (signing_receipt_id),
  constraint b2_signing_receipts_fingerprint_key unique (request_fingerprint)
);

create index b2_signing_receipts_project_pk_idx
on public.b2_signing_receipts (project_pk, issued_at desc);
create index b2_signing_receipts_media_object_pk_idx
on public.b2_signing_receipts (media_object_pk, issued_at desc);
create index b2_signing_receipts_auth_user_id_idx
on public.b2_signing_receipts (auth_user_id, issued_at desc);

create table public.server_action_receipts (
  id bigint generated always as identity primary key,
  server_action_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  requested_by uuid not null references auth.users (id) on delete restrict,
  action text not null,
  expected_revision bigint not null,
  prior_status text not null default '',
  result_status text not null default '',
  result_revision bigint not null default 0,
  request_fingerprint text not null,
  applied_at timestamptz not null default now(),
  constraint server_action_receipts_id_check
    check (server_action_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint server_action_receipts_action_check
    check (action in ('pause_run', 'resume_run', 'cancel_run')),
  constraint server_action_receipts_expected_revision_check
    check (expected_revision >= 1),
  constraint server_action_receipts_prior_status_check
    check (prior_status in ('queued', 'leased', 'running', 'paused', 'cancelling')),
  constraint server_action_receipts_result_status_check
    check (result_status in ('running', 'paused', 'cancelled')),
  constraint server_action_receipts_result_revision_check
    check (result_revision = expected_revision + 1),
  constraint server_action_receipts_fingerprint_check
    check (request_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint server_action_receipts_id_key unique (server_action_id),
  constraint server_action_receipts_fingerprint_key unique (request_fingerprint)
);

create index server_action_receipts_project_pk_idx
on public.server_action_receipts (project_pk, applied_at desc);
create index server_action_receipts_run_pk_idx
on public.server_action_receipts (run_pk, applied_at desc);
create index server_action_receipts_requested_by_idx
on public.server_action_receipts (requested_by, applied_at desc);

create function private.apply_controlled_server_action()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_status text;
  target_revision bigint;
  next_status text;
begin
  perform pg_catalog.pg_advisory_xact_lock(
    pg_catalog.hashtextextended(new.server_action_id, 0)
  );
  if exists (
    select 1 from public.server_action_receipts receipt
    where receipt.server_action_id = new.server_action_id
  ) then
    raise exception 'controlled server action ID already exists'
      using errcode = '23505';
  end if;

  if not exists (
    select 1
    from public.project_memberships membership
    where membership.project_pk = new.project_pk
      and membership.auth_user_id = new.requested_by
      and membership.status = 'active'
      and membership.role in ('curator', 'administrator')
  ) then
    raise exception 'verified actor lacks run-control authority'
      using errcode = '42501';
  end if;

  select run.status, run.revision
  into target_status, target_revision
  from public.runs run
  where run.id = new.run_pk and run.project_pk = new.project_pk
  for update;

  if not found then
    raise exception 'controlled run does not exist in project'
      using errcode = '23503';
  end if;
  if target_revision <> new.expected_revision then
    raise exception 'controlled run revision is stale'
      using errcode = '40001';
  end if;

  next_status := case new.action
    when 'pause_run' then
      case when target_status = 'running' then 'paused' else null end
    when 'resume_run' then
      case when target_status = 'paused' then 'running' else null end
    when 'cancel_run' then
      case when target_status in (
        'queued', 'leased', 'running', 'paused', 'cancelling'
      ) then 'cancelled' else null end
    else null
  end;

  if next_status is null then
    raise exception 'controlled run action is invalid for current state'
      using errcode = '23514';
  end if;

  update public.runs
  set status = next_status,
      finished_at = case when next_status = 'cancelled' then now() else null end,
      updated_at = now(),
      revision = revision + 1
  where id = new.run_pk;

  new.prior_status := target_status;
  new.result_status := next_status;
  new.result_revision := target_revision + 1;
  new.applied_at := now();
  return new;
end;
$$;

create trigger server_action_receipts_apply
before insert on public.server_action_receipts
for each row execute function private.apply_controlled_server_action();

create function private.reject_service_receipt_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'service receipts are append only' using errcode = '55000';
end;
$$;

create trigger server_action_receipts_reject_mutation
before update or delete on public.server_action_receipts
for each row execute function private.reject_service_receipt_mutation();

create trigger b2_signing_receipts_reject_mutation
before update or delete on public.b2_signing_receipts
for each row execute function private.reject_service_receipt_mutation();

alter table public.b2_signing_receipts enable row level security;
alter table public.server_action_receipts enable row level security;

create policy b2_signing_receipts_self_read
on public.b2_signing_receipts for select to authenticated
using (auth_user_id = (select auth.uid()));

create policy b2_signing_receipts_curator_read
on public.b2_signing_receipts for select to authenticated
using ((select private.has_project_role(
  project_pk, array['curator', 'administrator']::text[]
)));

create policy server_action_receipts_self_read
on public.server_action_receipts for select to authenticated
using (requested_by = (select auth.uid()));

create policy server_action_receipts_curator_read
on public.server_action_receipts for select to authenticated
using ((select private.has_project_role(
  project_pk, array['curator', 'administrator']::text[]
)));

revoke all on table public.b2_signing_receipts,
  public.server_action_receipts from public, anon, authenticated;
revoke all on sequence public.b2_signing_receipts_id_seq,
  public.server_action_receipts_id_seq from public, anon, authenticated;

grant select on table public.b2_signing_receipts,
  public.server_action_receipts to authenticated;
grant select, insert on table public.b2_signing_receipts,
  public.server_action_receipts to service_role;
grant usage, select on sequence public.b2_signing_receipts_id_seq,
  public.server_action_receipts_id_seq to service_role;

revoke all on function private.apply_controlled_server_action(),
  private.reject_service_receipt_mutation()
from public, anon, authenticated;
grant execute on function private.apply_controlled_server_action(),
  private.reject_service_receipt_mutation() to service_role;

comment on table public.b2_signing_receipts is
  'Append-only private-object signing receipts; signed URLs, query strings, credentials, and storage keys are never persisted.';
comment on table public.server_action_receipts is
  'Append-only expected-revision receipts for the closed pause, resume, and cancel run-control boundary.';
