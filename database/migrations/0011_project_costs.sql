-- NRG SolarConnect — Lightweight Cost Tracking for Non-Material Bills
-- Follows 0002-0010. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 38. Vendor and transport bills usually don't mention a
-- project at all, so AI content-matching (the rule used everywhere
-- else for document-to-project linking) has nothing to match against —
-- MP has to assign these by hand, and sometimes there's genuinely no
-- single project to assign to (one transport bill covering several
-- residential dispatches on the same truck). This is capture only —
-- no margin/profitability view is built here, that stays deferred
-- until margin itself is properly defined.

create table project_costs (
  project_cost_id     uuid primary key default gen_random_uuid(),
  project_id           uuid references projects(project_id),   -- set once assigned; null while unassigned or deliberately general
  cost_type             text not null,   -- free text, app-level reference list: 'vendor_bill' | 'transport' | 'fabrication' | 'installation_subcontract' | 'other'
  vendor_id              uuid references partners(partner_id),
  amount                  numeric(14,2) not null,
  bill_date                 date,
  source_document_id          uuid references documents(document_id),  -- the vendor/transport bill itself
  assignment_status              text not null default 'unassigned'
                                  check (assignment_status in ('unassigned','assigned','general')),
  assigned_by                     uuid references employees(employee_id),
  assigned_at                      timestamptz,
  notes                             text,   -- e.g. "covers 3 residential dispatches on the same truck, left general"
  created_at                         timestamptz not null default now()
);

create index on project_costs (project_id);
create index on project_costs (assignment_status);

-- Same shape as every other AI-can't-fully-resolve-this pattern already
-- in the schema (payment_receipts.match_status, reorder_alerts,
-- drive_folder_import_candidates): a bill lands as 'unassigned' and
-- sits on MP's Pending board until MP either sets project_id and flips
-- it to 'assigned', or deliberately flips it to 'general' with a note.
-- 'general' and 'unassigned' are deliberately different states —
-- collapsing them into one null-project_id value would make it
-- impossible to tell "still pending" from "resolved as general."
