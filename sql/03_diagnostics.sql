-- =============================================================================
-- 03_diagnostics.sql — READ-ONLY. Run these against the live database.
-- Nothing here changes data. Every query answers one dangerous question.
-- =============================================================================
-- Run them from the Supabase SQL editor, or:  supabase db query -f 03_diagnostics.sql
-- Any query returning rows is a finding. All five should return ZERO rows.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- FINDING 1 — Tables anyone can read or write
-- -----------------------------------------------------------------------------
-- A policy whose condition is `true` grants every authenticated user (and often
-- every anonymous visitor) full access. One such policy — named demo_all — is
-- live in this estate right now. This is the exact pattern behind CVE-2025-48757,
-- which publicly exposed 170+ AI-built applications including customer records.
--
-- ANY ROW HERE IS A LIVE DATA BREACH WAITING TO BE FOUND.

-- Policies whose name ends in `_public_ok` are DECLARED, REVIEWED exceptions and
-- must carry a comment saying why (e.g. anonymous visitors must be able to file
-- an error report, or the failures that block sign-in become invisible). They
-- are excluded here but listed separately below, so an intentional exception is
-- reviewable rather than either invisible or permanently noisy.

select 'PERMISSIVE POLICY' as finding,
       schemaname || '.' || tablename as object,
       policyname,
       cmd as applies_to,
       'This policy lets anyone do this. Replace `true` with a real condition — or, '
       'if it is genuinely intentional, rename it to end in _public_ok and add a '
       'COMMENT ON POLICY explaining why.' as fix
from pg_policies
where schemaname not in ('pg_catalog','information_schema')
  and (qual = 'true' or with_check = 'true')
  and policyname not like '%\_public\_ok';

-- The declared exceptions, for review. Not a failure — but read them.
select 'DECLARED PUBLIC (review)' as finding,
       schemaname || '.' || tablename as object,
       policyname,
       cmd as applies_to,
       coalesce(obj_description(p.oid, 'pg_policy'), '⚠ NO COMMENT — say why this is safe') as reason
from pg_policies pol
join pg_policy p on p.polname = pol.policyname
where pol.schemaname not in ('pg_catalog','information_schema')
  and (pol.qual = 'true' or pol.with_check = 'true')
  and pol.policyname like '%\_public\_ok';


-- -----------------------------------------------------------------------------
-- FINDING 2 — Tables with row-level security switched OFF
-- -----------------------------------------------------------------------------
-- In Supabase, a table in an exposed schema with RLS off is readable by anyone
-- holding the public key — which is printed in your own page source.

select 'RLS DISABLED' as finding,
       schemaname || '.' || tablename as object,
       'Anyone with the public key can read this table. Run: alter table '
         || schemaname || '.' || tablename || ' enable row level security;' as fix
from pg_tables
where schemaname in ('public','storage')
  and not rowsecurity;


-- -----------------------------------------------------------------------------
-- FINDING 3 — RLS on, but no policies at all
-- -----------------------------------------------------------------------------
-- This fails CLOSED (nobody can read it), so it is not a breach — but it is
-- almost always a feature that silently returns empty results forever, which
-- looks exactly like "the app has no data" and wastes days of debugging.

select 'RLS ENABLED BUT NO POLICIES' as finding,
       t.schemaname || '.' || t.tablename as object,
       'Every query against this table returns nothing. Add a policy or the '
         || 'feature that uses it will appear permanently empty.' as fix
from pg_tables t
where t.schemaname = 'public'
  and t.rowsecurity
  and not exists (select 1 from pg_policies p
                  where p.schemaname = t.schemaname and p.tablename = t.tablename);


-- -----------------------------------------------------------------------------
-- FINDING 4 — UPDATE/ALL policies missing WITH CHECK
-- -----------------------------------------------------------------------------
-- A policy with USING but no WITH CHECK lets a user modify a row they can see
-- into a row they should NOT own — e.g. reassigning someone else's order to
-- themselves. Classic broken object-level authorization.

select 'UPDATE POLICY WITHOUT WITH CHECK' as finding,
       schemaname || '.' || tablename as object,
       policyname,
       'A user can edit a row into one they should not own. Add a WITH CHECK '
         || 'clause matching the USING clause.' as fix
from pg_policies
where cmd in ('UPDATE','ALL')
  and schemaname = 'public'
  and with_check is null;


-- -----------------------------------------------------------------------------
-- FINDING 5 — Columns that are almost certainly dead
-- -----------------------------------------------------------------------------
-- The audit found fields the server collected that no UI writes and no logic
-- reads: "Focus/Mix industry percentages — no UI asks for them, the server
-- fabricates them, and the matcher ignores them entirely. Dead data behind a
-- headline feature."
--
-- SQL alone cannot see the application code, so this finds the strong signal:
-- a column that is 100% NULL or 100% one value across every row. Confirm each
-- hit against the codebase before deleting.

do $$
declare r record; total bigint; nulls bigint; distincts bigint;
begin
  raise notice '%', 'COLUMN | ROWS | NULLS | DISTINCT VALUES | VERDICT';
  for r in
    select c.table_name, c.column_name
    from information_schema.columns c
    join pg_tables t on t.tablename = c.table_name and t.schemaname = 'public'
    where c.table_schema = 'public'
      and c.column_name not in ('id','created_at','updated_at','deleted_at')
      -- count(distinct) needs an equality operator. On json, xml and point it
      -- raises "could not identify an equality operator", which under
      -- ON_ERROR_STOP=1 aborts the whole CI security step — a diagnostic that
      -- kills the build it is meant to inform.
      and c.data_type not in ('json','xml','point','line','lseg','box','path','polygon','circle')
  loop
    begin
      execute format(
        'select count(*), count(*) filter (where %I is null), count(distinct %I) from public.%I',
        r.column_name, r.column_name, r.table_name)
        into total, nulls, distincts;
    exception when others then
      continue;   -- an un-comparable column is not a finding, just unreadable here
    end;

    if total > 20 and (nulls = total or distincts <= 1) then
      raise notice '%.% | % rows | % null | % distinct | LIKELY DEAD — confirm nothing reads it, then drop it',
        r.table_name, r.column_name, total, nulls, distincts;
    end if;
  end loop;
end $$;
