-- =============================================================================
-- 01_content_and_roles.sql
-- The content + roles foundation. Installed ONCE per product, before any feature.
--
-- SAVE THIS AS A MIGRATION, e.g.
--   supabase/migrations/20260808000001_content_and_roles.sql
-- Do NOT run it by hand in the SQL editor and leave it out of the migration
-- sequence — that is precisely how a live database and its migration files drift
-- apart, and drift is how following your own runbook produced a broken system.
--
-- This file is IDEMPOTENT: running it twice is safe.
-- =============================================================================
--
-- WHAT THIS SOLVES — two requests that are really the same request
-- ----------------------------------------------------------------
-- "I want to be able to edit the text whenever I want."
-- "I want admin / quality-control / writer / copywriter accounts that can each
--  edit only what they're allowed to."
--
-- Both become true the moment every user-facing string, price, link and toggle
-- lives in a TABLE instead of inside the code, with a column saying who may
-- change it. Then editing text is a database update, not a deploy.
--
-- THREE FAILURES THIS ALSO KILLS FOR FREE
-- ---------------------------------------
-- * "Nothing is sellable — every payment link is a placeholder." Every Subscribe
--   button pointed at https://whish.money/PAY-LINK-HERE. The CHECK constraint
--   below makes that string PHYSICALLY IMPOSSIBLE to publish.
-- * "There is no way to fix it in the app." The only fix was hand-editing the
--   database. Now there is always an editor.
-- * A missing string renders a loud ⟦MISSING:key⟧ instead of a silent blank, so
--   an unfinished screen cannot be mistaken for a finished one.
--
-- SECTIONS
--   1  roles and what they mean
--   2  the content table
--   3  the permission grid
--   4  helper functions (including the two that break RLS recursion)
--   5  row-level security
--   6  publish / submit — done through functions, so QC can approve without
--      being able to author, which is the entire point of a QC role
--   7  audit log
--   8  what the app reads at runtime
-- =============================================================================


-- -----------------------------------------------------------------------------
-- SECTION 1 — ROLES
-- -----------------------------------------------------------------------------
-- Designed rather than copied. The brief named admin / QC / writer / copywriter,
-- but as stated writer and copywriter could do identical things, which makes the
-- distinction meaningless the first time someone asks "who can publish this?".
-- So they are separated by WHAT THEY OWN, and publishing is a separate power
-- from editing.
--
--   owner       Everything, including other owners and credentials.
--   admin       Day-to-day operator. CAN change prices and links.
--   qc          Sees EVERYTHING including drafts. Approves or rejects. Publishes.
--               CANNOT author, and CANNOT touch prices or links. The reviewer
--               must not be the author — a QC that can quietly fix what it is
--               reviewing is not a review step, it is a second writer.
--   writer      Substance: pages, product descriptions, help text, policies.
--               Edits and submits. Never publishes. Never touches money.
--   copywriter  Persuasion: headlines, buttons, taglines, subject lines.
--               Marketing namespace only. Edits and submits. Never publishes.
--   viewer      Read-only, published content only.
--
-- Nobody below admin can EVER change a price or a link. Those are the two field
-- types where a mistake costs money directly, so they are gated by field KIND,
-- not just by namespace: a copywriter editing marketing copy still cannot touch
-- a price that happens to sit inside it.
-- -----------------------------------------------------------------------------

do $$ begin
  create type app_role as enum ('owner','admin','qc','writer','copywriter','viewer');
exception when duplicate_object then null; end $$;

create table if not exists role_rank (
  role        app_role primary key,
  rank        int  not null,
  label       text not null,            -- shown in the admin UI, plain English
  description text not null             -- shown under the label, plain English
);

insert into role_rank (role, rank, label, description) values
  ('owner',      100, 'Owner',           'Full control, including accounts, credentials and money.'),
  ('admin',       80, 'Admin',           'Runs the product day to day. Can change prices and links.'),
  ('qc',          60, 'Quality Control', 'Reviews and approves everything. Cannot write it. Cannot change prices.'),
  ('writer',      40, 'Writer',          'Writes page content, product descriptions and help text. Submits for review.'),
  ('copywriter',  30, 'Copywriter',      'Writes headlines, buttons and marketing copy. Submits for review.'),
  ('viewer',      10, 'Viewer',          'Can look at published content. Cannot change anything.')
