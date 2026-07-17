-- ButterflyLens 3.1.3: fingerprinted media, model-state, and fenced worker records.
-- This migration defines persistence only. It does not run YOLOE or BioCLIP.

create table public.media_objects (
  id bigint generated always as identity primary key,
  media_object_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  flickr_photo_pk bigint references public.flickr_photos (id) on delete restrict,
  parent_media_pk bigint references public.media_objects (id) on delete restrict,
  source_kind text not null,
  object_kind text not null,
  storage_backend text not null,
  storage_key text,
  media_state text not null default 'pending',
  content_sha256 text,
  byte_count bigint,
  media_type text,
  width_pixels integer,
  height_pixels integer,
  perceptual_hash text,
  perceptual_hash_version text,
  decode_status text not null default 'pending',
  rights_fingerprint text not null,
  rights_status text not null default 'unknown',
  download_allowed boolean not null default false,
  model_inference_allowed boolean not null default false,
  display_allowed boolean not null default false,
  redistribution_allowed boolean not null default false,
  media_fingerprint text not null,
  created_at timestamptz not null default now(),
  committed_at timestamptz,
  removed_at timestamptz,
  constraint media_objects_id_check
    check (media_object_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint media_objects_source_kind_check
    check (source_kind in ('flickr', 'reference', 'derived')),
  constraint media_objects_flickr_source_check
    check ((source_kind = 'flickr') = (flickr_photo_pk is not null)),
  constraint media_objects_object_kind_check
    check (
      object_kind in (
        'source_image', 'private_review_image', 'public_thumbnail',
        'full_frame_visual_input'
      )
    ),
  constraint media_objects_storage_backend_check
    check (storage_backend in ('b2', 'local_cache', 'external')),
  constraint media_objects_storage_key_check
    check (
      storage_key is null
      or (
        length(storage_key) between 1 and 1000
        and storage_key !~ '://'
        and storage_key !~ '(^|/)\.\.(/|$)'
      )
    ),
  constraint media_objects_state_check
    check (media_state in ('pending', 'committed', 'quarantined', 'removed')),
  constraint media_objects_content_shape_check
    check (
      (content_sha256 is null and byte_count is null and media_type is null)
      or (
        content_sha256 ~ '^[0-9a-f]{64}$'
        and byte_count >= 0
        and length(media_type) between 3 and 120
      )
    ),
  constraint media_objects_dimensions_check
    check (
      (width_pixels is null and height_pixels is null)
      or (width_pixels > 0 and height_pixels > 0)
    ),
  constraint media_objects_perceptual_hash_check
    check (
      (perceptual_hash is null and perceptual_hash_version is null)
      or (
        length(perceptual_hash) between 8 and 256
        and length(perceptual_hash_version) between 1 and 120
      )
    ),
  constraint media_objects_decode_status_check
    check (decode_status in ('pending', 'valid', 'invalid', 'download_failed', 'not_applicable')),
  constraint media_objects_rights_fingerprint_check
    check (rights_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_objects_rights_status_check
    check (rights_status in ('unknown', 'allowed', 'blocked', 'quarantined', 'removed')),
  constraint media_objects_rights_gate_check
    check (
      rights_status = 'allowed'
      or not (download_allowed or model_inference_allowed or display_allowed or redistribution_allowed)
    ),
  constraint media_objects_fingerprint_check
    check (media_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_objects_commit_shape_check
    check (
      (media_state = 'pending' and committed_at is null)
      or (
        media_state in ('committed', 'quarantined', 'removed')
        and committed_at is not null
        and storage_key is not null
        and content_sha256 is not null
      )
    ),
  constraint media_objects_removal_check
    check (
      (media_state = 'removed' and rights_status = 'removed' and removed_at is not null)
      or (media_state <> 'removed' and removed_at is null)
    ),
  constraint media_objects_timestamp_check
    check (
      (committed_at is null or committed_at >= created_at)
      and (removed_at is null or removed_at >= committed_at)
    ),
  constraint media_objects_id_key unique (media_object_id),
  constraint media_objects_fingerprint_key unique (media_fingerprint)
);

create index media_objects_project_pk_idx on public.media_objects (project_pk);
create index media_objects_run_pk_idx on public.media_objects (run_pk);
create index media_objects_flickr_photo_pk_idx on public.media_objects (flickr_photo_pk)
where flickr_photo_pk is not null;
create index media_objects_parent_media_pk_idx on public.media_objects (parent_media_pk)
where parent_media_pk is not null;
create index media_objects_content_sha256_idx on public.media_objects (content_sha256)
where content_sha256 is not null;
create index media_objects_pending_idx on public.media_objects (run_pk, id)
where media_state = 'pending';

create table public.duplicate_groups (
  id bigint generated always as identity primary key,
  duplicate_group_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  representative_media_pk bigint not null references public.media_objects (id) on delete restrict,
  grouping_kind text not null,
  algorithm text not null,
  algorithm_version text not null,
  threshold numeric(12, 6),
  group_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint duplicate_groups_id_check
    check (duplicate_group_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint duplicate_groups_kind_check
    check (grouping_kind in ('exact_content', 'perceptual_candidate', 'confirmed_duplicate')),
  constraint duplicate_groups_algorithm_check
    check (length(algorithm) between 1 and 120 and length(algorithm_version) between 1 and 120),
  constraint duplicate_groups_threshold_check check (threshold is null or threshold >= 0),
  constraint duplicate_groups_fingerprint_check
    check (group_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint duplicate_groups_id_key unique (duplicate_group_id),
  constraint duplicate_groups_fingerprint_key unique (group_fingerprint)
);

create index duplicate_groups_project_pk_idx on public.duplicate_groups (project_pk);
create index duplicate_groups_run_pk_idx on public.duplicate_groups (run_pk);
create index duplicate_groups_representative_media_pk_idx
on public.duplicate_groups (representative_media_pk);

create table public.duplicate_group_members (
  id bigint generated always as identity primary key,
  duplicate_group_pk bigint not null references public.duplicate_groups (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  member_role text not null,
  distance numeric(12, 6),
  membership_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint duplicate_group_members_role_check
    check (member_role in ('representative', 'member', 'candidate')),
  constraint duplicate_group_members_distance_check check (distance is null or distance >= 0),
  constraint duplicate_group_members_fingerprint_check
    check (membership_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint duplicate_group_members_pair_key unique (duplicate_group_pk, media_object_pk),
  constraint duplicate_group_members_fingerprint_key unique (membership_fingerprint)
);

create index duplicate_group_members_group_pk_idx
on public.duplicate_group_members (duplicate_group_pk);
create index duplicate_group_members_media_pk_idx
on public.duplicate_group_members (media_object_pk);

create table public.pipeline_stages (
  id bigint generated always as identity primary key,
  pipeline_stage_id text not null,
  run_pk bigint not null references public.runs (id) on delete restrict,
  stage_kind text not null,
  partition_key text not null default 'default',
  attempt integer not null default 1,
  status text not null default 'planned',
  status_reason text not null default '',
  work_fingerprint text not null,
  checkpoint_fingerprint text,
  output_fingerprint text,
  queued_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint pipeline_stages_id_check
    check (pipeline_stage_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint pipeline_stages_kind_check
    check (
      stage_kind in (
        'metadata', 'download', 'media_validation', 'deduplication',
        'yoloe_route', 'full_frame_transformation', 'bioclip_embedding',
        'candidate_score', 'artifact_commit', 'cache_cleanup'
      )
    ),
  constraint pipeline_stages_partition_check check (length(partition_key) between 1 and 240),
  constraint pipeline_stages_attempt_check check (attempt >= 1),
  constraint pipeline_stages_status_check
    check (
      status in (
        'planned', 'queued', 'leased', 'running', 'checkpointed', 'succeeded',
        'failed', 'blocked', 'skipped_unfinished', 'cancelled'
      )
    ),
  constraint pipeline_stages_status_reason_check check (length(status_reason) <= 1000),
  constraint pipeline_stages_work_fingerprint_check
    check (work_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint pipeline_stages_checkpoint_fingerprint_check
    check (checkpoint_fingerprint is null or checkpoint_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint pipeline_stages_output_fingerprint_check
    check (output_fingerprint is null or output_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint pipeline_stages_started_check
    check (status not in ('running', 'checkpointed', 'succeeded', 'failed', 'cancelled') or started_at is not null),
  constraint pipeline_stages_finished_check
    check (
      (status in ('succeeded', 'failed', 'blocked', 'skipped_unfinished', 'cancelled'))
      = (finished_at is not null)
    ),
  constraint pipeline_stages_success_check
    check (status <> 'succeeded' or output_fingerprint is not null),
  constraint pipeline_stages_unfinished_check
    check (
      status not in ('blocked', 'skipped_unfinished')
      or (length(status_reason) > 0 and output_fingerprint is null)
    ),
  constraint pipeline_stages_timestamp_check
    check (
      updated_at >= queued_at
      and (started_at is null or started_at >= queued_at)
      and (finished_at is null or finished_at >= coalesce(started_at, queued_at))
    ),
  constraint pipeline_stages_id_key unique (pipeline_stage_id),
  constraint pipeline_stages_work_attempt_key
    unique (run_pk, stage_kind, partition_key, attempt),
  constraint pipeline_stages_work_fingerprint_key unique (work_fingerprint)
);

create index pipeline_stages_run_pk_idx on public.pipeline_stages (run_pk, id);
create index pipeline_stages_queue_idx on public.pipeline_stages (status, queued_at)
where status in ('planned', 'queued', 'checkpointed');

create table public.worker_leases (
  id bigint generated always as identity primary key,
  worker_lease_id text not null,
  pipeline_stage_pk bigint not null references public.pipeline_stages (id) on delete restrict,
  worker_id text not null,
  lease_revision bigint not null,
  fencing_token_sha256 text not null,
  state text not null default 'active',
  is_current boolean not null default true,
  acquired_at timestamptz not null default now(),
  expires_at timestamptz not null,
  released_at timestamptz,
  release_reason text,
  checkpoint_fingerprint text,
  constraint worker_leases_id_check
    check (worker_lease_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint worker_leases_worker_id_check
    check (worker_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint worker_leases_revision_check check (lease_revision >= 1),
  constraint worker_leases_fencing_token_check
    check (fencing_token_sha256 ~ '^[0-9a-f]{64}$'),
  constraint worker_leases_state_check
    check (state in ('active', 'released', 'expired', 'revoked')),
  constraint worker_leases_state_shape_check
    check (
      (state = 'active' and is_current and released_at is null and release_reason is null)
      or (
        state <> 'active' and not is_current and released_at is not null
        and length(release_reason) between 1 and 500
      )
    ),
  constraint worker_leases_expiry_check check (expires_at > acquired_at),
  constraint worker_leases_release_check check (released_at is null or released_at >= acquired_at),
  constraint worker_leases_checkpoint_check
    check (checkpoint_fingerprint is null or checkpoint_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint worker_leases_id_key unique (worker_lease_id),
  constraint worker_leases_revision_key unique (pipeline_stage_pk, lease_revision),
  constraint worker_leases_fencing_token_key unique (fencing_token_sha256)
);

create index worker_leases_pipeline_stage_pk_idx on public.worker_leases (pipeline_stage_pk);
create index worker_leases_worker_id_idx on public.worker_leases (worker_id, acquired_at desc);
create unique index worker_leases_one_current_idx on public.worker_leases (pipeline_stage_pk)
where is_current;
create index worker_leases_expiry_idx on public.worker_leases (expires_at)
where is_current;

create table public.worker_heartbeats (
  id bigint generated always as identity primary key,
  worker_heartbeat_id text not null,
  worker_id text not null,
  worker_lease_pk bigint references public.worker_leases (id) on delete restrict,
  pipeline_stage_pk bigint references public.pipeline_stages (id) on delete restrict,
  observed_at timestamptz not null,
  health_state text not null,
  machine_fingerprint text not null,
  current_stage text,
  metrics jsonb not null default '{}'::jsonb,
  model_status jsonb not null default '{}'::jsonb,
  graceful_shutdown boolean not null default false,
  heartbeat_fingerprint text not null,
  recorded_at timestamptz not null default now(),
  constraint worker_heartbeats_id_check
    check (worker_heartbeat_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint worker_heartbeats_worker_id_check
    check (worker_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint worker_heartbeats_health_check
    check (health_state in ('healthy', 'degraded', 'draining', 'offline_reported')),
  constraint worker_heartbeats_machine_fingerprint_check
    check (machine_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint worker_heartbeats_stage_check
    check (current_stage is null or length(current_stage) between 1 and 120),
  constraint worker_heartbeats_json_check
    check (jsonb_typeof(metrics) = 'object' and jsonb_typeof(model_status) = 'object'),
  constraint worker_heartbeats_no_secrets_check
    check (
      not (metrics ?| array['api_key', 'auth_token', 'oauth_token', 'secret'])
      and not (model_status ?| array['api_key', 'auth_token', 'oauth_token', 'secret'])
    ),
  constraint worker_heartbeats_fingerprint_check
    check (heartbeat_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint worker_heartbeats_recording_check check (recorded_at >= observed_at),
  constraint worker_heartbeats_id_key unique (worker_heartbeat_id),
  constraint worker_heartbeats_fingerprint_key unique (heartbeat_fingerprint)
);

create index worker_heartbeats_worker_id_observed_idx
on public.worker_heartbeats (worker_id, observed_at desc);
create index worker_heartbeats_worker_lease_pk_idx
on public.worker_heartbeats (worker_lease_pk)
where worker_lease_pk is not null;
create index worker_heartbeats_pipeline_stage_pk_idx
on public.worker_heartbeats (pipeline_stage_pk)
where pipeline_stage_pk is not null;

create table public.model_evidence (
  id bigint generated always as identity primary key,
  model_evidence_id text not null,
  pipeline_stage_pk bigint not null references public.pipeline_stages (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  evidence_kind text not null,
  evidence_status text not null,
  status_reason text not null default '',
  model_id text,
  model_revision text,
  weights_sha256 text,
  input_fingerprint text,
  output_content_sha256 text,
  raw_score double precision,
  calibrated_probability double precision,
  calibrator_fingerprint text,
  evidence_payload jsonb not null default '{}'::jsonb,
  evidence_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint model_evidence_id_check
    check (model_evidence_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint model_evidence_kind_check
    check (evidence_kind in ('yoloe_route', 'bioclip_embedding', 'prototype', 'candidate_score')),
  constraint model_evidence_status_check
    check (evidence_status in ('completed', 'failed', 'blocked', 'skipped_unfinished')),
  constraint model_evidence_status_reason_check check (length(status_reason) <= 1000),
  constraint model_evidence_weights_check
    check (weights_sha256 is null or weights_sha256 ~ '^[0-9a-f]{64}$'),
  constraint model_evidence_input_check
    check (input_fingerprint is null or input_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint model_evidence_output_check
    check (output_content_sha256 is null or output_content_sha256 ~ '^[0-9a-f]{64}$'),
  constraint model_evidence_raw_score_check
    check (
      raw_score is null
      or (
        raw_score <> 'Infinity'::float8
        and raw_score <> '-Infinity'::float8
        and raw_score <> 'NaN'::float8
      )
    ),
  constraint model_evidence_probability_check
    check (calibrated_probability is null or calibrated_probability between 0 and 1),
  constraint model_evidence_calibration_check
    check (
      (calibrated_probability is null and calibrator_fingerprint is null)
      or (
        calibrated_probability is not null
        and calibrator_fingerprint ~ '^[0-9a-f]{64}$'
      )
    ),
  constraint model_evidence_payload_check check (jsonb_typeof(evidence_payload) = 'object'),
  constraint model_evidence_no_secrets_check
    check (not (evidence_payload ?| array['api_key', 'auth_token', 'oauth_token', 'secret'])),
  constraint model_evidence_completed_shape_check
    check (
      evidence_status <> 'completed'
      or (
        model_id is not null
        and length(model_id) between 1 and 240
        and model_revision is not null
        and length(model_revision) between 1 and 240
        and weights_sha256 is not null
        and input_fingerprint is not null
        and output_content_sha256 is not null
      )
    ),
  constraint model_evidence_unfinished_shape_check
    check (
      evidence_status = 'completed'
      or (
        length(status_reason) > 0
        and output_content_sha256 is null
        and raw_score is null
        and calibrated_probability is null
      )
    ),
  constraint model_evidence_fingerprint_check
    check (evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint model_evidence_id_key unique (model_evidence_id),
  constraint model_evidence_fingerprint_key unique (evidence_fingerprint)
);

create index model_evidence_pipeline_stage_pk_idx
on public.model_evidence (pipeline_stage_pk);
create index model_evidence_media_object_pk_idx on public.model_evidence (media_object_pk);
create index model_evidence_species_pk_idx on public.model_evidence (species_pk)
where species_pk is not null;

alter table public.media_objects enable row level security;
alter table public.duplicate_groups enable row level security;
alter table public.duplicate_group_members enable row level security;
alter table public.pipeline_stages enable row level security;
alter table public.worker_leases enable row level security;
alter table public.worker_heartbeats enable row level security;
alter table public.model_evidence enable row level security;

revoke all on table public.media_objects, public.duplicate_groups,
  public.duplicate_group_members, public.pipeline_stages, public.worker_leases,
  public.worker_heartbeats, public.model_evidence
from public, anon, authenticated;
revoke all on sequence public.media_objects_id_seq, public.duplicate_groups_id_seq,
  public.duplicate_group_members_id_seq, public.pipeline_stages_id_seq,
  public.worker_leases_id_seq, public.worker_heartbeats_id_seq,
  public.model_evidence_id_seq
from public, anon, authenticated;

grant select, insert, update, delete on table public.media_objects,
  public.pipeline_stages, public.worker_leases to service_role;
grant select, insert on table public.duplicate_groups,
  public.duplicate_group_members, public.worker_heartbeats, public.model_evidence
to service_role;
grant usage, select on sequence public.media_objects_id_seq,
  public.duplicate_groups_id_seq, public.duplicate_group_members_id_seq,
  public.pipeline_stages_id_seq, public.worker_leases_id_seq,
  public.worker_heartbeats_id_seq, public.model_evidence_id_seq
to service_role;

comment on table public.media_objects is
  'Content-addressed media metadata; source rights remain attached to every derived object.';
comment on table public.duplicate_groups is
  'Fingerprint-preserving exact or perceptual duplicate groups; membership is never discarded.';
comment on table public.worker_leases is
  'Time-bounded fenced stage leases; only the current monotonically revised lease may commit.';
comment on table public.worker_heartbeats is
  'Append-only observed worker health; presence of a row is not a scientific or future-availability claim.';
comment on table public.model_evidence is
  'Raw fingerprinted model output or explicit unfinished state; no calibrated or human-verification claim is implied.';
comment on column public.pipeline_stages.stage_kind is
  'YOLOE and BioCLIP values reserve typed unfinished state only; this migration performs no model execution.';
