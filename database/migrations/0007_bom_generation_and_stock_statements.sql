-- NRG SolarConnect — BOM Generation Origin Tracking and Monthly Stock Statements
-- Follows 0002-0006. Consolidated from docs/nrg-solarconnect-handover.md
-- Sections 33-34. Sheet-driven BOM generation for standard systems (rates
-- from Tally, quantity formulas stay in NRG's private SPP sheet — the
-- exact input/output cell contract is deferred, mapped in a later
-- session) and the monthly bank-facing stock statement.

-- ============================================================
-- BOM generation origin + Tally live-sync marker
-- ============================================================

alter table boms add column origin text not null default 'uploaded_workbook'
  check (origin in ('uploaded_workbook','system_calculated'));
alter table boms add column generation_inputs jsonb;
  -- the driver values sent to the sheet: panel_count, rows, frame_length_ft,
  -- structure_height_ft, legs_per_frame, string_count, etc. Only set when
  -- origin = 'system_calculated'.

-- boms.source_document_id stays not null even for a calculated BOM — once
-- approved, the system generates a clean printable output and logs that as
-- the Document, so "documents are the source of truth" holds with no
-- exception. Approval reuses the existing extraction_status/confirmed_by/
-- confirmed_at columns on boms unchanged; a calculated BOM just starts in
-- 'ai_extracted' like any other.

alter table tally_ledger_entries add column sync_source text not null default 'manual_upload'
  check (sync_source in ('manual_upload','tally_live_sync'));

-- source_document_id on tally_ledger_entries was already nullable (0006) —
-- exactly right here, since a live-synced entry has no uploaded document.

-- ============================================================
-- Monthly Stock Statement
-- ============================================================

create table stock_statements (
  stock_statement_id  uuid primary key default gen_random_uuid(),
  statement_period     date not null,    -- the period-end date this statement represents, e.g. 2026-06-30
  status                text not null default 'draft' check (status in ('draft','finalized')),
  finalized_by           uuid references employees(employee_id),
  finalized_at            timestamptz,
  source_document_id      uuid references documents(document_id),  -- the PDF actually submitted to the bank, once generated
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (statement_period)
);

create table stock_statement_items (
  stock_statement_item_id  uuid primary key default gen_random_uuid(),
  stock_statement_id        uuid not null references stock_statements(stock_statement_id),
  material_id                 uuid not null references materials(material_id),
  book_quantity                 numeric(14,3) not null,   -- system-computed as of statement_period, via material_stock_as_of below
  physical_quantity             numeric(14,3),             -- entered after the physical count; null until counted
  declared_quantity             numeric(14,3) not null,    -- what actually goes on the statement — editable, the final word
  rate                          numeric(14,2) not null,    -- valuation rate as of statement_period, from real purchase history (Tally-fed)
  notes                         text,                       -- why declared differs from book, if it does
  created_at                    timestamptz not null default now(),
  updated_at                    timestamptz not null default now(),
  unique (stock_statement_id, material_id)
);

create index on stock_statement_items (stock_statement_id);
create index on stock_statement_items (material_id);

-- declared_quantity is deliberately plain and always-editable, not derived —
-- defaults to the physical count once one exists, but stays overridable
-- with a note, since the person signing off on a bank submission needs the
-- final say.

-- ============================================================
-- Point-in-time stock and valuation lookups
-- ============================================================

-- material_stock (0003) has no date parameter — it always means "now." A
-- statement for June generated a week into July, built off the live view,
-- would silently include July's transactions. These two functions fix that.

create function material_stock_as_of(as_of_date date)
returns table(material_id uuid, current_stock numeric) as $$
  select
    material_id,
    coalesce(sum(quantity) filter (where movement_type = 'purchased'), 0)
      - coalesce(sum(quantity) filter (where movement_type = 'issued_to_site'), 0)
      + coalesce(sum(quantity) filter (where movement_type = 'returned_to_warehouse'), 0)
  from material_transactions
  where transaction_date <= as_of_date
  group by material_id;
$$ language sql stable;

create function material_weighted_avg_rate_as_of(p_material_id uuid, as_of_date date)
returns numeric as $$
  select weighted_avg_rate
  from material_purchase_running_avg
  where material_id = p_material_id and transaction_date <= as_of_date
  order by transaction_date desc, transaction_id desc
  limit 1;
$$ language sql stable;

-- material_weighted_avg_rate_as_of mirrors the LATERAL-join logic
-- material_transaction_cost (0005) already uses for costing — same
-- weighted-average machinery, reused for stock valuation instead of BOM
-- cost variance.

-- ============================================================
-- Stock group rollup + month-over-month comparison
-- ============================================================

alter table materials add column stock_group text;
  -- coarse rollup for statements/reporting, distinct from materials.category
  -- (the ~15 BOM engineering categories): 'panels' | 'inverters' | 'cables' |
  -- 'hardware' | 'electrical_accessories' | 'safety' | 'other'

create view stock_statement_summary as
select
  ss.statement_period, ss.status,
  m.stock_group, m.category, m.material_id, m.canonical_name,
  ssi.declared_quantity, ssi.rate, ssi.declared_quantity * ssi.rate as amount
from stock_statement_items ssi
join stock_statements ss on ss.stock_statement_id = ssi.stock_statement_id
join materials m on m.material_id = ssi.material_id;

-- "Panels in June vs. August" is stock_group = 'panels', two
-- statement_period values, one filtered query against this view — no
-- special comparison logic needed.
