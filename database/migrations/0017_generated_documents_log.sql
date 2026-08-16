-- NRG SolarConnect — Generated Documents Log
-- Follows 0002-0016. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 46.

-- ============================================================
-- Two generated-document types were missing their own number
-- ============================================================

-- delivery_challans.dc_number (0010) already uses next_document_number()
-- (0010). purchase_orders and commissioning_reports never got the same
-- treatment — a real gap once "list everything we've generated" is an
-- actual screen, not just a per-project tab. Same series-per-fiscal-year
-- pattern, reusing the function 0010 already built for exactly this.

alter table purchase_orders add column po_number text unique;
alter table purchase_orders add column created_by uuid references employees(employee_id);

alter table commissioning_reports add column cr_number text unique;

-- purchase_orders.created_by was missing outright, not just unnumbered —
-- delivery_challans.created_by already exists (0010), so this brings POs
-- in line rather than leaving "who raised this" unanswerable for one
-- document type but not the others.

-- ============================================================
-- One place to see everything NRG SolarConnect has generated
-- ============================================================

-- Four different tables, four different shapes — a real list needs one
-- common one. A view, not a new table: nothing here is new data, it's
-- exposing rows that already exist in delivery_challans/purchase_orders/
-- commissioning_reports/boms under one shape the UI can page/filter/sort
-- without knowing which underlying table a row came from.

create view generated_documents_log as
select
  'delivery_challan'    as document_type,
  dc.delivery_challan_id as document_id,
  dc.dc_number            as document_number,
  c.name                   as related_to,       -- project/customer name
  dc.dispatch_date          as document_date,
  dc.status                  as status,
  e.name                      as generated_by,
  dc.created_at                as created_at
from delivery_challans dc
join projects p on p.project_id = dc.project_id
join customers c on c.customer_id = p.customer_id
left join employees e on e.employee_id = dc.created_by

union all

select
  'purchase_order'    as document_type,
  po.purchase_order_id as document_id,
  po.po_number           as document_number,
  v.name                   as related_to,       -- vendor name — POs aren't project-scoped
  po.order_date             as document_date,
  po.status                  as status,
  e.name                      as generated_by,
  po.created_at                as created_at
from purchase_orders po
join partners v on v.partner_id = po.vendor_id
left join employees e on e.employee_id = po.created_by

union all

select
  'commissioning_report'      as document_type,
  cr.commissioning_report_id   as document_id,
  cr.cr_number                  as document_number,
  c.name                          as related_to,
  cr.commissioning_date            as document_date,
  cr.extraction_status              as status,     -- ai_extracted / confirmed / corrected
  null                                as generated_by,  -- technician_name is free text, not an employee_id (0010) — nothing to join
  cr.created_at                        as created_at
from commissioning_reports cr
join projects p on p.project_id = cr.project_id
join customers c on c.customer_id = p.customer_id

union all

select
  'bom'                as document_type,
  b.bom_id               as document_id,
  'v' || b.version         as document_number,   -- BOMs version instead of number — one project, revised in place, not a fiscal-year series
  c.name                    as related_to,
  b.created_at::date          as document_date,
  case
    when b.extraction_status <> 'confirmed' then 'pending_review'
    when b.origin <> 'uploaded_workbook' and b.owner_approved_at is null then 'pending_owner_approval'
    else 'approved'
  end                           as status,        -- folds the two-stage gate (0016) into one status instead of exposing three raw columns
  e.name                          as generated_by,
  b.created_at                      as created_at
from boms b
join projects p on p.project_id = b.project_id
join customers c on c.customer_id = p.customer_id
left join employees e on e.employee_id = b.person_in_charge;

-- Deliberately a UNION, not a shared parent table — these four things
-- have almost nothing in common structurally (a BOM has cost columns, a
-- DC has an e-way-bill flag, a PO doesn't even belong to a project) and
-- forcing one table would mean a wall of nullable columns. The view is
-- the "list" the UI actually needs; each row's document_type + document_id
-- is enough to deep-link back into the real record for detail.
