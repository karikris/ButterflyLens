-- ButterflyLens 3.1.5: authoritative-baseline impact cells and blocked-by-default release candidates.

create table public.geographic_impact (
  id bigint generated always as identity primary key,
  geographic_impact_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  species_pk bigint references public.species (id) on delete restrict,
  quality_snapshot_pk bigint references public.quality_snapshots (id) on delete restrict,
  worker_heartbeat_pk bigint references public.worker_heartbeats (id) on delete restrict,
  snapshot_mode text not null,
  snapshot_state text not null,
  snapshot_state_reason text,
  source_commit text not null,
  source_snapshot_fingerprint text not null,
  ala_baseline_authority text not null default 'butterflylens_rebuilt',
  ala_baseline_fingerprint text not null,
  flickr_snapshot_fingerprint text,
  provider_union_fingerprint text not null,
  review_projection_fingerprint text not null,
  scope_kind text not null,
  scope_id text not null,
  grid_name text,
  grid_version text,
  h3_resolution smallint,
  h3_cell text,
  source_precision text not null,
  ala_baseline_count bigint,
  ala_baseline_count_state text not null,
  ala_baseline_count_reason text,
  flickr_candidate_count bigint,
  flickr_candidate_count_state text not null,
  flickr_candidate_count_reason text,
  yoloe_butterfly_count bigint,
  yoloe_butterfly_count_state text not null,
  yoloe_butterfly_count_reason text,
  bioclip_species_candidate_count bigint,
  bioclip_species_candidate_count_state text not null,
  bioclip_species_candidate_count_reason text,
  community_reviewed_count bigint,
  community_reviewed_count_state text not null,
  community_reviewed_count_reason text,
  human_supported_count bigint,
  human_supported_count_state text not null,
  human_supported_count_reason text,
  release_ready_count bigint,
  release_ready_count_state text not null,
  release_ready_count_reason text,
  potential_coverage_gap boolean,
  potential_coverage_gap_state text not null,
  potential_coverage_gap_reason text,
  human_supported_additional boolean,
  human_supported_additional_state text not null,
  human_supported_additional_reason text,
  release_ready_additional boolean,
  release_ready_additional_state text not null,
  release_ready_additional_reason text,
  nearest_ala_distance_m double precision,
  nearest_ala_distance_state text not null,
  nearest_ala_distance_reason text,
  latest_ala_date date,
  latest_ala_date_state text not null,
  latest_ala_date_reason text,
  latest_flickr_date date,
  latest_flickr_date_state text not null,
  latest_flickr_date_reason text,
  data_deficiency_state text not null,
  data_deficiency_reason text not null,
  visibility_state text not null default 'private',
  evidence_fingerprints text[] not null,
  impact_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint geographic_impact_id_check
    check (geographic_impact_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint geographic_impact_snapshot_mode_check
    check (snapshot_mode in ('submitted', 'live')),
  constraint geographic_impact_snapshot_state_check
    check (snapshot_state in ('available', 'stale', 'unavailable')),
  constraint geographic_impact_snapshot_shape_check
    check (
      (snapshot_state = 'available' and snapshot_state_reason is null)
      or (
        snapshot_state in ('stale', 'unavailable')
        and snapshot_state_reason is not null
        and length(snapshot_state_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_mode_heartbeat_check
    check (
      (snapshot_mode = 'submitted' and worker_heartbeat_pk is null and snapshot_state = 'available')
      or (
        snapshot_mode = 'live'
        and (
          (snapshot_state in ('available', 'stale') and worker_heartbeat_pk is not null)
          or (snapshot_state = 'unavailable' and worker_heartbeat_pk is null)
        )
      )
    ),
  constraint geographic_impact_source_commit_check check (source_commit ~ '^[0-9a-f]{40}$'),
  constraint geographic_impact_snapshot_fingerprint_check
    check (source_snapshot_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_ala_authority_check
    check (ala_baseline_authority = 'butterflylens_rebuilt'),
  constraint geographic_impact_ala_fingerprint_check
    check (ala_baseline_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_flickr_fingerprint_check
    check (flickr_snapshot_fingerprint is null or flickr_snapshot_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_provider_fingerprint_check
    check (provider_union_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_review_fingerprint_check
    check (review_projection_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_scope_check
    check (scope_kind in ('australia', 'state_territory', 'ibra', 'lga', 'h3', 'species')),
  constraint geographic_impact_species_scope_check
    check (scope_kind <> 'species' or species_pk is not null),
  constraint geographic_impact_scope_id_check check (length(scope_id) between 1 and 240),
  constraint geographic_impact_h3_shape_check
    check (
      (
        scope_kind = 'h3'
        and grid_name = 'H3'
        and grid_version is not null and length(grid_version) between 1 and 40
        and h3_resolution is not null and h3_resolution between 0 and 15
        and h3_cell is not null and h3_cell ~ '^[0-9a-f]{15}$'
      )
      or (
        scope_kind <> 'h3' and grid_name is null and grid_version is null
        and h3_resolution is null and h3_cell is null
      )
    ),
  constraint geographic_impact_precision_check
    check (source_precision in ('exact', 'generalised', 'coarse_rollup', 'withheld')),
  constraint geographic_impact_ala_count_check
    check (
      (ala_baseline_count_state = 'available' and ala_baseline_count is not null and ala_baseline_count >= 0 and ala_baseline_count_reason is null)
      or (
        ala_baseline_count_state in ('unavailable', 'withheld', 'not_applicable')
        and ala_baseline_count is null and ala_baseline_count_reason is not null
        and length(ala_baseline_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_flickr_count_check
    check (
      (flickr_candidate_count_state = 'available' and flickr_candidate_count is not null and flickr_candidate_count >= 0 and flickr_candidate_count_reason is null)
      or (
        flickr_candidate_count_state in ('unavailable', 'withheld', 'not_applicable')
        and flickr_candidate_count is null and flickr_candidate_count_reason is not null
        and length(flickr_candidate_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_yoloe_count_check
    check (
      (yoloe_butterfly_count_state = 'available' and yoloe_butterfly_count is not null and yoloe_butterfly_count >= 0 and yoloe_butterfly_count_reason is null)
      or (
        yoloe_butterfly_count_state in ('unavailable', 'withheld', 'not_applicable')
        and yoloe_butterfly_count is null and yoloe_butterfly_count_reason is not null
        and length(yoloe_butterfly_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_bioclip_count_check
    check (
      (bioclip_species_candidate_count_state = 'available' and bioclip_species_candidate_count is not null and bioclip_species_candidate_count >= 0 and bioclip_species_candidate_count_reason is null)
      or (
        bioclip_species_candidate_count_state in ('unavailable', 'withheld', 'not_applicable')
        and bioclip_species_candidate_count is null and bioclip_species_candidate_count_reason is not null
        and length(bioclip_species_candidate_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_community_count_check
    check (
      (community_reviewed_count_state = 'available' and community_reviewed_count is not null and community_reviewed_count >= 0 and community_reviewed_count_reason is null)
      or (
        community_reviewed_count_state in ('unavailable', 'withheld', 'not_applicable')
        and community_reviewed_count is null and community_reviewed_count_reason is not null
        and length(community_reviewed_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_human_count_check
    check (
      (human_supported_count_state = 'available' and human_supported_count is not null and human_supported_count >= 0 and human_supported_count_reason is null)
      or (
        human_supported_count_state in ('unavailable', 'withheld', 'not_applicable')
        and human_supported_count is null and human_supported_count_reason is not null
        and length(human_supported_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_release_count_check
    check (
      (release_ready_count_state = 'available' and release_ready_count is not null and release_ready_count >= 0 and release_ready_count_reason is null)
      or (
        release_ready_count_state in ('unavailable', 'withheld', 'not_applicable')
        and release_ready_count is null and release_ready_count_reason is not null
        and length(release_ready_count_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_potential_gap_check
    check (
      (potential_coverage_gap_state = 'available' and potential_coverage_gap is not null and potential_coverage_gap_reason is null)
      or (
        potential_coverage_gap_state in ('unavailable', 'withheld', 'not_applicable')
        and potential_coverage_gap is null and potential_coverage_gap_reason is not null
        and length(potential_coverage_gap_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_human_additional_check
    check (
      (human_supported_additional_state = 'available' and human_supported_additional is not null and human_supported_additional_reason is null)
      or (
        human_supported_additional_state in ('unavailable', 'withheld', 'not_applicable')
        and human_supported_additional is null and human_supported_additional_reason is not null
        and length(human_supported_additional_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_release_additional_check
    check (
      (release_ready_additional_state = 'available' and release_ready_additional is not null and release_ready_additional_reason is null)
      or (
        release_ready_additional_state in ('unavailable', 'withheld', 'not_applicable')
        and release_ready_additional is null and release_ready_additional_reason is not null
        and length(release_ready_additional_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_distance_check
    check (
      (nearest_ala_distance_state = 'available' and nearest_ala_distance_m is not null and nearest_ala_distance_m >= 0 and nearest_ala_distance_reason is null)
      or (
        nearest_ala_distance_state in ('unavailable', 'withheld', 'not_applicable')
        and nearest_ala_distance_m is null and nearest_ala_distance_reason is not null
        and length(nearest_ala_distance_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_latest_ala_check
    check (
      (latest_ala_date_state = 'available' and latest_ala_date is not null and latest_ala_date_reason is null)
      or (
        latest_ala_date_state in ('unavailable', 'withheld', 'not_applicable')
        and latest_ala_date is null and latest_ala_date_reason is not null
        and length(latest_ala_date_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_latest_flickr_check
    check (
      (latest_flickr_date_state = 'available' and latest_flickr_date is not null and latest_flickr_date_reason is null)
      or (
        latest_flickr_date_state in ('unavailable', 'withheld', 'not_applicable')
        and latest_flickr_date is null and latest_flickr_date_reason is not null
        and length(latest_flickr_date_reason) between 1 and 500
      )
    ),
  constraint geographic_impact_deficiency_check
    check (
      data_deficiency_state in ('sufficient_for_comparison', 'data_deficient', 'unavailable', 'withheld')
      and length(data_deficiency_reason) between 1 and 500
    ),
  constraint geographic_impact_visibility_check
    check (visibility_state in ('private', 'public', 'withheld', 'withdrawn')),
  constraint geographic_impact_evidence_check
    check (cardinality(evidence_fingerprints) > 0 and array_position(evidence_fingerprints, null) is null),
  constraint geographic_impact_fingerprint_check
    check (impact_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint geographic_impact_id_key unique (geographic_impact_id),
  constraint geographic_impact_fingerprint_key unique (impact_fingerprint)
);

create index geographic_impact_project_pk_idx
on public.geographic_impact (project_pk, snapshot_mode, created_at desc);
create index geographic_impact_run_pk_idx on public.geographic_impact (run_pk);
create index geographic_impact_species_pk_idx on public.geographic_impact (species_pk)
where species_pk is not null;
create index geographic_impact_quality_snapshot_pk_idx
on public.geographic_impact (quality_snapshot_pk) where quality_snapshot_pk is not null;
create index geographic_impact_worker_heartbeat_pk_idx
on public.geographic_impact (worker_heartbeat_pk) where worker_heartbeat_pk is not null;
create index geographic_impact_scope_idx
on public.geographic_impact (snapshot_mode, scope_kind, scope_id, species_pk);
create index geographic_impact_public_idx
on public.geographic_impact (snapshot_mode, scope_kind, scope_id)
where visibility_state = 'public';

create table public.release_candidates (
  id bigint generated always as identity primary key,
  release_candidate_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  run_pk bigint not null references public.runs (id) on delete restrict,
  species_pk bigint not null references public.species (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  consensus_pk bigint not null references public.consensus (id) on delete restrict,
  quality_snapshot_pk bigint not null references public.quality_snapshots (id) on delete restrict,
  geographic_impact_pk bigint references public.geographic_impact (id) on delete restrict,
  supersedes_release_candidate_pk bigint references public.release_candidates (id) on delete restrict,
  candidate_state text not null default 'blocked',
  human_supported_identity boolean not null default false,
  qualified_consensus_passed boolean not null default false,
  expert_review_required boolean not null default false,
  expert_review_passed boolean not null default false,
  coordinate_valid boolean not null default false,
  date_valid boolean not null default false,
  duplicate_independence_passed boolean not null default false,
  rights_provenance_passed boolean not null default false,
  quality_threshold_passed boolean not null default false,
  no_unresolved_conflict boolean not null default false,
  evidence_packet_complete boolean not null default false,
  all_release_gates_passed boolean not null default false,
  release_blockers text[] not null,
  occurrence_date date,
  public_cell_id text,
  rights_fingerprint text not null,
  evidence_packet_fingerprint text,
  authorized_by_reviewer_pk bigint references public.reviewer_profiles (id) on delete restrict,
  authorization_role text,
  authorized_at timestamptz,
  candidate_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint release_candidates_id_check
    check (release_candidate_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint release_candidates_state_check
    check (candidate_state in ('blocked', 'eligible', 'approved', 'exported', 'withdrawn')),
  constraint release_candidates_expert_gate_check
    check (not expert_review_required or expert_review_passed),
  constraint release_candidates_gate_equivalence_check
    check (
      all_release_gates_passed = (
        human_supported_identity and qualified_consensus_passed
        and (not expert_review_required or expert_review_passed)
        and coordinate_valid and date_valid and duplicate_independence_passed
        and rights_provenance_passed and quality_threshold_passed
        and no_unresolved_conflict and evidence_packet_complete
      )
    ),
  constraint release_candidates_state_gate_check
    check (
      (candidate_state = 'blocked' and not all_release_gates_passed)
      or (candidate_state in ('eligible', 'approved', 'exported') and all_release_gates_passed)
      or candidate_state = 'withdrawn'
    ),
  constraint release_candidates_blockers_check
    check (
      (all_release_gates_passed and cardinality(release_blockers) = 0)
      or (not all_release_gates_passed and cardinality(release_blockers) > 0)
    ),
  constraint release_candidates_occurrence_shape_check
    check (
      (coordinate_valid and public_cell_id is not null and length(public_cell_id) between 1 and 240)
      or (not coordinate_valid and public_cell_id is null)
    ),
  constraint release_candidates_date_shape_check
    check ((date_valid and occurrence_date is not null) or (not date_valid and occurrence_date is null)),
  constraint release_candidates_rights_fingerprint_check
    check (rights_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint release_candidates_packet_check
    check (
      (
        evidence_packet_complete and evidence_packet_fingerprint is not null
        and evidence_packet_fingerprint ~ '^[0-9a-f]{64}$'
      )
      or (not evidence_packet_complete and evidence_packet_fingerprint is null)
    ),
  constraint release_candidates_authorization_check
    check (
      (
        candidate_state in ('approved', 'exported')
        and authorized_by_reviewer_pk is not null
        and authorization_role in ('curator', 'administrator')
        and authorized_at is not null
      )
      or (
        candidate_state not in ('approved', 'exported')
        and authorized_by_reviewer_pk is null
        and authorization_role is null and authorized_at is null
      )
    ),
  constraint release_candidates_fingerprint_check
    check (candidate_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint release_candidates_id_key unique (release_candidate_id),
  constraint release_candidates_fingerprint_key unique (candidate_fingerprint)
);

create index release_candidates_project_pk_idx
on public.release_candidates (project_pk, candidate_state, created_at desc);
create index release_candidates_run_pk_idx on public.release_candidates (run_pk);
create index release_candidates_species_pk_idx
on public.release_candidates (species_pk, candidate_state);
create index release_candidates_media_object_pk_idx on public.release_candidates (media_object_pk);
create index release_candidates_consensus_pk_idx on public.release_candidates (consensus_pk);
create index release_candidates_quality_snapshot_pk_idx
on public.release_candidates (quality_snapshot_pk);
create index release_candidates_geographic_impact_pk_idx
on public.release_candidates (geographic_impact_pk)
where geographic_impact_pk is not null;
create index release_candidates_supersedes_pk_idx
on public.release_candidates (supersedes_release_candidate_pk)
where supersedes_release_candidate_pk is not null;
create index release_candidates_authorizer_pk_idx
on public.release_candidates (authorized_by_reviewer_pk)
where authorized_by_reviewer_pk is not null;

alter table public.geographic_impact enable row level security;
alter table public.release_candidates enable row level security;

revoke all on table public.geographic_impact, public.release_candidates
from public, anon, authenticated;
revoke all on sequence public.geographic_impact_id_seq,
  public.release_candidates_id_seq from public, anon, authenticated;

grant select, insert on table public.geographic_impact, public.release_candidates
to service_role;
grant usage, select on sequence public.geographic_impact_id_seq,
  public.release_candidates_id_seq to service_role;

comment on table public.geographic_impact is
  'Append-only submitted/live evidence comparisons; missing or skipped evidence is unavailable, never a fabricated zero.';
comment on column public.geographic_impact.ala_baseline_authority is
  'Only the rebuilt ButterflyLens ALA baseline is authoritative for impact comparisons.';
comment on table public.release_candidates is
  'Append-only occurrence candidates blocked by default; passing gates does not imply downstream acceptance.';
