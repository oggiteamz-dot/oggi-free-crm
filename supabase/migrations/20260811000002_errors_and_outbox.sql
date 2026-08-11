-- =============================================================================
-- 02_errors_and_outbox.sql
-- The "nothing fails silently" foundation. Installed ONCE per product.
-- =============================================================================
--
-- THE FAILURE THIS EXISTS TO PREVENT
-- ----------------------------------
-- A lead submitted the form. The system matched them to a freelancer. The match
-- saved correctly. And then NOBODY WAS TOLD — not the freelancer, not the lead.
-- No error appeared anywhere. The lead watched their matches page and waited for
-- a call that was never going to come. It ran like that for weeks.
--
-- WHY A CODE SCANNER CANNOT CATCH THIS
-- ------------------------------------
-- There was no exception to swallow. The notification code NEVER RAN. A lint
-- rule can find a swallowed error; nothing static can detect silence.
--
-- Only two things detect silence:
--   1. An OUTBOX — the intent to notify is written in the SAME TRANSACTION as
--      the business record. If the order saved, the "tell someone" row saved too.
--      A relay then retries until it is delivered or declared dead. Rows are
--      never deleted, so "we tried and failed" is permanently visible.
--   2. A HEARTBEAT — every recurring job reports "I ran". An alarm fires when a
--      job STOPS reporting. The alarm is triggered by ABSENCE, which is the only
--      way to notice something that isn't happening.
--
-- Supabase makes this worse than it looks: net._http_response retains only about
-- 6 hours and has no documented retry, so a failed webhook becomes invisible
-- within a day. The outbox is not optional on this stack.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. THE ERROR INBOX — every failure, in one place a human actually reads
-- -----------------------------------------------------------------------------
create table if not exists app_error (
  id bigserial primary key,
  code text not null,                    -- stable UPPER_SNAKE_CASE, e.g. ORDER_SAVE_FAILED
  message text not null,
  context jsonb not null default '{}',   -- what the user was doing, which record
  severity text not null default 'error' -- info | warn | error | critical
    check (severity in ('info','warn','error','critical')),
  user_id uuid,
  url text,
  user_agent text,
  seen_at timestamptz,                   -- null = nobody has looked at it yet
  resolved_at timestamptz,
  at timestamptz not null default now()
);
create index if not exists app_error_at_idx on app_error (at desc);
create index if not exists app_error_code_idx on app_error (code, at desc);
create index if not exists app_error_open_idx on app_error (severity) where resolved_at is null;

-- The front end posts here via reportError(). Anyone may WRITE an error — a
-- logged-out visitor hits errors too, and an error report that requires a login
-- misses exactly the failures that stop people logging in. Only staff may READ.
alter table app_error enable row level security;

drop policy if exists error_insert_public_ok on app_error;
create policy error_insert_public_ok on app_error for insert with check (true);
comment on policy error_insert_public_ok on app_error is
  'DECLARED PUBLIC (insert only): anonymous visitors must be able to report errors, '
  'or the failures that block sign-in are invisible. Reads are staff-only. '
  'Rate-limited client-side in error-sink.js.';

drop policy if exists error_read_staff on app_error;
create policy error_read_staff on app_error for select to authenticated
  using (is_staff() or has_role('qc'));

-- What the Admin Error Inbox screen shows: newest unresolved first, grouped.
create or replace view error_inbox as
  select code,
         severity,
         count(*)          as occurrences,
         max(at)           as last_seen,
         min(at)           as first_seen,
         (array_agg(message order by at desc))[1] as latest_message,
         (array_agg(url    order by at desc))[1] as latest_url
  from app_error
  where resolved_at is null
  group by code, severity
  order by max(at) desc;


-- -----------------------------------------------------------------------------
-- 2. THE OUTBOX — "somebody must be told" survives a crash
-- -----------------------------------------------------------------------------
-- USAGE, and this is the whole point: the insert into notification_outbox must
-- happen in the SAME TRANSACTION as the business write.
--
--     begin;
--       insert into matches (...) values (...);
--       insert into notification_outbox (channel, recipient, template, payload)
--         values ('whatsapp', '+9613...', 'new_match', jsonb_build_object(...));
--     commit;
--
-- If the match saved, the notification intent saved. They cannot diverge.

