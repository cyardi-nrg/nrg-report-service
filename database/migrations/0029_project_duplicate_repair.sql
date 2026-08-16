-- NRG SolarConnect — Repairing a Project Created Twice (or Three Times)
-- by Different People
-- Follows 0002-0028. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 69.

-- ============================================================
-- Same duplicate-record problem already solved for materials
-- (Section 60), now for projects
-- ============================================================

-- Real, confirmed risk with + New Project (Section 68) existing at
-- all now: Sales creates a project the moment a deal starts, Service
-- creates one when a site visit happens, whoever processes an
-- uploaded document creates a third when nothing matches on a quick
-- look — three project_id rows for one real project, nobody's fault
-- specifically, just three people entering data independently with no
-- way to see what already exists. Exactly the same shape as the
-- materials duplicate problem (Section 60): prevention is a workflow
-- change (fuzzy-search before creating), repair is a schema gap that
-- needs a real column.

-- Prevention, no schema change: New Project should fuzzy-match the
-- typed customer/company name against existing customers.name/aliases
-- (Section 39) and the typed site address against existing
-- projects.site_address before creating anything, surfacing "does
-- this match an existing project?" the same AI-suggests/human-confirms
-- way aliases already works everywhere else in this schema. If
-- confirmed as the same project, nothing new is created — the person
-- just navigates to the existing one instead.

alter table projects add column merged_into_project_id uuid references projects(project_id);

create index on projects (merged_into_project_id);

-- Repair, one new column, same pattern as materials.merged_into_material_id
-- (0023): an audit trail, not a live redirect other queries need to
-- know about. The merge itself is an application-level operation, done
-- once, when someone confirms two project rows are the same real
-- project:
--   1. Re-point every project_id foreign key from the duplicate to the
--      surviving project_id — documents, boms, material_transactions,
--      project_costs, project_milestones, project_external_references,
--      sales_invoices, financial_obligations, delivery_challans,
--      commissioning_reports, and any project-linked purchase_orders.
--      All history stays intact under one project_id, not split across
--      two or three.
--   2. Merge whatever the duplicate rows knew that the survivor didn't
--      (a consumer number entered on one, a DISCOM entered on
--      another) onto the surviving row.
--   3. Set merged_into_project_id on the now-empty duplicate row(s),
--      pointing at the survivor.
-- Everything downstream (project_confirmed_bom, project_margin,
-- material_requirement, every view keyed on project_id) keeps working
-- unchanged once the foreign keys are re-pointed — no view needs to
-- know merges exist. merged_into_project_id only exists so the
-- Projects list (and the New Project fuzzy-search above) can filter
-- merged rows out (where merged_into_project_id is null), and so
-- anyone auditing later can see why a project_id that once existed no
-- longer shows up as selectable.
