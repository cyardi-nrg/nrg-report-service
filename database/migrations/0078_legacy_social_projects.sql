-- NRG SolarConnect — Legacy (pre-app) projects for Social Media
-- Follows 0002-0077.
--
-- Owner: "for the social media....i already have several folders with
-- our older projects...for which i want to point to the folder
-- location...and give basic details like client name, kw, year,
-- panels used, inverter used, system cost....savings you should
-- calculate...payback you should calculate... include this in the
-- page..."
--
-- social_projects (0059) is deliberately NOT the right table for this:
-- it's a NOT NULL UNIQUE FK to projects, and 0061 explicitly removed its
-- pasted-Drive-link flow on the owner's own standing rule ("no one else
-- has access to Google Drive... it shouldn't ask for a link at all") —
-- that rule is about the app's OWN service-account-managed project
-- folders, where the app can always just create/reuse one itself
-- (ensureProjectDriveFolder). These older installs predate the app
-- entirely: there is no projects row, and their Drive folders are the
-- owner's own personal ones — pasting a link to one is the only way to
-- reference it, and doesn't reopen the case 0061 closed.
--
-- Standalone table, same shape as payback_reports (0017-ish) — a
-- freestanding calculator record, not required to hang off a real
-- project. No AI post-generation for these (that reads photos via the
-- app's own Drive service account, which has no access to the owner's
-- personal old-project folders) — just the entered facts plus the real
-- payback/savings formulas (lib/payback.ts) run against them.

create table legacy_social_projects (
  legacy_project_id  uuid primary key default gen_random_uuid(),
  client_name        text not null,
  kw_capacity        numeric not null check (kw_capacity > 0),
  install_year       integer not null check (install_year between 2000 and 2100),
  panels_used        text,
  inverter_used      text,
  system_cost        numeric not null check (system_cost > 0),
  drive_folder_url   text,
  created_by         uuid references employees(employee_id),
  created_at         timestamptz not null default now()
);

-- 0074's RLS baseline lockdown applies to every table going forward, not
-- just the ones that existed that night — a fresh table defaults to RLS
-- OFF (the Postgres default), which would reopen exactly the hole 0074
-- closed. Same policy shape: 'authenticated' (every real read/write in
-- this app, via lib/supabase/server.ts) gets full access; 'anon' gets
-- none.
alter table legacy_social_projects enable row level security;
create policy legacy_social_projects_authenticated_full_access on legacy_social_projects
  for all to authenticated using (true) with check (true);