create table if not exists notification_outbox (
  id bigserial primary key,
  channel text not null,                 -- whatsapp | email | sms | push | webhook
  recipient text not null,
  template text not null,
  payload jsonb not null default '{}',
  status text not null default 'pending' -- pending | sent | dead
    check (status in ('pending','sent','dead')),
  attempts int not null default 0,
  last_error text,
  next_attempt_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  sent_at timestamptz
);
create index if not exists outbox_pending_idx on notification_outbox (status, next_attempt_at)
  where status = 'pending';
create index if not exists outbox_created_idx on notification_outbox (created_at desc);

alter table notification_outbox enable row level security;
drop policy if exists outbox_staff on notification_outbox;
create policy outbox_staff on notification_outbox for select to authenticated
  using (is_staff());

-- THE VIEW THAT WOULD HAVE CAUGHT THE ORIGINAL BUG ON DAY ONE.
-- Anything sitting here for more than 10 minutes means somebody is waiting for a
-- message that has not arrived. Put this on the admin dashboard as a red number.
create or replace view undelivered_notifications as
  select id, channel, recipient, template, attempts, last_error,
         age(now(), created_at) as waiting_for
  from notification_outbox
  where status <> 'sent' and created_at < now() - interval '10 minutes'
  order by created_at;


-- -----------------------------------------------------------------------------
-- 3. HEARTBEATS — the alarm that fires on SILENCE
-- -----------------------------------------------------------------------------
-- Every recurring job calls beat('job-name') on each successful run. If a job
-- stops running entirely — the failure mode with no error to catch — its row
-- goes stale and it appears in stale_jobs.

create table if not exists job_heartbeat (
  job          text primary key,
  expect_every interval not null,        -- e.g. '1 hour', '1 day'
  last_beat    timestamptz,
  last_ok      boolean,
  note         text
);

-- UPSERT, not UPDATE. A plain UPDATE silently affected zero rows when the job
-- was never registered — so calling beat('some-job') succeeded, the job never
-- appeared in job_heartbeat, and therefore never appeared in stale_jobs either.
-- The silence detector was itself silent about unregistered jobs.
create or replace function beat(
  p_job text,
  p_ok boolean default true,
  p_note text default null,
  p_expect_every interval default '1 hour'
) returns void
language plpgsql security definer set search_path = public as $$
begin
  insert into job_heartbeat (job, expect_every, last_beat, last_ok, note)
  values (p_job, p_expect_every, now(), p_ok, p_note)
  on conflict (job) do update
    set last_beat = now(),
        last_ok   = p_ok,
        note      = coalesce(p_note, job_heartbeat.note);
end $$;

-- Put this on the admin dashboard. A non-empty result means something that is
-- supposed to be happening has quietly stopped happening.
--
-- NOTE the null handling. Writing age(now(), coalesce(last_beat, '-infinity'))
-- raises "timestamp out of range" — Postgres refuses age() on an infinite
-- timestamp. So a job that had NEVER run once, which is the only case this view
-- exists to catch, made the whole view throw, and the dashboard number that must
-- always read zero was a 500 instead.
create or replace view stale_jobs as
  select job,
         last_beat,
         expect_every,
         case when last_beat is null then null else age(now(), last_beat) end as silent_for,
         case when last_beat is null then 'has never run once' else 'has stopped running' end as verdict
  from job_heartbeat
  where last_beat is null
     or last_beat < now() - (expect_every * 2)
  order by last_beat nulls first;

alter table job_heartbeat enable row level security;
drop policy if exists heartbeat_staff on job_heartbeat;
create policy heartbeat_staff on job_heartbeat for select to authenticated
  using (is_staff());

-- =============================================================================
-- WIRING CHECKLIST (do all four, or this file is decoration)
-- =============================================================================
-- [ ] Front end loads error-sink.js so window.onerror, unhandledrejection and
--     every catch block call reportError(err, context) -> app_error.
-- [ ] Every "somebody must be told" write goes through notification_outbox, in
--     the same transaction as the business record.
-- [ ] A relay function runs every minute: take pending rows whose next_attempt_at
--     has passed, try to send, mark sent OR increment attempts with backoff, and
--     mark dead after 10 attempts. Never delete a row.
-- [ ] Every recurring job is registered in job_heartbeat and calls beat() on
--     success. The admin dashboard shows stale_jobs and undelivered_notifications
--     as two red numbers that should always be zero.
-- =============================================================================
