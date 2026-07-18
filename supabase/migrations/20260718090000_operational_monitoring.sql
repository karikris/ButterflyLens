-- ButterflyLens 12.3: append-only, public-safe operational monitoring projection.
-- Raw heartbeat JSON, worker identity, queue items, errors, coordinates, and URLs
-- remain outside this table and outside the credential-free response boundary.

create table public.operational_monitoring_snapshots (
  id bigint generated always as identity primary key,
  monitoring_snapshot_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint references public.runs (id) on delete restrict,
  worker_heartbeat_pk bigint references public.worker_heartbeats (id) on delete restrict,
  observed_at timestamptz not null,

  heartbeat_state text not null,
  heartbeat_observed_at timestamptz,
  worker_state text,
  heartbeat_reason text not null,

  api_budget_state text not null,
  api_budget_limit bigint,
  api_budget_used bigint,
  api_budget_remaining bigint,
  api_budget_resets_at timestamptz,
  api_budget_reason text not null,

  stage_health_state text not null,
  current_stage text,
  stage_state text,
  healthy_stage_count bigint,
  failed_stage_count bigint,
  stage_health_reason text not null,

  queue_state text not null,
  queue_depth bigint,
  queue_capacity bigint,
  queue_reason text not null,

  failure_state text not null,
  failure_count bigint,
  failure_reason text not null,

  artifact_state text not null,
  artifact_fingerprint text,
  artifact_committed_at timestamptz,
  artifact_reason text not null,

  map_state text not null,
  map_fingerprint text,
  map_refreshed_at timestamptz,
  map_reason text not null,

  model_state text not null,
  yoloe_state text not null,
  bioclip_state text not null,
  model_reason text not null,

  resource_state text not null,
  free_disk_bytes bigint,
  process_rss_bytes bigint,
  memory_capacity_bytes bigint,
  mps_allocated_bytes bigint,
  mps_reserved_bytes bigint,
  resource_reason text not null,

  scientific_claim_allowed boolean not null default false,
  snapshot_fingerprint text not null,
  recorded_at timestamptz not null default now(),

  constraint operational_monitoring_snapshots_id_check
    check (monitoring_snapshot_id ~ '^blmon:v1:[0-9a-f]{24}$'),
  constraint operational_monitoring_snapshots_heartbeat_state_check
    check (heartbeat_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_worker_state_check
    check (
      worker_state is null
      or worker_state in ('starting', 'idle', 'leased', 'running', 'paused', 'draining', 'degraded')
    ),
  constraint operational_monitoring_snapshots_heartbeat_shape_check
    check (
      (
        heartbeat_state = 'unavailable'
        and heartbeat_observed_at is null
        and worker_state is null
        and worker_heartbeat_pk is null
      )
      or (
        heartbeat_state in ('available', 'degraded')
        and heartbeat_observed_at is not null
        and worker_state is not null
      )
    ),
  constraint operational_monitoring_snapshots_heartbeat_time_check
    check (heartbeat_observed_at is null or heartbeat_observed_at <= observed_at),

  constraint operational_monitoring_snapshots_api_state_check
    check (api_budget_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_api_shape_check
    check (
      (
        api_budget_state = 'unavailable'
        and api_budget_limit is null
        and api_budget_used is null
        and api_budget_remaining is null
        and api_budget_resets_at is null
      )
      or (
        api_budget_state in ('available', 'degraded')
        and api_budget_limit is not null
        and api_budget_used is not null
        and api_budget_remaining is not null
        and api_budget_used + api_budget_remaining = api_budget_limit
      )
    ),

  constraint operational_monitoring_snapshots_stage_state_check
    check (stage_health_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_stage_detail_check
    check (
      stage_state is null
      or stage_state in ('queued', 'running', 'paused', 'succeeded', 'failed', 'blocked', 'unavailable')
    ),
  constraint operational_monitoring_snapshots_stage_shape_check
    check (
      (
        stage_health_state = 'unavailable'
        and current_stage is null
        and stage_state is null
        and healthy_stage_count is null
        and failed_stage_count is null
      )
      or (
        stage_health_state in ('available', 'degraded')
        and healthy_stage_count is not null
        and failed_stage_count is not null
        and ((current_stage is null) = (stage_state is null))
      )
    ),
  constraint operational_monitoring_snapshots_current_stage_check
    check (current_stage is null or current_stage ~ '^[a-z0-9][a-z0-9._:-]{0,119}$'),

  constraint operational_monitoring_snapshots_queue_state_check
    check (queue_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_queue_shape_check
    check (
      (
        queue_state = 'unavailable'
        and queue_depth is null
        and queue_capacity is null
      )
      or (
        queue_state in ('available', 'degraded')
        and queue_depth is not null
        and queue_capacity is not null
        and queue_depth <= queue_capacity
      )
    ),

  constraint operational_monitoring_snapshots_failure_state_check
    check (failure_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_failure_shape_check
    check (
      (failure_state = 'unavailable' and failure_count is null)
      or (failure_state in ('available', 'degraded') and failure_count is not null)
    ),

  constraint operational_monitoring_snapshots_artifact_state_check
    check (artifact_state in ('available', 'submitted', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_artifact_shape_check
    check (
      (
        artifact_state = 'unavailable'
        and artifact_fingerprint is null
        and artifact_committed_at is null
      )
      or (
        artifact_state in ('available', 'submitted', 'degraded')
        and artifact_fingerprint ~ '^[0-9a-f]{64}$'
        and artifact_committed_at is not null
        and artifact_committed_at <= observed_at
      )
    ),
  constraint operational_monitoring_snapshots_map_state_check
    check (map_state in ('available', 'submitted', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_map_shape_check
    check (
      (
        map_state = 'unavailable'
        and map_fingerprint is null
        and map_refreshed_at is null
      )
      or (
        map_state in ('available', 'submitted', 'degraded')
        and map_fingerprint ~ '^[0-9a-f]{64}$'
        and map_refreshed_at is not null
        and map_refreshed_at <= observed_at
      )
    ),

  constraint operational_monitoring_snapshots_model_state_check
    check (model_state in ('available', 'unfinished', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_model_components_check
    check (
      yoloe_state in ('ready', 'unfinished', 'unavailable', 'failed')
      and bioclip_state in ('ready', 'unfinished', 'unavailable', 'failed')
      and (
        model_state <> 'unfinished'
        or (yoloe_state = 'unfinished' and bioclip_state = 'unfinished')
      )
    ),

  constraint operational_monitoring_snapshots_resource_state_check
    check (resource_state in ('available', 'degraded', 'unavailable')),
  constraint operational_monitoring_snapshots_resource_shape_check
    check (
      (
        resource_state = 'unavailable'
        and free_disk_bytes is null
        and process_rss_bytes is null
        and memory_capacity_bytes is null
        and mps_allocated_bytes is null
        and mps_reserved_bytes is null
      )
      or (
        resource_state in ('available', 'degraded')
        and free_disk_bytes is not null
        and process_rss_bytes is not null
        and memory_capacity_bytes is not null
      )
    ),

  constraint operational_monitoring_snapshots_nonnegative_counts_check
    check (
      api_budget_limit between 0 and 9007199254740991
      and api_budget_used between 0 and 9007199254740991
      and api_budget_remaining between 0 and 9007199254740991
      and healthy_stage_count between 0 and 9007199254740991
      and failed_stage_count between 0 and 9007199254740991
      and queue_depth between 0 and 9007199254740991
      and queue_capacity between 0 and 9007199254740991
      and failure_count between 0 and 9007199254740991
      and free_disk_bytes between 0 and 9007199254740991
      and process_rss_bytes between 0 and 9007199254740991
      and memory_capacity_bytes between 0 and 9007199254740991
      and mps_allocated_bytes between 0 and 9007199254740991
      and mps_reserved_bytes between 0 and 9007199254740991
    ),
  constraint operational_monitoring_snapshots_reasons_check
    check (
      length(heartbeat_reason) between 1 and 512
      and length(api_budget_reason) between 1 and 512
      and length(stage_health_reason) between 1 and 512
      and length(queue_reason) between 1 and 512
      and length(failure_reason) between 1 and 512
      and length(artifact_reason) between 1 and 512
      and length(map_reason) between 1 and 512
      and length(model_reason) between 1 and 512
      and length(resource_reason) between 1 and 512
    ),
  constraint operational_monitoring_snapshots_claim_check
    check (scientific_claim_allowed = false),
  constraint operational_monitoring_snapshots_fingerprint_check
    check (snapshot_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint operational_monitoring_snapshots_recording_check
    check (recorded_at >= observed_at),
  constraint operational_monitoring_snapshots_id_key unique (monitoring_snapshot_id),
  constraint operational_monitoring_snapshots_fingerprint_key unique (snapshot_fingerprint)
);

create index operational_monitoring_snapshots_project_observed_idx
on public.operational_monitoring_snapshots (project_pk, observed_at desc);
create index operational_monitoring_snapshots_run_pk_idx
on public.operational_monitoring_snapshots (run_pk)
where run_pk is not null;
create index operational_monitoring_snapshots_worker_heartbeat_pk_idx
on public.operational_monitoring_snapshots (worker_heartbeat_pk)
where worker_heartbeat_pk is not null;

create or replace function private.validate_operational_monitoring_lineage()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  run_project_pk bigint;
  heartbeat_run_pk bigint;
begin
  if new.run_pk is not null then
    select run.project_pk into run_project_pk
    from public.runs run
    where run.id = new.run_pk;
    if run_project_pk is distinct from new.project_pk then
      raise exception using
        errcode = '23514',
        message = 'monitoring run lineage does not match project';
    end if;
  end if;

  if new.worker_heartbeat_pk is not null then
    select stage.run_pk into heartbeat_run_pk
    from public.worker_heartbeats heartbeat
    left join public.pipeline_stages stage on stage.id = heartbeat.pipeline_stage_pk
    where heartbeat.id = new.worker_heartbeat_pk;
    if heartbeat_run_pk is not null and heartbeat_run_pk is distinct from new.run_pk then
      raise exception using
        errcode = '23514',
        message = 'monitoring heartbeat lineage does not match run';
    end if;
  end if;
  return new;
end;
$$;

create trigger operational_monitoring_snapshots_validate_lineage
before insert on public.operational_monitoring_snapshots
for each row execute function private.validate_operational_monitoring_lineage();

create or replace function private.reject_operational_monitoring_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception using
    errcode = '55000',
    message = 'operational monitoring snapshots are append only';
end;
$$;

create trigger operational_monitoring_snapshots_reject_mutation
before update or delete on public.operational_monitoring_snapshots
for each row execute function private.reject_operational_monitoring_mutation();

alter table public.operational_monitoring_snapshots enable row level security;

revoke all on table public.operational_monitoring_snapshots
from public, anon, authenticated;
revoke all on sequence public.operational_monitoring_snapshots_id_seq
from public, anon, authenticated;
revoke all on function private.validate_operational_monitoring_lineage()
from public, anon, authenticated;
revoke all on function private.reject_operational_monitoring_mutation()
from public, anon, authenticated;

grant select, insert on table public.operational_monitoring_snapshots to service_role;
grant usage, select on sequence public.operational_monitoring_snapshots_id_seq to service_role;
grant execute on function private.validate_operational_monitoring_lineage() to service_role;
grant execute on function private.reject_operational_monitoring_mutation() to service_role;

comment on table public.operational_monitoring_snapshots is
  'Append-only public-safe aggregate monitoring; not a scientific, identity, occurrence, or dataset-quality claim.';
comment on column public.operational_monitoring_snapshots.worker_heartbeat_pk is
  'Optional private lineage only; no worker identifier or raw heartbeat JSON crosses the public status boundary.';
