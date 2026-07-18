-- ButterflyLens 8.6: independent conflict and adjudication workflow.
-- Conflict snapshots retain the exact effective review events. Adjudication is
-- a separate append-only ledger and never erases minority evidence.

create table public.review_conflicts (
  id bigint generated always as identity primary key,
  review_conflict_id text not null,
  verification_campaign_pk bigint not null
    references public.verification_campaigns (id) on delete restrict,
  media_object_pk bigint not null
    references public.media_objects (id) on delete restrict,
  conflict_field text not null,
  source_event_count smallint not null,
  conflict_fingerprint text not null,
  detected_at timestamptz not null default now(),
  constraint review_conflicts_id_check
    check (review_conflict_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint review_conflicts_field_check
    check (conflict_field in ('outcome', 'alternative_taxon')),
  constraint review_conflicts_source_count_check check (source_event_count >= 2),
  constraint review_conflicts_fingerprint_check
    check (conflict_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint review_conflicts_id_key unique (review_conflict_id),
  constraint review_conflicts_fingerprint_key unique (conflict_fingerprint)
);

create index review_conflicts_campaign_pk_idx
on public.review_conflicts (verification_campaign_pk, detected_at desc);
create index review_conflicts_media_object_pk_idx
on public.review_conflicts (media_object_pk, detected_at desc);

create table public.review_conflict_events (
  review_conflict_pk bigint not null
    references public.review_conflicts (id) on delete restrict,
  review_event_pk bigint not null
    references public.review_events (id) on delete restrict,
  event_fingerprint text not null,
  reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  primary key (review_conflict_pk, review_event_pk),
  constraint review_conflict_events_fingerprint_check
    check (event_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint review_conflict_events_fingerprint_key
    unique (review_conflict_pk, event_fingerprint)
);

create index review_conflict_events_event_pk_idx
on public.review_conflict_events (review_event_pk);
create index review_conflict_events_reviewer_pk_idx
on public.review_conflict_events (reviewer_profile_pk);

create table public.adjudication_assignments (
  id bigint generated always as identity primary key,
  adjudication_assignment_id text not null,
  review_conflict_pk bigint not null
    references public.review_conflicts (id) on delete restrict,
  adjudicator_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  status text not null default 'assigned',
  assigned_at timestamptz not null default now(),
  opened_at timestamptz,
  responded_at timestamptz,
  assignment_policy_version text not null default 'independent-adjudication-v1',
  assignment_fingerprint text not null,
  constraint adjudication_assignments_id_check
    check (adjudication_assignment_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint adjudication_assignments_status_check
    check (status in ('assigned', 'opened', 'responded', 'expired', 'withdrawn')),
  constraint adjudication_assignments_timestamp_check check (
    (opened_at is null or opened_at >= assigned_at)
    and (responded_at is null or responded_at >= assigned_at)
    and (status <> 'responded' or responded_at is not null)
  ),
  constraint adjudication_assignments_policy_check
    check (assignment_policy_version = 'independent-adjudication-v1'),
  constraint adjudication_assignments_fingerprint_check
    check (assignment_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint adjudication_assignments_id_key unique (adjudication_assignment_id),
  constraint adjudication_assignments_identity_key
    unique (id, review_conflict_pk, adjudicator_profile_pk),
  constraint adjudication_assignments_reviewer_key
    unique (review_conflict_pk, adjudicator_profile_pk),
  constraint adjudication_assignments_fingerprint_key unique (assignment_fingerprint)
);

create unique index adjudication_assignments_one_active_idx
on public.adjudication_assignments (review_conflict_pk)
where status not in ('expired', 'withdrawn');
create index adjudication_assignments_adjudicator_pk_idx
on public.adjudication_assignments (adjudicator_profile_pk, assigned_at desc);

create table public.adjudication_events (
  id bigint generated always as identity primary key,
  adjudication_event_id text not null,
  adjudication_assignment_pk bigint not null,
  review_conflict_pk bigint not null,
  adjudicator_profile_pk bigint not null,
  verification_campaign_pk bigint not null
    references public.verification_campaigns (id) on delete restrict,
  media_object_pk bigint not null
    references public.media_objects (id) on delete restrict,
  question text not null,
  image_sha256 text not null,
  decision text not null,
  alternative_species_pk bigint references public.species (id) on delete restrict,
  comment text not null default '',
  confidence smallint not null,
  decided_at timestamptz not null,
  duration_ms integer not null,
  source_event_fingerprints text[] not null,
  conflicting_reviewer_profile_pks bigint[] not null,
  independence_check text not null default 'passed',
  assignment_policy_version text not null,
  source_version text not null,
  model_version text not null,
  lineage_fingerprint text not null,
  adjudication_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  recorded_at timestamptz not null default now(),
  constraint adjudication_events_assignment_identity_fk
    foreign key (
      adjudication_assignment_pk, review_conflict_pk, adjudicator_profile_pk
    ) references public.adjudication_assignments (
      id, review_conflict_pk, adjudicator_profile_pk
    ) on delete restrict,
  constraint adjudication_events_id_check
    check (adjudication_event_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint adjudication_events_question_check check (length(question) between 1 and 1000),
  constraint adjudication_events_image_check check (image_sha256 ~ '^[0-9a-f]{64}$'),
  constraint adjudication_events_decision_check
    check (decision in ('yes', 'no', 'alternative_taxon')),
  constraint adjudication_events_alternative_check
    check ((decision = 'alternative_taxon') = (alternative_species_pk is not null)),
  constraint adjudication_events_comment_check check (length(comment) <= 4000),
  constraint adjudication_events_confidence_check check (confidence between 1 and 5),
  constraint adjudication_events_duration_check
    check (duration_ms between 0 and 86400000),
  constraint adjudication_events_sources_check check (
    cardinality(source_event_fingerprints) >= 2
    and cardinality(source_event_fingerprints)
      = cardinality(conflicting_reviewer_profile_pks)
    and array_position(source_event_fingerprints, null) is null
    and array_position(conflicting_reviewer_profile_pks, null) is null
  ),
  constraint adjudication_events_independence_check check (independence_check = 'passed'),
  constraint adjudication_events_policy_check
    check (assignment_policy_version = 'independent-adjudication-v1'),
  constraint adjudication_events_source_version_check
    check (length(source_version) between 1 and 240),
  constraint adjudication_events_model_version_check
    check (length(model_version) between 1 and 240),
  constraint adjudication_events_lineage_fingerprint_check
    check (lineage_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint adjudication_events_fingerprint_check
    check (adjudication_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint adjudication_events_no_scientific_claim_check
    check (not scientific_claim_allowed),
  constraint adjudication_events_recording_check check (recorded_at >= decided_at),
  constraint adjudication_events_id_key unique (adjudication_event_id),
  constraint adjudication_events_assignment_key unique (adjudication_assignment_pk),
  constraint adjudication_events_fingerprint_key unique (adjudication_fingerprint)
);

create index adjudication_events_conflict_pk_idx
on public.adjudication_events (review_conflict_pk, recorded_at desc);
create index adjudication_events_adjudicator_pk_idx
on public.adjudication_events (adjudicator_profile_pk, recorded_at desc);
create index adjudication_events_campaign_pk_idx
on public.adjudication_events (verification_campaign_pk, recorded_at desc);
create index adjudication_events_media_object_pk_idx
on public.adjudication_events (media_object_pk);
create index adjudication_events_alternative_species_pk_idx
on public.adjudication_events (alternative_species_pk)
where alternative_species_pk is not null;

create function private.reject_adjudication_event_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'adjudication events are append only' using errcode = '55000';
end;
$$;

create trigger adjudication_events_reject_mutation
before update or delete on public.adjudication_events
for each row execute function private.reject_adjudication_event_mutation();

create function private.enforce_adjudication_assignment_independence()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  conflict_record record;
  member_record record;
begin
  if tg_op = 'UPDATE' and row(
    old.review_conflict_pk, old.adjudicator_profile_pk,
    old.assignment_policy_version, old.assignment_fingerprint
  ) is distinct from row(
    new.review_conflict_pk, new.adjudicator_profile_pk,
    new.assignment_policy_version, new.assignment_fingerprint
  ) then
    raise exception 'adjudication assignment identity is immutable'
      using errcode = '23514';
  end if;
  if tg_op = 'UPDATE' and old.status in ('responded', 'expired', 'withdrawn')
     and new.status is distinct from old.status then
    raise exception 'terminal adjudication assignment cannot be reopened'
      using errcode = '23514';
  end if;
  if tg_op = 'UPDATE' and old.responded_at is not null
     and new.responded_at is distinct from old.responded_at then
    raise exception 'adjudication response timestamp is immutable'
      using errcode = '23514';
  end if;

  select conflict.id, campaign.project_pk
  into conflict_record
  from public.review_conflicts conflict
  join public.verification_campaigns campaign
    on campaign.id = conflict.verification_campaign_pk
  where conflict.id = new.review_conflict_pk
  for key share of conflict;

  if not found then
    raise exception 'review conflict does not exist' using errcode = '23503';
  end if;
  perform pg_advisory_xact_lock(new.review_conflict_pk);

  if tg_op = 'INSERT' and exists (
    select 1 from public.review_conflict_events source
    where source.review_conflict_pk = new.review_conflict_pk
      and source.reviewer_profile_pk = new.adjudicator_profile_pk
  ) then
    raise exception 'adjudicator must be independent of conflicting reviews'
      using errcode = '23514';
  end if;
  if tg_op = 'INSERT' and exists (
    select 1 from public.adjudication_events event
    where event.review_conflict_pk = new.review_conflict_pk
  ) then
    raise exception 'resolved conflict cannot be assigned again'
      using errcode = '23514';
  end if;

  select profile.status, profile.qualification_state, membership.status as member_status,
    membership.role
  into member_record
  from public.reviewer_profiles profile
  join public.project_memberships membership
    on membership.reviewer_profile_pk = profile.id
    and membership.project_pk = conflict_record.project_pk
  where profile.id = new.adjudicator_profile_pk;

  if not found or member_record.status <> 'active'
     or member_record.member_status <> 'active'
     or member_record.qualification_state <> 'verified'
     or member_record.role not in ('expert', 'curator', 'administrator') then
    raise exception 'adjudication requires an active independent qualified project expert'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger adjudication_assignments_enforce_independence
before insert or update on public.adjudication_assignments
for each row execute function private.enforce_adjudication_assignment_independence();

create function private.open_review_conflict(
  target_review_conflict_id text,
  target_verification_campaign_id text,
  target_media_object_id text,
  target_conflict_fingerprint text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  campaign_pk bigint;
  media_pk bigint;
  inserted_conflict_pk bigint;
  effective_count integer;
  distinct_reviewer_count integer;
  distinct_decision_count integer;
  conflict_kind text;
begin
  select campaign.id into campaign_pk
  from public.verification_campaigns campaign
  where campaign.verification_campaign_id = target_verification_campaign_id;
  select media.id into media_pk
  from public.media_objects media
  where media.media_object_id = target_media_object_id;
  if campaign_pk is null or media_pk is null then
    raise exception 'conflict campaign or media does not exist' using errcode = '23503';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(campaign_pk::text || ':' || media_pk::text, 0)
  );

  with effective as (
    select event.* from public.review_events event
    where event.verification_campaign_pk = campaign_pk
      and event.media_object_pk = media_pk
      and event.decision in ('yes', 'no', 'alternative_taxon')
      and not exists (
        select 1 from public.review_events correction
        where correction.supersedes_event_pk = event.id
      )
  )
  select count(*), count(distinct reviewer_profile_pk),
    count(distinct row(decision, alternative_species_pk)),
    case when count(distinct decision) > 1 then 'outcome' else 'alternative_taxon' end
  into effective_count, distinct_reviewer_count, distinct_decision_count, conflict_kind
  from effective;

  if effective_count < 2 or distinct_reviewer_count < 2
     or distinct_decision_count < 2 then
    raise exception 'independent conflicting effective reviews do not exist'
      using errcode = '23514';
  end if;
  if exists (
    select 1 from public.review_conflicts conflict
    where conflict.verification_campaign_pk = campaign_pk
      and conflict.media_object_pk = media_pk
      and not exists (
        select 1 from public.adjudication_events adjudication
        where adjudication.review_conflict_pk = conflict.id
      )
  ) then
    raise exception 'an unresolved conflict already exists for this item'
      using errcode = '23505';
  end if;

  insert into public.review_conflicts (
    review_conflict_id, verification_campaign_pk, media_object_pk,
    conflict_field, source_event_count, conflict_fingerprint
  ) values (
    target_review_conflict_id, campaign_pk, media_pk, conflict_kind,
    effective_count, target_conflict_fingerprint
  ) returning id into inserted_conflict_pk;

  insert into public.review_conflict_events (
    review_conflict_pk, review_event_pk, event_fingerprint, reviewer_profile_pk
  )
  select inserted_conflict_pk, event.id, event.event_fingerprint,
    event.reviewer_profile_pk
  from public.review_events event
  where event.verification_campaign_pk = campaign_pk
    and event.media_object_pk = media_pk
    and event.decision in ('yes', 'no', 'alternative_taxon')
    and not exists (
      select 1 from public.review_events correction
      where correction.supersedes_event_pk = event.id
    )
  order by event.event_fingerprint;

  return target_review_conflict_id;
end;
$$;

create function private.enforce_adjudication_event_lineage()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected_fingerprints text[];
  expected_reviewers bigint[];
  assignment_record record;
begin
  perform pg_advisory_xact_lock(new.review_conflict_pk);
  select assignment.assigned_at, assignment.assignment_policy_version
  into assignment_record
  from public.adjudication_assignments assignment
  where assignment.id = new.adjudication_assignment_pk;
  if not found then
    raise exception 'adjudication assignment does not exist' using errcode = '23503';
  end if;
  if new.decided_at < assignment_record.assigned_at then
    raise exception 'adjudication decision predates its assignment'
      using errcode = '23514';
  end if;

  select array_agg(source.event_fingerprint order by source.event_fingerprint),
    array_agg(source.reviewer_profile_pk order by source.event_fingerprint)
  into expected_fingerprints, expected_reviewers
  from public.review_conflict_events source
  where source.review_conflict_pk = new.review_conflict_pk;

  if new.source_event_fingerprints is distinct from expected_fingerprints
     or new.conflicting_reviewer_profile_pks is distinct from expected_reviewers
     or new.adjudicator_profile_pk = any(expected_reviewers)
     or new.assignment_policy_version is distinct from assignment_record.assignment_policy_version
     or new.independence_check <> 'passed'
     or new.scientific_claim_allowed then
    raise exception 'adjudication does not preserve independent conflict lineage'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger adjudication_events_enforce_lineage
before insert on public.adjudication_events
for each row execute function private.enforce_adjudication_event_lineage();

create function public.submit_adjudication_event(
  target_adjudication_assignment_id text,
  target_adjudication_event_id text,
  target_decision text,
  target_comment text,
  target_confidence smallint,
  target_decided_at timestamptz,
  target_duration_ms integer,
  target_source_version text,
  target_model_version text,
  target_lineage_fingerprint text,
  target_adjudication_fingerprint text,
  target_alternative_species_id text default null
)
returns table (
  stored_adjudication_event_id text,
  stored_adjudication_assignment_id text,
  stored_adjudication_fingerprint text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  assignment_record record;
  alternative_species_pk bigint;
  source_fingerprints text[];
  source_reviewers bigint[];
  inserted_record record;
begin
  if caller_auth_user_id is null then
    raise exception 'adjudication submission requires authentication'
      using errcode = '42501';
  end if;

  select assignment.id, assignment.adjudication_assignment_id,
    assignment.review_conflict_pk, assignment.adjudicator_profile_pk,
    assignment.assignment_policy_version, assignment.status,
    conflict.verification_campaign_pk, conflict.media_object_pk,
    campaign.project_pk, campaign.question, media.content_sha256 as image_sha256
  into assignment_record
  from public.adjudication_assignments assignment
  join public.reviewer_profiles profile
    on profile.id = assignment.adjudicator_profile_pk
  join public.review_conflicts conflict on conflict.id = assignment.review_conflict_pk
  join public.verification_campaigns campaign
    on campaign.id = conflict.verification_campaign_pk
  join public.media_objects media on media.id = conflict.media_object_pk
  where assignment.adjudication_assignment_id = target_adjudication_assignment_id
    and assignment.status in ('assigned', 'opened')
    and profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and campaign.status = 'open'
    and media.media_state = 'committed'
    and media.decode_status = 'valid'
    and media.rights_status = 'allowed'
    and media.display_allowed
  for update of assignment;

  if not found then
    raise exception 'active independent adjudication assignment does not exist'
      using errcode = '42501';
  end if;

  if target_alternative_species_id is not null then
    select species.id into alternative_species_pk
    from public.species species
    where species.project_pk = assignment_record.project_pk
      and species.species_id = target_alternative_species_id
      and species.status = 'accepted';
    if not found then
      raise exception 'accepted alternative taxon does not exist in this project'
        using errcode = '23503';
    end if;
  end if;

  select array_agg(source.event_fingerprint order by source.event_fingerprint),
    array_agg(source.reviewer_profile_pk order by source.event_fingerprint)
  into source_fingerprints, source_reviewers
  from public.review_conflict_events source
  where source.review_conflict_pk = assignment_record.review_conflict_pk;

  insert into public.adjudication_events (
    adjudication_event_id, adjudication_assignment_pk, review_conflict_pk,
    adjudicator_profile_pk, verification_campaign_pk, media_object_pk,
    question, image_sha256, decision, alternative_species_pk, comment,
    confidence, decided_at, duration_ms, source_event_fingerprints,
    conflicting_reviewer_profile_pks, independence_check,
    assignment_policy_version, source_version, model_version,
    lineage_fingerprint, adjudication_fingerprint, scientific_claim_allowed
  ) values (
    target_adjudication_event_id, assignment_record.id,
    assignment_record.review_conflict_pk, assignment_record.adjudicator_profile_pk,
    assignment_record.verification_campaign_pk, assignment_record.media_object_pk,
    assignment_record.question, assignment_record.image_sha256, target_decision,
    alternative_species_pk, coalesce(target_comment, ''), target_confidence,
    target_decided_at, target_duration_ms, source_fingerprints, source_reviewers,
    'passed', assignment_record.assignment_policy_version, target_source_version,
    target_model_version, target_lineage_fingerprint,
    target_adjudication_fingerprint, false
  ) returning adjudication_event_id, adjudication_fingerprint, recorded_at
  into inserted_record;

  update public.adjudication_assignments
  set status = 'responded', responded_at = inserted_record.recorded_at
  where id = assignment_record.id;

  return query select inserted_record.adjudication_event_id,
    assignment_record.adjudication_assignment_id,
    inserted_record.adjudication_fingerprint, inserted_record.recorded_at;
end;
$$;

alter table public.review_conflicts enable row level security;
alter table public.review_conflict_events enable row level security;
alter table public.adjudication_assignments enable row level security;
alter table public.adjudication_events enable row level security;

revoke all on table public.review_conflicts, public.review_conflict_events,
  public.adjudication_assignments, public.adjudication_events
from public, anon, authenticated;
revoke all on sequence public.review_conflicts_id_seq,
  public.adjudication_assignments_id_seq, public.adjudication_events_id_seq
from public, anon, authenticated;

grant select on table public.review_conflicts, public.review_conflict_events,
  public.adjudication_events to service_role;
grant select, insert, update on table public.adjudication_assignments to service_role;
grant usage, select on sequence public.review_conflicts_id_seq,
  public.adjudication_assignments_id_seq, public.adjudication_events_id_seq
to service_role;

grant select on table public.adjudication_assignments to authenticated;
create policy adjudication_assignments_self_read
on public.adjudication_assignments for select to authenticated
using (
  exists (
    select 1 from public.reviewer_profiles profile
    where profile.id = adjudication_assignments.adjudicator_profile_pk
      and profile.auth_user_id = (select auth.uid())
  )
);

create policy review_conflicts_adjudicator_read
on public.review_conflicts for select to authenticated
using (
  exists (
    select 1 from public.adjudication_assignments assignment
    join public.reviewer_profiles profile
      on profile.id = assignment.adjudicator_profile_pk
    where assignment.review_conflict_pk = review_conflicts.id
      and profile.auth_user_id = (select auth.uid())
  )
);

create policy media_objects_adjudicator_read
on public.media_objects for select to authenticated
using (
  media_state = 'committed' and decode_status = 'valid'
  and rights_status = 'allowed' and display_allowed
  and exists (
    select 1 from public.review_conflicts conflict
    join public.adjudication_assignments assignment
      on assignment.review_conflict_pk = conflict.id
    join public.reviewer_profiles profile
      on profile.id = assignment.adjudicator_profile_pk
    where conflict.media_object_pk = media_objects.id
      and assignment.status in ('assigned', 'opened', 'responded')
      and profile.auth_user_id = (select auth.uid())
  )
);

grant select (
  id, review_conflict_id, verification_campaign_pk, media_object_pk,
  conflict_field, source_event_count, conflict_fingerprint, detected_at
) on public.review_conflicts to authenticated;

create view public.my_adjudication_queue
with (security_invoker = true)
as
select assignment.adjudication_assignment_id, conflict.review_conflict_id,
  campaign.verification_campaign_id, media.media_object_id, campaign.question,
  assignment.status, assignment.assigned_at, assignment.opened_at,
  assignment.responded_at, assignment.assignment_policy_version,
  assignment.assignment_fingerprint, conflict.conflict_field,
  conflict.source_event_count, conflict.conflict_fingerprint,
  media.content_sha256 as image_sha256, media.byte_count, media.media_type,
  media.width_pixels, media.height_pixels, media.rights_fingerprint,
  false as scientific_claim_allowed
from public.adjudication_assignments assignment
join public.review_conflicts conflict on conflict.id = assignment.review_conflict_pk
join public.verification_campaigns campaign
  on campaign.id = conflict.verification_campaign_pk
join public.media_objects media on media.id = conflict.media_object_pk
where assignment.status in ('assigned', 'opened', 'responded')
  and campaign.status = 'open'
  and media.media_state = 'committed' and media.decode_status = 'valid'
  and media.rights_status = 'allowed' and media.display_allowed;

revoke all on table public.my_adjudication_queue from public, anon, authenticated;
grant select on table public.my_adjudication_queue to authenticated;

revoke all on function private.open_review_conflict(text, text, text, text)
from public, anon, authenticated;
grant execute on function private.open_review_conflict(text, text, text, text)
to service_role;
revoke all on function private.reject_adjudication_event_mutation(),
  private.enforce_adjudication_assignment_independence(),
  private.enforce_adjudication_event_lineage()
from public, anon, authenticated;
revoke all on function public.submit_adjudication_event(
  text, text, text, text, smallint, timestamptz, integer, text, text, text,
  text, text
) from public, anon, authenticated;
grant execute on function public.submit_adjudication_event(
  text, text, text, text, smallint, timestamptz, integer, text, text, text,
  text, text
) to authenticated;

comment on table public.review_conflicts is
  'Immutable conflict snapshots retain exact effective dissenting review events.';
comment on table public.adjudication_events is
  'Append-only independent adjudication evidence; it does not erase dissent or permit a scientific claim.';
comment on view public.my_adjudication_queue is
  'Blind adjudication work queue without source decisions or reviewer identities.';
