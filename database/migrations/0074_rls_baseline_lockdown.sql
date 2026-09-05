-- NRG SolarConnect — RLS baseline lockdown
-- Follows 0002-0073.
--
-- Real, serious gap found the night before go-live: every single table in
-- the public schema except user_devices (94 of them) had Row-Level
-- Security completely disabled. NEXT_PUBLIC_SUPABASE_ANON_KEY is, by
-- design, public — it ships in the browser bundle. With RLS off, anyone
-- who pulls that key out of the deployed JS (trivial) can read or write
-- every one of these tables directly through Supabase's REST API,
-- completely bypassing the app, its login screen, and its device-approval
-- gate. This is almost certainly what triggered the Supabase security
-- advisory email the owner remembered receiving.
--
-- This is the SAFE baseline fix, not the final one: enable RLS on every
-- affected table and add one permissive policy that allows the
-- 'authenticated' Postgres role to do everything — i.e. exactly what
-- already happens today, since every real read/write in this app goes
-- through lib/supabase/server.ts's createClient() (anon key + the
-- signed-in user's session, which Supabase maps to the 'authenticated'
-- role) or the explicit service-role client. Nothing built on
-- createClient() changes behavior. What changes: the 'anon' role (i.e.
-- anyone hitting the REST API with the bare public key and no valid
-- login) can no longer touch these tables at all.
--
-- This intentionally does NOT yet build real per-role policies (e.g. a
-- salesperson only seeing their own projects at the database level, not
-- just the app-layer filter added for /projects). That is real,
-- worthwhile follow-up work, tracked separately — this migration's job is
-- to close the "wide open to the entire internet" hole tonight without
-- risking breaking the live app hours before client delivery.
do $$
declare
  t text;
begin
  for t in
    select tablename from pg_tables
    where schemaname = 'public' and rowsecurity = false
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format(
      'create policy %I on public.%I for all to authenticated using (true) with check (true)',
      t || '_authenticated_full_access', t
    );
  end loop;
end $$;

-- Prevent the exact data corruption that broke every quote save tonight:
-- quote_kw_band_rates had every band duplicated (20 rows, 10 distinct
-- ranges), which made createQuote()'s .maybeSingle() range lookup error
-- out on every single quote request, for every system size. The
-- duplicate rows were removed directly (data fix, not part of this
-- migration); this constraint stops it from silently happening again.
alter table quote_kw_band_rates
  add constraint quote_kw_band_rates_range_unique unique (organization_id, min_kw, max_kw);