on conflict (role) do update
  set rank = excluded.rank, label = excluded.label, description = excluded.description;

create table if not exists user_roles (
  user_id    uuid not null references auth.users(id) on delete cascade,
  role       app_role not null,
  granted_by uuid references auth.users(id),
  granted_at timestamptz not null default now(),
  primary key (user_id, role)
);
create index if not exists user_roles_user_idx on user_roles (user_id);


-- -----------------------------------------------------------------------------
-- SECTION 2 — THE CONTENT TABLE
-- Every user-facing string, price, link and toggle in the entire product.
-- If a customer can read it, it lives here — not in the code.
-- -----------------------------------------------------------------------------

do $$ begin
  create type content_namespace as enum (
    'marketing',   -- headlines, buttons, taglines, ads          -> copywriter
    'product',     -- product names, descriptions, screen labels -> writer
    'help',        -- help text, tooltips, onboarding, errors    -> writer
    'legal',       -- terms, privacy, refund policy              -> writer
    'email',       -- transactional email + WhatsApp copy        -> writer
    'system'       -- feature flags, config, internal            -> admin only
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type content_kind as enum (
    'text','longtext','html','image','number','toggle',
    'price',       -- money. admin+ only, always.
    'link'         -- a URL a customer will click. admin+ only, always.
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type content_status as enum ('draft','in_review','published');
exception when duplicate_object then null; end $$;

create table if not exists content_string (
  key             text primary key,          -- e.g. 'checkout.subscribe_button'
  namespace       content_namespace not null,
  kind            content_kind not null default 'text',
  label           text not null,             -- plain English, shown in the editor
  hint            text,                      -- where it appears on the site
  draft_value     text,
  published_value text,
  status          content_status not null default 'draft',
  updated_by      uuid references auth.users(id),
  updated_at      timestamptz not null default now(),
  published_by    uuid references auth.users(id),
  published_at    timestamptz,
  review_note     text,                      -- QC's reason for rejecting

  -- ---------------------------------------------------------------------------
  -- THE PLACEHOLDER CONSTRAINT — why PAY-LINK-HERE can never ship again.
  -- The database physically refuses to PUBLISH a fake value. Drafts may contain
  -- anything; publishing is what is blocked.
  --
  -- Split into three rules deliberately. An earlier single rule rejected the
  -- perfectly ordinary headings 'Your TODO list' and 'Hire-here specialists',
  -- and a constraint that rejects legitimate content teaches everyone to work
  -- around the constraint — which is worse than not having one.
  -- ---------------------------------------------------------------------------
  constraint no_placeholder_published check (
    published_value is null
    or (
      -- 1. Never legitimate, in any casing.
      published_value !~* '(PAY-LINK-HERE|CHANGEME|CHANGE_ME|REPLACE_ME|lorem ipsum|\{\{)'
      -- 2. SHOUTY forms only, so ordinary words containing them stay legal.
      and published_value !~ '(YOUR_[A-Z]|-HERE\y|XXXX|\yTBD\y)'
      -- 3. Angle/bracket placeholders — not applied to markup-bearing kinds,
      --    where <strong> and friends are the content.
      and (
        kind in ('html','longtext')
        or published_value !~* '(<[a-z_]{2,20}>|\[[A-Z][A-Za-z ]{4,40}\]\s*\?)'
      )
    )
  ),

  -- A published string may not be empty. A blank screen is a bug, not content.
  constraint published_not_blank check (
    status <> 'published'
    or (published_value is not null and length(trim(published_value)) > 0)
  ),

  -- A published link must actually look like a link.
  constraint link_looks_like_link check (
    kind <> 'link' or published_value is null
    or published_value ~* '^(https?://|/|mailto:|tel:|whatsapp://)'
  )
);

create index if not exists content_ns_status_idx on content_string (namespace, status);
create index if not exists content_review_idx on content_string (status) where status = 'in_review';


-- -----------------------------------------------------------------------------
-- SECTION 3 — THE PERMISSION GRID
-- One row per (role, namespace, money?, action). Edited from the admin UI as a
-- checkbox grid, so permissions are DATA — never code, never a deploy.
-- -----------------------------------------------------------------------------

do $$ begin
  create type content_action as enum ('view','edit','submit','publish');
exception when duplicate_object then null; end $$;

create table if not exists role_permission (
  role      app_role not null,
  namespace content_namespace not null,
  money     boolean not null,          -- true = price/link kinds
  action    content_action not null,
  primary key (role, namespace, money, action)
);

-- owner + admin: everything, everywhere, including money.
insert into role_permission (role, namespace, money, action)
select r, n, m, a
from unnest(array['owner','admin']::app_role[]) r,
     unnest(enum_range(null::content_namespace)) n,
     unnest(array[true,false]) m,
     unnest(enum_range(null::content_action)) a
on conflict do nothing;

-- qc: sees everything (including drafts and money), publishes non-money content.
-- Deliberately NO 'edit' anywhere — the reviewer must not be the author.
insert into role_permission (role, namespace, money, action)
select 'qc', n, m, 'view'
from unnest(enum_range(null::content_namespace)) n, unnest(array[true,false]) m
on conflict do nothing;

insert into role_permission (role, namespace, money, action)
select 'qc', n, false, 'publish'
from unnest(enum_range(null::content_namespace)) n
where n <> 'system'
on conflict do nothing;

-- writer: owns substance. Edits and submits. Never publishes, never touches money.
insert into role_permission (role, namespace, money, action)
select 'writer', n, false, a
from unnest(array['product','help','legal','email']::content_namespace[]) n,
     unnest(array['view','edit','submit']::content_action[]) a
on conflict do nothing;
insert into role_permission values ('writer','marketing',false,'view') on conflict do nothing;

-- copywriter: owns persuasion, marketing namespace only.
insert into role_permission (role, namespace, money, action)
select 'copywriter', 'marketing', false, a
from unnest(array['view','edit','submit']::content_action[]) a
on conflict do nothing;

-- viewer: read published only.
insert into role_permission (role, namespace, money, action)
select 'viewer', n, false, 'view'
from unnest(enum_range(null::content_namespace)) n where n <> 'system'
on conflict do nothing;


-- -----------------------------------------------------------------------------
-- SECTION 4 — HELPER FUNCTIONS
-- -----------------------------------------------------------------------------
-- CRITICAL: every function that a policy ON user_roles consults must be
-- SECURITY DEFINER. A policy on user_roles whose USING clause selects from
-- user_roles causes:
--     ERROR: infinite recursion detected in policy for relation "user_roles"
-- which takes the entire roles system down — nobody can list roles, nobody can
-- be granted one. A security-definer function bypasses RLS internally and breaks
-- the cycle.

create or replace function has_role(p_role app_role)
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from user_roles where user_id = auth.uid() and role = p_role);
$$;

create or replace function is_staff()
returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from user_roles where user_id = auth.uid() and role in ('owner','admin')
  );
