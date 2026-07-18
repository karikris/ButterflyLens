-- ButterflyLens 10.6: private, append-only evidence contribution recognition.
-- Recognition is self-visible and cannot create scientific or reviewer authority.

create table public.contributor_impact_snapshots (
  id bigint generated always as identity primary key,
  contributor_impact_snapshot_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  snapshot_state text not null,
  snapshot_state_reason text,
  reviewed_image_count bigint,
  resolved_conflict_count bigint,
  species_helped_count bigint,
  region_helped_count bigint,
  control_coverage_count bigint,
  expert_contribution_state text not null,
  expert_contribution_count bigint,
  expert_contribution_reason text,
  calculation_version text not null,
  source_event_fingerprints text[] not null,
  source_evidence_fingerprint text,
  projection_fingerprint text,
  visibility text not null default 'self_only',
  ranking_permitted boolean not null default false,
  speed_metric_permitted boolean not null default false,
  scientific_claim_allowed boolean not null default false,
  calculated_at timestamptz,
  recorded_at timestamptz not null default now(),
  constraint contributor_impact_snapshots_id_check check (
    contributor_impact_snapshot_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint contributor_impact_snapshots_state_check
    check (snapshot_state in ('available', 'unavailable')),
  constraint contributor_impact_snapshots_shape_check check (
    (
      snapshot_state = 'available'
      and snapshot_state_reason is null
      and reviewed_image_count >= 0
      and resolved_conflict_count >= 0
      and species_helped_count >= 0
      and region_helped_count >= 0
      and control_coverage_count >= 0
      and source_evidence_fingerprint ~ '^[0-9a-f]{64}$'
      and projection_fingerprint ~ '^[0-9a-f]{64}$'
      and calculated_at is not null
    )
    or (
      snapshot_state = 'unavailable'
      and length(snapshot_state_reason) between 1 and 500
      and reviewed_image_count is null
      and resolved_conflict_count is null
      and species_helped_count is null
      and region_helped_count is null
      and control_coverage_count is null
      and cardinality(source_event_fingerprints) = 0
      and source_evidence_fingerprint is null
      and projection_fingerprint is null
      and calculated_at is null
    )
  ),
  constraint contributor_impact_snapshots_expert_state_check
    check (expert_contribution_state in ('available', 'not_applicable', 'unavailable')),
  constraint contributor_impact_snapshots_expert_shape_check check (
    (
      expert_contribution_state = 'available'
      and snapshot_state = 'available'
      and expert_contribution_count >= 0
      and expert_contribution_reason is null
    )
    or (
      expert_contribution_state = 'not_applicable'
      and snapshot_state = 'available'
      and expert_contribution_count is null
      and length(expert_contribution_reason) between 1 and 500
    )
    or (
      expert_contribution_state = 'unavailable'
      and snapshot_state = 'unavailable'
      and expert_contribution_count is null
      and length(expert_contribution_reason) between 1 and 500
    )
  ),
  constraint contributor_impact_snapshots_calculation_check check (
    calculation_version = 'butterflylens-contributor-impact-calculation:v1.0.0'
  ),
  constraint contributor_impact_snapshots_source_fingerprints_check check (
    array_position(source_event_fingerprints, null) is null
  ),
  constraint contributor_impact_snapshots_boundaries_check check (
    visibility = 'self_only'
    and not ranking_permitted
    and not speed_metric_permitted
    and not scientific_claim_allowed
  ),
  constraint contributor_impact_snapshots_recording_check
    check (calculated_at is null or recorded_at >= calculated_at),
  constraint contributor_impact_snapshots_id_key
    unique (contributor_impact_snapshot_id),
  constraint contributor_impact_snapshots_projection_key
    unique (projection_fingerprint)
);

create index contributor_impact_snapshots_reviewer_pk_idx
on public.contributor_impact_snapshots (
  reviewer_profile_pk, project_pk, calculated_at desc, id desc
);
create index contributor_impact_snapshots_project_pk_idx
on public.contributor_impact_snapshots (project_pk, recorded_at desc);

create function private.validate_contributor_impact_snapshot()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  profile_record record;
  normalized_source_fingerprints text[];
begin
  select profile.status, profile.role, profile.qualification_state
  into profile_record
  from public.reviewer_profiles profile
  where profile.id = new.reviewer_profile_pk;

  if profile_record.status is distinct from 'active'
     or not exists (
       select 1
       from public.project_memberships membership
       where membership.project_pk = new.project_pk
         and membership.reviewer_profile_pk = new.reviewer_profile_pk
         and membership.status = 'active'
     ) then
    raise exception 'contributor snapshot requires an active project member'
      using errcode = '23514';
  end if;

  select coalesce(array_agg(distinct fingerprint order by fingerprint), '{}'::text[])
  into normalized_source_fingerprints
  from unnest(new.source_event_fingerprints) fingerprint;
  if new.source_event_fingerprints is distinct from normalized_source_fingerprints
     or exists (
       select 1 from unnest(new.source_event_fingerprints) fingerprint
       where fingerprint !~ '^[0-9a-f]{64}$'
     ) then
    raise exception 'contributor source fingerprints must be unique sorted SHA-256 values'
      using errcode = '23514';
  end if;

  if new.expert_contribution_state = 'available'
     and not (
       profile_record.role in ('expert', 'curator', 'administrator')
       and profile_record.qualification_state = 'verified'
     ) then
    raise exception 'expert contribution requires a currently verified expert role'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger contributor_impact_snapshots_validate
before insert on public.contributor_impact_snapshots
for each row execute function private.validate_contributor_impact_snapshot();

create function private.reject_contributor_impact_snapshot_mutation()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  raise exception 'contributor impact snapshots are append only' using errcode = '55000';
end;
$$;

create trigger contributor_impact_snapshots_reject_mutation
before update or delete on public.contributor_impact_snapshots
for each row execute function private.reject_contributor_impact_snapshot_mutation();

alter table public.contributor_impact_snapshots enable row level security;

revoke all on table public.contributor_impact_snapshots
from public, anon, authenticated;
revoke all on sequence public.contributor_impact_snapshots_id_seq
from public, anon, authenticated;
grant select, insert on table public.contributor_impact_snapshots to service_role;
grant usage, select on sequence public.contributor_impact_snapshots_id_seq
to service_role;
grant select on table public.contributor_impact_snapshots to authenticated;

create policy contributor_impact_snapshots_self_read
on public.contributor_impact_snapshots for select to authenticated
using (
  exists (
    select 1
    from public.reviewer_profiles profile
    join public.project_memberships membership
      on membership.reviewer_profile_pk = profile.id
      and membership.project_pk = contributor_impact_snapshots.project_pk
    where profile.id = contributor_impact_snapshots.reviewer_profile_pk
      and profile.auth_user_id = (select auth.uid())
      and profile.status = 'active'
      and membership.status = 'active'
  )
);

create view public.my_contributor_impact
with (security_invoker = true)
as
select distinct on (snapshot.project_pk, snapshot.reviewer_profile_pk)
  snapshot.contributor_impact_snapshot_id,
  project.project_id,
  profile.reviewer_profile_id,
  profile.public_name,
  snapshot.snapshot_state,
  snapshot.snapshot_state_reason,
  snapshot.reviewed_image_count,
  snapshot.resolved_conflict_count,
  snapshot.species_helped_count,
  snapshot.region_helped_count,
  snapshot.control_coverage_count,
  snapshot.expert_contribution_state,
  snapshot.expert_contribution_count,
  snapshot.expert_contribution_reason,
  snapshot.calculation_version,
  snapshot.source_evidence_fingerprint,
  snapshot.projection_fingerprint,
  snapshot.visibility,
  snapshot.ranking_permitted,
  snapshot.speed_metric_permitted,
  snapshot.scientific_claim_allowed,
  snapshot.calculated_at
from public.contributor_impact_snapshots snapshot
join public.projects project on project.id = snapshot.project_pk
join public.reviewer_profiles profile on profile.id = snapshot.reviewer_profile_pk
where profile.auth_user_id = (select auth.uid())
order by snapshot.project_pk, snapshot.reviewer_profile_pk,
  snapshot.calculated_at desc nulls last, snapshot.id desc;

revoke all on table public.my_contributor_impact
from public, anon, authenticated;
grant select on table public.my_contributor_impact to authenticated;

revoke all on function private.validate_contributor_impact_snapshot(),
  private.reject_contributor_impact_snapshot_mutation()
from public, anon, authenticated;

comment on table public.contributor_impact_snapshots is
  'Append-only self-visible evidence contribution totals; never a leaderboard, pace measure, reliability score, or scientific authority.';
comment on view public.my_contributor_impact is
  'Latest self-only contribution recognition; private control identities and reviewer/Auth identifiers remain excluded.';
