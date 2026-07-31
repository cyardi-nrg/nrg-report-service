-- ProjectPulse core schema
-- Consolidated from docs/projectpulse-handover.md (Sections 5, 19, 21, 23, 27)
-- as of the "ProjectPulse architecture handover" design session.
--
-- Run this after 0001_init.sql (auth/profiles). Tables are ordered by
-- foreign-key dependency so this applies cleanly top to bottom.
--
-- NOT included here (still design-in-progress — see the handover doc's
-- "Next Session" list): financial_obligations, project_milestones,
-- vendor_quotes, sales_documents, electrical_test_records. Nothing below
-- has a hard FK dependency on those, so this migration is self-contained.

create extension if not exists pgcrypto;

-- ============================================================
-- Master tables (no dependencies)
-- ============================================================

create table employees (
  employee_id   uuid primary key default gen_random_uuid(),
  name          text not null,
  role          text,             -- e.g. 'Sales Person', 'Electrical Supervisor'
  phone         text,
  email         text,
  license_no    text,             -- e.g. the Electrical Supervisor permit no. seen on drawing sign-offs
  active        boolean not null default true,
  created_at    timestamptz not null default now()
);

create table partners (
  partner_id      uuid primary key default gen_random_uuid(),
  name            text not null,
  category        text not null,   -- 'fabricator' | 'electrician' | 'civil_contractor' | 'transporter' | 'design_consultant' | 'vendor' | 'other'
                                     -- free text, not a hard enum, same reasoning as bom_items.category below
  contact_number  text,
  email           text,
  gstin           text,
  address         text,
  created_at      timestamptz not null default now()
);

