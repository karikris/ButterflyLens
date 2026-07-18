-- ButterflyLens 13.2: private, append-only community moderation.
-- Content visibility and project membership effects are separate from the
-- immutable scientific review event. Reports never become reliability truth.

create table public.moderation_cases (
  id bigint generated always as identity primary key,
  moderation_case_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  target_kind text not null,
  target_review_event_pk bigint references public.review_events (id) on delete restrict,
  target_reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  reason_category text not null,
  reason_summary text not null,
  policy_version text not null
    default 'butterflylens-community-moderation:v1.0.0',
  case_fingerprint text not null,
  opened_at timestamptz not null default now(),
  constraint moderation_cases_id_check check (
    moderation_case_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint moderation_cases_target_kind_check check (
    target_kind in ('review_comment', 'reviewer_account', 'review_audit')
  ),
  constraint moderation_cases_target_shape_check check (
    (target_kind in ('review_comment', 'review_audit') and target_review_event_pk is not null)
    or (target_kind = 'reviewer_account' and target_review_event_pk is null)
  ),
  constraint moderation_cases_reason_category_check check (
    reason_category in (
      'abuse', 'harassment', 'hate', 'threat', 'doxxing',
      'sensitive_location', 'impersonation', 'rights', 'spam',
      'review_manipulation', 'integrity_audit', 'other'
    )
  ),
  constraint moderation_cases_reason_summary_check
    check (length(reason_summary) between 1 and 500),
  constraint moderation_cases_policy_check check (
    policy_version = 'butterflylens-community-moderation:v1.0.0'
  ),
  constraint moderation_cases_fingerprint_check
    check (case_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint moderation_cases_id_key unique (moderation_case_id),
  constraint moderation_cases_fingerprint_key unique (case_fingerprint)
);

create index moderation_cases_project_opened_idx
on public.moderation_cases (project_pk, opened_at desc, id desc);
create index moderation_cases_target_review_idx
on public.moderation_cases (target_review_event_pk, opened_at desc)
where target_review_event_pk is not null;
create index moderation_cases_target_reviewer_idx
on public.moderation_cases (target_reviewer_profile_pk, opened_at desc);

create table private.moderation_reporters (
  moderation_case_pk bigint primary key
    references public.moderation_cases (id) on delete restrict,
  reporter_reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  report_detail text not null,
  reported_at timestamptz not null default now(),
  constraint moderation_reporters_detail_check
    check (length(report_detail) between 1 and 2000)
);

create index moderation_reporters_reporter_idx
on private.moderation_reporters (reporter_reviewer_profile_pk, reported_at desc);

create table public.moderation_appeals (
  id bigint generated always as identity primary key,
  moderation_appeal_id text not null,
  moderation_case_pk bigint not null
    references public.moderation_cases (id) on delete restrict,
  appellant_reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  rationale text not null,
  appeal_fingerprint text not null,
  submitted_at timestamptz not null default now(),
  constraint moderation_appeals_id_check check (
    moderation_appeal_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint moderation_appeals_rationale_check
    check (length(rationale) between 1 and 4000),
  constraint moderation_appeals_fingerprint_check
    check (appeal_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint moderation_appeals_id_key unique (moderation_appeal_id),
  constraint moderation_appeals_case_key unique (moderation_case_pk),
  constraint moderation_appeals_fingerprint_key unique (appeal_fingerprint)
);

create index moderation_appeals_appellant_idx
on public.moderation_appeals (appellant_reviewer_profile_pk, submitted_at desc);

create table public.moderation_curator_notes (
  id bigint generated always as identity primary key,
  moderation_curator_note_id text not null,
  moderation_case_pk bigint not null
    references public.moderation_cases (id) on delete restrict,
  curator_reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  note text not null,
  note_fingerprint text not null,
  recorded_at timestamptz not null default now(),
  constraint moderation_curator_notes_id_check check (
    moderation_curator_note_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint moderation_curator_notes_note_check
    check (length(note) between 1 and 4000),
  constraint moderation_curator_notes_fingerprint_check
    check (note_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint moderation_curator_notes_id_key unique (moderation_curator_note_id),
  constraint moderation_curator_notes_fingerprint_key unique (note_fingerprint)
);

create index moderation_curator_notes_case_recorded_idx
on public.moderation_curator_notes (moderation_case_pk, recorded_at desc, id desc);
create index moderation_curator_notes_curator_idx
on public.moderation_curator_notes (curator_reviewer_profile_pk, recorded_at desc);

create table public.moderation_events (
  id bigint generated always as identity primary key,
  moderation_event_id text not null,
  moderation_case_pk bigint not null
    references public.moderation_cases (id) on delete restrict,
  event_sequence integer not null,
  action text not null,
  actor_reviewer_profile_pk bigint not null
    references public.reviewer_profiles (id) on delete restrict,
  reason text not null,
  evidence_fingerprints text[] not null default '{}',
  related_evidence_fingerprint text,
  visibility_effect text not null default 'unchanged',
  membership_effect text not null default 'unchanged',
  scientific_claim_allowed boolean not null default false,
  event_fingerprint text not null,
  recorded_at timestamptz not null default now(),
  constraint moderation_events_id_check check (
    moderation_event_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint moderation_events_sequence_check check (event_sequence >= 1),
  constraint moderation_events_action_check check (
    action in (
      'reported', 'content_hidden', 'content_restored',
      'reviewer_suspended', 'reviewer_reinstated',
      'review_audit_opened', 'review_audit_completed',
      'appeal_submitted', 'appeal_upheld', 'appeal_denied',
      'curator_note_added', 'case_closed'
    )
  ),
  constraint moderation_events_reason_check check (length(reason) between 1 and 1000),
  constraint moderation_events_evidence_fingerprints_check check (
    array_position(evidence_fingerprints, null) is null
  ),
  constraint moderation_events_related_fingerprint_check check (
    related_evidence_fingerprint is null
    or related_evidence_fingerprint ~ '^[0-9a-f]{64}$'
  ),
  constraint moderation_events_visibility_effect_check
    check (visibility_effect in ('unchanged', 'hidden', 'restored')),
  constraint moderation_events_membership_effect_check
    check (membership_effect in ('unchanged', 'suspended', 'reinstated')),
  constraint moderation_events_no_scientific_claim_check
    check (not scientific_claim_allowed),
  constraint moderation_events_fingerprint_check
    check (event_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint moderation_events_id_key unique (moderation_event_id),
  constraint moderation_events_case_sequence_key
    unique (moderation_case_pk, event_sequence),
  constraint moderation_events_fingerprint_key unique (event_fingerprint)
);

create index moderation_events_case_recorded_idx
on public.moderation_events (moderation_case_pk, event_sequence desc);
create index moderation_events_actor_idx
on public.moderation_events (actor_reviewer_profile_pk, recorded_at desc);
create index moderation_events_visibility_idx
on public.moderation_events (moderation_case_pk, event_sequence desc)
where visibility_effect <> 'unchanged';

create function private.validate_moderation_case()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  review_record record;
begin
  if new.target_review_event_pk is not null then
    select campaign.project_pk, review.reviewer_profile_pk
    into review_record
    from public.review_events review
    join public.verification_campaigns campaign
      on campaign.id = review.verification_campaign_pk
    where review.id = new.target_review_event_pk;

    if not found
       or review_record.project_pk <> new.project_pk
       or review_record.reviewer_profile_pk <> new.target_reviewer_profile_pk then
      raise exception 'moderation target does not match review project and author'
        using errcode = '23514';
    end if;
  elsif not exists (
    select 1 from public.project_memberships membership
    where membership.project_pk = new.project_pk
      and membership.reviewer_profile_pk = new.target_reviewer_profile_pk
  ) then
    raise exception 'moderation target is not a project reviewer'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create function private.validate_moderation_event()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  case_record public.moderation_cases%rowtype;
  expected_sequence integer;
  normalized_fingerprints text[];
begin
  select * into case_record
  from public.moderation_cases moderation_case
  where moderation_case.id = new.moderation_case_pk
  for update;
  if not found then
    raise exception 'moderation case does not exist' using errcode = '23503';
  end if;

  select coalesce(max(event.event_sequence), 0) + 1
  into expected_sequence
  from public.moderation_events event
  where event.moderation_case_pk = new.moderation_case_pk;
  if new.event_sequence <> expected_sequence then
    raise exception 'moderation event sequence must be contiguous'
      using errcode = '23514';
  end if;
  if exists (
    select 1 from public.moderation_events event
    where event.moderation_case_pk = new.moderation_case_pk
      and event.action = 'case_closed'
  ) then
    raise exception 'closed moderation case cannot change' using errcode = '23514';
  end if;

  select coalesce(array_agg(distinct fingerprint order by fingerprint), '{}'::text[])
  into normalized_fingerprints
  from unnest(new.evidence_fingerprints) fingerprint;
  if new.evidence_fingerprints is distinct from normalized_fingerprints
     or exists (
       select 1 from unnest(new.evidence_fingerprints) fingerprint
       where fingerprint !~ '^[0-9a-f]{64}$'
     ) then
    raise exception 'moderation evidence fingerprints must be unique sorted SHA-256 values'
      using errcode = '23514';
  end if;

  if new.action = 'reported' then
    if new.event_sequence <> 1
       or case_record.target_kind <> 'review_comment'
       or new.visibility_effect <> 'unchanged'
       or new.membership_effect <> 'unchanged'
       or new.related_evidence_fingerprint is not null
       or not exists (
         select 1 from private.moderation_reporters reporter
         where reporter.moderation_case_pk = new.moderation_case_pk
           and reporter.reporter_reviewer_profile_pk = new.actor_reviewer_profile_pk
       ) then
      raise exception 'reported event does not match its private reporter and comment case'
        using errcode = '23514';
    end if;
  elsif new.action = 'appeal_submitted' then
    if new.actor_reviewer_profile_pk <> case_record.target_reviewer_profile_pk
       or new.visibility_effect <> 'unchanged'
       or new.membership_effect <> 'unchanged'
       or not exists (
         select 1 from public.moderation_appeals appeal
         where appeal.moderation_case_pk = new.moderation_case_pk
           and appeal.appellant_reviewer_profile_pk = new.actor_reviewer_profile_pk
           and appeal.appeal_fingerprint = new.related_evidence_fingerprint
       ) then
      raise exception 'appeal event does not match its target reviewer and appeal'
        using errcode = '23514';
    end if;
  else
    if not exists (
      select 1 from public.project_memberships membership
      where membership.project_pk = case_record.project_pk
        and membership.reviewer_profile_pk = new.actor_reviewer_profile_pk
        and membership.status = 'active'
        and membership.role in ('curator', 'administrator')
    ) then
      raise exception 'moderation action requires an active project curator'
        using errcode = '42501';
    end if;
  end if;

  if new.action = 'content_hidden' and (
    case_record.target_review_event_pk is null
    or new.visibility_effect <> 'hidden'
    or new.membership_effect <> 'unchanged'
    or new.related_evidence_fingerprint is not null
  ) then
    raise exception 'content-hidden action has invalid effects' using errcode = '23514';
  elsif new.action = 'content_restored' and (
    case_record.target_review_event_pk is null
    or new.visibility_effect <> 'restored'
    or new.membership_effect <> 'unchanged'
    or new.related_evidence_fingerprint is not null
  ) then
    raise exception 'content-restored action has invalid effects' using errcode = '23514';
  elsif new.action = 'reviewer_suspended' and (
    new.visibility_effect <> 'unchanged'
    or new.membership_effect <> 'suspended'
    or new.related_evidence_fingerprint is not null
  ) then
    raise exception 'reviewer-suspended action has invalid effects' using errcode = '23514';
  elsif new.action = 'reviewer_reinstated' and (
    new.visibility_effect <> 'unchanged'
    or new.membership_effect <> 'reinstated'
    or new.related_evidence_fingerprint is not null
  ) then
    raise exception 'reviewer-reinstated action has invalid effects' using errcode = '23514';
  elsif new.action in ('review_audit_opened', 'case_closed') and (
    new.visibility_effect <> 'unchanged'
    or new.membership_effect <> 'unchanged'
    or new.related_evidence_fingerprint is not null
  ) then
    raise exception 'moderation state action has invalid effects' using errcode = '23514';
  elsif new.action in ('review_audit_completed', 'appeal_denied', 'curator_note_added') and (
    new.visibility_effect <> 'unchanged'
    or new.membership_effect <> 'unchanged'
    or new.related_evidence_fingerprint is null
  ) then
    raise exception 'moderation evidence action has invalid effects' using errcode = '23514';
  elsif new.action = 'appeal_upheld' and new.related_evidence_fingerprint is null then
    raise exception 'upheld appeal requires its exact appeal fingerprint'
      using errcode = '23514';
  end if;

  if new.action = 'curator_note_added' and not exists (
    select 1 from public.moderation_curator_notes note
    where note.moderation_case_pk = new.moderation_case_pk
      and note.curator_reviewer_profile_pk = new.actor_reviewer_profile_pk
      and note.note_fingerprint = new.related_evidence_fingerprint
  ) then
    raise exception 'curator-note event does not match its private note'
      using errcode = '23514';
  end if;
  if new.action in ('appeal_upheld', 'appeal_denied') and not exists (
    select 1 from public.moderation_appeals appeal
    where appeal.moderation_case_pk = new.moderation_case_pk
      and appeal.appeal_fingerprint = new.related_evidence_fingerprint
  ) then
    raise exception 'appeal decision does not match an appeal'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create function private.reject_moderation_ledger_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'moderation ledgers are append only' using errcode = '55000';
end;
$$;

create trigger moderation_cases_validate
before insert on public.moderation_cases
for each row execute function private.validate_moderation_case();
create trigger moderation_cases_reject_mutation
before update or delete on public.moderation_cases
for each row execute function private.reject_moderation_ledger_mutation();
create trigger moderation_reporters_reject_mutation
before update or delete on private.moderation_reporters
for each row execute function private.reject_moderation_ledger_mutation();
create trigger moderation_appeals_reject_mutation
before update or delete on public.moderation_appeals
for each row execute function private.reject_moderation_ledger_mutation();
create trigger moderation_curator_notes_reject_mutation
before update or delete on public.moderation_curator_notes
for each row execute function private.reject_moderation_ledger_mutation();
create trigger moderation_events_validate
before insert on public.moderation_events
for each row execute function private.validate_moderation_event();
create trigger moderation_events_reject_mutation
before update or delete on public.moderation_events
for each row execute function private.reject_moderation_ledger_mutation();

create function private.is_moderation_case_party(target_case_pk bigint)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.moderation_cases moderation_case
    join public.reviewer_profiles profile
      on profile.auth_user_id = (select auth.uid())
    left join private.moderation_reporters reporter
      on reporter.moderation_case_pk = moderation_case.id
    where moderation_case.id = target_case_pk
      and (
        moderation_case.target_reviewer_profile_pk = profile.id
        or reporter.reporter_reviewer_profile_pk = profile.id
      )
  );
$$;

create function public.report_review_comment(
  target_review_event_id text,
  target_reason_category text,
  target_report_detail text,
  target_case_fingerprint text,
  target_event_fingerprint text
)
returns table (
  stored_moderation_case_id text,
  stored_moderation_event_id text,
  stored_case_fingerprint text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  reporter_profile_pk bigint;
  target_record record;
  inserted_case record;
  inserted_event record;
begin
  if caller_auth_user_id is null then
    raise exception 'comment reporting requires authentication' using errcode = '42501';
  end if;
  if target_reason_category not in (
    'abuse', 'harassment', 'hate', 'threat', 'doxxing',
    'sensitive_location', 'impersonation', 'rights', 'spam',
    'review_manipulation', 'other'
  ) or length(btrim(target_report_detail)) not between 1 and 2000 then
    raise exception 'comment report reason or detail is invalid' using errcode = '22023';
  end if;

  select review.id as review_event_pk, review.reviewer_profile_pk,
    campaign.project_pk, review.comment
  into target_record
  from public.review_events review
  join public.verification_campaigns campaign
    on campaign.id = review.verification_campaign_pk
  where review.review_event_id = target_review_event_id
  for key share of review;
  if not found or length(btrim(target_record.comment)) = 0 then
    raise exception 'reportable review comment does not exist' using errcode = '22023';
  end if;

  select profile.id into reporter_profile_pk
  from public.reviewer_profiles profile
  join public.project_memberships membership
    on membership.reviewer_profile_pk = profile.id
    and membership.project_pk = target_record.project_pk
  where profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and membership.status = 'active';
  if not found then
    raise exception 'comment reporting requires an active project member'
      using errcode = '42501';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(reporter_profile_pk::text || ':' || target_record.review_event_pk::text, 0)
  );
  if exists (
    select 1
    from public.moderation_cases moderation_case
    join private.moderation_reporters reporter
      on reporter.moderation_case_pk = moderation_case.id
    where moderation_case.target_review_event_pk = target_record.review_event_pk
      and reporter.reporter_reviewer_profile_pk = reporter_profile_pk
  ) then
    raise exception 'reviewer has already reported this comment' using errcode = '23505';
  end if;

  insert into public.moderation_cases (
    moderation_case_id, project_pk, target_kind, target_review_event_pk,
    target_reviewer_profile_pk, reason_category, reason_summary, case_fingerprint
  ) values (
    'moderation-case:' || replace(gen_random_uuid()::text, '-', ''),
    target_record.project_pk, 'review_comment', target_record.review_event_pk,
    target_record.reviewer_profile_pk, target_reason_category,
    'Community report: ' || replace(target_reason_category, '_', ' ') || '.',
    target_case_fingerprint
  ) returning id, moderation_case_id, case_fingerprint into inserted_case;

  insert into private.moderation_reporters (
    moderation_case_pk, reporter_reviewer_profile_pk, report_detail
  ) values (inserted_case.id, reporter_profile_pk, btrim(target_report_detail));

  insert into public.moderation_events (
    moderation_event_id, moderation_case_pk, event_sequence, action,
    actor_reviewer_profile_pk, reason, event_fingerprint
  ) values (
    'moderation-event:' || replace(gen_random_uuid()::text, '-', ''),
    inserted_case.id, 1, 'reported', reporter_profile_pk,
    'Community member reported a review comment for curator assessment.',
    target_event_fingerprint
  ) returning moderation_event_id, recorded_at into inserted_event;

  return query select inserted_case.moderation_case_id,
    inserted_event.moderation_event_id, inserted_case.case_fingerprint,
    inserted_event.recorded_at;
end;
$$;

create function public.open_review_audit_case(
  target_review_event_id text,
  target_reason_summary text,
  target_case_fingerprint text,
  target_event_fingerprint text
)
returns table (
  stored_moderation_case_id text,
  stored_moderation_event_id text,
  stored_case_fingerprint text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  curator_profile_pk bigint;
  target_record record;
  inserted_case record;
  inserted_event record;
begin
  if caller_auth_user_id is null
     or length(btrim(target_reason_summary)) not between 1 and 500 then
    raise exception 'review audit request is invalid' using errcode = '22023';
  end if;

  select review.id as review_event_pk, review.reviewer_profile_pk,
    campaign.project_pk
  into target_record
  from public.review_events review
  join public.verification_campaigns campaign
    on campaign.id = review.verification_campaign_pk
  where review.review_event_id = target_review_event_id
  for key share of review;
  if not found then
    raise exception 'review audit target does not exist' using errcode = '22023';
  end if;

  select profile.id into curator_profile_pk
  from public.reviewer_profiles profile
  join public.project_memberships membership
    on membership.reviewer_profile_pk = profile.id
    and membership.project_pk = target_record.project_pk
  where profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and membership.status = 'active'
    and membership.role in ('curator', 'administrator');
  if not found then
    raise exception 'review audit requires an active project curator'
      using errcode = '42501';
  end if;

  perform pg_advisory_xact_lock(target_record.review_event_pk);
  if exists (
    select 1 from public.moderation_cases moderation_case
    where moderation_case.target_kind = 'review_audit'
      and moderation_case.target_review_event_pk = target_record.review_event_pk
      and not exists (
        select 1 from public.moderation_events event
        where event.moderation_case_pk = moderation_case.id
          and event.action = 'case_closed'
      )
  ) then
    raise exception 'an open review audit already exists' using errcode = '23505';
  end if;

  insert into public.moderation_cases (
    moderation_case_id, project_pk, target_kind, target_review_event_pk,
    target_reviewer_profile_pk, reason_category, reason_summary, case_fingerprint
  ) values (
    'moderation-case:' || replace(gen_random_uuid()::text, '-', ''),
    target_record.project_pk, 'review_audit', target_record.review_event_pk,
    target_record.reviewer_profile_pk, 'integrity_audit',
    btrim(target_reason_summary), target_case_fingerprint
  ) returning id, moderation_case_id, case_fingerprint into inserted_case;

  insert into public.moderation_events (
    moderation_event_id, moderation_case_pk, event_sequence, action,
    actor_reviewer_profile_pk, reason, event_fingerprint
  ) values (
    'moderation-event:' || replace(gen_random_uuid()::text, '-', ''),
    inserted_case.id, 1, 'review_audit_opened', curator_profile_pk,
    btrim(target_reason_summary), target_event_fingerprint
  ) returning moderation_event_id, recorded_at into inserted_event;

  return query select inserted_case.moderation_case_id,
    inserted_event.moderation_event_id, inserted_case.case_fingerprint,
    inserted_event.recorded_at;
end;
$$;

create function public.appeal_moderation_case(
  target_moderation_case_id text,
  target_rationale text,
  target_appeal_fingerprint text,
  target_event_fingerprint text
)
returns table (
  stored_moderation_appeal_id text,
  stored_moderation_event_id text,
  stored_appeal_fingerprint text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  appellant_profile_pk bigint;
  case_record public.moderation_cases%rowtype;
  next_sequence integer;
  inserted_appeal record;
  inserted_event record;
  current_visibility text;
  current_membership text;
begin
  if caller_auth_user_id is null
     or length(btrim(target_rationale)) not between 1 and 4000 then
    raise exception 'moderation appeal is invalid' using errcode = '22023';
  end if;
  select moderation_case.* into case_record
  from public.moderation_cases moderation_case
  where moderation_case.moderation_case_id = target_moderation_case_id
  for update;
  if not found then
    raise exception 'moderation case does not exist' using errcode = '22023';
  end if;

  select profile.id into appellant_profile_pk
  from public.reviewer_profiles profile
  where profile.auth_user_id = caller_auth_user_id
    and profile.id = case_record.target_reviewer_profile_pk;
  if not found then
    raise exception 'only the affected reviewer may appeal' using errcode = '42501';
  end if;
  if exists (
    select 1 from public.moderation_appeals appeal
    where appeal.moderation_case_pk = case_record.id
  ) then
    raise exception 'moderation case already has an appeal' using errcode = '23505';
  end if;

  select event.visibility_effect into current_visibility
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id
    and event.visibility_effect <> 'unchanged'
  order by event.event_sequence desc limit 1;
  select event.membership_effect into current_membership
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id
    and event.membership_effect <> 'unchanged'
  order by event.event_sequence desc limit 1;
  if current_visibility is distinct from 'hidden'
     and current_membership is distinct from 'suspended' then
    raise exception 'moderation case has no active appealable effect'
      using errcode = '23514';
  end if;

  insert into public.moderation_appeals (
    moderation_appeal_id, moderation_case_pk, appellant_reviewer_profile_pk,
    rationale, appeal_fingerprint
  ) values (
    'moderation-appeal:' || replace(gen_random_uuid()::text, '-', ''),
    case_record.id, appellant_profile_pk, btrim(target_rationale),
    target_appeal_fingerprint
  ) returning moderation_appeal_id, appeal_fingerprint into inserted_appeal;

  select coalesce(max(event.event_sequence), 0) + 1 into next_sequence
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id;
  insert into public.moderation_events (
    moderation_event_id, moderation_case_pk, event_sequence, action,
    actor_reviewer_profile_pk, reason, related_evidence_fingerprint,
    event_fingerprint
  ) values (
    'moderation-event:' || replace(gen_random_uuid()::text, '-', ''),
    case_record.id, next_sequence, 'appeal_submitted', appellant_profile_pk,
    'Affected reviewer submitted an appeal for curator review.',
    target_appeal_fingerprint, target_event_fingerprint
  ) returning moderation_event_id, recorded_at into inserted_event;

  return query select inserted_appeal.moderation_appeal_id,
    inserted_event.moderation_event_id, inserted_appeal.appeal_fingerprint,
    inserted_event.recorded_at;
end;
$$;

create function public.moderate_community_case(
  target_moderation_case_id text,
  target_action text,
  target_reason text,
  target_evidence_fingerprints text[],
  target_related_evidence_fingerprint text,
  target_event_fingerprint text
)
returns table (
  stored_moderation_case_id text,
  stored_moderation_event_id text,
  stored_action text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  curator_profile_pk bigint;
  case_record public.moderation_cases%rowtype;
  target_membership record;
  next_sequence integer;
  visibility_effect text := 'unchanged';
  membership_effect text := 'unchanged';
  current_visibility text;
  appeal_record record;
  inserted_event record;
begin
  if caller_auth_user_id is null
     or target_action not in (
       'content_hidden', 'content_restored', 'reviewer_suspended',
       'reviewer_reinstated', 'review_audit_opened',
       'review_audit_completed', 'appeal_upheld', 'appeal_denied', 'case_closed'
     )
     or length(btrim(target_reason)) not between 1 and 1000
     or coalesce(cardinality(target_evidence_fingerprints), 0) < 1 then
    raise exception 'moderation action is invalid' using errcode = '22023';
  end if;

  select moderation_case.* into case_record
  from public.moderation_cases moderation_case
  where moderation_case.moderation_case_id = target_moderation_case_id
  for update;
  if not found then
    raise exception 'moderation case does not exist' using errcode = '22023';
  end if;
  if exists (
    select 1 from public.moderation_events event
    where event.moderation_case_pk = case_record.id and event.action = 'case_closed'
  ) then
    raise exception 'closed moderation case cannot change' using errcode = '23514';
  end if;

  select profile.id into curator_profile_pk
  from public.reviewer_profiles profile
  join public.project_memberships membership
    on membership.reviewer_profile_pk = profile.id
    and membership.project_pk = case_record.project_pk
  where profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and membership.status = 'active'
    and membership.role in ('curator', 'administrator');
  if not found then
    raise exception 'moderation action requires an active project curator'
      using errcode = '42501';
  end if;

  select event.visibility_effect into current_visibility
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id
    and event.visibility_effect <> 'unchanged'
  order by event.event_sequence desc limit 1;

  if target_action = 'content_hidden' then
    if case_record.target_review_event_pk is null
       or current_visibility is not distinct from 'hidden' then
      raise exception 'comment is unavailable or already hidden' using errcode = '23514';
    end if;
    visibility_effect := 'hidden';
  elsif target_action = 'content_restored' then
    if current_visibility is distinct from 'hidden' then
      raise exception 'comment is not hidden' using errcode = '23514';
    end if;
    visibility_effect := 'restored';
  elsif target_action in ('reviewer_suspended', 'reviewer_reinstated') then
    if curator_profile_pk = case_record.target_reviewer_profile_pk then
      raise exception 'curator cannot moderate their own membership'
        using errcode = '42501';
    end if;
    select membership.id, membership.status, membership.role
    into target_membership
    from public.project_memberships membership
    where membership.project_pk = case_record.project_pk
      and membership.reviewer_profile_pk = case_record.target_reviewer_profile_pk
    for update;
    if not found or target_membership.role not in ('reviewer', 'expert') then
      raise exception 'only reviewer or expert membership may be suspended here'
        using errcode = '42501';
    end if;
    if target_action = 'reviewer_suspended' then
      if target_membership.status <> 'active' then
        raise exception 'reviewer membership is not active' using errcode = '23514';
      end if;
      update public.project_memberships
      set status = 'paused', updated_at = now()
      where id = target_membership.id;
      membership_effect := 'suspended';
    else
      if target_membership.status <> 'paused' then
        raise exception 'reviewer membership is not suspended' using errcode = '23514';
      end if;
      update public.project_memberships
      set status = 'active', updated_at = now()
      where id = target_membership.id;
      membership_effect := 'reinstated';
    end if;
  elsif target_action = 'review_audit_opened' then
    if exists (
      select 1 from public.moderation_events event
      where event.moderation_case_pk = case_record.id
        and event.action in ('review_audit_opened', 'review_audit_completed')
    ) then
      raise exception 'review audit already exists for this case' using errcode = '23505';
    end if;
  elsif target_action = 'review_audit_completed' then
    if target_related_evidence_fingerprint is null
       or not exists (
         select 1 from public.moderation_events event
         where event.moderation_case_pk = case_record.id
           and event.action = 'review_audit_opened'
       )
       or exists (
         select 1 from public.moderation_events event
         where event.moderation_case_pk = case_record.id
           and event.action = 'review_audit_completed'
       ) then
      raise exception 'review audit completion lacks an open audit or evidence'
        using errcode = '23514';
    end if;
  elsif target_action in ('appeal_upheld', 'appeal_denied') then
    select appeal.id, appeal.appeal_fingerprint into appeal_record
    from public.moderation_appeals appeal
    where appeal.moderation_case_pk = case_record.id
      and appeal.appeal_fingerprint = target_related_evidence_fingerprint;
    if not found or exists (
      select 1 from public.moderation_events event
      where event.moderation_case_pk = case_record.id
        and event.action in ('appeal_upheld', 'appeal_denied')
    ) then
      raise exception 'appeal decision lacks one unresolved exact appeal'
        using errcode = '23514';
    end if;
    if target_action = 'appeal_upheld' then
      if current_visibility is not distinct from 'hidden' then
        visibility_effect := 'restored';
      end if;
      select membership.id, membership.status, membership.role
      into target_membership
      from public.project_memberships membership
      where membership.project_pk = case_record.project_pk
        and membership.reviewer_profile_pk = case_record.target_reviewer_profile_pk
      for update;
      if found and target_membership.status = 'paused'
         and target_membership.role in ('reviewer', 'expert') then
        update public.project_memberships
        set status = 'active', updated_at = now()
        where id = target_membership.id;
        membership_effect := 'reinstated';
      end if;
    end if;
  end if;

  if target_action not in ('review_audit_completed', 'appeal_upheld', 'appeal_denied')
     and target_related_evidence_fingerprint is not null then
    raise exception 'related fingerprint is not allowed for this action'
      using errcode = '22023';
  end if;
  if target_action in ('appeal_upheld', 'appeal_denied', 'review_audit_completed')
     and target_related_evidence_fingerprint is null then
    raise exception 'moderation action requires related evidence fingerprint'
      using errcode = '22023';
  end if;

  select coalesce(max(event.event_sequence), 0) + 1 into next_sequence
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id;
  insert into public.moderation_events (
    moderation_event_id, moderation_case_pk, event_sequence, action,
    actor_reviewer_profile_pk, reason, evidence_fingerprints,
    related_evidence_fingerprint, visibility_effect, membership_effect,
    event_fingerprint
  ) values (
    'moderation-event:' || replace(gen_random_uuid()::text, '-', ''),
    case_record.id, next_sequence, target_action, curator_profile_pk,
    btrim(target_reason), target_evidence_fingerprints,
    target_related_evidence_fingerprint, visibility_effect, membership_effect,
    target_event_fingerprint
  ) returning moderation_event_id, action, recorded_at into inserted_event;

  return query select case_record.moderation_case_id,
    inserted_event.moderation_event_id, inserted_event.action,
    inserted_event.recorded_at;
end;
$$;

create function public.add_moderation_curator_note(
  target_moderation_case_id text,
  target_note text,
  target_note_fingerprint text,
  target_event_fingerprint text
)
returns table (
  stored_moderation_curator_note_id text,
  stored_moderation_event_id text,
  stored_note_fingerprint text,
  stored_recorded_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  curator_profile_pk bigint;
  case_record public.moderation_cases%rowtype;
  next_sequence integer;
  inserted_note record;
  inserted_event record;
begin
  if caller_auth_user_id is null
     or length(btrim(target_note)) not between 1 and 4000 then
    raise exception 'curator note is invalid' using errcode = '22023';
  end if;
  select moderation_case.* into case_record
  from public.moderation_cases moderation_case
  where moderation_case.moderation_case_id = target_moderation_case_id
  for update;
  if not found then
    raise exception 'moderation case does not exist' using errcode = '22023';
  end if;
  select profile.id into curator_profile_pk
  from public.reviewer_profiles profile
  join public.project_memberships membership
    on membership.reviewer_profile_pk = profile.id
    and membership.project_pk = case_record.project_pk
  where profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and membership.status = 'active'
    and membership.role in ('curator', 'administrator');
  if not found then
    raise exception 'curator note requires an active project curator'
      using errcode = '42501';
  end if;

  insert into public.moderation_curator_notes (
    moderation_curator_note_id, moderation_case_pk,
    curator_reviewer_profile_pk, note, note_fingerprint
  ) values (
    'moderation-note:' || replace(gen_random_uuid()::text, '-', ''),
    case_record.id, curator_profile_pk, btrim(target_note), target_note_fingerprint
  ) returning moderation_curator_note_id, note_fingerprint into inserted_note;

  select coalesce(max(event.event_sequence), 0) + 1 into next_sequence
  from public.moderation_events event
  where event.moderation_case_pk = case_record.id;
  insert into public.moderation_events (
    moderation_event_id, moderation_case_pk, event_sequence, action,
    actor_reviewer_profile_pk, reason, related_evidence_fingerprint,
    event_fingerprint
  ) values (
    'moderation-event:' || replace(gen_random_uuid()::text, '-', ''),
    case_record.id, next_sequence, 'curator_note_added', curator_profile_pk,
    'A private curator note was added to the moderation audit.',
    target_note_fingerprint, target_event_fingerprint
  ) returning moderation_event_id, recorded_at into inserted_event;

  return query select inserted_note.moderation_curator_note_id,
    inserted_event.moderation_event_id, inserted_note.note_fingerprint,
    inserted_event.recorded_at;
end;
$$;

alter table public.moderation_cases enable row level security;
alter table private.moderation_reporters enable row level security;
alter table public.moderation_appeals enable row level security;
alter table public.moderation_curator_notes enable row level security;
alter table public.moderation_events enable row level security;

revoke all on table public.moderation_cases, public.moderation_appeals,
  public.moderation_curator_notes, public.moderation_events
from public, anon, authenticated;
revoke all on table private.moderation_reporters
from public, anon, authenticated;
revoke all on sequence public.moderation_cases_id_seq,
  public.moderation_appeals_id_seq, public.moderation_curator_notes_id_seq,
  public.moderation_events_id_seq
from public, anon, authenticated;

grant select on table public.moderation_cases, public.moderation_appeals,
  public.moderation_curator_notes, public.moderation_events to authenticated;
grant select on table public.moderation_cases, public.moderation_appeals,
  public.moderation_curator_notes, public.moderation_events to service_role;

create policy moderation_cases_party_read
on public.moderation_cases for select to authenticated
using ((select private.is_moderation_case_party(id)));
create policy moderation_cases_curator_read
on public.moderation_cases for select to authenticated
using ((select private.has_project_role(
  project_pk, array['curator', 'administrator']::text[]
)));

create policy moderation_events_party_read
on public.moderation_events for select to authenticated
using ((select private.is_moderation_case_party(moderation_case_pk)));
create policy moderation_events_curator_read
on public.moderation_events for select to authenticated
using (exists (
  select 1 from public.moderation_cases moderation_case
  where moderation_case.id = moderation_events.moderation_case_pk
    and private.has_project_role(
      moderation_case.project_pk, array['curator', 'administrator']::text[]
    )
));

create policy moderation_appeals_self_read
on public.moderation_appeals for select to authenticated
using (exists (
  select 1 from public.reviewer_profiles profile
  where profile.id = moderation_appeals.appellant_reviewer_profile_pk
    and profile.auth_user_id = (select auth.uid())
));
create policy moderation_appeals_curator_read
on public.moderation_appeals for select to authenticated
using (exists (
  select 1 from public.moderation_cases moderation_case
  where moderation_case.id = moderation_appeals.moderation_case_pk
    and private.has_project_role(
      moderation_case.project_pk, array['curator', 'administrator']::text[]
    )
));

create policy moderation_curator_notes_curator_read
on public.moderation_curator_notes for select to authenticated
using (exists (
  select 1 from public.moderation_cases moderation_case
  where moderation_case.id = moderation_curator_notes.moderation_case_pk
    and private.has_project_role(
      moderation_case.project_pk, array['curator', 'administrator']::text[]
    )
));

create view public.moderated_review_comments
with (security_invoker = true)
as
select review.review_event_id,
  case
    when coalesce(latest_visibility.visibility_effect, 'restored') = 'hidden'
      then null
    else review.comment
  end as display_comment,
  case
    when coalesce(latest_visibility.visibility_effect, 'restored') = 'hidden'
      then 'hidden'
    else 'visible'
  end as visibility_state,
  review.event_fingerprint as retained_review_event_fingerprint,
  latest_visibility.moderation_case_id,
  latest_visibility.moderation_event_id as visibility_event_id
from public.review_events review
left join lateral (
  select event.visibility_effect, moderation_case.moderation_case_id,
    event.moderation_event_id
  from public.moderation_cases moderation_case
  join public.moderation_events event
    on event.moderation_case_pk = moderation_case.id
  where moderation_case.target_review_event_pk = review.id
    and event.visibility_effect <> 'unchanged'
  order by event.recorded_at desc, event.id desc
  limit 1
) latest_visibility on true
where length(review.comment) > 0;

revoke all on table public.moderated_review_comments
from public, anon, authenticated;
grant select on table public.moderated_review_comments to authenticated;

revoke all on function private.validate_moderation_case(),
  private.validate_moderation_event(), private.reject_moderation_ledger_mutation(),
  private.is_moderation_case_party(bigint)
from public, anon, authenticated;
grant execute on function private.is_moderation_case_party(bigint) to authenticated;

revoke all on function public.report_review_comment(text, text, text, text, text),
  public.open_review_audit_case(text, text, text, text),
  public.appeal_moderation_case(text, text, text, text),
  public.moderate_community_case(text, text, text, text[], text, text),
  public.add_moderation_curator_note(text, text, text, text)
from public, anon, authenticated;
grant execute on function public.report_review_comment(text, text, text, text, text),
  public.open_review_audit_case(text, text, text, text),
  public.appeal_moderation_case(text, text, text, text),
  public.moderate_community_case(text, text, text, text[], text, text),
  public.add_moderation_curator_note(text, text, text, text)
to authenticated;

comment on table public.moderation_cases is
  'Immutable moderation targets and public reason categories; reporter identity and detail remain private.';
comment on table public.moderation_events is
  'Append-only moderation audit with explicit content and project-membership effects; never scientific or reliability truth.';
comment on table public.moderation_appeals is
  'Append-only affected-reviewer appeals, visible only to the appellant and authorized curators.';
comment on table public.moderation_curator_notes is
  'Append-only private curator notes, excluded from reporter and target projections.';
comment on view public.moderated_review_comments is
  'Authenticated self/curator review projection that hides comment text without deleting the retained review event.';
