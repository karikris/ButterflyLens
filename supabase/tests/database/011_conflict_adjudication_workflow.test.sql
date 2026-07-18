begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(28);

select has_table('public', 'review_conflicts', 'conflict snapshots exist');
select has_table('public', 'review_conflict_events', 'conflict event lineage exists');
select has_table('public', 'adjudication_assignments', 'adjudication assignments exist');
select has_table('public', 'adjudication_events', 'adjudication events exist');
select ok((select relrowsecurity from pg_class where oid = 'public.review_conflicts'::regclass), 'conflicts have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.review_conflict_events'::regclass), 'conflict lineage has RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.adjudication_assignments'::regclass), 'adjudication assignments have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.adjudication_events'::regclass), 'adjudication events have RLS');
select has_view('public', 'my_adjudication_queue', 'blind adjudication queue exists');
select has_function(
  'private', 'open_review_conflict', array['text', 'text', 'text', 'text'],
  'service conflict projection exists'
);
select has_function(
  'public', 'submit_adjudication_event',
  array[
    'text', 'text', 'text', 'text', 'smallint', 'timestamp with time zone',
    'integer', 'text', 'text', 'text', 'text', 'text'
  ],
  'authenticated adjudication submission exists'
);
select ok(not has_function_privilege(
  'anon',
  'public.submit_adjudication_event(text,text,text,text,smallint,timestamp with time zone,integer,text,text,text,text,text)',
  'execute'
), 'guests cannot adjudicate');
select ok(has_function_privilege(
  'authenticated',
  'public.submit_adjudication_event(text,text,text,text,smallint,timestamp with time zone,integer,text,text,text,text,text)',
  'execute'
), 'authenticated assignees may submit adjudication');
select ok(not has_table_privilege('authenticated', 'public.adjudication_events', 'insert'), 'browser cannot bypass adjudication RPC');
select ok(not has_table_privilege('authenticated', 'public.adjudication_events', 'update'), 'browser cannot overwrite adjudication');
select ok(not has_table_privilege('authenticated', 'public.adjudication_events', 'delete'), 'browser cannot delete adjudication');
select ok(not has_table_privilege('service_role', 'public.adjudication_events', 'update'), 'service cannot overwrite adjudication');
select ok(not has_table_privilege('authenticated', 'public.review_conflict_events', 'select'), 'source reviewer identities remain private');
select has_trigger('public', 'adjudication_assignments', 'adjudication_assignments_enforce_independence', 'assignment independence trigger exists');
select has_trigger('public', 'adjudication_events', 'adjudication_events_enforce_lineage', 'adjudication lineage trigger exists');
select has_trigger('public', 'adjudication_events', 'adjudication_events_reject_mutation', 'append-only trigger exists');
select has_index('public', 'adjudication_assignments', 'adjudication_assignments_one_active_idx', 'one active adjudicator per conflict');
select has_index('public', 'adjudication_events', 'adjudication_events_conflict_pk_idx', 'adjudication conflict FK indexed');
select col_is_fk('public', 'review_conflict_events', 'review_event_pk', 'conflict links exact review events');
select col_is_fk('public', 'adjudication_events', 'alternative_species_pk', 'alternative taxon is governed');
select col_not_null('public', 'adjudication_events', 'source_event_fingerprints');
select col_not_null('public', 'adjudication_events', 'independence_check');
select col_not_null('public', 'adjudication_events', 'scientific_claim_allowed');

select * from finish();
rollback;
