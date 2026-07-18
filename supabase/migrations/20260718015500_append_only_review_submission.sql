-- ButterflyLens 8.5: append-only review and comment submission.
-- The authenticated RPC derives reviewer, campaign, media, question, and image
-- identity server-side and atomically marks the assignment responded.

alter table public.review_events
add constraint review_events_duration_upper_bound_check
  check (duration_ms is null or duration_ms <= 86400000);

create function private.enforce_review_event_append_lineage()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  current_event record;
  superseded_event record;
  assignment_record record;
begin
  perform pg_advisory_xact_lock(new.assignment_pk);

  select assignment.assigned_at, assignment.blind_payload_fingerprint,
    assignment.assignment_policy_version
  into assignment_record
  from public.assignments assignment
  where assignment.id = new.assignment_pk;

  if not found then
    raise exception 'review assignment does not exist' using errcode = '23503';
  end if;
  if new.confidence is null then
    raise exception 'review confidence must be recorded' using errcode = '23514';
  end if;
  if new.duration_ms is null then
    raise exception 'review duration must be recorded' using errcode = '23514';
  end if;
  if new.model_version is null or btrim(new.model_version) = '' then
    raise exception 'model version or explicit unavailable state must be recorded'
      using errcode = '23514';
  end if;
  if new.decided_at < assignment_record.assigned_at then
    raise exception 'review decision predates its assignment' using errcode = '23514';
  end if;
  if (new.review_context ->> 'blind_payload_fingerprint')
       is distinct from assignment_record.blind_payload_fingerprint
     or (new.review_context ->> 'assignment_policy_version')
       is distinct from assignment_record.assignment_policy_version
     or not coalesce(
       new.review_context ->> 'blind_state'
         in ('blind', 'post_disclosure_correction'),
       false
     )
     or (new.review_context -> 'scientific_claim_allowed')
       is distinct from 'false'::jsonb then
    raise exception 'review context does not preserve assignment and blind lineage'
      using errcode = '23514';
  end if;

  select event.id, event.assignment_pk, event.verification_campaign_pk,
    event.media_object_pk, event.reviewer_profile_pk, event.decided_at
  into current_event
  from public.review_events event
  where event.assignment_pk = new.assignment_pk
    and not exists (
      select 1 from public.review_events correction
      where correction.supersedes_event_pk = event.id
    )
  order by event.recorded_at desc, event.id desc
  limit 1;

  if not found then
    if new.supersedes_event_pk is not null then
      raise exception 'first review event cannot supersede another event'
        using errcode = '23514';
    end if;
    return new;
  end if;

  if new.supersedes_event_pk is null
     or new.supersedes_event_pk <> current_event.id then
    raise exception 'review correction must supersede the current event'
      using errcode = '23514';
  end if;

  select event.assignment_pk, event.verification_campaign_pk,
    event.media_object_pk, event.reviewer_profile_pk, event.decided_at
  into superseded_event
  from public.review_events event
  where event.id = new.supersedes_event_pk;

  if superseded_event.assignment_pk <> new.assignment_pk
     or superseded_event.verification_campaign_pk <> new.verification_campaign_pk
     or superseded_event.media_object_pk <> new.media_object_pk
     or superseded_event.reviewer_profile_pk <> new.reviewer_profile_pk then
    raise exception 'review correction crosses assignment identity'
      using errcode = '23514';
  end if;
  if new.decided_at < superseded_event.decided_at then
    raise exception 'review correction time precedes the event it supersedes'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_review_event_append_lineage()
from public, anon, authenticated;
grant execute on function private.enforce_review_event_append_lineage()
to service_role;

create trigger review_events_enforce_append_lineage
before insert on public.review_events
for each row execute function private.enforce_review_event_append_lineage();

drop policy if exists review_events_self_insert on public.review_events;
revoke insert on table public.review_events from authenticated;
revoke usage, select on sequence public.review_events_id_seq from authenticated;

