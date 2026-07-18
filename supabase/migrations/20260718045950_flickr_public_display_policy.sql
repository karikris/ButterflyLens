-- ButterflyLens 10.5: service-only Flickr display, cache, and removal gates.
-- This migration performs no Flickr API call and publishes no Flickr photo.

create table public.flickr_application_approvals (
  id bigint generated always as identity primary key,
  application_approval_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  approval_kind text not null,
  application_key_fingerprint text not null,
  terms_url text not null,
  privacy_disclosure_url text not null,
  approved_at timestamptz not null,
  terms_revalidated_at timestamptz not null,
  active boolean not null default true,
  revoked_at timestamptz,
  approval_evidence_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint flickr_application_approvals_id_check
    check (application_approval_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint flickr_application_approvals_kind_check
    check (approval_kind in ('noncommercial_approved', 'commercial_approved')),
  constraint flickr_application_approvals_key_fingerprint_check
    check (application_key_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_application_approvals_terms_url_check
    check (terms_url = 'https://www.flickr.com/help/terms/api'),
  constraint flickr_application_approvals_privacy_url_check
    check (privacy_disclosure_url ~ '^https://'),
  constraint flickr_application_approvals_evidence_check
    check (approval_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_application_approvals_timeline_check
    check (
      approved_at <= terms_revalidated_at
      and terms_revalidated_at <= created_at + interval '5 minutes'
      and ((active and revoked_at is null) or (not active and revoked_at is not null))
      and (revoked_at is null or revoked_at >= approved_at)
    ),
  constraint flickr_application_approvals_id_key unique (application_approval_id),
  constraint flickr_application_approvals_fingerprint_key
    unique (approval_evidence_fingerprint)
);

create table public.flickr_removal_cases (
  id bigint generated always as identity primary key,
  removal_case_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  flickr_photo_pk bigint not null references public.flickr_photos (id) on delete restrict,
  requester_basis text not null,
  received_at timestamptz not null,
  deadline_at timestamptz not null,
  quarantine_started_at timestamptz not null,
  authority_evidence_fingerprint text not null,
  case_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint flickr_removal_cases_id_check
    check (removal_case_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint flickr_removal_cases_requester_basis_check
    check (requester_basis in ('owner', 'rights_holder', 'authorized_agent', 'provider', 'legal', 'privacy')),
  constraint flickr_removal_cases_deadline_check
    check (deadline_at = received_at + interval '24 hours'),
  constraint flickr_removal_cases_quarantine_check
    check (quarantine_started_at >= received_at and quarantine_started_at <= created_at + interval '5 minutes'),
  constraint flickr_removal_cases_authority_fingerprint_check
    check (authority_evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_removal_cases_fingerprint_check
    check (case_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_removal_cases_id_key unique (removal_case_id),
  constraint flickr_removal_cases_fingerprint_key unique (case_fingerprint)
);

create table public.flickr_display_assets (
  id bigint generated always as identity primary key,
  display_asset_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  flickr_photo_pk bigint not null references public.flickr_photos (id) on delete restrict,
  media_object_pk bigint not null references public.media_objects (id) on delete restrict,
  application_approval_pk bigint not null references public.flickr_application_approvals (id) on delete restrict,
  removal_case_pk bigint references public.flickr_removal_cases (id) on delete restrict,
  photographer text not null,
  attribution text not null,
  source_url text not null,
  licence_id text not null,
  licence_url text not null,
  source_record_fingerprint text not null,
  rights_fingerprint text not null,
  display_fingerprint text not null,
  display_state text not null default 'eligible',
  cached_at timestamptz not null,
  revalidated_at timestamptz not null,
  cache_expires_at timestamptz not null,
  quarantined_at timestamptz,
  removed_at timestamptz,
  flickr_notice text not null default 'This product uses the Flickr API but is not endorsed or certified by SmugMug, Inc.',
  created_at timestamptz not null default now(),
  constraint flickr_display_assets_id_check
    check (display_asset_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint flickr_display_assets_text_check
    check (length(photographer) between 1 and 500 and length(attribution) between 1 and 2000),
  constraint flickr_display_assets_source_url_check
    check (source_url ~ '^https://www\.flickr\.com/photos/'),
  constraint flickr_display_assets_licence_check
    check (length(licence_id) between 1 and 120 and licence_url ~ '^https://'),
  constraint flickr_display_assets_source_fingerprint_check
    check (source_record_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_display_assets_rights_fingerprint_check
    check (rights_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_display_assets_fingerprint_check
    check (display_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_display_assets_state_check
    check (display_state in ('eligible', 'expired', 'quarantined', 'removed')),
  constraint flickr_display_assets_cache_check
    check (
      cached_at <= revalidated_at
      and revalidated_at < cache_expires_at
      and cache_expires_at <= cached_at + interval '24 hours'
    ),
  constraint flickr_display_assets_removal_shape_check
    check (
      (display_state = 'eligible' and removal_case_pk is null and quarantined_at is null and removed_at is null)
      or (display_state = 'expired' and removal_case_pk is null and quarantined_at is null and removed_at is null)
      or (display_state = 'quarantined' and removal_case_pk is not null and quarantined_at is not null and removed_at is null)
      or (display_state = 'removed' and removal_case_pk is not null and quarantined_at is not null and removed_at is not null)
    ),
  constraint flickr_display_assets_notice_check
    check (flickr_notice = 'This product uses the Flickr API but is not endorsed or certified by SmugMug, Inc.'),
  constraint flickr_display_assets_id_key unique (display_asset_id),
  constraint flickr_display_assets_fingerprint_key unique (display_fingerprint),
  constraint flickr_display_assets_photo_media_key unique (flickr_photo_pk, media_object_pk)
);

create table public.flickr_removal_events (
  id bigint generated always as identity primary key,
  removal_event_id text not null,
  removal_case_pk bigint not null references public.flickr_removal_cases (id) on delete restrict,
  dependency_kind text not null,
  action text not null,
  dependency_fingerprint text not null,
  occurred_at timestamptz not null,
  event_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint flickr_removal_events_id_check
    check (removal_event_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint flickr_removal_events_dependency_check
    check (dependency_kind in ('source_cache', 'public_display', 'thumbnail', 'model_input', 'embedding', 'review', 'public_cell', 'packet', 'export', 'mirror', 'signed_url')),
  constraint flickr_removal_events_action_check
    check (action in ('quarantined', 'purged', 'removed', 'invalidated', 'retained_independent_rights', 'completion_attested', 'appeal_received', 'appeal_resolved')),
  constraint flickr_removal_events_dependency_fingerprint_check
    check (dependency_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_removal_events_event_fingerprint_check
    check (event_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint flickr_removal_events_timeline_check
    check (occurred_at <= created_at + interval '5 minutes'),
  constraint flickr_removal_events_id_key unique (removal_event_id),
  constraint flickr_removal_events_fingerprint_key unique (event_fingerprint),
  constraint flickr_removal_events_action_key
    unique (removal_case_pk, dependency_kind, dependency_fingerprint, action)
);

create index flickr_application_approvals_project_active_idx
on public.flickr_application_approvals (project_pk, terms_revalidated_at desc)
where active;
create index flickr_removal_cases_project_pk_idx on public.flickr_removal_cases (project_pk);
create index flickr_removal_cases_flickr_photo_pk_idx on public.flickr_removal_cases (flickr_photo_pk);
create index flickr_removal_cases_deadline_idx on public.flickr_removal_cases (deadline_at);
create index flickr_display_assets_project_pk_idx on public.flickr_display_assets (project_pk);
create index flickr_display_assets_flickr_photo_pk_idx on public.flickr_display_assets (flickr_photo_pk);
create index flickr_display_assets_media_object_pk_idx on public.flickr_display_assets (media_object_pk);
create index flickr_display_assets_application_approval_pk_idx on public.flickr_display_assets (application_approval_pk);
create index flickr_display_assets_removal_case_pk_idx on public.flickr_display_assets (removal_case_pk)
where removal_case_pk is not null;
create index flickr_display_assets_eligible_expiry_idx on public.flickr_display_assets (cache_expires_at, project_pk)
where display_state = 'eligible';
create index flickr_removal_events_case_pk_idx on public.flickr_removal_events (removal_case_pk);

alter table public.flickr_application_approvals enable row level security;
alter table public.flickr_removal_cases enable row level security;
alter table public.flickr_display_assets enable row level security;
alter table public.flickr_removal_events enable row level security;

create function private.validate_flickr_display_asset()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
  expected_photographer text;
begin
  if new.display_state in ('eligible', 'expired') then
    select coalesce(nullif(btrim(photo.owner_display_name), ''), photo.owner_nsid)
    into expected_photographer
    from public.flickr_photos photo
    join public.media_objects media on media.id = new.media_object_pk
    join public.flickr_application_approvals approval on approval.id = new.application_approval_pk
    where photo.id = new.flickr_photo_pk
      and media.flickr_photo_pk = photo.id
      and media.project_pk = new.project_pk
      and approval.project_pk = new.project_pk
      and approval.active
      and approval.revoked_at is null
      and photo.is_current
      and photo.visibility_state = 'public'
      and photo.rights_status = 'allowed'
      and photo.display_allowed
      and photo.redistribution_allowed
      and photo.removed_at is null
      and photo.source_url = new.source_url
      and photo.licence_id = new.licence_id
      and photo.licence_url = new.licence_url
      and photo.source_record_fingerprint = new.source_record_fingerprint
      and media.source_kind = 'flickr'
      and media.object_kind = 'public_thumbnail'
      and media.media_state = 'committed'
      and media.rights_status = 'allowed'
      and media.display_allowed
      and media.redistribution_allowed
      and media.removed_at is null
      and media.rights_fingerprint = new.rights_fingerprint;
  else
    select coalesce(nullif(btrim(photo.owner_display_name), ''), photo.owner_nsid)
    into expected_photographer
    from public.flickr_photos photo
    join public.media_objects media on media.id = new.media_object_pk
    where photo.id = new.flickr_photo_pk
      and media.flickr_photo_pk = photo.id
      and media.project_pk = new.project_pk
      and photo.source_url = new.source_url
      and photo.licence_id = new.licence_id
      and photo.licence_url = new.licence_url
      and photo.source_record_fingerprint = new.source_record_fingerprint
      and media.rights_fingerprint = new.rights_fingerprint;
  end if;

  if not found then
    raise exception 'Flickr display asset lacks a current public rights-approved source, thumbnail, or application approval' using errcode = '23514';
  end if;
  if new.photographer <> expected_photographer then
    raise exception 'Flickr photographer attribution does not match the source record' using errcode = '23514';
  end if;
  if new.display_state = 'eligible' and (
    new.cache_expires_at <= now()
    or new.revalidated_at < now() - interval '24 hours'
    or exists (
      select 1 from public.flickr_removal_cases removal
      where removal.flickr_photo_pk = new.flickr_photo_pk
    )
  ) then
    raise exception 'Flickr display asset cache is stale or removal-blocked' using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.validate_flickr_display_asset() from public, anon, authenticated;
grant execute on function private.validate_flickr_display_asset() to service_role;

create trigger flickr_display_assets_validate
before insert or update on public.flickr_display_assets
for each row execute function private.validate_flickr_display_asset();

create function private.quarantine_flickr_removal_case()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  update public.flickr_display_assets
  set display_state = 'quarantined', removal_case_pk = new.id,
      quarantined_at = new.quarantine_started_at
  where flickr_photo_pk = new.flickr_photo_pk and display_state in ('eligible', 'expired');

  update public.media_objects
  set media_state = 'quarantined', rights_status = 'quarantined',
      download_allowed = false, model_inference_allowed = false,
      display_allowed = false, redistribution_allowed = false
  where flickr_photo_pk = new.flickr_photo_pk and media_state <> 'removed';

  update public.flickr_photos
  set rights_status = 'quarantined', download_allowed = false,
      model_inference_allowed = false, display_allowed = false,
      redistribution_allowed = false
  where id = new.flickr_photo_pk and rights_status <> 'removed';
  return new;
end;
$$;

revoke all on function private.quarantine_flickr_removal_case() from public, anon, authenticated;
grant execute on function private.quarantine_flickr_removal_case() to service_role;

create trigger flickr_removal_cases_quarantine
after insert on public.flickr_removal_cases
for each row execute function private.quarantine_flickr_removal_case();

create policy flickr_application_approvals_curator_read
on public.flickr_application_approvals for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy flickr_removal_cases_curator_read
on public.flickr_removal_cases for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy flickr_display_assets_curator_read
on public.flickr_display_assets for select to authenticated
using (private.has_project_role(project_pk, array['curator', 'administrator']::text[]));
create policy flickr_removal_events_curator_read
on public.flickr_removal_events for select to authenticated
using (
  exists (
    select 1 from public.flickr_removal_cases removal
    where removal.id = flickr_removal_events.removal_case_pk
      and private.has_project_role(removal.project_pk, array['curator', 'administrator']::text[])
  )
);

grant select on table public.flickr_application_approvals, public.flickr_removal_cases,
  public.flickr_display_assets, public.flickr_removal_events to authenticated;
grant select, insert, update on table public.flickr_application_approvals,
  public.flickr_display_assets to service_role;
grant select, insert on table public.flickr_removal_cases,
  public.flickr_removal_events to service_role;
grant usage on sequence public.flickr_application_approvals_id_seq,
  public.flickr_removal_cases_id_seq, public.flickr_display_assets_id_seq,
  public.flickr_removal_events_id_seq to service_role;
revoke all on table public.flickr_application_approvals, public.flickr_removal_cases,
  public.flickr_display_assets, public.flickr_removal_events from anon;

create view public.flickr_public_display_projection
with (security_invoker = true)
as
select
  asset.display_asset_id,
  photo.flickr_photo_id,
  photo.title,
  asset.photographer,
  photo.owner_nsid,
  asset.source_url,
  media.storage_key as public_thumbnail_storage_key,
  asset.licence_id,
  asset.licence_url,
  asset.attribution,
  asset.cached_at,
  asset.revalidated_at,
  asset.cache_expires_at,
  asset.source_record_fingerprint,
  asset.rights_fingerprint,
  asset.display_fingerprint,
  asset.flickr_notice
from public.flickr_display_assets asset
join public.flickr_photos photo on photo.id = asset.flickr_photo_pk
join public.media_objects media on media.id = asset.media_object_pk
join public.flickr_application_approvals approval on approval.id = asset.application_approval_pk
where asset.display_state = 'eligible'
  and asset.removal_case_pk is null
  and asset.cache_expires_at > now()
  and asset.revalidated_at >= now() - interval '24 hours'
  and approval.active and approval.revoked_at is null
  and photo.is_current and photo.visibility_state = 'public'
  and photo.rights_status = 'allowed' and photo.display_allowed and photo.redistribution_allowed
  and photo.removed_at is null
  and media.media_state = 'committed' and media.object_kind = 'public_thumbnail'
  and media.rights_status = 'allowed' and media.display_allowed and media.redistribution_allowed
  and media.removed_at is null
  and not exists (
    select 1 from public.flickr_removal_cases removal
    where removal.flickr_photo_pk = asset.flickr_photo_pk
  );

revoke all on table public.flickr_public_display_projection from public, anon, authenticated;
grant select on table public.flickr_public_display_projection to service_role;

comment on view public.flickr_public_display_projection is
  'Service-only, security-invoker Flickr display projection. The application must still enforce the 30-photo page cap and exact attribution/notice contract.';
