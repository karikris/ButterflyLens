begin;

create extension if not exists pgtap with schema extensions;
set search_path = public, private, extensions;

select plan(55);

select has_table('public', 'moderation_cases');
select has_table('private', 'moderation_reporters');
select has_table('public', 'moderation_events');
select has_table('public', 'moderation_appeals');
select has_table('public', 'moderation_curator_notes');
select has_view('public', 'moderated_review_comments');

select ok((select relrowsecurity from pg_class where oid = 'public.moderation_cases'::regclass), 'moderation cases have RLS');
select ok((select relrowsecurity from pg_class where oid = 'private.moderation_reporters'::regclass), 'private reporters have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.moderation_events'::regclass), 'moderation events have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.moderation_appeals'::regclass), 'appeals have RLS');
select ok((select relrowsecurity from pg_class where oid = 'public.moderation_curator_notes'::regclass), 'curator notes have RLS');

select has_trigger('public', 'moderation_cases', 'moderation_cases_validate');
select has_trigger('public', 'moderation_cases', 'moderation_cases_reject_mutation');
select has_trigger('private', 'moderation_reporters', 'moderation_reporters_reject_mutation');
select has_trigger('public', 'moderation_appeals', 'moderation_appeals_reject_mutation');
select has_trigger('public', 'moderation_curator_notes', 'moderation_curator_notes_reject_mutation');
select has_trigger('public', 'moderation_events', 'moderation_events_validate');
select has_trigger('public', 'moderation_events', 'moderation_events_reject_mutation');

select has_function('public', 'report_review_comment', array['text', 'text', 'text', 'text', 'text']);
select has_function('public', 'open_review_audit_case', array['text', 'text', 'text', 'text']);
select has_function('public', 'appeal_moderation_case', array['text', 'text', 'text', 'text']);
select has_function('public', 'moderate_community_case', array['text', 'text', 'text', 'text[]', 'text', 'text']);
select has_function('public', 'add_moderation_curator_note', array['text', 'text', 'text', 'text']);

select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'report_review_comment'
), 'comment-report RPC is a fixed-search-path security definer');
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'open_review_audit_case'
), 'review-audit RPC is a fixed-search-path security definer');
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'appeal_moderation_case'
), 'appeal RPC is a fixed-search-path security definer');
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'moderate_community_case'
), 'curator-action RPC is a fixed-search-path security definer');
select ok((
  select function.prosecdef and function.proconfig @> array['search_path=""']
  from pg_proc function join pg_namespace namespace on namespace.oid = function.pronamespace
  where namespace.nspname = 'public' and function.proname = 'add_moderation_curator_note'
), 'curator-note RPC is a fixed-search-path security definer');

select ok(not has_function_privilege('anon', 'public.report_review_comment(text,text,text,text,text)', 'execute'), 'guest cannot report comments');
select ok(not has_function_privilege('anon', 'public.open_review_audit_case(text,text,text,text)', 'execute'), 'guest cannot open audits');
select ok(not has_function_privilege('anon', 'public.appeal_moderation_case(text,text,text,text)', 'execute'), 'guest cannot appeal');
select ok(not has_function_privilege('anon', 'public.moderate_community_case(text,text,text,text[],text,text)', 'execute'), 'guest cannot moderate');
select ok(not has_function_privilege('anon', 'public.add_moderation_curator_note(text,text,text,text)', 'execute'), 'guest cannot add notes');

select ok(has_function_privilege('authenticated', 'public.report_review_comment(text,text,text,text,text)', 'execute'), 'member may call report RPC');
select ok(has_function_privilege('authenticated', 'public.open_review_audit_case(text,text,text,text)', 'execute'), 'curator may call audit RPC');
select ok(has_function_privilege('authenticated', 'public.appeal_moderation_case(text,text,text,text)', 'execute'), 'affected reviewer may call appeal RPC');
select ok(has_function_privilege('authenticated', 'public.moderate_community_case(text,text,text,text[],text,text)', 'execute'), 'curator may call moderation RPC');
select ok(has_function_privilege('authenticated', 'public.add_moderation_curator_note(text,text,text,text)', 'execute'), 'curator may call note RPC');

select ok(not has_table_privilege('authenticated', 'public.moderation_cases', 'insert'), 'browser cannot bypass case RPC');
select ok(not has_table_privilege('authenticated', 'public.moderation_events', 'insert'), 'browser cannot bypass event RPC');
select ok(not has_table_privilege('authenticated', 'public.moderation_cases', 'update'), 'cases cannot be overwritten');
select ok(not has_table_privilege('authenticated', 'public.moderation_events', 'delete'), 'events cannot be deleted');
select ok(not has_table_privilege('anon', 'public.moderation_cases', 'select'), 'guest cannot read cases');
select ok(not has_table_privilege('anon', 'public.moderated_review_comments', 'select'), 'guest cannot read review comments');
select ok(has_table_privilege('authenticated', 'public.moderated_review_comments', 'select'), 'authenticated self/curator projection is queryable');
select ok(not has_table_privilege('service_role', 'public.moderation_cases', 'update'), 'service role cannot rewrite cases');

select col_is_fk('public', 'moderation_cases', 'target_review_event_pk', 'case retains review-event lineage');
select col_is_fk('public', 'moderation_cases', 'target_reviewer_profile_pk', 'case retains affected reviewer lineage');
select col_is_fk('public', 'moderation_events', 'moderation_case_pk', 'event retains case lineage');
select col_is_fk('public', 'moderation_appeals', 'moderation_case_pk', 'appeal retains case lineage');
select col_is_fk('public', 'moderation_curator_notes', 'moderation_case_pk', 'curator note retains case lineage');
select col_is_fk('private', 'moderation_reporters', 'moderation_case_pk', 'private reporter retains case lineage');
select col_type_is('public', 'moderated_review_comments', 'display_comment', 'text');
select has_index('public', 'moderation_curator_notes', 'moderation_curator_notes_curator_idx', 'curator note foreign-key lookup is indexed');

select ok(not has_table_privilege('authenticated', 'public.review_events', 'update'), 'moderation cannot overwrite a review event');

select * from finish();
rollback;
