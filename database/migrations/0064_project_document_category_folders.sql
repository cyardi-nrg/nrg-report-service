-- NRG SolarConnect — Real Category Subfolders Under Each Project's Drive Folder
-- Follows 0002-0063.
--
-- The owner's own words: "without the link to the app, the Google Drive is
-- useless." Confirmed true by tracing the actual upload path — every
-- scanned document (GEDA/CEIG/DISCOM letters, dispatch challans, site
-- photos, everything) has always uploaded into ONE shared root folder and
-- never moved, even once its project was confirmed; only Postgres's own
-- documents.project_id recorded the real association. Fixed at the
-- application layer by relocating a document into its real project +
-- category subfolder once both are known (lib/google-drive.ts's
-- moveAndRenameFile, called from finalizeMaterialMovement/
-- finalizeGenericDocument/reassignDocument) — this column is that fix's
-- only schema dependency: a small cache so every upload doesn't have to
-- re-list Drive's contents to find "does this project already have a
-- CEIG folder."
--
-- One row's worth of state, keyed by the same category vocabulary
-- documents.document_type groups into for the Documents tab's own filter
-- chips (lib/document-types.ts: 'geda_discom' | 'ceig' | 'dispatch' |
-- 'sales_financial' | 'site_photos' | 'bom') — jsonb rather than six
-- separate nullable columns because the category list is an app-level
-- reference list, not a fixed enum, same reasoning as document_type
-- itself (0009) and module_key (0045).

alter table projects
  add column category_folder_ids jsonb not null default '{}'::jsonb;

comment on column projects.category_folder_ids is
  'Cache of {category_key: drive_folder_id} for this project''s category subfolders (GEDA & DISCOM, CEIG, Dispatch, Sales & Financial, Site Photos, BOM) — populated lazily on first use by ensureCategoryFolder, never hand-edited.';