create function public.submit_review_event(
  target_assignment_id text,
  target_review_event_id text,
  target_decision text,
  target_comment text,
  target_confidence smallint,
  target_decided_at timestamptz,
  target_duration_ms integer,
  target_source_version text,
  target_model_version text,
  target_event_fingerprint text,
  target_supersedes_review_event_id text default null,
  target_alternative_species_id text default null
)
returns table (
  stored_review_event_id text,
  stored_assignment_id text,
  stored_event_fingerprint text,
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
  supersedes_event_pk bigint;
  inserted_record record;
  blind_state text;
begin
  if caller_auth_user_id is null then
    raise exception 'review submission requires authentication'
      using errcode = '42501';
  end if;

  select assignment.id, assignment.assignment_id,
    assignment.verification_campaign_pk, assignment.media_object_pk,
    assignment.reviewer_profile_pk, assignment.status,
    assignment.blind_payload_fingerprint,
    assignment.assignment_policy_version,
    campaign.project_pk, campaign.question,
    media.content_sha256 as image_sha256
  into assignment_record
  from public.assignments assignment
  join public.reviewer_profiles profile
    on profile.id = assignment.reviewer_profile_pk
  join public.verification_campaigns campaign
    on campaign.id = assignment.verification_campaign_pk
  join public.media_objects media on media.id = assignment.media_object_pk
  where assignment.assignment_id = target_assignment_id
    and assignment.status in ('assigned', 'opened', 'responded')
    and profile.auth_user_id = caller_auth_user_id
    and profile.status = 'active'
    and campaign.status = 'open'
    and media.media_state = 'committed'
    and media.decode_status = 'valid'
    and media.rights_status = 'allowed'
    and media.display_allowed
  for update of assignment;

  if not found then
    raise exception 'active assigned review does not exist for this reviewer'
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

  if target_supersedes_review_event_id is not null then
    select event.id into supersedes_event_pk
    from public.review_events event
    where event.review_event_id = target_supersedes_review_event_id;
    if not found then
      raise exception 'superseded review event does not exist'
        using errcode = '23503';
    end if;
  end if;

  blind_state := case when exists (
    select 1 from public.review_disclosures disclosure
    where disclosure.assignment_pk = assignment_record.id
  ) then 'post_disclosure_correction' else 'blind' end;

  insert into public.review_events (
    review_event_id, assignment_pk, verification_campaign_pk,
    media_object_pk, reviewer_profile_pk, question, image_sha256,
    decision, alternative_species_pk, comment, confidence, decided_at,
    duration_ms, supersedes_event_pk, source_version, model_version,
    review_context, event_fingerprint
  ) values (
    target_review_event_id, assignment_record.id,
    assignment_record.verification_campaign_pk,
    assignment_record.media_object_pk,
    assignment_record.reviewer_profile_pk,
    assignment_record.question, assignment_record.image_sha256,
    target_decision, alternative_species_pk, coalesce(target_comment, ''),
    target_confidence, target_decided_at, target_duration_ms,
    supersedes_event_pk, target_source_version, target_model_version,
    jsonb_build_object(
      'blind_payload_fingerprint', assignment_record.blind_payload_fingerprint,
      'assignment_policy_version', assignment_record.assignment_policy_version,
      'blind_state', blind_state,
      'scientific_claim_allowed', false
    ),
    target_event_fingerprint
  )
  returning review_event_id, event_fingerprint, recorded_at
  into inserted_record;

  update public.assignments
  set status = 'responded',
    responded_at = coalesce(responded_at, inserted_record.recorded_at)
  where id = assignment_record.id;

  return query select inserted_record.review_event_id,
    assignment_record.assignment_id, inserted_record.event_fingerprint,
    inserted_record.recorded_at;
end;
$$;

revoke all on function public.submit_review_event(
  text, text, text, text, smallint, timestamptz, integer, text, text, text,
  text, text
) from public, anon, authenticated;
grant execute on function public.submit_review_event(
  text, text, text, text, smallint, timestamptz, integer, text, text, text,
  text, text
) to authenticated;

comment on function public.submit_review_event(
  text, text, text, text, smallint, timestamptz, integer, text, text, text,
  text, text
) is
  'Atomically appends a self-owned review/comment event and marks its assignment responded; corrections supersede without mutation.';
