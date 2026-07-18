-- ButterflyLens 8.3: repeated, independent, policy-bound review assignment.
-- Assignment creation remains curator/service controlled; reviewers can read
-- only their own rows under the existing RLS policies.

create table private.review_assignment_policies (
  campaign_kind text primary key,
  default_review_count smallint not null,
  minimum_review_count smallint not null,
  maximum_review_count smallint not null,
  disagreement_review_count smallint not null,
  minimum_qualified_review_count smallint not null default 0,
  expert_gate_required boolean not null default false,
  policy_version text not null default 'repeated-independent-v1',
  constraint review_assignment_policies_kind_check
    check (campaign_kind in (
      'ordinary_image', 'disagreement', 'potential_gap', 'reference_image',
      'high_impact_release'
    )),
  constraint review_assignment_policies_counts_check
    check (
      minimum_review_count >= 2
      and default_review_count between minimum_review_count and maximum_review_count
      and disagreement_review_count between minimum_review_count and maximum_review_count
      and minimum_qualified_review_count between 0 and minimum_review_count
    ),
  constraint review_assignment_policies_expert_check
    check (not expert_gate_required or minimum_qualified_review_count >= 2),
  constraint review_assignment_policies_version_check
    check (policy_version = 'repeated-independent-v1')
);

insert into private.review_assignment_policies (
  campaign_kind, default_review_count, minimum_review_count,
  maximum_review_count, disagreement_review_count,
  minimum_qualified_review_count, expert_gate_required
) values
  ('ordinary_image', 2, 2, 2, 2, 0, false),
  ('disagreement', 3, 3, 3, 3, 0, false),
  ('potential_gap', 3, 3, 5, 4, 0, false),
  ('reference_image', 2, 2, 2, 2, 0, false),
  ('high_impact_release', 3, 3, 5, 4, 2, true);

revoke all on table private.review_assignment_policies
from public, anon, authenticated;
grant usage on schema private to service_role;
grant select on table private.review_assignment_policies to service_role;

alter table public.assignments
add column assignment_reason text not null default 'ordinary',
add column required_reviewer_role text not null default 'reviewer',
add column assignment_policy_version text not null default 'repeated-independent-v1',
add constraint assignments_reason_check
  check (assignment_reason in ('ordinary', 'conflict', 'potential_gap', 'reference')),
add constraint assignments_required_role_check
  check (required_reviewer_role in ('reviewer', 'qualified', 'expert')),
add constraint assignments_policy_version_check
  check (assignment_policy_version = 'repeated-independent-v1');

create function private.enforce_campaign_assignment_policy()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  policy private.review_assignment_policies%rowtype;
begin
  select candidate.* into policy
  from private.review_assignment_policies candidate
  where candidate.campaign_kind = new.campaign_kind;

  if not found then
    return new;
  end if;

  if new.target_review_count not between policy.minimum_review_count
      and policy.maximum_review_count then
    raise exception 'campaign review count violates repeated assignment policy'
      using errcode = '23514';
  end if;
  if new.minimum_qualified_review_count < policy.minimum_qualified_review_count then
    raise exception 'campaign requires more qualified independent reviews'
      using errcode = '23514';
  end if;
  if new.expert_gate_required <> policy.expert_gate_required then
    raise exception 'campaign expert gate violates repeated assignment policy'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_campaign_assignment_policy()
from public, anon, authenticated;
grant execute on function private.enforce_campaign_assignment_policy()
to service_role;

create trigger verification_campaigns_enforce_assignment_policy
before insert or update of campaign_kind, target_review_count,
  minimum_qualified_review_count, expert_gate_required
on public.verification_campaigns
for each row execute function private.enforce_campaign_assignment_policy();

create function private.enforce_repeated_independent_assignment()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  campaign record;
  expected_reason text;
  expected_role text := 'reviewer';
  member_role text;
  member_status text;
  profile_status text;
  profile_qualification text;
  active_assignment_count bigint;
  maximum_assignment_sequence integer;
  active_qualified_count bigint;
  active_expert_count bigint;
