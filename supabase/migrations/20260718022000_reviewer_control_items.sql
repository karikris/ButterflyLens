-- ButterflyLens 9.1: private, evidence-bound reviewer control items.
-- Control identity and expected answers never enter reviewer-facing projections.

create table private.reviewer_control_types (
  control_kind text primary key,
  description text not null,
  policy_version text not null default 'reviewer-controls-v1',
  constraint reviewer_control_types_kind_check check (control_kind in (
    'known_butterfly', 'known_non_butterfly', 'ambiguous_image',
    'duplicate', 'media_failure', 'life_stage'
  )),
  constraint reviewer_control_types_description_check
    check (length(description) between 1 and 500),
  constraint reviewer_control_types_policy_check
    check (policy_version = 'reviewer-controls-v1')
);

insert into private.reviewer_control_types (control_kind, description) values
  ('known_butterfly', 'Evidence-backed butterfly-positive control.'),
  ('known_non_butterfly', 'Evidence-backed butterfly-negative control.'),
  ('ambiguous_image', 'Image whose governed expected response is cannot tell.'),
  ('duplicate', 'Known duplicate-media relationship control.'),
  ('media_failure', 'Deliberate client media-failure handling control.'),
  ('life_stage', 'Evidence-backed butterfly life-stage control.');

