-- NRG SolarConnect — Havells Heat Pump Quotes
-- Follows 0002-0040. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 84.
--
-- Source: the complete, literal Apps Script backend (`HHP-GAS-v5.1`, all
-- ~140 lines — doPost/doGet/toNum/saveHHPQuote/generatePDF/
-- generateHHPQuoteNo/getQuotes/jsonResp) pasted directly by the owner
-- after the script's own Drive link couldn't be opened, plus the live
-- `HHP_QUOTES` sheet's real header row and several real rows (confirmed
-- via Drive full-text search of spreadsheet 1A4_WmWF...), plus the
-- quoting frontend `havells_quote_v2.html` (nrg-cover, read in full) for
-- the Client Type / salesperson / product-catalog values the backend
-- itself only ever receives as opaque strings.
--
-- ============================================================
-- THE CONFIRMED LIVE BUG — this migration exists partly to fix it
-- ============================================================
-- saveHHPQuote() always returns `{ ok: true, quoteNo, pdfUrl }`, even
-- when PDF generation fails. On failure, pdfUrl is set to the literal
-- string 'PDF generation failed: ' + err.message and written into the
-- sheet's "PDF URL" column — verified directly against live data: real
-- rows in HHP_QUOTES contain values like 'PDF generation failed: You do
-- not have permission to call DriveApp.getRootFolder...' sitting exactly
-- where a Drive link should be. Sales staff have no reliable way to tell
-- a quote's PDF doesn't exist without opening the row and reading it as
-- English text. This schema makes that structurally impossible: success
-- and failure are two different columns (pdf_drive_file_id vs.
-- pdf_generation_error), never one column doing double duty.
-- ============================================================

-- ============================================================
-- Product catalog — a small dedicated table, not a bolt-on to
-- `materials` (Section 19). Havells units carry attributes (a
-- manufacturer product code, a Split/All-in-One/Commercial type, a
-- capacity that's sometimes litres and sometimes kW) that don't fit
-- materials' BOM-shaped columns (category/canonical_name/default_unit/
-- aliases) without adding columns meaningless to every solar BOM row.
-- No natural anchor-table FK either, so organization_id direct, same
-- reasoning as quote_kw_band_rates and referral_contacts.
-- ============================================================

create table havells_products (
  product_id        uuid primary key default gen_random_uuid(),
  organization_id   uuid not null references organizations(organization_id),
  product_code      text not null,   -- manufacturer SKU, e.g. 'GHWAPHSWS300'
  product_name      text not null,   -- e.g. 'HP30 Split 300L'
  product_type      text not null check (product_type in ('split','all_in_one','commercial')),
  capacity_label    text,            -- e.g. '300L' or '18kW' — units genuinely differ by type, kept as the one label rather than two mutually-exclusive numeric columns
  mrp               numeric(12,2) not null,
  active            boolean not null default true,
  created_at        timestamptz not null default now(),
  unique (organization_id, product_code)
);

-- ============================================================
-- Quotes — customer_id reuses the shared `customers` anchor (0002)
-- instead of the live sheet's raw clientName/phone/email/address
-- columns, same upgrade already made for solar Quotes (0036): one
-- customer record across every module a person touches, not a
-- disconnected copy per tool. The live system has no customer-matching
-- step at all — every historical row will need one done at import time,
-- same as quotes.imported_from_legacy already anticipates.
-- ============================================================

