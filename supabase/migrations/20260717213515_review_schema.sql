-- ButterflyLens 3.1.4: independent review, append-only decisions, and private quality evidence.

create table public.reviewer_profiles (
  id bigint generated always as identity primary key,
  reviewer_profile_id text not null,
  auth_user_id uuid not null references auth.users (id) on delete restrict,
  public_name text not null,
  role text not null default 'reviewer',
  status text not null default 'active',
  qualification_state text not null default 'unverified',
  qualification_evidence jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint reviewer_profiles_id_check
    check (reviewer_profile_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint reviewer_profiles_public_name_check check (length(public_name) between 2 and 80),
  constraint reviewer_profiles_role_check
    check (role in ('reviewer', 'expert', 'curator', 'administrator')),
  constraint reviewer_profiles_status_check
    check (status in ('active', 'paused', 'suspended', 'retired')),
  constraint reviewer_profiles_qualification_check
    check (qualification_state in ('unverified', 'pending', 'verified', 'expired', 'revoked')),
  constraint reviewer_profiles_qualification_evidence_check
    check (jsonb_typeof(qualification_evidence) = 'object'),
  constraint reviewer_profiles_no_secrets_check
    check (not (qualification_evidence ?| array['api_key', 'auth_token', 'oauth_token', 'secret'])),
  constraint reviewer_profiles_role_qualification_check
    check (role not in ('expert', 'curator') or qualification_state = 'verified'),
  constraint reviewer_profiles_timestamp_check check (updated_at >= created_at),
  constraint reviewer_profiles_id_key unique (reviewer_profile_id),
  constraint reviewer_profiles_auth_user_key unique (auth_user_id),
  constraint reviewer_profiles_public_name_key unique (public_name)
);

create index reviewer_profiles_active_role_idx on public.reviewer_profiles (role, id)
where status = 'active';

create table public.verification_campaigns (
  id bigint generated always as identity primary key,
  verification_campaign_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  created_by_reviewer_pk bigint references public.reviewer_profiles (id) on delete restrict,
  campaign_kind text not null,
  name text not null,
  question text not null,
  status text not null default 'draft',
  target_review_count smallint not null,
  minimum_qualified_review_count smallint not null default 0,
  expert_gate_required boolean not null default false,
  blind_model_label boolean not null default true,
  blind_model_score boolean not null default true,
  blind_query_term boolean not null default true,
  blind_source_comment boolean not null default true,
  blind_peer_decisions boolean not null default true,
  sampling_stratum text,
  inclusion_probability double precision,
  campaign_fingerprint text not null,
  created_at timestamptz not null default now(),
  opens_at timestamptz,
  closes_at timestamptz,
  constraint verification_campaigns_id_check
    check (verification_campaign_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint verification_campaigns_kind_check
    check (
      campaign_kind in (
        'ordinary_image', 'disagreement', 'potential_gap', 'reference_image',
        'high_impact_release', 'representative_audit', 'targeted_failure_discovery',
        'reviewer_control'
      )
    ),
  constraint verification_campaigns_text_check
    check (length(name) between 1 and 160 and length(question) between 1 and 1000),
  constraint verification_campaigns_status_check
    check (status in ('draft', 'open', 'paused', 'closed', 'cancelled')),
  constraint verification_campaigns_counts_check
    check (
      target_review_count between 1 and 20
      and minimum_qualified_review_count between 0 and target_review_count
    ),
  constraint verification_campaigns_expert_gate_check
    check (not expert_gate_required or minimum_qualified_review_count >= 1),
  constraint verification_campaigns_sampling_check
    check (
      (sampling_stratum is null and inclusion_probability is null)
      or (
        sampling_stratum is not null
        and length(sampling_stratum) between 1 and 240
        and inclusion_probability is not null
        and inclusion_probability > 0 and inclusion_probability <= 1
      )
    ),
  constraint verification_campaigns_fingerprint_check
    check (campaign_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint verification_campaigns_window_check
    check (closes_at is null or (opens_at is not null and closes_at > opens_at)),
  constraint verification_campaigns_id_key unique (verification_campaign_id),
  constraint verification_campaigns_fingerprint_key unique (campaign_fingerprint)
);

create index verification_campaigns_project_pk_idx
on public.verification_campaigns (project_pk);
create index verification_campaigns_species_pk_idx
on public.verification_campaigns (species_pk) where species_pk is not null;
create index verification_campaigns_creator_pk_idx
on public.verification_campaigns (created_by_reviewer_pk)
where created_by_reviewer_pk is not null;
create index verification_campaigns_open_idx
on public.verification_campaigns (project_pk, opens_at, id) where status = 'open';

create table public.assignments (
  id bigint generated always as identity primary key,
  assignment_id text not null,
  verification_campaign_pk bigint not null references public.verification_campaigns (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  reviewer_profile_pk bigint not null references public.reviewer_profiles (id) on delete restrict,
  assignment_sequence smallint not null,
  status text not null default 'assigned',
  blind_payload_fingerprint text not null,
  assignment_fingerprint text not null,
  assigned_at timestamptz not null default now(),
  due_at timestamptz,
  responded_at timestamptz,
  constraint assignments_id_check
    check (assignment_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint assignments_sequence_check check (assignment_sequence >= 1),
  constraint assignments_status_check
    check (status in ('assigned', 'opened', 'responded', 'expired', 'withdrawn')),
  constraint assignments_blind_fingerprint_check
    check (blind_payload_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint assignments_fingerprint_check
    check (assignment_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint assignments_response_check
    check ((status = 'responded') = (responded_at is not null)),
  constraint assignments_timestamps_check
    check (
      (due_at is null or due_at > assigned_at)
      and (responded_at is null or responded_at >= assigned_at)
    ),
  constraint assignments_id_key unique (assignment_id),
  constraint assignments_reviewer_independence_key
    unique (verification_campaign_pk, media_object_pk, reviewer_profile_pk),
  constraint assignments_sequence_key
    unique (verification_campaign_pk, media_object_pk, assignment_sequence),
  constraint assignments_fingerprint_key unique (assignment_fingerprint),
  constraint assignments_review_identity_key
    unique (id, verification_campaign_pk, media_object_pk, reviewer_profile_pk)
);

create index assignments_campaign_pk_idx on public.assignments (verification_campaign_pk);
create index assignments_media_object_pk_idx on public.assignments (media_object_pk);
create index assignments_reviewer_profile_pk_idx
on public.assignments (reviewer_profile_pk, assigned_at desc);
create index assignments_open_idx on public.assignments (reviewer_profile_pk, assigned_at)
where status in ('assigned', 'opened');

create table public.review_events (
  id bigint generated always as identity primary key,
  review_event_id text not null,
  assignment_pk bigint not null,
  verification_campaign_pk bigint not null,
  media_object_pk bigint not null,
  reviewer_profile_pk bigint not null,
  question text not null,
  image_sha256 text not null,
  decision text not null,
  alternative_species_pk bigint references public.species (id) on delete restrict,
  comment text not null default '',
  confidence smallint,
  decided_at timestamptz not null,
  duration_ms integer,
  supersedes_event_pk bigint,
  source_version text not null,
  model_version text,
  review_context jsonb not null default '{}'::jsonb,
  event_fingerprint text not null,
  recorded_at timestamptz not null default now(),
  constraint review_events_assignment_identity_fk
    foreign key (
      assignment_pk, verification_campaign_pk, media_object_pk, reviewer_profile_pk
    ) references public.assignments (
      id, verification_campaign_pk, media_object_pk, reviewer_profile_pk
    ) on delete restrict,
  constraint review_events_supersedes_fk
    foreign key (supersedes_event_pk) references public.review_events (id) on delete restrict,
  constraint review_events_id_check
    check (review_event_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint review_events_question_check check (length(question) between 1 and 1000),
  constraint review_events_image_sha256_check check (image_sha256 ~ '^[0-9a-f]{64}$'),
  constraint review_events_decision_check
    check (decision in ('yes', 'no', 'cannot_tell', 'cannot_view', 'skip', 'alternative_taxon')),
  constraint review_events_alternative_check
    check ((decision = 'alternative_taxon') = (alternative_species_pk is not null)),
  constraint review_events_comment_check check (length(comment) <= 4000),
  constraint review_events_confidence_check check (confidence is null or confidence between 1 and 5),
  constraint review_events_duration_check check (duration_ms is null or duration_ms >= 0),
  constraint review_events_source_version_check check (length(source_version) between 1 and 240),
  constraint review_events_model_version_check
    check (model_version is null or length(model_version) between 1 and 240),
  constraint review_events_context_check check (jsonb_typeof(review_context) = 'object'),
  constraint review_events_context_no_secrets_check
    check (not (review_context ?| array['api_key', 'auth_token', 'oauth_token', 'secret'])),
  constraint review_events_fingerprint_check check (event_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint review_events_recording_check check (recorded_at >= decided_at),
  constraint review_events_not_self_superseding_check
    check (supersedes_event_pk is null or supersedes_event_pk <> id),
  constraint review_events_id_key unique (review_event_id),
  constraint review_events_fingerprint_key unique (event_fingerprint)
);

create index review_events_assignment_pk_idx on public.review_events (assignment_pk);
create index review_events_campaign_pk_idx
on public.review_events (verification_campaign_pk, recorded_at);
create index review_events_media_object_pk_idx on public.review_events (media_object_pk);
create index review_events_reviewer_profile_pk_idx
on public.review_events (reviewer_profile_pk, recorded_at);
create index review_events_alternative_species_pk_idx
on public.review_events (alternative_species_pk) where alternative_species_pk is not null;
create index review_events_supersedes_event_pk_idx
on public.review_events (supersedes_event_pk) where supersedes_event_pk is not null;

create table public.consensus (
  id bigint generated always as identity primary key,
  consensus_id text not null,
  verification_campaign_pk bigint not null references public.verification_campaigns (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  consensus_layer text not null,
  status text not null,
  decision text,
  method text not null,
  method_version text not null,
  eligible_review_count integer not null,
  decisive_review_count integer not null,
  qualified_review_count integer not null default 0,
  expert_gate_satisfied boolean not null default false,
  minority_dissent_count integer not null default 0,
  review_event_fingerprints text[] not null,
  supersedes_consensus_pk bigint references public.consensus (id) on delete restrict,
  consensus_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint consensus_id_check
    check (consensus_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint consensus_layer_check
    check (consensus_layer in ('community_evidence', 'qualified_consensus', 'release_consensus')),
  constraint consensus_status_check
    check (status in ('insufficient', 'disputed', 'reached', 'rejected')),
  constraint consensus_decision_check
    check (decision is null or decision in ('yes', 'no', 'cannot_tell', 'cannot_view')),
  constraint consensus_status_decision_check
    check ((status = 'reached') = (decision is not null)),
  constraint consensus_method_check
    check (length(method) between 1 and 160 and length(method_version) between 1 and 120),
  constraint consensus_counts_check
    check (
      eligible_review_count >= 0
      and decisive_review_count between 0 and eligible_review_count
      and qualified_review_count between 0 and eligible_review_count
      and minority_dissent_count between 0 and decisive_review_count
    ),
  constraint consensus_release_gate_check
    check (consensus_layer <> 'release_consensus' or status <> 'reached' or expert_gate_satisfied),
  constraint consensus_events_check
    check (
      cardinality(review_event_fingerprints) = eligible_review_count
      and array_position(review_event_fingerprints, null) is null
    ),
  constraint consensus_fingerprint_check check (consensus_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint consensus_id_key unique (consensus_id),
  constraint consensus_fingerprint_key unique (consensus_fingerprint)
);

create index consensus_campaign_pk_idx on public.consensus (verification_campaign_pk);
create index consensus_media_object_pk_idx on public.consensus (media_object_pk);
create index consensus_species_pk_idx on public.consensus (species_pk)
where species_pk is not null;
create index consensus_supersedes_pk_idx on public.consensus (supersedes_consensus_pk)
where supersedes_consensus_pk is not null;

create table public.reviewer_reliability (
  id bigint generated always as identity primary key,
  reviewer_reliability_id text not null,
  reviewer_profile_pk bigint not null references public.reviewer_profiles (id) on delete restrict,
  project_pk bigint not null references public.projects (id) on delete restrict,
  family_taxon_key text not null,
  life_stage text not null,
  visual_domain text not null,
  weighting_state text not null default 'equal_weight',
  minimum_evidence_met boolean not null default false,
  control_count integer not null default 0,
  overlap_count integer not null default 0,
  adjudicated_count integer not null default 0,
  shrunk_weight double precision not null default 1,
  weight_lower double precision,
  weight_upper double precision,
  metrics jsonb not null default '{}'::jsonb,
  policy_version text not null,
  reliability_fingerprint text not null,
  measured_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  constraint reviewer_reliability_id_check
    check (reviewer_reliability_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint reviewer_reliability_domain_check
    check (
      length(family_taxon_key) between 1 and 160
      and length(life_stage) between 1 and 120
      and length(visual_domain) between 1 and 120
    ),
  constraint reviewer_reliability_state_check
    check (weighting_state in ('equal_weight', 'insufficient_evidence', 'shrunk_capped')),
  constraint reviewer_reliability_counts_check
    check (control_count >= 0 and overlap_count >= 0 and adjudicated_count >= 0),
  constraint reviewer_reliability_weight_check
    check (
      shrunk_weight between 0.5 and 2
      and (
        (weight_lower is null and weight_upper is null)
        or (
          weight_lower is not null and weight_upper is not null
          and weight_lower > 0 and weight_lower <= shrunk_weight
          and weight_upper >= shrunk_weight
        )
      )
    ),
  constraint reviewer_reliability_evidence_gate_check
    check (
      weighting_state <> 'shrunk_capped'
      or (minimum_evidence_met and control_count > 0 and overlap_count > 0)
    ),
  constraint reviewer_reliability_equal_weight_check
    check (weighting_state = 'shrunk_capped' or shrunk_weight = 1),
  constraint reviewer_reliability_metrics_check check (jsonb_typeof(metrics) = 'object'),
  constraint reviewer_reliability_no_circularity_check
    check (not (metrics ?| array['model_agreement', 'bioclip_agreement', 'majority_agreement_as_truth'])),
  constraint reviewer_reliability_policy_check check (length(policy_version) between 1 and 120),
  constraint reviewer_reliability_fingerprint_check
    check (reliability_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint reviewer_reliability_recording_check check (recorded_at >= measured_at),
  constraint reviewer_reliability_id_key unique (reviewer_reliability_id),
  constraint reviewer_reliability_fingerprint_key unique (reliability_fingerprint)
);

create index reviewer_reliability_reviewer_pk_idx
on public.reviewer_reliability (reviewer_profile_pk, measured_at desc);
create index reviewer_reliability_project_pk_idx
on public.reviewer_reliability (project_pk, measured_at desc);

create table public.quality_snapshots (
  id bigint generated always as identity primary key,
  quality_snapshot_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  verification_campaign_pk bigint references public.verification_campaigns (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  snapshot_kind text not null,
  scope_kind text not null,
  sampling_frame_fingerprint text not null,
  inclusion_probability_method text,
  reviewed_sample integer not null,
  decisive_reviews integer not null,
  effective_sample_size double precision,
  precision_estimate double precision,
  interval_lower double precision,
  interval_upper double precision,
  agreement_metrics jsonb not null default '{}'::jsonb,
  reference_health_flags text[] not null default '{}',
  release_blockers text[] not null default '{}',
  snapshot_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint quality_snapshots_id_check
    check (quality_snapshot_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint quality_snapshots_kind_check
    check (snapshot_kind in ('representative_audit', 'targeted_failure_discovery', 'operational')),
  constraint quality_snapshots_scope_check
    check (scope_kind in ('national', 'species', 'campaign')),
  constraint quality_snapshots_scope_shape_check
    check (
      (scope_kind = 'national' and species_pk is null)
      or (scope_kind = 'species' and species_pk is not null)
      or (scope_kind = 'campaign' and verification_campaign_pk is not null)
    ),
  constraint quality_snapshots_sampling_fingerprint_check
    check (sampling_frame_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint quality_snapshots_sampling_method_check
    check (
      snapshot_kind <> 'representative_audit'
      or (inclusion_probability_method is not null and length(inclusion_probability_method) between 1 and 240)
    ),
  constraint quality_snapshots_counts_check
    check (reviewed_sample >= 0 and decisive_reviews between 0 and reviewed_sample),
  constraint quality_snapshots_effective_sample_check
    check (effective_sample_size is null or effective_sample_size between 0 and reviewed_sample),
  constraint quality_snapshots_precision_check
    check (
      (precision_estimate is null and interval_lower is null and interval_upper is null)
      or (
        precision_estimate is not null
        and interval_lower is not null
        and interval_upper is not null
        and precision_estimate between 0 and 1
        and interval_lower between 0 and precision_estimate
        and interval_upper between precision_estimate and 1
      )
    ),
  constraint quality_snapshots_metrics_check check (jsonb_typeof(agreement_metrics) = 'object'),
  constraint quality_snapshots_arrays_check
    check (
      array_position(reference_health_flags, null) is null
      and array_position(release_blockers, null) is null
    ),
  constraint quality_snapshots_fingerprint_check
    check (snapshot_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint quality_snapshots_id_key unique (quality_snapshot_id),
  constraint quality_snapshots_fingerprint_key unique (snapshot_fingerprint)
);

create index quality_snapshots_project_pk_idx
on public.quality_snapshots (project_pk, created_at desc);
create index quality_snapshots_run_pk_idx on public.quality_snapshots (run_pk);
create index quality_snapshots_campaign_pk_idx
on public.quality_snapshots (verification_campaign_pk)
where verification_campaign_pk is not null;
create index quality_snapshots_species_pk_idx on public.quality_snapshots (species_pk)
where species_pk is not null;

alter table public.reviewer_profiles enable row level security;
alter table public.verification_campaigns enable row level security;
alter table public.assignments enable row level security;
alter table public.review_events enable row level security;
alter table public.consensus enable row level security;
alter table public.reviewer_reliability enable row level security;
alter table public.quality_snapshots enable row level security;

revoke all on table public.reviewer_profiles, public.verification_campaigns,
  public.assignments, public.review_events, public.consensus,
  public.reviewer_reliability, public.quality_snapshots
from public, anon, authenticated;
revoke all on sequence public.reviewer_profiles_id_seq,
  public.verification_campaigns_id_seq, public.assignments_id_seq,
  public.review_events_id_seq, public.consensus_id_seq,
  public.reviewer_reliability_id_seq, public.quality_snapshots_id_seq
from public, anon, authenticated;

grant select, insert, update, delete on table public.reviewer_profiles,
  public.verification_campaigns, public.assignments to service_role;
grant select, insert on table public.review_events, public.consensus,
  public.reviewer_reliability, public.quality_snapshots to service_role;
grant usage, select on sequence public.reviewer_profiles_id_seq,
  public.verification_campaigns_id_seq, public.assignments_id_seq,
  public.review_events_id_seq, public.consensus_id_seq,
  public.reviewer_reliability_id_seq, public.quality_snapshots_id_seq
to service_role;

comment on table public.review_events is
  'Append-only blind-review evidence; corrections supersede rather than mutate earlier events.';
comment on table public.reviewer_reliability is
  'Private domain-specific reliability snapshots; model or majority agreement cannot serve as truth.';
comment on table public.consensus is
  'Append-only layered consensus preserving dissent; consensus alone never creates a released occurrence.';
comment on table public.quality_snapshots is
  'Representative audits remain distinct from targeted failure-discovery and operational snapshots.';