create table private.reviewer_control_sets (
  id bigint generated always as identity primary key,
  reviewer_control_set_id text not null,
  project_pk bigint not null references public.projects (id) on delete restrict,
  status text not null default 'draft',
  policy_version text not null default 'reviewer-controls-v1',
  ground_truth_fingerprint text not null,
  created_at timestamptz not null default now(),
  constraint reviewer_control_sets_id_check
    check (reviewer_control_set_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint reviewer_control_sets_status_check
    check (status in ('draft', 'active', 'retired')),
  constraint reviewer_control_sets_policy_check
    check (policy_version = 'reviewer-controls-v1'),
  constraint reviewer_control_sets_fingerprint_check
    check (ground_truth_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint reviewer_control_sets_id_key unique (reviewer_control_set_id),
  constraint reviewer_control_sets_fingerprint_key unique (ground_truth_fingerprint)
);

create index reviewer_control_sets_project_pk_idx
on private.reviewer_control_sets (project_pk, status);

create table private.reviewer_control_items (
  id bigint generated always as identity primary key,
  reviewer_control_item_id text not null,
  reviewer_control_set_pk bigint not null
    references private.reviewer_control_sets (id) on delete restrict,
  verification_campaign_pk bigint not null
    references public.verification_campaigns (id) on delete restrict,
  media_object_pk bigint not null
    references public.media_objects (id) on delete restrict,
  control_kind text not null
    references private.reviewer_control_types (control_kind) on delete restrict,
  expected_decision text not null,
  expected_life_stage text,
  duplicate_of_media_object_pk bigint
    references public.media_objects (id) on delete restrict,
  expected_media_state text not null default 'viewable',
  evidence_kind text not null,
  evidence_fingerprint text not null,
  evidence_citation text not null,
  source_version text not null,
  control_fingerprint text not null,
  scientific_claim_allowed boolean not null default false,
  created_at timestamptz not null default now(),
  constraint reviewer_control_items_id_check
    check (reviewer_control_item_id ~ '^[a-z0-9][a-z0-9._:-]{0,159}$'),
  constraint reviewer_control_items_decision_check
    check (expected_decision in ('yes', 'no', 'cannot_tell', 'cannot_view')),
  constraint reviewer_control_items_life_stage_check
    check (expected_life_stage is null or expected_life_stage in ('adult', 'larva', 'pupa', 'egg', 'unknown')),
  constraint reviewer_control_items_media_state_check
    check (expected_media_state in ('viewable', 'client_media_failure')),
  constraint reviewer_control_items_evidence_kind_check
    check (evidence_kind in (
      'independent_adjudication', 'curated_reference',
      'duplicate_integrity_record', 'synthetic_media_fixture'
    )),
  constraint reviewer_control_items_shape_check check (
    (control_kind = 'known_butterfly' and expected_decision = 'yes'
      and expected_life_stage is null and duplicate_of_media_object_pk is null
      and expected_media_state = 'viewable')
    or (control_kind = 'known_non_butterfly' and expected_decision = 'no'
      and expected_life_stage is null and duplicate_of_media_object_pk is null
      and expected_media_state = 'viewable')
    or (control_kind = 'ambiguous_image' and expected_decision = 'cannot_tell'
      and expected_life_stage is null and duplicate_of_media_object_pk is null
      and expected_media_state = 'viewable')
    or (control_kind = 'duplicate' and expected_decision = 'yes'
      and expected_life_stage is null and duplicate_of_media_object_pk is not null
      and duplicate_of_media_object_pk <> media_object_pk
      and expected_media_state = 'viewable')
    or (control_kind = 'media_failure' and expected_decision = 'cannot_view'
      and expected_life_stage is null and duplicate_of_media_object_pk is null
      and expected_media_state = 'client_media_failure')
    or (control_kind = 'life_stage' and expected_decision = 'yes'
      and expected_life_stage is not null and duplicate_of_media_object_pk is null
      and expected_media_state = 'viewable')
  ),
  constraint reviewer_control_items_evidence_fingerprint_check
    check (evidence_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint reviewer_control_items_evidence_citation_check
    check (length(evidence_citation) between 1 and 1000),
  constraint reviewer_control_items_source_version_check
    check (length(source_version) between 1 and 240),
  constraint reviewer_control_items_fingerprint_check
    check (control_fingerprint ~ '^[0-9a-f]{64}$'),
  constraint reviewer_control_items_no_scientific_claim_check
    check (not scientific_claim_allowed),
  constraint reviewer_control_items_id_key unique (reviewer_control_item_id),
  constraint reviewer_control_items_set_media_key
    unique (reviewer_control_set_pk, media_object_pk, control_kind),
  constraint reviewer_control_items_fingerprint_key unique (control_fingerprint)
);

create index reviewer_control_items_set_pk_idx
on private.reviewer_control_items (reviewer_control_set_pk);
create index reviewer_control_items_campaign_pk_idx
on private.reviewer_control_items (verification_campaign_pk);
create index reviewer_control_items_media_pk_idx
on private.reviewer_control_items (media_object_pk);
create index reviewer_control_items_duplicate_media_pk_idx
on private.reviewer_control_items (duplicate_of_media_object_pk)
where duplicate_of_media_object_pk is not null;

create table private.reviewer_control_assignments (
  reviewer_control_item_pk bigint not null
    references private.reviewer_control_items (id) on delete restrict,
  assignment_pk bigint not null
    references public.assignments (id) on delete restrict,
  linked_at timestamptz not null default now(),
  primary key (reviewer_control_item_pk, assignment_pk),
  constraint reviewer_control_assignments_assignment_key unique (assignment_pk)
);

create index reviewer_control_assignments_assignment_pk_idx
on private.reviewer_control_assignments (assignment_pk);

create function private.enforce_reviewer_control_item()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  control_set record;
  campaign record;
  media record;
  duplicate_project_pk bigint;
begin
  select candidate.project_pk, candidate.status into control_set
  from private.reviewer_control_sets candidate
  where candidate.id = new.reviewer_control_set_pk;
  select candidate.project_pk, candidate.campaign_kind,
    candidate.blind_model_label, candidate.blind_model_score,
    candidate.blind_query_term, candidate.blind_source_comment,
    candidate.blind_peer_decisions
  into campaign
  from public.verification_campaigns candidate
  where candidate.id = new.verification_campaign_pk;
  select candidate.project_pk, candidate.media_state, candidate.decode_status,
    candidate.rights_status
  into media
  from public.media_objects candidate where candidate.id = new.media_object_pk;

  if control_set.project_pk is distinct from campaign.project_pk
     or control_set.project_pk is distinct from media.project_pk
     or campaign.campaign_kind <> 'reviewer_control' then
    raise exception 'control set, campaign, and media must share a reviewer-control project'
      using errcode = '23514';
  end if;
  if not (campaign.blind_model_label and campaign.blind_model_score
    and campaign.blind_query_term and campaign.blind_source_comment
    and campaign.blind_peer_decisions) then
    raise exception 'reviewer controls must remain fully blind'
      using errcode = '23514';
  end if;
  if media.media_state <> 'committed' or media.decode_status <> 'valid'
     or media.rights_status <> 'allowed' then
    raise exception 'reviewer control media must pass integrity and rights gates'
      using errcode = '23514';
  end if;
  if new.duplicate_of_media_object_pk is not null then
    select candidate.project_pk into duplicate_project_pk
    from public.media_objects candidate
    where candidate.id = new.duplicate_of_media_object_pk;
    if duplicate_project_pk is distinct from control_set.project_pk then
      raise exception 'duplicate control target must belong to the same project'
        using errcode = '23514';
    end if;
  end if;
  return new;
end;
$$;

create trigger reviewer_control_items_enforce_governance
before insert on private.reviewer_control_items
for each row execute function private.enforce_reviewer_control_item();

create function private.enforce_reviewer_control_assignment()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not exists (
    select 1
    from private.reviewer_control_items control
    join private.reviewer_control_sets control_set
      on control_set.id = control.reviewer_control_set_pk
    join public.assignments assignment on assignment.id = new.assignment_pk
    where control.id = new.reviewer_control_item_pk
      and control_set.status = 'active'
      and assignment.verification_campaign_pk = control.verification_campaign_pk
      and assignment.media_object_pk = control.media_object_pk
  ) then
    raise exception 'control assignment must bind an active exact campaign item'
      using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger reviewer_control_assignments_enforce_binding
before insert on private.reviewer_control_assignments
for each row execute function private.enforce_reviewer_control_assignment();

create function private.reject_reviewer_control_mutation()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  raise exception 'reviewer control evidence is immutable' using errcode = '55000';
end;
$$;

create trigger reviewer_control_items_reject_mutation
before update or delete on private.reviewer_control_items
for each row execute function private.reject_reviewer_control_mutation();
create trigger reviewer_control_assignments_reject_mutation
before update or delete on private.reviewer_control_assignments
for each row execute function private.reject_reviewer_control_mutation();

revoke all on table private.reviewer_control_types,
  private.reviewer_control_sets, private.reviewer_control_items,
  private.reviewer_control_assignments from public, anon, authenticated;
revoke all on sequence private.reviewer_control_sets_id_seq,
  private.reviewer_control_items_id_seq from public, anon, authenticated;
grant select on table private.reviewer_control_types to service_role;
grant select, insert, update on table private.reviewer_control_sets to service_role;
grant select, insert on table private.reviewer_control_items,
  private.reviewer_control_assignments to service_role;
grant usage, select on sequence private.reviewer_control_sets_id_seq,
  private.reviewer_control_items_id_seq to service_role;
revoke all on function private.enforce_reviewer_control_item(),
  private.enforce_reviewer_control_assignment(),
  private.reject_reviewer_control_mutation()
from public, anon, authenticated;

comment on table private.reviewer_control_items is
  'Private immutable ground-truth controls; expected answers and control identity are never reviewer-visible.';
