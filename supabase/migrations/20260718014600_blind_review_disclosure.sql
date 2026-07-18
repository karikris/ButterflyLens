-- ButterflyLens 8.4: enforce blind review in database projections and permit
-- only explicit, post-decision disclosure. Hiding client elements is not a
-- security boundary.

alter table public.review_events
add constraint review_events_assignment_event_identity_key
unique (id, assignment_pk);

create table public.review_disclosures (
  id bigint generated always as identity primary key,
  review_disclosure_id text not null,
  assignment_pk bigint not null references public.assignments (id) on delete restrict,
  revealed_after_event_pk bigint not null,
  disclosure_state text not null,
  disclosure_reason text not null,
  model_label text,
  model_score_band text,
  flickr_query_term text,
  provider_supplied_label text,
  source_comment_excerpt text,
  source_comment_display_allowed boolean not null default false,
  peer_decisive_count integer not null default 0,
  peer_yes_count integer not null default 0,
  peer_no_count integer not null default 0,
  peer_uncertain_count integer not null default 0,
  disclosure_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint review_disclosures_event_assignment_fk
    foreign key (revealed_after_event_pk, assignment_pk)
    references public.review_events (id, assignment_pk) on delete restrict,
  constraint review_disclosures_id_check
    check (review_disclosure_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint review_disclosures_state_check
    check (disclosure_state in ('available', 'unavailable', 'removed')),
  constraint review_disclosures_reason_check
    check (length(disclosure_reason) between 1 and 1000),
  constraint review_disclosures_model_label_check
    check (model_label is null or length(model_label) between 1 and 240),
  constraint review_disclosures_model_score_band_check
    check (
      model_score_band is null
      or model_score_band in ('very_low', 'low', 'medium', 'high', 'very_high')
    ),
  constraint review_disclosures_query_check
    check (flickr_query_term is null or length(flickr_query_term) between 1 and 500),
  constraint review_disclosures_provider_label_check
    check (provider_supplied_label is null or length(provider_supplied_label) between 1 and 500),
  constraint review_disclosures_comment_check
    check (
      (source_comment_excerpt is null or length(source_comment_excerpt) between 1 and 2000)
      and (source_comment_display_allowed or source_comment_excerpt is null)
    ),
  constraint review_disclosures_peer_counts_check
    check (
      peer_decisive_count >= 0
      and peer_yes_count >= 0
      and peer_no_count >= 0
      and peer_uncertain_count >= 0
      and peer_yes_count + peer_no_count <= peer_decisive_count
    ),
  constraint review_disclosures_removed_shape_check
    check (
      disclosure_state <> 'removed'
      or (
        model_label is null and model_score_band is null
        and flickr_query_term is null and provider_supplied_label is null
        and source_comment_excerpt is null
        and peer_decisive_count = 0 and peer_yes_count = 0
        and peer_no_count = 0 and peer_uncertain_count = 0
      )
    ),
  constraint review_disclosures_fingerprint_check
    check (disclosure_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint review_disclosures_no_scientific_claim_check
    check (not scientific_claim_allowed),
  constraint review_disclosures_id_key unique (review_disclosure_id),
  constraint review_disclosures_assignment_key unique (assignment_pk),
  constraint review_disclosures_fingerprint_key unique (disclosure_fingerprint)
);

create index review_disclosures_event_pk_idx
on public.review_disclosures (revealed_after_event_pk);

alter table public.review_disclosures enable row level security;
revoke all on table public.review_disclosures from public, anon, authenticated;
revoke all on sequence public.review_disclosures_id_seq
from public, anon, authenticated;
grant select, insert, update, delete on table public.review_disclosures
to service_role;
grant usage, select on sequence public.review_disclosures_id_seq to service_role;
grant select on table public.review_disclosures to authenticated;

create policy review_disclosures_respondent_read
on public.review_disclosures for select to authenticated
using (
  exists (
    select 1
    from public.assignments assignment
    join public.reviewer_profiles profile
      on profile.id = assignment.reviewer_profile_pk
    join public.review_events event
      on event.id = review_disclosures.revealed_after_event_pk
      and event.assignment_pk = assignment.id
      and event.reviewer_profile_pk = assignment.reviewer_profile_pk
    where assignment.id = review_disclosures.assignment_pk
      and assignment.status = 'responded'
      and profile.auth_user_id = (select auth.uid())
  )
);

create policy review_disclosures_curator_read
on public.review_disclosures for select to authenticated
using (
  exists (
    select 1
    from public.assignments assignment
    join public.verification_campaigns campaign
      on campaign.id = assignment.verification_campaign_pk
    where assignment.id = review_disclosures.assignment_pk
      and private.has_project_role(
        campaign.project_pk, array['curator', 'administrator']::text[]
      )
  )
);

create function private.enforce_blind_campaign()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not (
    new.blind_model_label
    and new.blind_model_score
    and new.blind_query_term
    and new.blind_source_comment
    and new.blind_peer_decisions
  ) then
    raise exception 'community review campaign must preserve the blind evidence boundary'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_blind_campaign()
from public, anon, authenticated;
grant execute on function private.enforce_blind_campaign() to service_role;

create trigger verification_campaigns_enforce_blind_review
before insert or update of blind_model_label, blind_model_score,
  blind_query_term, blind_source_comment, blind_peer_decisions
on public.verification_campaigns
for each row execute function private.enforce_blind_campaign();

grant select (
  id, media_object_id, project_pk, media_state, content_sha256, byte_count,
  media_type, width_pixels, height_pixels, decode_status, rights_fingerprint,
  rights_status, display_allowed, media_fingerprint, removed_at
) on public.media_objects to authenticated;

create policy media_objects_assigned_reviewer_read
on public.media_objects for select to authenticated
using (
  media_state = 'committed'
  and decode_status = 'valid'
  and rights_status = 'allowed'
  and display_allowed
  and exists (
    select 1
    from public.assignments assignment
    join public.reviewer_profiles profile
      on profile.id = assignment.reviewer_profile_pk
    where assignment.media_object_pk = media_objects.id
      and assignment.status in ('assigned', 'opened', 'responded')
      and profile.auth_user_id = (select auth.uid())
  )
);

create view public.blind_review_assignments
with (security_invoker = true)
as
select assignment.assignment_id, campaign.verification_campaign_id,
  media.media_object_id, campaign.question,
  assignment.status as assignment_status,
  assignment.blind_payload_fingerprint, media.content_sha256 as image_sha256,
  media.byte_count as image_byte_count, media.media_type,
  media.width_pixels, media.height_pixels, media.rights_fingerprint,
  false as scientific_claim_allowed
from public.assignments assignment
join public.verification_campaigns campaign
  on campaign.id = assignment.verification_campaign_pk
join public.media_objects media on media.id = assignment.media_object_pk
where assignment.status in ('assigned', 'opened', 'responded')
  and campaign.status = 'open'
  and media.media_state = 'committed'
  and media.decode_status = 'valid'
  and media.rights_status = 'allowed'
  and media.display_allowed
  and campaign.blind_model_label
  and campaign.blind_model_score
  and campaign.blind_query_term
  and campaign.blind_source_comment
  and campaign.blind_peer_decisions;

create view public.post_decision_review_disclosures
with (security_invoker = true)
as
select disclosure.review_disclosure_id, assignment.assignment_id,
  disclosure.disclosure_state, disclosure.disclosure_reason,
  disclosure.model_label, disclosure.model_score_band,
  disclosure.flickr_query_term, disclosure.provider_supplied_label,
  disclosure.source_comment_excerpt,
  disclosure.peer_decisive_count, disclosure.peer_yes_count,
  disclosure.peer_no_count, disclosure.peer_uncertain_count,
  disclosure.disclosure_fingerprint,
  disclosure.scientific_claim_allowed, disclosure.created_at
from public.review_disclosures disclosure
join public.assignments assignment on assignment.id = disclosure.assignment_pk;

revoke all on table public.blind_review_assignments,
  public.post_decision_review_disclosures from public;
grant select on table public.blind_review_assignments,
  public.post_decision_review_disclosures to authenticated;

comment on view public.blind_review_assignments is
  'Assigned-reviewer projection excluding model, query, source-comment, peer-decision, identity, and private-storage fields.';
comment on view public.post_decision_review_disclosures is
  'Allowlisted context visible only after the same reviewer has an append-only responded event.';
