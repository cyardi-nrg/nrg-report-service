-- NRG SolarConnect — Social Media: stop asking for a pasted Drive folder link
-- Follows 0002-0060.
--
-- 0059 had social_projects.photos_folder_url as "as pasted by whoever
-- connects it" — a manual paste-a-Drive-link step. That predates the
-- owner's explicit, standing correction made later the same build
-- session: "no one else has access to Google Drive... it shouldn't ask
-- for a link at all" (the same fix already applied to BOM saves and
-- document uploads via ensureProjectDriveFolder). Social Media never
-- got the same retrofit until now.
--
-- The real fix doesn't need a second Drive folder concept at all: every
-- project already has documents (0002), already-classified by AI into
-- document_type = 'site_photo' (lib/ai-extraction.ts's real, settled
-- vocabulary) when uploaded through the ordinary project Documents
-- flow. Post generation now reads those rows directly — no folder link,
-- no separate "connect" step, one less place for staff to get stuck.
--
-- social_projects stays (still the real place to track last_generated_at
-- per project), but the folder columns are no longer written to, so the
-- not-null constraint has to go.

alter table social_projects
  alter column photos_folder_url drop not null;

comment on column social_projects.photos_folder_url is
  'Legacy — pasted-link connection flow, removed. Left nullable for old rows; no longer written to. Post generation now reads documents.document_type = ''site_photo'' for the project directly.';
comment on column social_projects.photos_folder_id is
  'Legacy — see photos_folder_url. No longer written to.';
