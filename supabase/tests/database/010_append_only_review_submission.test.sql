begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, extensions;

select plan(14);

select has_function(
  'public', 'submit_review_event',
  array[
    'text', 'text', 'text', 'text', 'smallint', 'timestamp with time zone',
    'integer', 'text', 'text', 'text', 'text', 'text'
  ],
  'authenticated append-only review RPC exists'
);
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function
  join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'submit_review_event'
), 'review submission RPC is fixed-search-path security definer');
select ok(not has_function_privilege(
  'anon',
  'public.submit_review_event(text,text,text,text,smallint,timestamp with time zone,integer,text,text,text,text,text)',
  'execute'
), 'guests cannot submit reviews');
select ok(has_function_privilege(
  'authenticated',
  'public.submit_review_event(text,text,text,text,smallint,timestamp with time zone,integer,text,text,text,text,text)',
  'execute'
), 'authenticated reviewers may call the submission RPC');
select ok(not has_table_privilege(
  'authenticated', 'public.review_events', 'insert'
), 'browser roles cannot bypass the submission RPC');
select ok(not has_table_privilege(
  'authenticated', 'public.review_events', 'update'
), 'review events cannot be overwritten');
select ok(not has_table_privilege(
  'authenticated', 'public.review_events', 'delete'
), 'review events cannot be deleted');
select has_trigger(
  'public', 'review_events', 'review_events_enforce_append_lineage',
  'review event append-lineage trigger exists'
);
select col_is_fk(
  'public', 'review_events', 'supersedes_event_pk',
  'superseded event remains a foreign-key link'
);
select col_not_null('public', 'review_events', 'review_event_id');
select col_not_null('public', 'review_events', 'comment');
select col_not_null('public', 'review_events', 'decided_at');
select col_not_null('public', 'review_events', 'source_version');
select col_not_null('public', 'review_events', 'event_fingerprint');

select * from finish();
rollback;
