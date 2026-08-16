-- NRG SolarConnect — Reassigning a Misfiled Document to the Right Project
-- Follows 0002-0029. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 70.

-- ============================================================
-- A scanned document filed under the wrong project needs a real
-- correction path, not a delete-and-reupload
-- ============================================================

-- Real, concrete case: a document gets scanned and pasted into the
-- wrong project by mistake — two projects with similar names, a site
-- photo uploaded from the wrong folder, whatever the cause.
-- documents.project_id (nullable since Section 9) is a plain FK, so
-- editing it is mechanically trivial — the real gap is that nothing
-- records that a correction happened, which project it moved from,
-- who moved it, or why, breaking the same "never silently overwrite"
-- discipline every other correction in this schema already follows
-- (declared_quantity's note, stock_adjustments.reason,
-- project_document_exemptions.reason, the materials/projects merge
-- audit trail).

alter table documents add column reassigned_from_project_id uuid references projects(project_id);
alter table documents add column reassigned_by uuid references employees(employee_id);
alter table documents add column reassigned_at timestamptz;
alter table documents add column reassignment_reason text;

-- Reassigning a document is an ordinary update to project_id, plus
-- populating these four together: reassigned_from_project_id captures
-- where it was filed before the correction (project_id itself only
-- ever holds the current, correct answer), reassigned_by/reassigned_at
-- who and when, reassignment_reason why — required at the point of
-- reassignment by the application, the same way every other reason
-- field in this schema is conditionally required without a DB
-- constraint enforcing it (there's nothing to reassign before the
-- first correction, so the column can't be not null outright). If a
-- document is ever moved more than once, these four columns hold the
-- most recent correction only — acceptable, since this is a rare
-- fix-up action, not a repeated workflow, and google_drive_file_id
-- (Section 27) stays stable across any move, so the underlying file
-- is never actually lost track of even if the full multi-hop history
-- isn't retained in the row itself.

-- ============================================================
-- Not everyone gets to move a document between projects
-- ============================================================

-- Confirmed real restriction: only the Owner or Purchase should be
-- able to reassign a document, nobody else who can see the Documents
-- tab. This is access control, not a schema concern, and it can't be
-- properly enforced until the real roles/permissions/RLS design
-- happens (Next Session item 4, same still-open item Section 68's
-- pipeline-visibility rule and Section 69's project-merge both defer
-- to) — flagged here as another concrete requirement for that design:
-- Move is Owner/Purchase only, everyone else (including whoever
-- uploaded the document in the first place) can see that a document
-- exists but not relocate it.
