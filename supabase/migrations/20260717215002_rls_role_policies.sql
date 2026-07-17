-- ButterflyLens 3.1.6: project roles and least-privilege browser policies.
-- Worker credentials and service_role remain server-only.

alter table public.reviewer_profiles
add constraint reviewer_profiles_identity_key unique (id, auth_user_id);

create table public.project_memberships (
  id bigint generated always as identity primary key,
  project_membership_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  reviewer_profile_pk bigint not null,
  auth_user_id uuid not null,
  role text not null,
  status text not null default 'active',
  approved_by_reviewer_pk bigint references public.reviewer_profiles (id) on delete restrict,
  joined_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint project_memberships_profile_identity_fk
    foreign key (reviewer_profile_pk, auth_user_id)
    references public.reviewer_profiles (id, auth_user_id) on delete restrict,
  constraint project_memberships_id_check
    check (project_membership_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint project_memberships_role_check
    check (role in ('reviewer', 'expert', 'curator', 'administrator')),
  constraint project_memberships_status_check
    check (status in ('invited', 'active', 'paused', 'revoked')),
  constraint project_memberships_approval_check
    check (status = 'invited' or approved_by_reviewer_pk is not null),
  constraint project_memberships_timestamp_check check (updated_at >= joined_at),
  constraint project_memberships_id_key unique (project_membership_id),
  constraint project_memberships_project_profile_key unique (project_pk, reviewer_profile_pk),
  constraint project_memberships_project_auth_key unique (project_pk, auth_user_id)
);

create index project_memberships_project_pk_idx on public.project_memberships (project_pk);
create index project_memberships_reviewer_profile_pk_idx
on public.project_memberships (reviewer_profile_pk);
create index project_memberships_auth_project_role_idx
on public.project_memberships (auth_user_id, project_pk, role)
where status = 'active';
create index project_memberships_approver_pk_idx
on public.project_memberships (approved_by_reviewer_pk)
where approved_by_reviewer_pk is not null;

create schema if not exists private;
revoke all on schema private from public, anon, authenticated;
grant usage on schema private to authenticated;

create function private.has_project_role(target_project_pk bigint, allowed_roles text[])
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.project_memberships membership
    where membership.project_pk = target_project_pk
      and membership.auth_user_id = (select auth.uid())
      and membership.status = 'active'
      and membership.role = any (allowed_roles)
  );
$$;

revoke all on function private.has_project_role(bigint, text[]) from public, anon;
grant execute on function private.has_project_role(bigint, text[]) to authenticated;

create function private.enforce_membership_role()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  profile_role text;
  profile_qualification text;
begin
  select role, qualification_state
  into profile_role, profile_qualification
  from public.reviewer_profiles
  where id = new.reviewer_profile_pk and auth_user_id = new.auth_user_id;

  if not found then
    raise exception 'membership reviewer identity does not exist' using errcode = '23503';
  end if;
  if new.role = 'expert'
     and (profile_role not in ('expert', 'curator', 'administrator')
          or profile_qualification <> 'verified') then
    raise exception 'expert membership requires verified expert profile' using errcode = '23514';
  end if;
  if new.role = 'curator'
     and (profile_role not in ('curator', 'administrator')
          or profile_qualification <> 'verified') then
    raise exception 'curator membership requires verified curator profile' using errcode = '23514';
  end if;
  if new.role = 'administrator' and profile_role <> 'administrator' then
    raise exception 'administrator membership requires administrator profile' using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_membership_role() from public, anon, authenticated;
grant execute on function private.enforce_membership_role() to service_role;

create trigger project_memberships_enforce_role
before insert or update of reviewer_profile_pk, auth_user_id, role
on public.project_memberships
for each row execute function private.enforce_membership_role();

create function private.validate_review_event_context()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected_question text;
  expected_image_sha256 text;