begin
  if tg_op = 'UPDATE' and row(
    old.verification_campaign_pk, old.media_object_pk,
    old.reviewer_profile_pk, old.assignment_sequence,
    old.assignment_reason, old.required_reviewer_role,
    old.assignment_policy_version
  ) is distinct from row(
    new.verification_campaign_pk, new.media_object_pk,
    new.reviewer_profile_pk, new.assignment_sequence,
    new.assignment_reason, new.required_reviewer_role,
    new.assignment_policy_version
  ) then
    raise exception 'assignment identity and policy fields are immutable'
      using errcode = '23514';
  end if;

  select candidate.id, candidate.project_pk, candidate.campaign_kind,
    candidate.target_review_count, candidate.minimum_qualified_review_count,
    candidate.expert_gate_required
  into campaign
  from public.verification_campaigns candidate
  where candidate.id = new.verification_campaign_pk
  for key share;

  if not found then
    raise exception 'assignment campaign does not exist' using errcode = '23503';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(
      new.verification_campaign_pk::text || ':' || new.media_object_pk::text,
      0
    )
  );

  select
    count(existing.id) filter (
      where existing.status not in ('expired', 'withdrawn')
    ),
    coalesce(max(existing.assignment_sequence), 0),
    count(existing.id) filter (
      where existing.status not in ('expired', 'withdrawn')
        and existing_profile.qualification_state = 'verified'
    ),
    count(existing.id) filter (
      where existing.status not in ('expired', 'withdrawn')
        and existing_profile.qualification_state = 'verified'
        and existing_membership.role in ('expert', 'curator', 'administrator')
    )
  into active_assignment_count, maximum_assignment_sequence,
    active_qualified_count, active_expert_count
  from public.assignments existing
  left join public.reviewer_profiles existing_profile
    on existing_profile.id = existing.reviewer_profile_pk
  left join public.project_memberships existing_membership
    on existing_membership.project_pk = campaign.project_pk
    and existing_membership.reviewer_profile_pk = existing.reviewer_profile_pk
    and existing_membership.status = 'active'
  where existing.verification_campaign_pk = new.verification_campaign_pk
    and existing.media_object_pk = new.media_object_pk
    and (tg_op = 'INSERT' or existing.id <> new.id);

  if active_assignment_count >= campaign.target_review_count then
    raise exception 'assignment exceeds campaign independent review count'
      using errcode = '23514';
  end if;
  if new.assignment_sequence <> maximum_assignment_sequence + 1 then
    raise exception 'assignment sequence must be the next independent round'
      using errcode = '23514';
  end if;

  expected_reason := case campaign.campaign_kind
    when 'disagreement' then
      case when active_assignment_count >= 2 then 'conflict' else 'ordinary' end
    when 'potential_gap' then 'potential_gap'
    when 'reference_image' then 'reference'
    else 'ordinary'
  end;

  if campaign.campaign_kind = 'high_impact_release' then
    if campaign.expert_gate_required
       and active_expert_count = 0
       and active_assignment_count = campaign.target_review_count - 1 then
      expected_role := 'expert';
    elsif active_qualified_count < campaign.minimum_qualified_review_count then
      expected_role := 'qualified';
    end if;
  end if;

  new.assignment_reason := expected_reason;
  new.required_reviewer_role := expected_role;
  if new.assignment_policy_version <> 'repeated-independent-v1' then
    raise exception 'assignment policy version is unsupported'
      using errcode = '23514';
  end if;

  select membership.role, membership.status, profile.status,
    profile.qualification_state
  into member_role, member_status, profile_status, profile_qualification
  from public.project_memberships membership
  join public.reviewer_profiles profile
    on profile.id = membership.reviewer_profile_pk
  where membership.project_pk = campaign.project_pk
    and membership.reviewer_profile_pk = new.reviewer_profile_pk;

  if not found or member_status <> 'active' or profile_status <> 'active' then
    raise exception 'assignment requires an active project reviewer'
      using errcode = '23514';
  end if;
  if expected_role in ('qualified', 'expert')
     and profile_qualification <> 'verified' then
    raise exception 'assignment requires a verified reviewer qualification'
      using errcode = '23514';
  end if;
  if expected_role = 'expert'
     and member_role not in ('expert', 'curator', 'administrator') then
    raise exception 'assignment requires an expert project role'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

revoke all on function private.enforce_repeated_independent_assignment()
from public, anon, authenticated;
grant execute on function private.enforce_repeated_independent_assignment()
to service_role;

create trigger assignments_enforce_repeated_independence
before insert or update of verification_campaign_pk, media_object_pk,
  reviewer_profile_pk, assignment_sequence, assignment_reason,
  required_reviewer_role, assignment_policy_version
on public.assignments
for each row execute function private.enforce_repeated_independent_assignment();

create function private.review_assignment_progress(
  target_campaign_pk bigint,
  target_media_object_pk bigint
)
returns table (
  required_review_count smallint,
  assigned_review_count bigint,
  responded_review_count bigint,
  remaining_assignment_count bigint,
  minimum_qualified_review_count smallint,
  responded_qualified_review_count bigint,
  expert_gate_required boolean,
  expert_gate_satisfied boolean
)
language sql
stable
security definer
set search_path = ''
as $$
  select campaign.target_review_count,
    count(assignment.id) filter (
      where assignment.status not in ('expired', 'withdrawn')
    ),
    count(assignment.id) filter (where assignment.status = 'responded'),
    greatest(
      campaign.target_review_count - count(assignment.id) filter (
        where assignment.status not in ('expired', 'withdrawn')
      ),
      0
    ),
    campaign.minimum_qualified_review_count,
    count(assignment.id) filter (
      where assignment.status = 'responded'
        and profile.qualification_state = 'verified'
    ),
    campaign.expert_gate_required,
    not campaign.expert_gate_required or coalesce(bool_or(
      assignment.status = 'responded'
      and profile.qualification_state = 'verified'
      and membership.role in ('expert', 'curator', 'administrator')
    ), false)
  from public.verification_campaigns campaign
  left join public.assignments assignment
    on assignment.verification_campaign_pk = campaign.id
    and assignment.media_object_pk = target_media_object_pk
  left join public.reviewer_profiles profile
    on profile.id = assignment.reviewer_profile_pk
  left join public.project_memberships membership
    on membership.project_pk = campaign.project_pk
    and membership.reviewer_profile_pk = assignment.reviewer_profile_pk
    and membership.status = 'active'
  where campaign.id = target_campaign_pk
  group by campaign.id;
$$;

revoke all on function private.review_assignment_progress(bigint, bigint)
from public, anon, authenticated;
grant execute on function private.review_assignment_progress(bigint, bigint)
to service_role;

comment on table private.review_assignment_policies is
  'Versioned server-only defaults for repeated independent review assignment.';
comment on function private.review_assignment_progress(bigint, bigint) is
  'Server-only item progress; does not expose other reviewer identities or decisions.';