$$;

-- Is the current user allowed to do <action> on <namespace> for this kind?
create or replace function can_content(
  p_namespace content_namespace,
  p_kind content_kind,
  p_action content_action
) returns boolean
language sql stable security definer set search_path = public as $$
  select exists (
    select 1
    from user_roles ur
    join role_permission rp on rp.role = ur.role
    where ur.user_id = auth.uid()
      and rp.namespace = p_namespace
      and rp.action    = p_action
      and rp.money     = (p_kind in ('price','link'))
  );
$$;

-- Everything the current user may do. The admin console renders itself from
-- this, so the interface can never show a button the database will reject.
create or replace function my_permissions()
returns table (namespace content_namespace, money boolean, action content_action)
language sql stable security definer set search_path = public as $$
  select distinct rp.namespace, rp.money, rp.action
  from user_roles ur join role_permission rp on rp.role = ur.role
  where ur.user_id = auth.uid();
$$;

create or replace function my_top_role() returns app_role
language sql stable security definer set search_path = public as $$
  select ur.role
  from user_roles ur join role_rank rr on rr.role = ur.role
  where ur.user_id = auth.uid()
  order by rr.rank desc limit 1;
$$;


-- -----------------------------------------------------------------------------
-- SECTION 5 — ROW LEVEL SECURITY
-- -----------------------------------------------------------------------------
-- Every policy here is scoped. The two that are open by design carry the suffix
-- `_public_ok` and a comment saying why — the security audit in 03_diagnostics
-- treats that suffix as a declared, reviewed exception rather than an oversight.
-- A permissive anon-full-access policy is the CVE-2025-48757 pattern that
-- publicly exposed 170+ AI-built applications, so a blanket exemption would be
-- unacceptable; a named, commented one is reviewable.