begin
  select campaign.question, media.content_sha256
  into expected_question, expected_image_sha256
  from public.assignments assignment
  join public.verification_campaigns campaign
    on campaign.id = assignment.verification_campaign_pk
  join public.media_objects media on media.id = assignment.media_object_pk
  where assignment.id = new.assignment_pk
    and assignment.verification_campaign_pk = new.verification_campaign_pk
    and assignment.media_object_pk = new.media_object_pk
    and assignment.reviewer_profile_pk = new.reviewer_profile_pk;

  if not found then
    raise exception 'review event does not match its assignment' using errcode = '23503';
  end if;
  if expected_image_sha256 is null or new.image_sha256 <> expected_image_sha256 then
    raise exception 'review image fingerprint does not match assigned media' using errcode = '23514';
  end if;
  if new.question <> expected_question then
    raise exception 'review question does not match assigned campaign' using errcode = '23514';
  end if;
  if new.decided_at > now() + interval '5 minutes' then
    raise exception 'review decision time is implausibly in the future' using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.validate_review_event_context()
from public, anon;
grant execute on function private.validate_review_event_context()
to authenticated, service_role;

create trigger review_events_validate_context
before insert on public.review_events
for each row execute function private.validate_review_event_context();

-- Close nullable-shape gaps in earlier media and model checks.
alter table public.media_objects
add constraint media_objects_content_nulls_match_check
check (
  (content_sha256 is null) = (byte_count is null)
  and (content_sha256 is null) = (media_type is null)
),
add constraint media_objects_dimension_nulls_match_check
check ((width_pixels is null) = (height_pixels is null)),
add constraint media_objects_perceptual_nulls_match_check
check ((perceptual_hash is null) = (perceptual_hash_version is null));

alter table public.model_evidence
add constraint model_evidence_calibration_nulls_match_check
check ((calibrated_probability is null) = (calibrator_fingerprint is null));

alter table public.geographic_impact
add column worker_heartbeat_fingerprint text,
add constraint geographic_impact_heartbeat_fingerprint_check
check (
  (
    snapshot_mode = 'submitted' and worker_heartbeat_fingerprint is null
  )
  or (
    snapshot_mode = 'live' and snapshot_state in ('available', 'stale')
    and worker_heartbeat_fingerprint is not null
    and worker_heartbeat_fingerprint ~ '^[0-9a-f]{64}$'
  )
  or (
    snapshot_mode = 'live' and snapshot_state = 'unavailable'
    and worker_heartbeat_fingerprint is null
  )
);

alter table public.project_memberships enable row level security;
revoke all on table public.project_memberships from public, anon, authenticated;
revoke all on sequence public.project_memberships_id_seq from public, anon, authenticated;
grant select, insert, update, delete on table public.project_memberships to service_role;
grant usage, select on sequence public.project_memberships_id_seq to service_role;

-- Public projections expose no raw discovery, private media, worker, or reliability rows.
grant select on table public.projects, public.species,
  public.geographic_impact, public.release_candidates to anon, authenticated;

create policy projects_public_read
on public.projects for select to anon, authenticated
using (status = 'active');

create policy species_public_read
on public.species for select to anon, authenticated
using (
  status = 'accepted'
  and exists (
    select 1 from public.projects project
    where project.id = species.project_pk and project.status = 'active'
  )
);

create policy geographic_impact_public_read
on public.geographic_impact for select to anon, authenticated
using (visibility_state = 'public');

create policy release_candidates_public_read
on public.release_candidates for select to anon, authenticated
using (candidate_state in ('approved', 'exported') and all_release_gates_passed);

-- Authenticated users can inspect their own pseudonymous identity and membership.
grant select on table public.reviewer_profiles, public.project_memberships
to authenticated;
grant update (public_name, updated_at) on table public.reviewer_profiles
to authenticated;

create policy reviewer_profiles_self_read
on public.reviewer_profiles for select to authenticated
using (auth_user_id = (select auth.uid()));

create policy reviewer_profiles_project_curator_read
on public.reviewer_profiles for select to authenticated
using (
  exists (
    select 1 from public.project_memberships membership
    where membership.reviewer_profile_pk = reviewer_profiles.id
      and private.has_project_role(
        membership.project_pk, array['curator', 'administrator']::text[]
      )
  )
);

create policy reviewer_profiles_self_update
on public.reviewer_profiles for update to authenticated
using (auth_user_id = (select auth.uid()))
with check (auth_user_id = (select auth.uid()));

