-- NRG SolarConnect — Social Media module
-- Follows 0002-0058. Brings the standalone "NRG Social" dashboard
-- (NRG_Social_Media_Handover v2.0 — Claude Design artifact, browser
-- localStorage, Google Sheet intake) into the real app: a project's
-- photo folder gets linked once, then AI reads those photos plus the
-- project's own real data to write platform captions, stored in the
-- database instead of a page-local posts array.

-- ============================================================
-- One row per project that's been connected for social — separate
-- from projects.google_drive_folder_id (0002), which is the project's
-- documents folder, not necessarily where install photos live
-- ============================================================

create table social_projects (
  social_project_id  uuid primary key default gen_random_uuid(),
  project_id         uuid not null unique references projects(project_id),
  photos_folder_url  text not null,   -- as pasted by whoever connects it
  photos_folder_id   text,            -- parsed Drive folder ID, once resolved
  connected_by       uuid references employees(employee_id),
  connected_at       timestamptz not null default now(),
  last_generated_at  timestamptz,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);

-- unique on project_id — "connect a folder" is a per-project link, not a
-- repeatable log; reconnecting overwrites the same row (see actions.ts).

-- ============================================================
-- Generated posts — one row per platform per generation run
-- ============================================================

create table social_posts (
  social_post_id     uuid primary key default gen_random_uuid(),
  social_project_id  uuid not null references social_projects(social_project_id) on delete cascade,
  platform           text not null check (platform in (
                        'linkedin_personal', 'linkedin_company', 'instagram', 'facebook', 'gmb', 'whatsapp'
                      )),
  caption            text not null,
  hashtags           text[] not null default '{}',
  status             text not null default 'draft' check (status in ('draft', 'posted')),
  generated_at       timestamptz not null default now(),
  created_at         timestamptz not null default now()
);

create index on social_posts (social_project_id);

-- Regenerating replaces a project's post set (app deletes the old rows
-- for that social_project_id before inserting the new ones) rather than
-- accumulating duplicates across runs — matches the source dashboard's
-- own "edits the posts array" behaviour, just persisted server-side now.
