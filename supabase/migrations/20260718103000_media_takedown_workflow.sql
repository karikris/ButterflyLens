-- ButterflyLens 13.4: private rights intake and fail-closed media takedown graph.
-- This migration performs no provider API call and deletes no media bytes.

create table public.media_rights_requests (
  id bigint generated always as identity primary key,
  media_rights_request_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  target_kind text not null,
  flickr_photo_pk bigint references public.flickr_photos (id) on delete restrict,
  media_object_pk bigint references public.media_objects (id) on delete restrict,
  flickr_removal_case_pk bigint references public.flickr_removal_cases (id) on delete restrict,
  target_fingerprint text not null,
  request_kind text not null,
  requester_basis text not null,
  public_summary text not null,
  policy_version text not null default 'butterflylens-media-rights:v1.0.0',
  received_at timestamptz not null,
  deadline_at timestamptz not null,
  request_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint media_rights_requests_id_check check (
    media_rights_request_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint media_rights_requests_target_kind_check
    check (target_kind in ('flickr_photo', 'media_object')),
  constraint media_rights_requests_target_shape_check check (
    (target_kind = 'flickr_photo' and flickr_photo_pk is not null
      and media_object_pk is null and flickr_removal_case_pk is not null)
    or
    (target_kind = 'media_object' and media_object_pk is not null
      and flickr_photo_pk is null and flickr_removal_case_pk is null)
  ),
  constraint media_rights_requests_target_fingerprint_check
    check (target_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_rights_requests_kind_check check (
    request_kind in (
      'takedown', 'privacy_removal', 'licence_correction',
      'attribution_correction', 'source_unavailable'
    )
  ),
  constraint media_rights_requests_basis_check check (
    requester_basis in (
      'owner', 'rights_holder', 'authorized_agent', 'provider', 'legal', 'privacy'
    )
  ),
  constraint media_rights_requests_summary_check check (
    public_summary = 'A private media rights request is under review.'
  ),
  constraint media_rights_requests_policy_check check (
    policy_version = 'butterflylens-media-rights:v1.0.0'
  ),
  constraint media_rights_requests_deadline_check
    check (deadline_at = received_at + interval '24 hours'),
  constraint media_rights_requests_fingerprint_check
    check (request_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_rights_requests_non_scientific_check
    check (not scientific_claim_allowed),
  constraint media_rights_requests_id_key unique (media_rights_request_id),
  constraint media_rights_requests_fingerprint_key unique (request_fingerprint),
  constraint media_rights_requests_flickr_target_key unique (flickr_photo_pk),
  constraint media_rights_requests_media_target_key unique (media_object_pk),
  constraint media_rights_requests_removal_case_key unique (flickr_removal_case_pk)
);

create table private.media_rights_requesters (
  media_rights_request_pk bigint primary key
    references public.media_rights_requests (id) on delete restrict,
  requester_reviewer_profile_pk bigint
    references public.reviewer_profiles (id) on delete restrict,
  external_request_reference text,
  private_request_detail text not null,
  contact_reference_fingerprint text not null,
  authority_evidence_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint media_rights_requesters_identity_shape_check check (
    (requester_reviewer_profile_pk is not null) <>
    (external_request_reference is not null)
  ),
  constraint media_rights_requesters_external_reference_check check (
    external_request_reference is null
    or (length(external_request_reference) between 1 and 240
      and external_request_reference !~ E'[\\r\\n\\t]')
  ),
  constraint media_rights_requesters_detail_check
    check (length(btrim(private_request_detail)) between 1 and 4000),
  constraint media_rights_requesters_contact_fingerprint_check
    check (contact_reference_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_rights_requesters_authority_fingerprint_check
    check (authority_evidence_fingerprint ~ '^[0-9a-f]{64}$')
);

create table public.media_takedown_dependencies (
  id bigint generated always as identity primary key,
  media_takedown_dependency_id text not null,
  media_rights_request_pk bigint not null
    references public.media_rights_requests (id) on delete restrict,
  dependency_kind text not null,
  dependency_fingerprint text not null,
  discovered_at timestamptz not null default now(),
  constraint media_takedown_dependencies_id_check check (
    media_takedown_dependency_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint media_takedown_dependencies_kind_check check (
    dependency_kind in (
      'source_record', 'source_cache', 'public_display', 'thumbnail',
      'model_input', 'embedding', 'review', 'public_cell', 'packet',
      'export', 'mirror', 'signed_url'
    )
  ),
  constraint media_takedown_dependencies_fingerprint_check
    check (dependency_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_takedown_dependencies_id_key
    unique (media_takedown_dependency_id),
  constraint media_takedown_dependencies_target_key
    unique (media_rights_request_pk, dependency_kind, dependency_fingerprint)
);

create table public.media_takedown_inventory_receipts (
  id bigint generated always as identity primary key,
  media_takedown_inventory_receipt_id text not null,
  media_rights_request_pk bigint not null
    references public.media_rights_requests (id) on delete restrict,
  dependency_entries text[] not null,
  inventory_fingerprint text not null,
  worker_evidence_fingerprint text not null,
  attested_at timestamptz not null default now(),
  constraint media_takedown_inventory_receipts_id_check check (
    media_takedown_inventory_receipt_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint media_takedown_inventory_receipts_entries_check check (
    cardinality(dependency_entries) > 0
    and array_position(dependency_entries, null) is null
  ),
  constraint media_takedown_inventory_receipts_inventory_check
    check (inventory_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_takedown_inventory_receipts_worker_check
    check (worker_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_takedown_inventory_receipts_id_key
    unique (media_takedown_inventory_receipt_id),
  constraint media_takedown_inventory_receipts_request_key
    unique (media_rights_request_pk),
  constraint media_takedown_inventory_receipts_fingerprint_key
    unique (inventory_fingerprint)
);

create table public.media_rights_request_events (
  id bigint generated always as identity primary key,
  media_rights_request_event_id text not null,
  media_rights_request_pk bigint not null
    references public.media_rights_requests (id) on delete restrict,
  event_sequence integer not null,
  action text not null,
  actor_kind text not null,
  actor_reviewer_profile_pk bigint
    references public.reviewer_profiles (id) on delete restrict,
  media_takedown_dependency_pk bigint
    references public.media_takedown_dependencies (id) on delete restrict,
  reason text not null,
  downstream_effect text not null,
  evidence_fingerprints text[] not null default '{}',
  event_fingerprint text not null,
  recorded_at timestamptz not null default now(),
  scientific_claim_allowed boolean not null default false,
  constraint media_rights_request_events_id_check check (
    media_rights_request_event_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'
  ),
  constraint media_rights_request_events_sequence_check check (event_sequence >= 1),
  constraint media_rights_request_events_action_check check (
    action in (
      'received', 'authority_verified', 'authority_rejected',
      'dependency_quarantined', 'dependency_purged', 'dependency_removed',
      'dependency_invalidated', 'dependency_retained_independent_rights',
      'takedown_completed', 'request_declined', 'appeal_received',
      'appeal_resolved'
    )
  ),
  constraint media_rights_request_events_actor_check check (
    (actor_kind = 'requester' and actor_reviewer_profile_pk is not null)
    or (actor_kind = 'external_requester' and actor_reviewer_profile_pk is null)
    or (actor_kind = 'service' and actor_reviewer_profile_pk is null)
    or (actor_kind = 'curator' and actor_reviewer_profile_pk is not null)
  ),
  constraint media_rights_request_events_dependency_shape_check check (
    (action like 'dependency_%') = (media_takedown_dependency_pk is not null)
  ),
  constraint media_rights_request_events_reason_check
    check (length(btrim(reason)) between 1 and 1000),
  constraint media_rights_request_events_effect_check
    check (length(btrim(downstream_effect)) between 1 and 1000),
  constraint media_rights_request_events_evidence_check
    check (array_position(evidence_fingerprints, null) is null),
  constraint media_rights_request_events_fingerprint_check
    check (event_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint media_rights_request_events_non_scientific_check
    check (not scientific_claim_allowed),
  constraint media_rights_request_events_id_key
    unique (media_rights_request_event_id),
  constraint media_rights_request_events_sequence_key
    unique (media_rights_request_pk, event_sequence),
  constraint media_rights_request_events_fingerprint_key
    unique (event_fingerprint)
);

create index media_rights_requests_project_received_idx
on public.media_rights_requests (project_pk, received_at desc);
create index media_rights_requests_deadline_idx
on public.media_rights_requests (deadline_at);
create index media_takedown_dependencies_request_idx
on public.media_takedown_dependencies (media_rights_request_pk, dependency_kind);
create index media_rights_request_events_request_idx
on public.media_rights_request_events (media_rights_request_pk, event_sequence);
create index media_rights_request_events_dependency_idx
on public.media_rights_request_events (media_takedown_dependency_pk)
where media_takedown_dependency_pk is not null;

create or replace function private.quarantine_flickr_removal_case()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  update public.flickr_display_assets
  set display_state = 'quarantined', removal_case_pk = new.id,
      quarantined_at = new.quarantine_started_at
  where flickr_photo_pk = new.flickr_photo_pk
    and display_state in ('eligible', 'expired');

  update public.media_objects
  set media_state = case when media_state = 'committed' then 'quarantined'
                         else media_state end,
      rights_status = 'quarantined', download_allowed = false,
      model_inference_allowed = false, display_allowed = false,
      redistribution_allowed = false
  where flickr_photo_pk = new.flickr_photo_pk
    and media_state in ('pending', 'committed');

  update public.flickr_photos
  set rights_status = 'quarantined', download_allowed = false,
      model_inference_allowed = false, display_allowed = false,
      redistribution_allowed = false
  where id = new.flickr_photo_pk and rights_status <> 'removed';
  return new;
end;
$$;

create function private.validate_and_quarantine_media_rights_request()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected_project_pk bigint;
  expected_fingerprint text;
begin
  if new.target_kind = 'flickr_photo' then
    select photo.project_pk, photo.source_record_fingerprint
    into expected_project_pk, expected_fingerprint
    from public.flickr_photos photo
    join public.flickr_removal_cases removal
      on removal.id = new.flickr_removal_case_pk
      and removal.flickr_photo_pk = photo.id
      and removal.project_pk = photo.project_pk
    where photo.id = new.flickr_photo_pk;
  else
    select media.project_pk, media.media_fingerprint
    into expected_project_pk, expected_fingerprint
    from public.media_objects media
    where media.id = new.media_object_pk and media.source_kind <> 'flickr';
  end if;
  if expected_project_pk is null
    or new.project_pk <> expected_project_pk
    or new.target_fingerprint <> expected_fingerprint then
    raise exception 'media rights target lineage does not match'
      using errcode = '23514';
  end if;

  if new.target_kind = 'media_object' then
    with recursive affected as (
      select media.id from public.media_objects media
      where media.id = new.media_object_pk
      union all
      select child.id from public.media_objects child
      join affected parent on child.parent_media_pk = parent.id
    )
    update public.media_objects media
    set media_state = case when media.media_state = 'committed' then 'quarantined'
                           else media.media_state end,
        rights_status = 'quarantined', download_allowed = false,
        model_inference_allowed = false, display_allowed = false,
        redistribution_allowed = false
    where media.id in (select id from affected)
      and media.media_state in ('pending', 'committed');
  end if;
  return new;
end;
$$;

create function private.validate_media_takedown_dependency()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if exists (
    select 1 from public.media_takedown_inventory_receipts receipt
    where receipt.media_rights_request_pk = new.media_rights_request_pk
  ) then
    raise exception 'takedown inventory is already sealed' using errcode = '55000';
  end if;
  return new;
end;
$$;

create function private.validate_media_takedown_inventory_receipt()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected_entries text[];
begin
  select array_agg(
    dependency.dependency_kind || ':' || dependency.dependency_fingerprint
    order by dependency.dependency_kind, dependency.dependency_fingerprint
  ) into expected_entries
  from public.media_takedown_dependencies dependency
  where dependency.media_rights_request_pk = new.media_rights_request_pk;

  if expected_entries is null or new.dependency_entries <> expected_entries then
    raise exception 'takedown inventory entries do not exactly match dependencies'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create function private.validate_media_rights_request_event()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  expected_sequence integer;
  request_project_pk bigint;
  canonical_evidence text[];
begin
  perform pg_catalog.pg_advisory_xact_lock(new.media_rights_request_pk);
  select coalesce(max(event.event_sequence), 0) + 1
  into expected_sequence
  from public.media_rights_request_events event
  where event.media_rights_request_pk = new.media_rights_request_pk;
  if new.event_sequence <> expected_sequence then
    raise exception 'media rights event sequence is not contiguous'
      using errcode = '23514';
  end if;

  select request.project_pk into request_project_pk
  from public.media_rights_requests request
  where request.id = new.media_rights_request_pk;
  if request_project_pk is null then
    raise exception 'media rights request does not exist' using errcode = '23503';
  end if;

  select array_agg(fingerprint order by fingerprint)
  into canonical_evidence
  from (select distinct unnest(new.evidence_fingerprints) fingerprint) evidence;
  if coalesce(canonical_evidence, '{}'::text[]) <> new.evidence_fingerprints
    or exists (
      select 1 from unnest(new.evidence_fingerprints) fingerprint
      where fingerprint !~ '^[0-9a-f]{64}$'
    ) then
    raise exception 'event evidence fingerprints must be sorted, unique SHA-256 values'
      using errcode = '23514';
  end if;

  if new.actor_kind = 'curator' and not exists (
    select 1 from public.project_memberships membership
    where membership.project_pk = request_project_pk
      and membership.reviewer_profile_pk = new.actor_reviewer_profile_pk
      and membership.status = 'active'
      and membership.role in ('curator', 'administrator')
  ) then
    raise exception 'media rights curator lacks project authority'
      using errcode = '42501';
  end if;
  if new.media_takedown_dependency_pk is not null and not exists (
    select 1 from public.media_takedown_dependencies dependency
    where dependency.id = new.media_takedown_dependency_pk
      and dependency.media_rights_request_pk = new.media_rights_request_pk
  ) then
    raise exception 'media rights dependency belongs to another request'
      using errcode = '23514';
  end if;

  if new.action = 'received' and new.event_sequence <> 1 then
    raise exception 'received must be the first media rights event'
      using errcode = '23514';
  elsif new.action <> 'received' and new.event_sequence = 1 then
    raise exception 'first media rights event must be received'
      using errcode = '23514';
  end if;
  if new.action in ('authority_verified', 'authority_rejected') and exists (
    select 1 from public.media_rights_request_events event
    where event.media_rights_request_pk = new.media_rights_request_pk
      and event.action in ('authority_verified', 'authority_rejected')
  ) then
    raise exception 'media rights authority already decided' using errcode = '23505';
  end if;
  if new.action = 'dependency_retained_independent_rights'
    and cardinality(new.evidence_fingerprints) = 0 then
    raise exception 'independent rights retention requires evidence'
      using errcode = '23514';
  end if;
  if new.action in (
    'dependency_purged', 'dependency_removed', 'dependency_invalidated',
    'dependency_retained_independent_rights'
  ) and exists (
    select 1 from public.media_rights_request_events event
    where event.media_takedown_dependency_pk = new.media_takedown_dependency_pk
      and event.action in (
        'dependency_purged', 'dependency_removed', 'dependency_invalidated',
        'dependency_retained_independent_rights'
      )
  ) then
    raise exception 'media takedown dependency already has a terminal action'
      using errcode = '23505';
  end if;
  if new.action = 'takedown_completed' then
    if exists (
      select 1 from public.media_rights_request_events event
      where event.media_rights_request_pk = new.media_rights_request_pk
        and event.action = 'takedown_completed'
    ) then
      raise exception 'media takedown is already complete' using errcode = '23505';
    elsif not exists (
      select 1 from public.media_rights_request_events event
      where event.media_rights_request_pk = new.media_rights_request_pk
        and event.action = 'authority_verified'
    ) or not exists (
      select 1 from public.media_takedown_inventory_receipts receipt
      where receipt.media_rights_request_pk = new.media_rights_request_pk
        and receipt.inventory_fingerprint = any(new.evidence_fingerprints)
    ) or exists (
      select 1 from public.media_takedown_dependencies dependency
      where dependency.media_rights_request_pk = new.media_rights_request_pk
        and not exists (
          select 1 from public.media_rights_request_events event
          where event.media_takedown_dependency_pk = dependency.id
            and event.action in (
              'dependency_purged', 'dependency_removed',
              'dependency_invalidated', 'dependency_retained_independent_rights'
            )
        )
    ) then
      raise exception 'takedown completion requires verified authority, exact inventory, and terminal dependency actions'
        using errcode = '23514';
    end if;
  end if;
  return new;
end;
$$;

create function private.reject_media_rights_ledger_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'media rights ledgers are append only' using errcode = '55000';
end;
$$;

create trigger media_rights_requests_validate
before insert on public.media_rights_requests
for each row execute function private.validate_and_quarantine_media_rights_request();
create trigger media_rights_requests_reject_mutation
before update or delete on public.media_rights_requests
for each row execute function private.reject_media_rights_ledger_mutation();
create trigger media_rights_requesters_reject_mutation
before update or delete on private.media_rights_requesters
for each row execute function private.reject_media_rights_ledger_mutation();
create trigger media_takedown_dependencies_validate
before insert on public.media_takedown_dependencies
for each row execute function private.validate_media_takedown_dependency();
create trigger media_takedown_dependencies_reject_mutation
before update or delete on public.media_takedown_dependencies
for each row execute function private.reject_media_rights_ledger_mutation();
create trigger media_takedown_inventory_receipts_validate
before insert on public.media_takedown_inventory_receipts
for each row execute function private.validate_media_takedown_inventory_receipt();
create trigger media_takedown_inventory_receipts_reject_mutation
before update or delete on public.media_takedown_inventory_receipts
for each row execute function private.reject_media_rights_ledger_mutation();
create trigger media_rights_request_events_validate
before insert on public.media_rights_request_events
for each row execute function private.validate_media_rights_request_event();
create trigger media_rights_request_events_reject_mutation
before update or delete on public.media_rights_request_events
for each row execute function private.reject_media_rights_ledger_mutation();

create function private.inventory_media_rights_request(target_request_pk bigint)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_request record;
begin
  select * into target_request from public.media_rights_requests request
  where request.id = target_request_pk;
  if not found then
    raise exception 'media rights request does not exist' using errcode = '23503';
  end if;

  if target_request.target_kind = 'flickr_photo' then
    insert into public.media_takedown_dependencies (
      media_takedown_dependency_id, media_rights_request_pk,
      dependency_kind, dependency_fingerprint
    ) values (
      'takedown-dependency:' || replace(gen_random_uuid()::text, '-', ''),
      target_request_pk, 'source_record', target_request.target_fingerprint
    );
  else
    insert into public.media_takedown_dependencies (
      media_takedown_dependency_id, media_rights_request_pk,
      dependency_kind, dependency_fingerprint
    ) values (
      'takedown-dependency:' || replace(gen_random_uuid()::text, '-', ''),
      target_request_pk, 'source_record', target_request.target_fingerprint
    );
  end if;

  with recursive affected as (
    select media.id, media.media_fingerprint, media.object_kind
    from public.media_objects media
    where (target_request.target_kind = 'flickr_photo'
      and media.flickr_photo_pk = target_request.flickr_photo_pk)
      or (target_request.target_kind = 'media_object'
        and media.id = target_request.media_object_pk)
    union
    select child.id, child.media_fingerprint, child.object_kind
    from public.media_objects child
    join affected parent on child.parent_media_pk = parent.id
  )
  insert into public.media_takedown_dependencies (
    media_takedown_dependency_id, media_rights_request_pk,
    dependency_kind, dependency_fingerprint
  )
  select 'takedown-dependency:' || replace(gen_random_uuid()::text, '-', ''),
    target_request_pk,
    case when affected.object_kind = 'public_thumbnail' then 'thumbnail'
         when affected.object_kind = 'source_image' then 'source_cache'
         else 'model_input' end,
    affected.media_fingerprint
  from affected
  on conflict (media_rights_request_pk, dependency_kind, dependency_fingerprint)
  do nothing;

  with recursive affected as (
    select media.id from public.media_objects media
    where (target_request.target_kind = 'flickr_photo'
      and media.flickr_photo_pk = target_request.flickr_photo_pk)
      or (target_request.target_kind = 'media_object'
        and media.id = target_request.media_object_pk)
    union select child.id from public.media_objects child
    join affected parent on child.parent_media_pk = parent.id
  ), dependencies as (
    select 'public_display'::text kind, asset.display_fingerprint fingerprint
    from public.flickr_display_assets asset where asset.media_object_pk in (select id from affected)
    union all
    select case when evidence.evidence_kind = 'bioclip_embedding' then 'embedding'
                else 'model_input' end, evidence.evidence_fingerprint
    from public.model_evidence evidence where evidence.media_object_pk in (select id from affected)
    union all
    select 'review', review.event_fingerprint
    from public.review_events review where review.media_object_pk in (select id from affected)
    union all
    select 'public_cell', candidate.candidate_fingerprint
    from public.release_candidates candidate where candidate.media_object_pk in (select id from affected)
    union all
    select 'packet', candidate.evidence_packet_fingerprint
    from public.release_candidates candidate where candidate.media_object_pk in (select id from affected)
      and candidate.evidence_packet_fingerprint is not null
    union all
    select 'export', candidate.candidate_fingerprint
    from public.release_candidates candidate where candidate.media_object_pk in (select id from affected)
      and candidate.candidate_state = 'exported'
    union all
    select 'mirror', member.membership_fingerprint
    from public.duplicate_group_members member where member.media_object_pk in (select id from affected)
    union all
    select 'signed_url', receipt.request_fingerprint
    from public.b2_signing_receipts receipt where receipt.media_object_pk in (select id from affected)
      and receipt.expires_at > now()
  )
  insert into public.media_takedown_dependencies (
    media_takedown_dependency_id, media_rights_request_pk,
    dependency_kind, dependency_fingerprint
  )
  select 'takedown-dependency:' || replace(gen_random_uuid()::text, '-', ''),
    target_request_pk, dependencies.kind, dependencies.fingerprint
  from dependencies
  on conflict (media_rights_request_pk, dependency_kind, dependency_fingerprint)
  do nothing;
end;
$$;

create function private.open_media_rights_request(
  target_kind text,
  target_id text,
  target_request_kind text,
  target_requester_basis text,
  target_private_detail text,
  target_requester_reviewer_profile_pk bigint,
  target_external_request_reference text,
  target_contact_reference_fingerprint text,
  target_authority_evidence_fingerprint text,
  target_request_fingerprint text,
  target_case_fingerprint text,
  target_received_event_fingerprint text
)
returns table (
  stored_media_rights_request_id text,
  stored_request_fingerprint text,
  stored_deadline_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_record record;
  removal_case_pk bigint;
  inserted_request record;
  received_at_value timestamptz := now();
  actor_value text;
begin
  if target_kind = 'flickr_photo' then
    select photo.id target_pk, photo.project_pk,
      photo.source_record_fingerprint as target_fingerprint
    into target_record from public.flickr_photos photo
    where photo.flickr_photo_id = target_id;
    if not found then
      raise exception 'requested Flickr photo does not exist' using errcode = '22023';
    end if;
    insert into public.flickr_removal_cases (
      removal_case_id, project_pk, flickr_photo_pk, requester_basis,
      received_at, deadline_at, quarantine_started_at,
      authority_evidence_fingerprint, case_fingerprint
    ) values (
      'flickr-removal:' || replace(gen_random_uuid()::text, '-', ''),
      target_record.project_pk, target_record.target_pk, target_requester_basis,
      received_at_value, received_at_value + interval '24 hours', received_at_value,
      target_authority_evidence_fingerprint, target_case_fingerprint
    ) returning id into removal_case_pk;
  elsif target_kind = 'media_object' then
    select media.id target_pk, media.project_pk,
      media.media_fingerprint as target_fingerprint
    into target_record from public.media_objects media
    where media.media_object_id = target_id and media.source_kind <> 'flickr';
    if not found then
      raise exception 'requested non-Flickr media object does not exist'
        using errcode = '22023';
    end if;
  else
    raise exception 'requested media target kind is invalid' using errcode = '22023';
  end if;

  insert into public.media_rights_requests (
    media_rights_request_id, project_pk, target_kind, flickr_photo_pk,
    media_object_pk, flickr_removal_case_pk, target_fingerprint,
    request_kind, requester_basis, public_summary, received_at, deadline_at,
    request_fingerprint
  ) values (
    'media-rights:' || replace(gen_random_uuid()::text, '-', ''),
    target_record.project_pk, target_kind,
    case when target_kind = 'flickr_photo' then target_record.target_pk end,
    case when target_kind = 'media_object' then target_record.target_pk end,
    removal_case_pk, target_record.target_fingerprint,
    target_request_kind, target_requester_basis,
    'A private media rights request is under review.', received_at_value,
    received_at_value + interval '24 hours', target_request_fingerprint
  ) returning id, media_rights_request_id, request_fingerprint, deadline_at
  into inserted_request;

  insert into private.media_rights_requesters (
    media_rights_request_pk, requester_reviewer_profile_pk,
    external_request_reference, private_request_detail,
    contact_reference_fingerprint, authority_evidence_fingerprint
  ) values (
    inserted_request.id, target_requester_reviewer_profile_pk,
    target_external_request_reference, btrim(target_private_detail),
    target_contact_reference_fingerprint, target_authority_evidence_fingerprint
  );
  perform private.inventory_media_rights_request(inserted_request.id);

  actor_value := case when target_requester_reviewer_profile_pk is null
    then 'external_requester' else 'requester' end;
  insert into public.media_rights_request_events (
    media_rights_request_event_id, media_rights_request_pk, event_sequence,
    action, actor_kind, actor_reviewer_profile_pk, reason, downstream_effect,
    evidence_fingerprints, event_fingerprint
  ) values (
    'media-rights-event:' || replace(gen_random_uuid()::text, '-', ''),
    inserted_request.id, 1, 'received', actor_value,
    target_requester_reviewer_profile_pk,
    'Private media rights request received for authority review.',
    'Target and known descendants quarantined; public release suppressed.',
    array[target_authority_evidence_fingerprint], target_received_event_fingerprint
  );
  return query select inserted_request.media_rights_request_id,
    inserted_request.request_fingerprint, inserted_request.deadline_at;
end;
$$;

create function public.request_media_takedown(
  target_kind text,
  target_id text,
  target_request_kind text,
  target_requester_basis text,
  target_private_detail text,
  target_contact_reference_fingerprint text,
  target_authority_evidence_fingerprint text,
  target_request_fingerprint text,
  target_case_fingerprint text,
  target_received_event_fingerprint text
)
returns table (
  stored_media_rights_request_id text,
  stored_request_fingerprint text,
  stored_deadline_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  caller_profile_pk bigint;
begin
  if caller_auth_user_id is null then
    raise exception 'media rights request requires authentication'
      using errcode = '42501';
  end if;
  select profile.id into caller_profile_pk
  from public.reviewer_profiles profile
  where profile.auth_user_id = caller_auth_user_id and profile.status = 'active';
  if not found then
    raise exception 'media rights requester lacks an active permanent profile'
      using errcode = '42501';
  end if;
  return query select * from private.open_media_rights_request(
    target_kind, target_id, target_request_kind, target_requester_basis,
    target_private_detail, caller_profile_pk, null,
    target_contact_reference_fingerprint, target_authority_evidence_fingerprint,
    target_request_fingerprint, target_case_fingerprint,
    target_received_event_fingerprint
  );
end;
$$;

create function public.intake_external_media_takedown(
  target_kind text,
  target_id text,
  target_request_kind text,
  target_requester_basis text,
  target_private_detail text,
  target_external_request_reference text,
  target_contact_reference_fingerprint text,
  target_authority_evidence_fingerprint text,
  target_request_fingerprint text,
  target_case_fingerprint text,
  target_received_event_fingerprint text
)
returns table (
  stored_media_rights_request_id text,
  stored_request_fingerprint text,
  stored_deadline_at timestamptz
)
language sql
security definer
set search_path = ''
as $$
  select * from private.open_media_rights_request(
    target_kind, target_id, target_request_kind, target_requester_basis,
    target_private_detail, null, target_external_request_reference,
    target_contact_reference_fingerprint, target_authority_evidence_fingerprint,
    target_request_fingerprint, target_case_fingerprint,
    target_received_event_fingerprint
  );
$$;

create function public.decide_media_rights_authority(
  target_media_rights_request_id text,
  target_verified boolean,
  target_reason text,
  target_evidence_fingerprints text[],
  target_event_fingerprint text
)
returns table (stored_event_id text, stored_recorded_at timestamptz)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  target_request record;
  actor_profile_pk bigint;
  next_sequence integer;
  inserted_event record;
begin
  select request.id, request.project_pk into target_request
  from public.media_rights_requests request
  where request.media_rights_request_id = target_media_rights_request_id;
  if not found then raise exception 'media rights request does not exist' using errcode = '22023'; end if;
  select membership.reviewer_profile_pk into actor_profile_pk
  from public.project_memberships membership
  where membership.project_pk = target_request.project_pk
    and membership.auth_user_id = caller_auth_user_id
    and membership.status = 'active'
    and membership.role in ('curator', 'administrator');
  if not found then raise exception 'media rights decision requires curator authority' using errcode = '42501'; end if;
  perform pg_catalog.pg_advisory_xact_lock(target_request.id);
  select coalesce(max(event_sequence), 0) + 1 into next_sequence
  from public.media_rights_request_events where media_rights_request_pk = target_request.id;
  insert into public.media_rights_request_events (
    media_rights_request_event_id, media_rights_request_pk, event_sequence,
    action, actor_kind, actor_reviewer_profile_pk, reason, downstream_effect,
    evidence_fingerprints, event_fingerprint
  ) values (
    'media-rights-event:' || replace(gen_random_uuid()::text, '-', ''),
    target_request.id, next_sequence,
    case when target_verified then 'authority_verified' else 'authority_rejected' end,
    'curator', actor_profile_pk, btrim(target_reason),
    case when target_verified
      then 'Takedown traversal remains quarantined pending dependency resolution.'
      else 'Quarantine remains fail-closed pending separate rights revalidation.' end,
    target_evidence_fingerprints, target_event_fingerprint
  ) returning media_rights_request_event_id, recorded_at into inserted_event;
  return query select inserted_event.media_rights_request_event_id, inserted_event.recorded_at;
end;
$$;

create function public.register_media_takedown_dependency(
  target_media_rights_request_id text,
  target_dependency_kind text,
  target_dependency_fingerprint text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_request_pk bigint;
  stored_id text;
begin
  select id into target_request_pk from public.media_rights_requests
  where media_rights_request_id = target_media_rights_request_id;
  if not found then raise exception 'media rights request does not exist' using errcode = '22023'; end if;
  insert into public.media_takedown_dependencies (
    media_takedown_dependency_id, media_rights_request_pk,
    dependency_kind, dependency_fingerprint
  ) values (
    'takedown-dependency:' || replace(gen_random_uuid()::text, '-', ''),
    target_request_pk, target_dependency_kind, target_dependency_fingerprint
  ) returning media_takedown_dependency_id into stored_id;
  return stored_id;
end;
$$;

create function public.seal_media_takedown_inventory(
  target_media_rights_request_id text,
  target_dependency_entries text[],
  target_inventory_fingerprint text,
  target_worker_evidence_fingerprint text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_request_pk bigint;
  stored_id text;
begin
  select id into target_request_pk from public.media_rights_requests
  where media_rights_request_id = target_media_rights_request_id;
  if not found then raise exception 'media rights request does not exist' using errcode = '22023'; end if;
  insert into public.media_takedown_inventory_receipts (
    media_takedown_inventory_receipt_id, media_rights_request_pk,
    dependency_entries, inventory_fingerprint, worker_evidence_fingerprint
  ) values (
    'takedown-inventory:' || replace(gen_random_uuid()::text, '-', ''),
    target_request_pk, target_dependency_entries, target_inventory_fingerprint,
    target_worker_evidence_fingerprint
  ) returning media_takedown_inventory_receipt_id into stored_id;
  return stored_id;
end;
$$;

create function public.record_media_takedown_dependency_action(
  target_media_takedown_dependency_id text,
  target_action text,
  target_reason text,
  target_downstream_effect text,
  target_evidence_fingerprints text[],
  target_event_fingerprint text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_dependency record;
  next_sequence integer;
  stored_id text;
begin
  select dependency.id, dependency.media_rights_request_pk into target_dependency
  from public.media_takedown_dependencies dependency
  where dependency.media_takedown_dependency_id = target_media_takedown_dependency_id;
  if not found then raise exception 'media takedown dependency does not exist' using errcode = '22023'; end if;
  if target_action not in (
    'dependency_quarantined', 'dependency_purged', 'dependency_removed',
    'dependency_invalidated', 'dependency_retained_independent_rights'
  ) then raise exception 'media takedown dependency action is invalid' using errcode = '22023'; end if;
  perform pg_catalog.pg_advisory_xact_lock(target_dependency.media_rights_request_pk);
  select coalesce(max(event_sequence), 0) + 1 into next_sequence
  from public.media_rights_request_events
  where media_rights_request_pk = target_dependency.media_rights_request_pk;
  insert into public.media_rights_request_events (
    media_rights_request_event_id, media_rights_request_pk, event_sequence,
    action, actor_kind, media_takedown_dependency_pk, reason,
    downstream_effect, evidence_fingerprints, event_fingerprint
  ) values (
    'media-rights-event:' || replace(gen_random_uuid()::text, '-', ''),
    target_dependency.media_rights_request_pk, next_sequence, target_action,
    'service', target_dependency.id, btrim(target_reason),
    btrim(target_downstream_effect), target_evidence_fingerprints,
    target_event_fingerprint
  ) returning media_rights_request_event_id into stored_id;
  return stored_id;
end;
$$;

create function public.complete_media_takedown(
  target_media_rights_request_id text,
  target_inventory_fingerprint text,
  target_reason text,
  target_event_fingerprint text
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  target_request record;
  actor_profile_pk bigint;
  next_sequence integer;
  stored_id text;
begin
  select request.id, request.project_pk into target_request
  from public.media_rights_requests request
  where request.media_rights_request_id = target_media_rights_request_id;
  if not found then raise exception 'media rights request does not exist' using errcode = '22023'; end if;
  select membership.reviewer_profile_pk into actor_profile_pk
  from public.project_memberships membership
  where membership.project_pk = target_request.project_pk
    and membership.auth_user_id = caller_auth_user_id
    and membership.status = 'active'
    and membership.role in ('curator', 'administrator');
  if not found then raise exception 'media takedown completion requires curator authority' using errcode = '42501'; end if;
  perform pg_catalog.pg_advisory_xact_lock(target_request.id);
  select coalesce(max(event_sequence), 0) + 1 into next_sequence
  from public.media_rights_request_events where media_rights_request_pk = target_request.id;
  insert into public.media_rights_request_events (
    media_rights_request_event_id, media_rights_request_pk, event_sequence,
    action, actor_kind, actor_reviewer_profile_pk, reason, downstream_effect,
    evidence_fingerprints, event_fingerprint
  ) values (
    'media-rights-event:' || replace(gen_random_uuid()::text, '-', ''),
    target_request.id, next_sequence, 'takedown_completed', 'curator',
    actor_profile_pk, btrim(target_reason),
    'Every sealed dependency has a terminal, fingerprinted action.',
    array[target_inventory_fingerprint], target_event_fingerprint
  ) returning media_rights_request_event_id into stored_id;
  return stored_id;
end;
$$;

create function private.is_media_rights_requester(target_request_pk bigint)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from private.media_rights_requesters requester
    join public.reviewer_profiles profile
      on profile.id = requester.requester_reviewer_profile_pk
    where requester.media_rights_request_pk = target_request_pk
      and profile.auth_user_id = (select auth.uid())
  );
$$;

create function private.has_media_takedown_for_release(target_release_candidate_pk bigint)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  with recursive lineage as (
    select media.id, media.parent_media_pk, media.flickr_photo_pk
    from public.release_candidates candidate
    join public.media_objects media on media.id = candidate.media_object_pk
    where candidate.id = target_release_candidate_pk
    union all
    select parent.id, parent.parent_media_pk, parent.flickr_photo_pk
    from public.media_objects parent
    join lineage child on parent.id = child.parent_media_pk
  )
  select exists (
    select 1 from public.media_rights_requests request
    where (request.target_kind = 'media_object'
      and request.media_object_pk in (select id from lineage))
      or (request.target_kind = 'flickr_photo'
        and request.flickr_photo_pk in (
          select flickr_photo_pk from lineage where flickr_photo_pk is not null
        ))
  );
$$;

create function private.has_media_takedown_for_impact(target_geographic_impact_pk bigint)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.release_candidates candidate
    where candidate.geographic_impact_pk = target_geographic_impact_pk
      and private.has_media_takedown_for_release(candidate.id)
  );
$$;

alter table public.media_rights_requests enable row level security;
alter table public.media_takedown_dependencies enable row level security;
alter table public.media_takedown_inventory_receipts enable row level security;
alter table public.media_rights_request_events enable row level security;

create policy media_rights_requests_self_read
on public.media_rights_requests for select to authenticated
using (private.is_media_rights_requester(id));
create policy media_rights_requests_curator_read
on public.media_rights_requests for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy media_takedown_dependencies_curator_read
on public.media_takedown_dependencies for select to authenticated
using (exists (
  select 1 from public.media_rights_requests request
  where request.id = media_takedown_dependencies.media_rights_request_pk
    and private.has_project_role(request.project_pk, array['curator', 'administrator']::text[])
));
create policy media_takedown_inventory_receipts_curator_read
on public.media_takedown_inventory_receipts for select to authenticated
using (exists (
  select 1 from public.media_rights_requests request
  where request.id = media_takedown_inventory_receipts.media_rights_request_pk
    and private.has_project_role(request.project_pk, array['curator', 'administrator']::text[])
));
create policy media_rights_request_events_party_read
on public.media_rights_request_events for select to authenticated
using (
  private.is_media_rights_requester(media_rights_request_pk)
  or exists (
    select 1 from public.media_rights_requests request
    where request.id = media_rights_request_events.media_rights_request_pk
      and private.has_project_role(request.project_pk, array['curator', 'administrator']::text[])
  )
);

create view public.media_rights_request_status
with (security_invoker = true)
as
select
  request.media_rights_request_id,
  request.target_kind,
  request.request_kind,
  request.public_summary,
  request.received_at,
  request.deadline_at,
  request.request_fingerprint,
  latest.action as current_action,
  latest.recorded_at as status_recorded_at,
  case
    when latest.action = 'takedown_completed' then 'completed'
    when latest.action = 'authority_rejected' then 'authority_rejected'
    when exists (
      select 1 from public.media_rights_request_events event
      where event.media_rights_request_pk = request.id
        and event.action = 'authority_verified'
    ) then 'resolving_dependencies'
    else 'under_review'
  end as request_status
from public.media_rights_requests request
left join lateral (
  select event.action, event.recorded_at
  from public.media_rights_request_events event
  where event.media_rights_request_pk = request.id
  order by event.event_sequence desc
  limit 1
) latest on true;

drop policy geographic_impact_public_read on public.geographic_impact;
create policy geographic_impact_public_read
on public.geographic_impact for select to anon, authenticated
using (
  visibility_state = 'public'
  and private.has_publishable_location_receipt('geographic_impact', id)
  and not private.has_media_takedown_for_impact(id)
);

drop policy release_candidates_public_read on public.release_candidates;
create policy release_candidates_public_read
on public.release_candidates for select to anon, authenticated
using (
  candidate_state in ('approved', 'exported') and all_release_gates_passed
  and private.has_publishable_location_receipt('release_candidate', id)
  and not private.has_media_takedown_for_release(id)
);

revoke all on table public.media_rights_requests,
  public.media_takedown_dependencies, public.media_takedown_inventory_receipts,
  public.media_rights_request_events from public, anon, authenticated;
revoke all on table private.media_rights_requesters
from public, anon, authenticated;
revoke all on sequence public.media_rights_requests_id_seq,
  public.media_takedown_dependencies_id_seq,
  public.media_takedown_inventory_receipts_id_seq,
  public.media_rights_request_events_id_seq from public, anon, authenticated;
grant select on table public.media_rights_requests,
  public.media_takedown_dependencies, public.media_takedown_inventory_receipts,
  public.media_rights_request_events to authenticated;
revoke all on table public.media_rights_request_status
from public, anon, authenticated;
grant select on table public.media_rights_request_status to authenticated;
grant select, insert on table public.media_rights_requests,
  public.media_takedown_dependencies, public.media_takedown_inventory_receipts,
  public.media_rights_request_events to service_role;
grant select, insert on table private.media_rights_requesters to service_role;
grant usage, select on sequence public.media_rights_requests_id_seq,
  public.media_takedown_dependencies_id_seq,
  public.media_takedown_inventory_receipts_id_seq,
  public.media_rights_request_events_id_seq to service_role;

revoke all on function public.request_media_takedown(
  text, text, text, text, text, text, text, text, text, text
) from public, anon, authenticated;
grant execute on function public.request_media_takedown(
  text, text, text, text, text, text, text, text, text, text
) to authenticated;
revoke all on function public.decide_media_rights_authority(
  text, boolean, text, text[], text
) from public, anon, authenticated;
grant execute on function public.decide_media_rights_authority(
  text, boolean, text, text[], text
) to authenticated;
revoke all on function public.complete_media_takedown(text, text, text, text)
from public, anon, authenticated;
grant execute on function public.complete_media_takedown(text, text, text, text)
to authenticated;

revoke all on function public.intake_external_media_takedown(
  text, text, text, text, text, text, text, text, text, text, text
), public.register_media_takedown_dependency(text, text, text),
  public.seal_media_takedown_inventory(text, text[], text, text),
  public.record_media_takedown_dependency_action(text, text, text, text, text[], text)
from public, anon, authenticated;
grant execute on function public.intake_external_media_takedown(
  text, text, text, text, text, text, text, text, text, text, text
), public.register_media_takedown_dependency(text, text, text),
  public.seal_media_takedown_inventory(text, text[], text, text),
  public.record_media_takedown_dependency_action(text, text, text, text, text[], text)
to service_role;

revoke all on function private.validate_and_quarantine_media_rights_request(),
  private.validate_media_takedown_dependency(),
  private.validate_media_takedown_inventory_receipt(),
  private.validate_media_rights_request_event(),
  private.reject_media_rights_ledger_mutation(),
  private.inventory_media_rights_request(bigint),
  private.open_media_rights_request(
    text, text, text, text, text, bigint, text, text, text, text, text, text
  ), private.is_media_rights_requester(bigint),
  private.has_media_takedown_for_release(bigint),
  private.has_media_takedown_for_impact(bigint)
from public, anon, authenticated;
grant execute on function private.is_media_rights_requester(bigint),
  private.has_media_takedown_for_release(bigint),
  private.has_media_takedown_for_impact(bigint) to authenticated;
grant execute on function private.has_media_takedown_for_release(bigint),
  private.has_media_takedown_for_impact(bigint) to anon;

comment on table private.media_rights_requesters is
  'Private requester linkage and claim detail; never exposed through public tables or status views.';
comment on table public.media_takedown_dependencies is
  'Append-only fingerprinted removal graph; an inventory receipt permanently seals its membership.';
comment on view public.media_rights_request_status is
  'Security-invoker requester-self or curator status with no requester identity or private claim detail.';
comment on function private.has_media_takedown_for_release(bigint) is
  'Fail-closed public-release gate across media ancestors and their Flickr source.';