create table havells_quotes (
  havells_quote_id      uuid primary key default gen_random_uuid(),
  quote_number           text not null unique,   -- 'HHP-001' etc — from next_document_number('havells_quote', 'perpetual'); see note below on why fiscal_year is a constant here
  customer_id             uuid not null references customers(customer_id),
  client_type              text not null check (client_type in ('residential','commercial','hotel_hospitality','hospital_institution','industrial')),
  salesperson_id            uuid not null references employees(employee_id),
  discount_pct               numeric(5,2) not null default 0,   -- as entered by the salesperson; NOT reverse-derivable from mrp vs. unit_price (confirmed against real data — the two don't reconcile by a simple formula), so stored as given rather than guessed at
  commission                  numeric(12,2) not null default 0,
  transport                    numeric(12,2) not null default 0,
  lifting                       numeric(12,2) not null default 0,
  pdf_drive_file_id              text,   -- null until a PDF genuinely exists. NEVER an error string — see banner above
  pdf_generation_error            text,  -- null on success; the real error message on failure, in its own column
  status                           text not null default 'quoted' check (status in ('quoted','converted','lost')),
  notes                             text,
  imported_from_legacy               boolean not null default false,
  created_by                          uuid references employees(employee_id),
  created_at                           timestamptz not null default now()
);

create index on havells_quotes (customer_id);
create index on havells_quotes (salesperson_id);
create index on havells_quotes (status);

-- next_document_number()'s primary key is (series_name, fiscal_year)
-- (0010/Section 37). The live HHP-NNN sequence never resets — it's a
-- flat scan-for-max-and-increment across the sheet's whole lifetime,
-- confirmed by reading generateHHPQuoteNo() itself. Reusing the existing
-- function with a constant p_fiscal_year ('perpetual') gets the same
-- reuse-not-reinvent benefit (atomic, race-free numbering) without
-- forcing a fiscal-year reset the live series was never designed to have.

-- ============================================================
-- Line items — normalized, not the live "Products (JSON)" blob, same
-- upgrade already made for solar Quote Extras (0036). product_id links
-- to the catalog above when it matches; product_code/product_name are
-- kept as typed regardless, so a legacy or one-off row that doesn't
-- match any catalog entry is never silently dropped.
-- ============================================================

create table havells_quote_line_items (
  line_item_id      uuid primary key default gen_random_uuid(),
  havells_quote_id  uuid not null references havells_quotes(havells_quote_id),
  product_id        uuid references havells_products(product_id),
  product_code      text,
  product_name      text not null,
  unit_price        numeric(12,2) not null,   -- the actual quoted price per unit, already whatever the sales UI's slab/margin logic decided — not re-derived here
  quantity          numeric(10,2) not null default 1,
  created_at        timestamptz not null default now()
);

create index on havells_quote_line_items (havells_quote_id);

-- ============================================================
-- Totals — compute, don't store (the same discipline as
-- customer_quote_rollup, project_warranty_status, amc_contract_status
-- every module so far). Verified against real live rows that this
-- exact arithmetic — product subtotal, + charges, *1.18 for GST — is
-- what the live sheet's own columns already agree with. GST rate is
-- hardcoded at 18% to match the live "GST (18%)" header; it is the one
-- number here that should become a configurable rate if GST on heat
-- pumps ever changes, flagged rather than silently baked in forever.
-- ============================================================

create view havells_quote_totals as
select
  q.havells_quote_id,
  coalesce(sum(li.unit_price * li.quantity), 0) as product_subtotal,
  (q.commission + q.transport + q.lifting) as charges_subtotal,
  coalesce(sum(li.unit_price * li.quantity), 0) + (q.commission + q.transport + q.lifting) as taxable_amount,
  round((coalesce(sum(li.unit_price * li.quantity), 0) + (q.commission + q.transport + q.lifting)) * 0.18, 2) as gst_amount,
  round((coalesce(sum(li.unit_price * li.quantity), 0) + (q.commission + q.transport + q.lifting)) * 1.18, 2) as grand_total
from havells_quotes q
left join havells_quote_line_items li on li.havells_quote_id = q.havells_quote_id
group by q.havells_quote_id, q.commission, q.transport, q.lifting;

-- ============================================================
-- Entitlement — its own module_key, not folded into 'sales_quotes'.
-- Havells Quotes is a genuinely independent live Apps Script deployment
-- (own spreadsheet, own Drive folder, own Railway PDF microservice) with
-- a product-line audience (Havells heat pumps) that most white-label
-- solar-EPC customers of this platform won't carry at all — same
-- "separate live deployment gets a separate boundary" reasoning already
-- applied to Quote Generator vs. Sales Follow-up (Section 79).
-- ============================================================

insert into module_entitlements (organization_id, module_key, tier) values
  ('00000000-0000-0000-0000-000000000001', 'havells_quotes', 'advanced');