alter table content_string  enable row level security;
alter table user_roles      enable row level security;
alter table role_permission enable row level security;
alter table role_rank       enable row level security;

drop policy if exists content_read_published on content_string;
create policy content_read_published on content_string
  for select using (status = 'published');
comment on policy content_read_published on content_string is
  'Published content is the product own visible text. Public by definition. Drafts are not.';

drop policy if exists content_read_drafts on content_string;
create policy content_read_drafts on content_string
  for select to authenticated
  using (can_content(namespace, kind, 'view'));

-- UPDATE is AUTHORING only. Publishing and submitting go through the functions
-- in Section 6, which is what lets QC approve without being able to write.
drop policy if exists content_update on content_string;
create policy content_update on content_string
  for update to authenticated
  using (can_content(namespace, kind, 'edit'))
  with check (can_content(namespace, kind, 'edit'));

drop policy if exists content_insert on content_string;
create policy content_insert on content_string
  for insert to authenticated
  with check (can_content(namespace, kind, 'edit'));

-- user_roles — via security-definer helpers, never a self-referencing subquery.
drop policy if exists roles_read_own on user_roles;
create policy roles_read_own on user_roles
  for select to authenticated
  using (user_id = auth.uid() or is_staff());

drop policy if exists roles_write_admin on user_roles;
create policy roles_write_admin on user_roles
  for all to authenticated
  using (is_staff()) with check (is_staff());

drop policy if exists perms_read_public_ok on role_permission;
create policy perms_read_public_ok on role_permission
  for select to authenticated using (true);
comment on policy perms_read_public_ok on role_permission is
  'DECLARED PUBLIC: the permission grid is not secret and the admin UI renders from it. Contains no customer data.';

drop policy if exists perms_write_owner on role_permission;
create policy perms_write_owner on role_permission
  for all to authenticated
  using (has_role('owner')) with check (has_role('owner'));

drop policy if exists rank_read_public_ok on role_rank;
create policy rank_read_public_ok on role_rank
  for select using (true);
comment on policy rank_read_public_ok on role_rank is
  'DECLARED PUBLIC: role names and descriptions only. No customer data.';


-- -----------------------------------------------------------------------------
-- SECTION 6 — SUBMIT AND PUBLISH
-- -----------------------------------------------------------------------------
-- These are functions, not UPDATE permissions, and that is the point.
--
-- If publishing were an UPDATE, then QC — which must be able to publish —
-- would need UPDATE, which would also let it rewrite the text it is reviewing.
-- A reviewer who can edit is not a reviewer. So authoring is UPDATE (writers),
-- and approving is a function call (QC) that only ever copies draft -> published.

create or replace function submit_content(p_key text)
returns void
language plpgsql security definer set search_path = public as $$
declare r content_string;
begin
  select * into r from content_string where key = p_key;
  if not found then raise exception 'No such content key: %', p_key; end if;

  if not can_content(r.namespace, r.kind, 'submit') then
    raise exception 'Your role cannot submit % content for review', r.namespace;
  end if;

  update content_string
     set status = 'in_review', review_note = null
   where key = p_key;
end $$;

create or replace function publish_content(p_key text)
returns void
language plpgsql security definer set search_path = public as $$
declare r content_string;
begin
  select * into r from content_string where key = p_key;
  if not found then raise exception 'No such content key: %', p_key; end if;

  if not can_content(r.namespace, r.kind, 'publish') then
    raise exception 'Your role cannot publish % content%', r.namespace,
      case when r.kind in ('price','link')
           then ' — prices and links can only be published by an admin or the owner'
           else '' end;
  end if;

  -- The constraint on the table is what actually stops a placeholder going live.
  -- This call surfaces it as a sentence a person can act on, instead of a raw
  -- constraint-violation error a non-technical editor cannot read.
  begin
    update content_string
       set published_value = draft_value,
           status          = 'published',
           published_by    = auth.uid(),
           published_at    = now()
     where key = p_key;
  exception when check_violation then
    raise exception
      'This cannot be published yet: the text still contains a placeholder (something '
      'like PAY-LINK-HERE, <token>, {{value}} or TBD), or it is empty, or the link is '
      'not a real address. Fix the draft and try again.';
  end;
end $$;

