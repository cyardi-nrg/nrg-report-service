-- NRG SolarConnect — Temporary debug error log
-- Follows 0002-0079.
--
-- Owner: "Why cant you get a simple click to work??" — Generate BOM
-- kept failing with Next's generic redacted "Server Components render"
-- error even after two rounds of hardening the throw itself
-- (generate-bom/actions.ts). Guessing a third theory blind wasn't the
-- responsible move. This table lets the real caught error (message +
-- stack) be written server-side and read back directly via Supabase,
-- completely bypassing whatever Next.js does to the message on its way
-- to the browser in production.
--
-- Temporary — this table and the logging call into it
-- (app/(app)/projects/[id]/generate-bom/actions.ts's saveGeneratedBom)
-- should come back out once the real root cause is found and fixed.

create table debug_error_log (
  debug_error_id uuid primary key default gen_random_uuid(),
  context text not null,
  message text,
  stack text,
  created_at timestamptz not null default now()
);

alter table debug_error_log enable row level security;
create policy debug_error_log_authenticated_full_access on debug_error_log
  for all to authenticated using (true) with check (true);