create table customers (
  customer_id             uuid primary key default gen_random_uuid(),
  name                    text not null,          -- Applicant Name / company name, as it appears on documents
  customer_type           text not null default 'individual' check (customer_type in ('individual','company')),
  gstin                   text,
  pan                     text,
  address                 text,
  area                    text,                    -- e.g. "Bharuch", "Karelibaug"
  google_maps_link        text,
  email                   text,
  primary_contact_number  text,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create table materials (
  material_id     uuid primary key default gen_random_uuid(),
  category        text not null,          -- e.g. Structure, Cabling, Panels, Inverter, Safety System
  canonical_name  text not null,          -- normalized name, e.g. "DC Cable 4 sq mm"
  default_unit    text not null,          -- e.g. Meter, Nos, Kg, Sq.Meter
  aliases         text[],                 -- raw name variants AI has seen across BOMs/invoices, for matching
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (category, canonical_name)
);

-- ============================================================
-- Customer_Contacts (depends on customers)
-- ============================================================

create table customer_contacts (
  contact_id    uuid primary key default gen_random_uuid(),
  customer_id   uuid not null references customers(customer_id),
  name          text not null,
  role          text not null,   -- 'owner' | 'purchase' | 'electrical' | 'accounts' | 'maintenance' | 'other' — free text
  phone         text,
  email         text,
  is_primary    boolean not null default false,
  created_at    timestamptz not null default now()
);

create index on customer_contacts (customer_id);

-- ============================================================
-- Projects (depends on customers, employees)
-- ============================================================

create table projects (
  project_id              uuid primary key default gen_random_uuid(),
  customer_id             uuid not null references customers(customer_id),
  site_address            text,
  project_type            text not null check (project_type in ('residential_subsidy','commercial_industrial')),
  status                  text not null default 'active'
                           check (status in ('active','commissioned','on_hold','cancelled')),
                           -- a coarse lifecycle flag only — physical/regulatory progress will live in project_milestones (not yet defined)
  discom                  text,          -- utility name, e.g. "MGVCL"
  division                text,          -- DISCOM sub-division
  sales_person_id         uuid references employees(employee_id),
  google_drive_folder_id  text unique,   -- the durable link to the project's Drive folder; null until linked or auto-created
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now()
);

create index on projects (customer_id);

-- consumer_number deliberately isn't a column — it's a project_external_references
-- row (reference_type = 'discom_consumer_number') instead, since a project carries
-- multiple independently-issued external reference numbers, not one fixed field.
--
-- Monitoring-portal credentials do NOT get a column here — route them through the
-- application's secrets manager (e.g. Supabase Vault), never a plaintext column.

-- ============================================================
-- Documents (depends on projects, employees)
-- ============================================================

create table documents (
  document_id             uuid primary key default gen_random_uuid(),
  project_id              uuid not null references projects(project_id),
  google_drive_file_id    text not null unique,
  document_type           text,          -- free text, AI-classified; nullable until classified
  version                 integer not null default 1,   -- a re-issued drawing/document is a new version, not an overwrite
  supersedes_document_id  uuid references documents(document_id),
  uploaded_by             uuid references employees(employee_id),
  upload_date             timestamptz not null default now(),
  ai_status                text not null default 'pending'
                            check (ai_status in ('pending','processing','extracted','failed','confirmed')),
  ai_confidence            numeric(3,2),
  created_at               timestamptz not null default now()
);

create index on documents (project_id);
create index on documents (document_type);

-- ============================================================
-- Project_External_References (depends on projects)
-- ============================================================

create table project_external_references (
  reference_id    uuid primary key default gen_random_uuid(),
  project_id      uuid not null references projects(project_id),
  reference_type  text not null
                   check (reference_type in ('nrg_internal','discom_consumer_number','geda_residential','geda_commercial','ceig')),
  reference_value text not null,
  created_at      timestamptz not null default now(),
  unique (reference_type, reference_value)
);

-- ============================================================
-- Drive_Folder_Import_Candidates (depends on projects, employees)
-- Staging/review queue for linking NRG's ~300 existing Drive project
-- folders — resolving a candidate is the only thing that writes to
-- projects.google_drive_folder_id for pre-existing folders.
-- ============================================================

create table drive_folder_import_candidates (
  candidate_id              uuid primary key default gen_random_uuid(),
  drive_folder_id           text not null unique,
  drive_folder_name         text not null,
  drive_parent_id           text not null,
  suggested_project_id      uuid references projects(project_id),    -- AI's best-guess match to an already-linked project
  suggested_customer_name   text,       -- AI's parse of the folder name / first few documents, for the "this is a new project" case
  suggested_kw              numeric(10,3),
  match_confidence          numeric(3,2),
  duplicate_of_candidate_id uuid references drive_folder_import_candidates(candidate_id),
                             -- set when this folder looks like the same project as another candidate (confirmed real duplicates exist today)
  is_project_folder         boolean,    -- AI's guess; false for things like "DRONE PHOTO", "GEB PAYMENT RECEIPT"
  status                    text not null default 'pending'
                             check (status in ('pending','confirmed_new_project','confirmed_existing_project','merged','rejected_not_a_project')),
  reviewed_by               uuid references employees(employee_id),
  reviewed_at               timestamptz,
  created_at                timestamptz not null default now()
);

create index on drive_folder_import_candidates (status);

-- ============================================================
-- Boms (depends on projects, documents, employees)
-- ============================================================

create table boms (
  bom_id                    uuid primary key default gen_random_uuid(),
  project_id                uuid not null references projects(project_id),
  source_document_id        uuid not null references documents(document_id),  -- the uploaded Engineering BOM file
  version                   integer not null default 1,        -- a project may get a revised BOM upload
  panel_wattage             numeric(10,2),      -- e.g. 620 (Wp per panel)
  panel_count               integer,
  kw_capacity               numeric(10,3),      -- panel_count * panel_wattage / 1000
  order_value               numeric(14,2),      -- quoted order value
  estimated_total_cost      numeric(14,2),      -- sum of bom_items.estimated_cost, as extracted
  estimated_margin          numeric(14,2),
  price_per_watt_estimated  numeric(10,2),
  actual_total_cost         numeric(14,2),      -- rolls up from bom_item_variance.actual_cost
  price_per_watt_actual     numeric(10,2),
  person_in_charge          uuid references employees(employee_id),
  sales_person              uuid references employees(employee_id),
  ai_confidence             numeric(3,2),
  extraction_status         text not null default 'ai_extracted'
                             check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at                timestamptz not null default now(),
  updated_at                timestamptz not null default now()
);

create index on boms (project_id);

-- ============================================================
-- BOM_Items (depends on boms, materials, partners, employees)
-- ============================================================

create table bom_items (
  bom_item_id             uuid primary key default gen_random_uuid(),
  bom_id                  uuid not null references boms(bom_id),
  material_id             uuid references materials(material_id),   -- nullable until AI match is confirmed
  category                text not null,      -- one of NRG's ~15 standard categories (Solar Panels, Structure, DC Cable, ...); free text, app-level reference list
  description             text not null,      -- raw text as it appears in the Engineering BOM
  specification            text,
  unit                    text not null,
  calculation_basis        text,               -- raw driver values from the workbook, for traceability only, not recalculated
  preferred_vendor_id       uuid references partners(partner_id),
  planned_quantity         numeric(14,3) not null,
  planned_rate             numeric(14,2) not null,   -- sourced from NRG's rate card at extraction time
  estimated_cost           numeric(14,2) not null,   -- as extracted from the workbook, not recomputed
  ai_confidence            numeric(3,2),       -- 0.00-1.00
  extraction_status        text not null default 'ai_extracted'
                            check (extraction_status in ('ai_extracted','confirmed','corrected')),
  confirmed_by             uuid references employees(employee_id),
  confirmed_at             timestamptz,
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

create index on bom_items (bom_id);
create index on bom_items (material_id);

-- ============================================================
-- Material_Transactions (depends on materials, bom_items, projects, partners, documents)
-- The shared movement ledger for BOM variance tracking AND inventory.
-- ============================================================

create table material_transactions (
  transaction_id      uuid primary key default gen_random_uuid(),
  material_id         uuid not null references materials(material_id),
  bom_item_id         uuid references bom_items(bom_item_id),   -- null for a warehouse purchase not yet tied to a project
  project_id          uuid references projects(project_id),     -- null for warehouse-level purchase; set on issue/return
  movement_type        text not null
                         check (movement_type in ('purchased','issued_to_site','returned_to_warehouse')),
  quantity             numeric(14,3) not null,
  rate                 numeric(14,2),      -- populated for 'purchased'; null for issue/return
  vendor_id            uuid references partners(partner_id),    -- populated for 'purchased'
  transaction_date     date not null,
  source_document_id   uuid not null references documents(document_id),
                         -- Purchase Invoice / Delivery Challan / Material Return Note / Material Out / Material In / Gate Pass
  ai_confidence        numeric(3,2),
  created_at           timestamptz not null default now()
);

create index on material_transactions (material_id);
create index on material_transactions (bom_item_id);
create index on material_transactions (project_id);

-- "Used at Site" quantity is derived as issued_to_site - returned_to_warehouse
-- (no dedicated consumption document exists yet). Actual cost is computed only
-- from 'purchased' transactions directly linked to a bom_item_id; materials
-- drawn from general warehouse stock at a different historical rate need a
-- costing method (weighted-average/FIFO) not yet designed.

-- ============================================================
-- BOM_Item_Variance (derived view — nothing stored)
-- ============================================================

create view bom_item_variance as
select
  b.bom_item_id,
  b.bom_id,
  bm.project_id,
  b.category,
  b.description,
  b.unit,
  b.planned_quantity,
  coalesce(sum(t.quantity) filter (where t.movement_type = 'issued_to_site'), 0)          as dispatched_quantity,
  coalesce(sum(t.quantity) filter (where t.movement_type = 'returned_to_warehouse'), 0)   as returned_quantity,
  coalesce(sum(t.quantity) filter (where t.movement_type = 'issued_to_site'), 0)
    - coalesce(sum(t.quantity) filter (where t.movement_type = 'returned_to_warehouse'), 0)   as used_quantity,
  b.planned_quantity
    - (coalesce(sum(t.quantity) filter (where t.movement_type = 'issued_to_site'), 0)
       - coalesce(sum(t.quantity) filter (where t.movement_type = 'returned_to_warehouse'), 0)) as quantity_variance,
  b.estimated_cost,
  coalesce(sum(t.quantity * t.rate) filter (where t.movement_type = 'purchased'), 0)       as actual_cost,
  coalesce(sum(t.quantity * t.rate) filter (where t.movement_type = 'purchased'), 0) - b.estimated_cost as cost_variance
from bom_items b
join boms bm on bm.bom_id = b.bom_id
left join material_transactions t on t.bom_item_id = b.bom_item_id
group by b.bom_item_id, b.bom_id, bm.project_id, b.category, b.description, b.unit, b.planned_quantity, b.estimated_cost;