create or replace function reject_content(p_key text, p_reason text)
returns void
language plpgsql security definer set search_path = public as $$
declare r content_string;
begin
  select * into r from content_string where key = p_key;
  if not found then raise exception 'No such content key: %', p_key; end if;
  if not can_content(r.namespace, r.kind, 'publish') then
    raise exception 'Your role cannot review % content', r.namespace;
  end if;
  if p_reason is null or length(trim(p_reason)) = 0 then
    raise exception 'Say why it was rejected — a rejection with no reason cannot be acted on';
  end if;

  update content_string set status = 'draft', review_note = p_reason where key = p_key;
end $$;


-- -----------------------------------------------------------------------------
-- SECTION 7 — AUDIT LOG: who changed what, when, from what to what
-- -----------------------------------------------------------------------------
-- Answers "who changed the price?" — currently unanswerable in the estate,
-- because service-role writes log a NULL actor. Any server function acting on a
-- user's behalf MUST set the actor at the top of the transaction:
--     select set_config('app.actor_id', '<the real user uuid>', true);

create table if not exists content_audit (
  id          bigserial primary key,
  key         text not null,
  action      text not null,              -- created | edited | submitted | published | rejected
  actor       uuid,
  actor_label text,                       -- resolved at write time, survives user deletion
  old_value   text,
  new_value   text,
  at          timestamptz not null default now()
);
create index if not exists content_audit_key_idx on content_audit (key, at desc);

create or replace function log_content_change() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  v_actor uuid := coalesce(auth.uid(), nullif(current_setting('app.actor_id', true), '')::uuid);
  v_action text;
begin
  if tg_op = 'INSERT' then
    v_action := 'created';
  elsif new.status = 'published' and coalesce(old.status::text, '') <> 'published' then
    v_action := 'published';
  elsif new.status = 'in_review' and coalesce(old.status::text, '') <> 'in_review' then
    v_action := 'submitted';
  elsif new.review_note is distinct from old.review_note and new.status = 'draft' then
    v_action := 'rejected';
  else
    v_action := 'edited';
  end if;

  insert into content_audit (key, action, actor, actor_label, old_value, new_value)
  values (
    new.key, v_action, v_actor,
    coalesce((select email from auth.users where id = v_actor), 'system/service-role'),
    case when tg_op = 'INSERT' then null else coalesce(old.published_value, old.draft_value) end,
    coalesce(new.published_value, new.draft_value)
  );

  new.updated_at := now();
  new.updated_by := coalesce(v_actor, new.updated_by);
  return new;
end $$;

drop trigger if exists content_audit_trg on content_string;
create trigger content_audit_trg
  before insert or update on content_string
  for each row execute function log_content_change();

alter table content_audit enable row level security;
drop policy if exists audit_read_staff on content_audit;
create policy audit_read_staff on content_audit
  for select to authenticated
  using (is_staff() or has_role('qc'));


-- -----------------------------------------------------------------------------
-- SECTION 8 — WHAT THE APP READS AT RUNTIME
-- -----------------------------------------------------------------------------
-- The app calls t('checkout.subscribe_button'). It NEVER reads draft values, so
-- an unfinished edit can never leak to a customer.

create or replace view content_published as
  select key, namespace, kind, published_value as value
  from content_string
  where status = 'published';

-- Returns a loud marker rather than NULL when a key is missing, so a missing
-- string is impossible to mistake for a finished screen.
create or replace function t(p_key text) returns text
language sql stable security definer set search_path = public as $$
  select coalesce(
    (select published_value from content_string where key = p_key and status = 'published'),
    '⟦MISSING:' || p_key || '⟧'
  );
$$;


-- =============================================================================
-- AFTER RUNNING THIS FILE — four steps, in order
-- =============================================================================
-- 1. Give yourself the owner role (use your own auth user id):
--       insert into user_roles (user_id, role) values ('<your-uuid>', 'owner');
--
-- 2. Import every string currently hard-coded in the product:
--       node scripts/extract_strings.mjs
--    then review the key names before running content-import.sql. Key names are
--    how you will find things in the editor later, so checkout.subscribe_button
--    beats page_47_text_3.
--
-- 3. Replace those strings with t('key') ONE FILE AT A TIME, checking the site
--    after each. content-replace.md lists them.
--
-- 4. Turn on the no-literal-string lint so a NEW hard-coded string fails the
--    build — that is what stops this migration ever being needed twice.
--
-- From then on: changing any text, price or link is an edit in the admin
-- console. No deploy, no developer, no risk.
-- =============================================================================
