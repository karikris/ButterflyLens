-- ButterflyLens 8.1: low-friction permanent reviewer registration.
-- Guest browsing continues through existing anon projections. Only trusted
-- server paths may assign expert, curator, or administrator authority.

alter table public.reviewer_profiles
add constraint reviewer_profiles_public_name_pseudonym_check
check (
  public_name = btrim(public_name)
  and public_name !~ E'[\\r\\n\\t]'
  and position('@' in public_name) = 0
  and public_name !~* '(^|[[:space:]])https?://'
);

create unique index reviewer_profiles_public_name_ci_key
on public.reviewer_profiles (lower(public_name));

alter table public.project_memberships
add column enrollment_kind text not null default 'approved',
add constraint project_memberships_enrollment_kind_check
  check (enrollment_kind in ('self_service', 'invitation', 'approved'));

alter table public.project_memberships
drop constraint project_memberships_approval_check,
add constraint project_memberships_approval_check
check (
  (
    enrollment_kind = 'self_service'
    and role = 'reviewer'
    and status = 'active'
    and approved_by_reviewer_pk is null
  )
  or (
    enrollment_kind = 'invitation'
    and status = 'invited'
    and approved_by_reviewer_pk is null
  )
  or (
    enrollment_kind = 'approved'
    and approved_by_reviewer_pk is not null
  )
);

create function public.register_reviewer(
  target_project_id text,
  requested_public_name text
)
returns table (
  reviewer_profile_id text,
  public_name text,
  project_membership_id text,
  membership_role text
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller_auth_user_id uuid := (select auth.uid());
  normalized_public_name text := btrim(requested_public_name);
  target_project_pk bigint;
  profile_pk bigint;
  profile_external_id text;
  profile_public_name text;
  profile_status text;
  membership_external_id text;
  membership_status text;
begin
  if caller_auth_user_id is null then
    raise exception 'reviewer registration requires authentication'
      using errcode = '42501';
  end if;

  if not exists (
    select 1
    from auth.users auth_user
    where auth_user.id = caller_auth_user_id
      and not coalesce(auth_user.is_anonymous, false)
  ) then
    raise exception 'reviewer registration requires a permanent account'
      using errcode = '42501';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(caller_auth_user_id::text, 0));

  if normalized_public_name is null
     or length(normalized_public_name) not between 2 and 80
     or normalized_public_name ~ E'[\\r\\n\\t]'
     or position('@' in normalized_public_name) > 0
     or normalized_public_name ~* '(^|[[:space:]])https?://' then
    raise exception 'public name must be a 2-80 character pseudonym without contact details'
      using errcode = '22023';
  end if;

  select project.id
  into target_project_pk
  from public.projects project
  where project.project_id = target_project_id
    and project.status = 'active';

  if not found then
    raise exception 'active review project does not exist'
      using errcode = '22023';
  end if;

  select profile.id, profile.reviewer_profile_id, profile.public_name, profile.status
  into profile_pk, profile_external_id, profile_public_name, profile_status
  from public.reviewer_profiles profile
  where profile.auth_user_id = caller_auth_user_id;

  if found and profile_status <> 'active' then
    raise exception 'reviewer profile requires curator action'
      using errcode = '42501';
  end if;

  if profile_pk is null then
    insert into public.reviewer_profiles (
      reviewer_profile_id,
      auth_user_id,
      public_name,
      role,
      status,
      qualification_state
    ) values (
      'reviewer:' || replace(gen_random_uuid()::text, '-', ''),
      caller_auth_user_id,
      normalized_public_name,
      'reviewer',
      'active',
      'unverified'
    )
    returning id, reviewer_profiles.reviewer_profile_id,
      reviewer_profiles.public_name, reviewer_profiles.status
    into profile_pk, profile_external_id, profile_public_name, profile_status;
  end if;

  select membership.project_membership_id, membership.status
  into membership_external_id, membership_status
  from public.project_memberships membership
  where membership.project_pk = target_project_pk
    and membership.auth_user_id = caller_auth_user_id;

  if found and membership_status <> 'active' then
    raise exception 'project membership requires curator action'
      using errcode = '42501';
  end if;

  if membership_external_id is null then
    insert into public.project_memberships (
      project_membership_id,
      project_pk,
      reviewer_profile_pk,
      auth_user_id,
      role,
      status,
      enrollment_kind,
      approved_by_reviewer_pk
    ) values (
      'membership:' || replace(gen_random_uuid()::text, '-', ''),
      target_project_pk,
      profile_pk,
      caller_auth_user_id,
      'reviewer',
      'active',
      'self_service',
      null
    )
    returning project_memberships.project_membership_id
    into membership_external_id;
  end if;

  return query
  select profile_external_id, profile_public_name, membership_external_id, 'reviewer'::text;
end;
$$;

revoke all on function public.register_reviewer(text, text)
from public, anon, authenticated;
grant execute on function public.register_reviewer(text, text)
to authenticated;

comment on function public.register_reviewer(text, text) is
  'Idempotently creates a pseudonymous base reviewer membership for a permanent Auth user; privileged roles remain server-controlled.';
