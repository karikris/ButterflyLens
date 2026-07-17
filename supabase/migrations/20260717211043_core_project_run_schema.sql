-- ButterflyLens 3.1.1: typed project and run control state.
-- Public-schema tables are deliberately not exposed to browser roles yet.

create table public.projects (
  id bigint generated always as identity primary key,
  schema_version text not null default 'butterflylens-project:v1.0.0',
  project_id text not null,
  slug text not null,
  name text not null,
  description text not null default '',
  status text not null default 'draft',
  country_code text not null default 'AU',
  boundary_id text not null,
  boundary_version text not null,
  boundary_sha256 text not null,
  sensitive_coordinate_policy_version text not null,
  root_taxon_keys text[] not null,
  taxonomy_fingerprint text not null,
  search_plan_fingerprint text not null,
  public_discovery_claim text not null,
  data_policy_version text not null,
  consent_policy_version text not null,
  created_by uuid references auth.users (id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint projects_schema_version_check
    check (schema_version = 'butterflylens-project:v1.0.0'),
  constraint projects_project_id_check
    check (project_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint projects_slug_check
    check (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$' and length(slug) <= 80),
  constraint projects_name_check check (length(name) between 1 and 120),
  constraint projects_description_check check (length(description) <= 2000),
  constraint projects_status_check
    check (status in ('draft', 'active', 'paused', 'archived')),
  constraint projects_country_code_check check (country_code = 'AU'),
  constraint projects_boundary_id_check
    check (boundary_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint projects_boundary_version_check
    check (length(boundary_version) between 1 and 120),
  constraint projects_boundary_sha256_check
    check (boundary_sha256 ~ '^[0-9a-f]{64}$'),
  constraint projects_sensitive_coordinate_policy_version_check
    check (length(sensitive_coordinate_policy_version) between 1 and 120),
  constraint projects_root_taxon_keys_check
    check (cardinality(root_taxon_keys) > 0 and array_position(root_taxon_keys, null) is null),
  constraint projects_taxonomy_fingerprint_check
    check (taxonomy_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint projects_search_plan_fingerprint_check
    check (search_plan_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint projects_public_discovery_claim_check
    check (
      public_discovery_claim =
        'All butterfly candidate images discoverable through the published ButterflyLens Flickr search plan.'
    ),
  constraint projects_data_policy_version_check
    check (length(data_policy_version) between 1 and 120),
  constraint projects_consent_policy_version_check
    check (length(consent_policy_version) between 1 and 120),
  constraint projects_timestamps_check check (updated_at >= created_at),
  constraint projects_project_id_key unique (project_id),
  constraint projects_slug_key unique (slug)
);

create index projects_created_by_idx on public.projects (created_by)
where created_by is not null;

create table public.runs (
  id bigint generated always as identity primary key,
  schema_version text not null default 'butterflylens-run:v1.0.0',
  run_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_kind text not null,
  mode text not null,
  status text not null default 'queued',
  requested_actor_type text not null,
  requested_actor_id text,
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  engine_repository text not null,
  engine_commit text not null,
  engine_interface_version text not null,
  engine_command text not null,
  input_fingerprints text[] not null default '{}',
  error_code text,
  error_message text,
  error_retryable boolean,
  error_stage_id text,
  revision bigint not null default 1,
  constraint runs_schema_version_check
    check (schema_version = 'butterflylens-run:v1.0.0'),
  constraint runs_run_id_check
    check (run_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint runs_run_kind_check
    check (
      run_kind in (
        'taxonomy_pack', 'ala_baseline', 'reference_bank', 'flickr_discovery',
        'vision_pipeline', 'geographic_impact', 'quality_snapshot',
        'release_export', 'full_pipeline'
      )
    ),
  constraint runs_mode_check check (mode in ('live', 'submitted', 'replay')),
  constraint runs_status_check
    check (
      status in (
        'queued', 'leased', 'running', 'paused', 'cancelling', 'cancelled',
        'succeeded', 'failed'
      )
    ),
  constraint runs_requested_actor_check
    check (
      (requested_actor_type = 'system' and requested_actor_id is null)
      or (
        requested_actor_type in ('account', 'operator')
        and requested_actor_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
      )
    ),
  constraint runs_engine_repository_check
    check (length(engine_repository) between 1 and 200),
  constraint runs_engine_commit_check check (engine_commit ~ '^[0-9a-f]{40}$'),
  constraint runs_engine_interface_version_check
    check (length(engine_interface_version) between 1 and 120),
  constraint runs_engine_command_check
    check (length(engine_command) between 1 and 500),
  constraint runs_input_fingerprints_check
    check (array_position(input_fingerprints, null) is null),
  constraint runs_error_shape_check
    check (
      (
        error_code is null and error_message is null and error_retryable is null
        and error_stage_id is null
      )
      or (
        length(error_code) between 1 and 120
        and length(error_message) between 1 and 1000
        and error_retryable is not null
        and (
          error_stage_id is null
          or error_stage_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
        )
      )
    ),
  constraint runs_revision_check check (revision >= 1),
  constraint runs_queued_state_check
    check (
      status <> 'queued'
      or (started_at is null and finished_at is null and error_code is null)
    ),
  constraint runs_active_state_check
    check (
      status not in ('running', 'paused', 'cancelling')
      or (started_at is not null and finished_at is null)
    ),
  constraint runs_terminal_state_check
    check (
      status not in ('cancelled', 'succeeded', 'failed') or finished_at is not null
    ),
  constraint runs_failure_state_check check (status <> 'failed' or error_code is not null),
  constraint runs_success_state_check check (status <> 'succeeded' or error_code is null),
  constraint runs_timestamp_order_check
    check (
      updated_at >= requested_at
      and (started_at is null or started_at >= requested_at)
      and (finished_at is null or finished_at >= coalesce(started_at, requested_at))
    ),
  constraint runs_run_id_key unique (run_id)
);

create index runs_project_pk_requested_at_idx
on public.runs (project_pk, requested_at desc);

create index runs_active_status_idx
on public.runs (status, requested_at)
where status in ('queued', 'leased', 'running', 'paused', 'cancelling');

alter table public.projects enable row level security;
alter table public.runs enable row level security;

revoke all on table public.projects, public.runs from public, anon, authenticated;
revoke all on sequence public.projects_id_seq, public.runs_id_seq
from public, anon, authenticated;

grant select, insert, update, delete on table public.projects, public.runs
to service_role;
grant usage, select on sequence public.projects_id_seq, public.runs_id_seq
to service_role;

comment on table public.projects is
  'Versioned Australian ButterflyLens project scope; browser access remains denied until Task 3.1.6 policies.';
comment on table public.runs is
  'Mutable run control state; immutable stages, artifacts, and evidence events use separate tables.';
comment on column public.projects.created_by is
  'Nullable only for system-created projects; project membership and user roles are added with RLS policies.';
