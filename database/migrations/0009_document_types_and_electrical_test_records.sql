-- NRG SolarConnect — Document Type Taxonomy Fallout
-- Follows 0002-0008. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 36. Assembling the full document_type reference list out of
-- Sections 22-25's real examples surfaced three genuine schema gaps —
-- this migration is those three, not the taxonomy itself (document_type
-- stays free text, an app-level reference list, same as always).

-- ============================================================
-- documents.project_id must be nullable
-- ============================================================

-- A latent bug, not new scope: warehouse-level purchase documents
-- (material_transactions rows with project_id null, since 0002) and
-- direct-sale invoices (0008) both legitimately have no project, but
-- documents.project_id has been not null since 0002 — meaning neither
-- could actually be stored. Mirrors the sales_invoices.project_id fix
-- from 0008.

alter table documents alter column project_id drop not null;

-- ============================================================
-- Electrical Test Records (CEIG)
-- ============================================================

-- Section 22 flagged the Test Inspection Application + CEI Approval /
-- Inspection Report pair as genuinely measurable, fixed-shape facts —
-- a strong candidate for a small dedicated table rather than generic
-- AI Facts rows. Section 23 adds that the same File No. links the
-- application and its response, and that issuing authority varies
-- (regional vs. Chief Electrical Inspector) rather than being fixed.

create table electrical_test_records (
  electrical_test_record_id  uuid primary key default gen_random_uuid(),
  project_id                  uuid not null references projects(project_id),
  file_no                      text,     -- shared CAF-style ID linking the application and its response, e.g. "TestInspection-D-BRD-..."
  consumer_number               text,
  application_document_id        uuid references documents(document_id),  -- the Test Inspection Application
  report_document_id              uuid references documents(document_id), -- the CEIG Approval Letter / Inspection Report
  inspection_date                  date,
  issuing_authority                 text,   -- e.g. "Chief Electrical Inspector - Gandhinagar" vs a regional office; free text, not fixed
  megger_r_y                        numeric(10,3),
  megger_y_b                        numeric(10,3),
  megger_r_b                        numeric(10,3),
  megger_ryb_earth                  numeric(10,3),
  earth_pit_resistance               numeric(10,3)[],  -- one value per pit, typically 4
  contractor_license_no              text,
  supervisor_license_no              text,
  status                              text check (status in ('satisfactory','unsatisfactory','pending')),
  remarks                             text,
  ai_confidence                       numeric(3,2),
  extraction_status                   text not null default 'ai_extracted'
                                       check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at                          timestamptz not null default now()
);

create index on electrical_test_records (project_id);
create index on electrical_test_records (file_no);

-- status feeds the CEIG track's completion milestone in project_milestones
-- (Section 21/32) — 'satisfactory' is the trigger event, same role the
-- GEDA Registration Letter plays for the geda_registration track.

-- ============================================================
-- Panel batch tracking: DCR/NDCR flag, batch ref no., replacement traceability
-- ============================================================

-- Section 24: NRG's internal "Solar Panel Ref List"/"Inverter Ref List"
-- logs track Domestic Content Requirement status per purchase batch
-- (government-scheme eligibility) and a sequential batch identifier
-- (fiscal-year + type-letter + sequence, e.g. "18-19-P-01") — neither
-- field existed on material_transactions before this.

alter table material_transactions
  add column dcr_ndcr_status text check (dcr_ndcr_status in ('dcr','ndcr','not_applicable'));
alter table material_transactions
  add column batch_ref_no text;

-- Also from Section 24: at least one real warranty replacement was found
-- where a new serial supersedes a failed one against the same project.
-- serial_numbers (0003) records what's on a transaction but not that it
-- replaces an earlier one — this closes that gap.

alter table material_transactions
  add column replaces_transaction_id uuid references material_transactions(transaction_id);

create index on material_transactions (replaces_transaction_id);
