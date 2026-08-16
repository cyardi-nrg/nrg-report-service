-- NRG SolarConnect — Documents the System Generates: Delivery Challans and
-- Commissioning Reports
-- Follows 0002-0009. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 37. Confirmed priority: Delivery Challan is the most critical
-- of these (today's real daily pain — without it nobody has a reliable
-- answer to "what do I send, and how much"); Commissioning Report matters
-- too but works differently (generated, then hand-filled on-site, then
-- re-read, not purely generated). BOM generation already has its schema
-- (Section 33 / migration 0007). PO generation and financial/margin
-- reporting are explicitly deferred — not built here.

-- ============================================================
-- Controlled document numbering — reusable across series
-- ============================================================

create table document_number_sequences (
  series_name   text not null,
  fiscal_year   text not null,
  last_number   integer not null default 0,
  primary key (series_name, fiscal_year)
);

create function next_document_number(p_series text, p_fiscal_year text)
returns integer as $$
  insert into document_number_sequences (series_name, fiscal_year, last_number)
  values (p_series, p_fiscal_year, 1)
  on conflict (series_name, fiscal_year)
  do update set last_number = document_number_sequences.last_number + 1
  returning last_number;
$$ language sql;

-- Fiscal-year-scoped, matching NRG's own real numbering convention
-- (e.g. NRG/24-25/xxx). Reusable for Purchase Orders or any other
-- system-generated series later without new schema — just a new
-- series_name.

-- ============================================================
-- Delivery Challans
-- ============================================================

create table delivery_challans (
  delivery_challan_id    uuid primary key default gen_random_uuid(),
  dc_number              text not null unique,   -- e.g. 'DC/26-27/00042', built from next_document_number()
  project_id             uuid not null references projects(project_id),
  dispatch_date          date not null default current_date,
  vehicle_or_driver      text,
  status                 text not null default 'issued' check (status in ('issued','cancelled')),
  total_value            numeric(14,2),          -- for the e-way bill threshold check
  eway_bill_number       text,                    -- movement above ₹50,000 needs one — flag at generation time, fill in once raised
  generated_document_id  uuid references documents(document_id),  -- the generated PDF, logged as a Document like any other
  created_by             uuid references employees(employee_id),
  created_at             timestamptz not null default now()
);

create index on delivery_challans (project_id);

alter table material_transactions
  add column delivery_challan_id uuid references delivery_challans(delivery_challan_id);

create index on material_transactions (delivery_challan_id);

-- material_transactions.source_document_id stays not null either way —
-- for a system-generated DC it points at the same generated_document_id;
-- for a rare paper-book fallback (still handwritten, still scanned) it
-- points at the scanned document and delivery_challan_id stays null.
-- That null/not-null split is the whole signal for generated-vs-manual —
-- no separate flag needed. If the fallback book stays in use for
-- outages, give it a distinct series_name
-- ('delivery_challan_manual_fallback') so its numbers never collide with
-- system-generated ones.

-- ============================================================
-- Commissioning Reports
-- ============================================================

create table commissioning_reports (
  commissioning_report_id  uuid primary key default gen_random_uuid(),
  project_id                uuid not null references projects(project_id),
  template_document_id       uuid references documents(document_id),  -- the system-generated prefilled printout
  filled_document_id          uuid references documents(document_id), -- the re-uploaded scan with handwritten readings
  commissioning_date           date,
  final_ac_capacity_kw          numeric(8,2),
  final_dc_capacity_kw           numeric(8,2),
  technician_name                 text,
  customer_signed                 boolean,
  remarks                          text,
  ai_confidence                    numeric(3,2),
  extraction_status                 text not null default 'ai_extracted'
                                     check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at                        timestamptz not null default now(),
  updated_at                        timestamptz not null default now()
);

create index on commissioning_reports (project_id);

-- Kept separate from electrical_test_records (0009) even though the
-- shape rhymes — different real documents: CEIG's is a government
-- inspection artifact with its own File No. and issuing authority; this
-- is NRG's own internal sign-off that installation is complete and
-- working. A confirmed commissioning report (extraction_status =
-- 'confirmed') is the natural trigger for projects.status moving to
-- 'commissioned' (0002) — wire that up at the application layer.