create policy project_memberships_self_read
on public.project_memberships for select to authenticated
using (auth_user_id = (select auth.uid()));

create policy project_memberships_curator_read
on public.project_memberships for select to authenticated
using (
  private.has_project_role(project_pk, array['curator', 'administrator']::text[])
);

create policy projects_member_read
on public.projects for select to authenticated
using (
  private.has_project_role(
    id, array['reviewer', 'expert', 'curator', 'administrator']::text[]
  )
);

create policy species_curator_read
on public.species for select to authenticated
using (
  private.has_project_role(project_pk, array['curator', 'administrator']::text[])
);

-- Curators can inspect server-produced evidence but browser roles cannot mutate it.
grant select on table public.runs, public.name_assertions,
  public.query_definitions, public.query_associations, public.api_requests,
  public.flickr_photos, public.media_objects, public.duplicate_groups,
  public.duplicate_group_members, public.pipeline_stages, public.worker_leases,
  public.worker_heartbeats, public.model_evidence to authenticated;

create policy runs_curator_read on public.runs for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy name_assertions_curator_read on public.name_assertions for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy query_definitions_curator_read on public.query_definitions for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy query_associations_curator_read on public.query_associations for select to authenticated
using (
  exists (
    select 1 from public.query_definitions definition
    where definition.id = query_associations.query_definition_pk
      and private.has_project_role(
        definition.project_pk, array['curator', 'administrator']::text[]
      )
  )
);
create policy api_requests_curator_read on public.api_requests for select to authenticated
using (
  exists (
    select 1 from public.runs run
    where run.id = api_requests.run_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);
create policy flickr_photos_curator_read on public.flickr_photos for select to authenticated
using (
  exists (
    select 1 from public.api_requests request join public.runs run on run.id = request.run_pk
    where request.id = flickr_photos.api_request_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);
create policy media_objects_curator_read on public.media_objects for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy duplicate_groups_curator_read on public.duplicate_groups for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy duplicate_group_members_curator_read on public.duplicate_group_members for select to authenticated
using (
  exists (
    select 1 from public.duplicate_groups duplicate_group
    where duplicate_group.id = duplicate_group_members.duplicate_group_pk
      and private.has_project_role(
        duplicate_group.project_pk, array['curator', 'administrator']::text[]
      )
  )
);
create policy pipeline_stages_curator_read on public.pipeline_stages for select to authenticated
using (
  exists (
    select 1 from public.runs run
    where run.id = pipeline_stages.run_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);
create policy worker_leases_curator_read on public.worker_leases for select to authenticated
using (
  exists (
    select 1 from public.pipeline_stages stage join public.runs run on run.id = stage.run_pk
    where stage.id = worker_leases.pipeline_stage_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);
create policy worker_heartbeats_curator_read on public.worker_heartbeats for select to authenticated
using (
  exists (
    select 1 from public.pipeline_stages stage join public.runs run on run.id = stage.run_pk
    where stage.id = worker_heartbeats.pipeline_stage_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
  or exists (
    select 1 from public.worker_leases lease
    join public.pipeline_stages stage on stage.id = lease.pipeline_stage_pk
    join public.runs run on run.id = stage.run_pk
    where lease.id = worker_heartbeats.worker_lease_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);
create policy model_evidence_curator_read on public.model_evidence for select to authenticated
using (
  exists (
    select 1 from public.pipeline_stages stage join public.runs run on run.id = stage.run_pk
    where stage.id = model_evidence.pipeline_stage_pk
      and private.has_project_role(run.project_pk, array['curator', 'administrator']::text[])
  )
);

-- Campaigns and assignments are curator-managed; reviewers see only open work assigned to them.
grant select, insert, update, delete on table public.verification_campaigns,
  public.assignments to authenticated;
grant usage, select on sequence public.verification_campaigns_id_seq,
  public.assignments_id_seq to authenticated;

create policy verification_campaigns_member_read
on public.verification_campaigns for select to authenticated
using (
  status <> 'draft'
  and private.has_project_role(
    project_pk, array['reviewer', 'expert', 'curator', 'administrator']::text[]
  )
);
create policy verification_campaigns_curator_all
on public.verification_campaigns for all to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]))
with check (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));

create policy assignments_self_read
on public.assignments for select to authenticated
using (
  exists (
    select 1 from public.reviewer_profiles profile
    where profile.id = assignments.reviewer_profile_pk
      and profile.auth_user_id = (select auth.uid())
  )
);
create policy assignments_curator_all
on public.assignments for all to authenticated
using (
  exists (
    select 1 from public.verification_campaigns campaign
    where campaign.id = assignments.verification_campaign_pk
      and private.has_project_role(
        campaign.project_pk, array['curator', 'administrator']::text[]
      )
  )
)
with check (
  exists (
    select 1 from public.verification_campaigns campaign
    where campaign.id = assignments.verification_campaign_pk
      and private.has_project_role(
        campaign.project_pk, array['curator', 'administrator']::text[]
      )
  )
);

-- Review events are insert-only; policies preserve assignment identity and blind review.
grant select, insert on table public.review_events to authenticated;
grant usage, select on sequence public.review_events_id_seq to authenticated;

create policy review_events_self_read
on public.review_events for select to authenticated
using (
  exists (
    select 1 from public.reviewer_profiles profile
    where profile.id = review_events.reviewer_profile_pk
      and profile.auth_user_id = (select auth.uid())
  )
);
create policy review_events_curator_read
on public.review_events for select to authenticated
using (
  exists (
    select 1 from public.verification_campaigns campaign
    where campaign.id = review_events.verification_campaign_pk
      and private.has_project_role(
        campaign.project_pk, array['curator', 'administrator']::text[]
      )
  )
);
create policy review_events_self_insert
on public.review_events for insert to authenticated
with check (
  exists (
    select 1
    from public.assignments assignment
    join public.reviewer_profiles profile
      on profile.id = assignment.reviewer_profile_pk
    join public.verification_campaigns campaign
      on campaign.id = assignment.verification_campaign_pk
    where assignment.id = review_events.assignment_pk
      and assignment.verification_campaign_pk = review_events.verification_campaign_pk
      and assignment.media_object_pk = review_events.media_object_pk
      and assignment.reviewer_profile_pk = review_events.reviewer_profile_pk
      and assignment.status in ('assigned', 'opened', 'responded')
      and profile.auth_user_id = (select auth.uid())
      and campaign.status = 'open'
      and private.has_project_role(
        campaign.project_pk,
        array['reviewer', 'expert', 'curator', 'administrator']::text[]
      )
  )
);

-- Consensus stays blind until a reviewer responds; reliability is private to self and curators.
grant select on table public.consensus, public.reviewer_reliability,
  public.quality_snapshots to authenticated;

create policy consensus_respondent_read
on public.consensus for select to authenticated
using (
  exists (
    select 1 from public.assignments assignment
    join public.reviewer_profiles profile on profile.id = assignment.reviewer_profile_pk
    where assignment.verification_campaign_pk = consensus.verification_campaign_pk
      and assignment.media_object_pk = consensus.media_object_pk
      and assignment.status = 'responded'
      and profile.auth_user_id = (select auth.uid())
  )
);
create policy consensus_curator_read
on public.consensus for select to authenticated
using (
  exists (
    select 1 from public.verification_campaigns campaign
    where campaign.id = consensus.verification_campaign_pk
      and private.has_project_role(
        campaign.project_pk, array['curator', 'administrator']::text[]
      )
  )
);
create policy reviewer_reliability_self_read
on public.reviewer_reliability for select to authenticated
using (
  exists (
    select 1 from public.reviewer_profiles profile
    where profile.id = reviewer_reliability.reviewer_profile_pk
      and profile.auth_user_id = (select auth.uid())
  )
);
create policy reviewer_reliability_curator_read
on public.reviewer_reliability for select to authenticated
using (
  private.has_project_role(project_pk, array['curator', 'administrator']::text[])
);
create policy quality_snapshots_member_read
on public.quality_snapshots for select to authenticated
using (
  private.has_project_role(
    project_pk, array['reviewer', 'expert', 'curator', 'administrator']::text[]
  )
);

create policy geographic_impact_member_read
on public.geographic_impact for select to authenticated
using (
  private.has_project_role(
    project_pk, array['reviewer', 'expert', 'curator', 'administrator']::text[]
  )
);
create policy release_candidates_curator_read
on public.release_candidates for select to authenticated
using (
  private.has_project_role(project_pk, array['curator', 'administrator']::text[])
);

-- Exposed views and matching column grants prevent RLS-approved rows from
-- leaking auth identities, private media links, or internal release authority.
revoke select on table public.projects, public.species,
  public.geographic_impact, public.release_candidates from anon, authenticated;
grant select (
  id, schema_version, project_id, slug, name, description, status, country_code,
  boundary_id, boundary_version, boundary_sha256,
  sensitive_coordinate_policy_version, root_taxon_keys, taxonomy_fingerprint,
  search_plan_fingerprint, public_discovery_claim, data_policy_version,
  consent_policy_version, created_at, updated_at
) on public.projects to anon, authenticated;
grant select on table public.species to anon, authenticated;
grant select (
  geographic_impact_id, project_pk, species_pk, snapshot_mode, snapshot_state,
  snapshot_state_reason, source_commit, source_snapshot_fingerprint,
  ala_baseline_authority, ala_baseline_fingerprint, flickr_snapshot_fingerprint,
  provider_union_fingerprint, review_projection_fingerprint, scope_kind,
  scope_id, grid_name, grid_version, h3_resolution, h3_cell, source_precision,
  ala_baseline_count, ala_baseline_count_state, ala_baseline_count_reason,
  flickr_candidate_count, flickr_candidate_count_state,
  flickr_candidate_count_reason, yoloe_butterfly_count,
  yoloe_butterfly_count_state, yoloe_butterfly_count_reason,
  bioclip_species_candidate_count, bioclip_species_candidate_count_state,
  bioclip_species_candidate_count_reason, community_reviewed_count,
  community_reviewed_count_state, community_reviewed_count_reason,
  human_supported_count, human_supported_count_state,
  human_supported_count_reason, release_ready_count,
  release_ready_count_state, release_ready_count_reason,
  potential_coverage_gap, potential_coverage_gap_state,
  potential_coverage_gap_reason, human_supported_additional,
  human_supported_additional_state, human_supported_additional_reason,
  release_ready_additional, release_ready_additional_state,
  release_ready_additional_reason, nearest_ala_distance_m,
  nearest_ala_distance_state, nearest_ala_distance_reason, latest_ala_date,
  latest_ala_date_state, latest_ala_date_reason, latest_flickr_date,
  latest_flickr_date_state, latest_flickr_date_reason, data_deficiency_state,
  data_deficiency_reason, visibility_state, evidence_fingerprints,
  impact_fingerprint, worker_heartbeat_fingerprint, created_at
) on public.geographic_impact to anon, authenticated;
grant select (
  release_candidate_id, project_pk, species_pk, candidate_state,
  human_supported_identity, qualified_consensus_passed,
  expert_review_required, expert_review_passed, coordinate_valid, date_valid,
  duplicate_independence_passed, rights_provenance_passed,
  quality_threshold_passed, no_unresolved_conflict, evidence_packet_complete,
  all_release_gates_passed, release_blockers, occurrence_date, public_cell_id,
  rights_fingerprint, evidence_packet_fingerprint, candidate_fingerprint,
  created_at
) on public.release_candidates to anon, authenticated;

create view public.public_projects
with (security_invoker = true)
as
select project_id, slug, name, description, country_code, boundary_id,
  boundary_version, boundary_sha256, sensitive_coordinate_policy_version,
  root_taxon_keys, taxonomy_fingerprint, search_plan_fingerprint,
  public_discovery_claim, data_policy_version, consent_policy_version,
  created_at, updated_at
from public.projects;

create view public.public_species
with (security_invoker = true)
as
select project.project_id, species.species_id,
  species.butterflylens_taxon_key, species.accepted_scientific_name,
  species.taxonomy_fingerprint, species.taxon_source, species.taxon_source_id,
  species.status, species.created_at
from public.species species
join public.projects project on project.id = species.project_pk;

create view public.public_geographic_impact
with (security_invoker = true)
as
select impact.geographic_impact_id, project.project_id, species.species_id,
  impact.snapshot_mode, impact.snapshot_state, impact.snapshot_state_reason,
  impact.source_commit, impact.source_snapshot_fingerprint,
  impact.ala_baseline_authority, impact.ala_baseline_fingerprint,
  impact.flickr_snapshot_fingerprint, impact.provider_union_fingerprint,
  impact.review_projection_fingerprint, impact.worker_heartbeat_fingerprint,
  impact.scope_kind, impact.scope_id, impact.grid_name, impact.grid_version,
  impact.h3_resolution, impact.h3_cell, impact.source_precision,
  impact.ala_baseline_count, impact.ala_baseline_count_state,
  impact.ala_baseline_count_reason, impact.flickr_candidate_count,
  impact.flickr_candidate_count_state, impact.flickr_candidate_count_reason,
  impact.yoloe_butterfly_count, impact.yoloe_butterfly_count_state,
  impact.yoloe_butterfly_count_reason, impact.bioclip_species_candidate_count,
  impact.bioclip_species_candidate_count_state,
  impact.bioclip_species_candidate_count_reason,
  impact.community_reviewed_count, impact.community_reviewed_count_state,
  impact.community_reviewed_count_reason, impact.human_supported_count,
  impact.human_supported_count_state, impact.human_supported_count_reason,
  impact.release_ready_count, impact.release_ready_count_state,
  impact.release_ready_count_reason, impact.potential_coverage_gap,
  impact.potential_coverage_gap_state, impact.potential_coverage_gap_reason,
  impact.human_supported_additional, impact.human_supported_additional_state,
  impact.human_supported_additional_reason, impact.release_ready_additional,
  impact.release_ready_additional_state, impact.release_ready_additional_reason,
  impact.nearest_ala_distance_m, impact.nearest_ala_distance_state,
  impact.nearest_ala_distance_reason, impact.latest_ala_date,
  impact.latest_ala_date_state, impact.latest_ala_date_reason,
  impact.latest_flickr_date, impact.latest_flickr_date_state,
  impact.latest_flickr_date_reason, impact.data_deficiency_state,
  impact.data_deficiency_reason, impact.evidence_fingerprints,
  impact.impact_fingerprint, impact.created_at
from public.geographic_impact impact
join public.projects project on project.id = impact.project_pk
left join public.species species on species.id = impact.species_pk;

create view public.public_release_candidates
with (security_invoker = true)
as
select candidate.release_candidate_id, project.project_id, species.species_id,
  candidate.candidate_state, candidate.human_supported_identity,
  candidate.qualified_consensus_passed, candidate.expert_review_required,
  candidate.expert_review_passed, candidate.coordinate_valid,
  candidate.date_valid, candidate.duplicate_independence_passed,
  candidate.rights_provenance_passed, candidate.quality_threshold_passed,
  candidate.no_unresolved_conflict, candidate.evidence_packet_complete,
  candidate.all_release_gates_passed, candidate.release_blockers,
  candidate.occurrence_date, candidate.public_cell_id,
  candidate.rights_fingerprint, candidate.evidence_packet_fingerprint,
  candidate.candidate_fingerprint, candidate.created_at
from public.release_candidates candidate
join public.projects project on project.id = candidate.project_pk
join public.species species on species.id = candidate.species_pk;

revoke all on table public.public_projects, public.public_species,
  public.public_geographic_impact, public.public_release_candidates
from public;
grant select on table public.public_projects, public.public_species,
  public.public_geographic_impact, public.public_release_candidates
to anon, authenticated;

comment on table public.project_memberships is
  'Project-scoped role binding; authenticated alone grants no project authority.';
comment on function private.has_project_role(bigint, text[]) is
  'Fixed-query RLS helper in a non-exposed schema; uses auth.uid and no caller-controlled SQL.';
comment on function private.validate_review_event_context() is
  'Fixed-query trigger validates assignment, campaign question, and image content identity before append.';
