-- NRG SolarConnect — Quote Generator + Sales Follow-up, Rebuilt as One
-- Connected Module
-- Follows 0002-0035. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 79.
--
-- Replaces two live Apps Script projects that today share one Google
-- Sheet with no real API boundary between them (see
-- docs/system-understanding-2026-08-16.md, Sections 1a/1b/4). Built as
-- one migration, not two, specifically because that coupling is real —
-- Quote Generator's Quotes tab is Sales Follow-up's primary data
-- source, live, unmediated. Gated behind module_entitlements (0035)
-- module_key = 'sales_quotes' and 'sales_followup' — two separate
-- entitlement rows since a future tenant might buy one without the
-- other, even though NRG uses both together.
--
-- Deliberately fixes three real bugs found reading the live source,
-- rather than carrying them forward:
--   1. Sales Follow-up's CEO-discount path read Quote Generator's
--      spreadsheet by hardcoded column position — a normal table with
--      named columns makes that whole bug class impossible.
--   2. "Historical" (2020-2021 bulk-imported quotes) and live Quotes
--      were two tabs, read two different fragile ways by the two
--      projects. Here they're the same table, same columns, always.
--   3. Deal Status (per-quote)/Temperature (per-customer)/Follow-up
--      Status (per-customer) were three overlapping vocabularies with
--      no reconciliation. Kept as three real, distinct concepts here
--      too (they answer different questions), but each lives in
--      exactly one place, named so the difference is obvious.

-- ============================================================
-- Leads — a raw inbound inquiry, before it's ever been quoted
-- ============================================================

create table leads (
  lead_id         uuid primary key default gen_random_uuid(),
  customer_id     uuid references customers(customer_id),   -- set once matched/created; nullable until then
  raw_name        text not null,      -- as typed at capture time, before any customer match
  raw_phone       text not null,
  source          text,               -- free text: 'referral' | 'website' | 'walk-in' | ... — app-level reference list
  status          text not null default 'new' check (status in ('new','quoted','not_interested')),
  quote_id        uuid,               -- set by markLeadQuoted equivalent once this lead's first quote exists; FK added below, quotes doesn't exist yet at this point in the file
  assigned_to     uuid references employees(employee_id),
  created_by      uuid references employees(employee_id),
  created_at      timestamptz not null default now()
);

create index on leads (customer_id);
create index on leads (status);

-- ============================================================
-- Customer Pipeline — the CRM/sales-tracking state of a customer,
-- kept OUT of the core `customers` table on purpose. A tenant without
-- the sales_followup module enabled has no reason for these columns
-- to exist on every customer row; this way they simply have no rows
-- here at all. One row per customer that Sales has ever engaged with.
-- ============================================================

create table customer_pipeline (
  customer_id         uuid primary key references customers(customer_id),
  temperature          text not null default 'warm' check (temperature in ('hot','warm','cold')),
  follow_up_status      text not null default 'active'
                         check (follow_up_status in ('active','won','lost','won_pending_advance','not_interested')),
  stage                  integer not null default 1,   -- numeric pipeline stage; stage *labels* are a UI/app concern, not schema
  last_follow_up_date     date,
  call_count               integer not null default 0,
  whatsapp_count            integer not null default 0,
  visit_count                integer not null default 0,
  last_contacted_by           uuid references employees(employee_id),
  updated_at                   timestamptz not null default now()
);

-- Times Quoted / Latest Quote — deliberately NOT columns here. Same
-- "compute, don't store" discipline as bom_category_cost (Section 59)
-- and everywhere else in this schema: the live system stored these on
-- the Clients tab and they could drift from the real Quotes data
-- (confirmed real risk, Section 79/system-understanding doc). See
-- customer_quote_rollup view below — always live, never stale.

-- ============================================================
-- Quote pricing — a real rate table, not a spreadsheet scanned by
-- position (the live system locates wattage bands, brand rows, and
-- KW bands by scanning for magic markers in specific rows/columns —
-- confirmed working today, but a fragile pattern; a normal table with
-- named columns removes that whole class of bug for free).
-- ============================================================

create table quote_panel_rates (
  rate_id        uuid primary key default gen_random_uuid(),
  material_id    uuid not null references materials(material_id),   -- the panel itself, e.g. "Solar Panel 545W · Adani (DCR)" — already exists as a material (Section 19)
  rate_type      text not null check (rate_type in ('DCR','NDCR')),
  rate_per_watt  numeric(10,2) not null,
  updated_by     uuid references employees(employee_id),
  updated_at     timestamptz not null default now(),
  unique (material_id, rate_type)
);

-- This is a SELLING rate (what a quote charges per watt for this
-- panel), not a cost figure — deliberately separate from
-- bom_items.planned_rate (Section 19), which is sourced from actual
-- purchase history. The two numbers answer different questions and
-- must never be confused with each other.

create table quote_kw_band_rates (
  band_id                 uuid primary key default gen_random_uuid(),
  organization_id         uuid not null references organizations(organization_id),
    -- no anchor table to inherit from (Section 78) — this is tenant-level
    -- pricing configuration, not tied to any one project/customer/material
  min_kw                  numeric(10,2) not null,
  max_kw                  numeric(10,2) not null,
  above_panel_rate_per_watt  numeric(10,2) not null default 0,
  margin_rate_per_watt        numeric(10,2) not null default 0,
  discount_rate_per_watt       numeric(10,2) not null default 0,
  updated_at                    timestamptz not null default now(),
  check (max_kw > min_kw)
);

create index on quote_kw_band_rates (organization_id);

-- ============================================================
-- Quotes — replaces both the live "Quotes" tab and "Historical" tab.
-- One table, one shape, always. A no-phone legacy quote just has
-- customer_phone_at_quote null instead of needing a second synthetic
-- key scheme (confirmed real pattern in the live Historical tab,
-- system-understanding doc Section 5).
-- ============================================================

create table quotes (
  quote_id                uuid primary key default gen_random_uuid(),
  quote_number             text not null unique,   -- e.g. 'NRG/26-27/RES/019', from next_document_number(), series_name = 'quote_' || quote_type_code (Section 37/0010, reused as-is)
  customer_id              uuid not null references customers(customer_id),
  salesperson_id            uuid not null references employees(employee_id),
  quote_type                 text not null check (quote_type in ('residential','apartment_common','extension','commercial_industrial','ndcr')),
  system_size_kw              numeric(10,3) not null,
  panel_material_id             uuid references materials(material_id),
  panel_count                    integer,
  inverter_material_id             uuid references materials(material_id),
  system_type                       text check (system_type in ('1PH','3PH')),
  structure_height_m                 numeric(6,2),
  system_cost                         numeric(14,2) not null,
  structure_cost                       numeric(14,2) not null default 0,
  geda_charge                           numeric(14,2) not null default 0,
  meter_charge                           numeric(14,2) not null default 0,
  strengthening_charge                    numeric(14,2) not null default 0,
  discount_per_kw                          numeric(10,2) not null default 0,
  discount_amount                           numeric(14,2) not null default 0,
  gross_cost                                 numeric(14,2) not null,
  subsidy                                     numeric(14,2) not null default 0,
  customer_payable                             numeric(14,2) not null,
  payment_terms                                 text,
  document_requirements                          text,
  notes                                           text,
  reference_person                                 text,
  quote_time_temperature                            text check (quote_time_temperature in ('hot','warm','cold')),
    -- how the deal felt AT THE MOMENT this quote was made — a real,
    -- separate signal from customer_pipeline.temperature (the
    -- customer's CURRENT state), not a duplicate of it. Deliberately
    -- does NOT auto-write customer_pipeline.temperature — the live
    -- system's "every re-quote silently bumps Cold to Warm and blanks
    -- Last Follow-up Date" behaviour is exactly the kind of silent
    -- side effect this schema's discipline argues against elsewhere
    -- (Section 64/68's "missing cost must never silently read as
    -- zero" principle, same reasoning applied to CRM state: a
    -- customer's temperature must never change without a visible,
    -- attributable action).
  sp_discount                                       numeric(14,2),   -- CEO-only override, see below
  sp_discount_set_by                                 uuid references employees(employee_id),
  sp_discount_set_at                                  timestamptz,
  generated_document_id                                uuid references documents(document_id),   -- the quote PDF, an ordinary Document like every other generated document
  imported_from_legacy                                  boolean not null default false,   -- true for rows carried over from the old "Historical" tab, so provenance is never lost even though the shape is identical
  created_by                                             uuid references employees(employee_id),
  created_at                                              timestamptz not null default now()
);

create index on quotes (customer_id);
create index on quotes (salesperson_id);
create index on quotes (quote_type);

alter table leads add constraint leads_quote_id_fkey foreign key (quote_id) references quotes(quote_id);

-- CEO-only special discount: sp_discount/sp_discount_set_by/
-- sp_discount_set_at are a real, distinct override from
-- discount_per_kw/discount_amount above (the ordinary salesperson
-- discount, capped only client-side today, ₹4,000/kW — that cap
-- belongs in the application layer alongside real RLS, not schema).
-- Setting sp_discount should regenerate the quote PDF as a NEW
-- documents row with documents.supersedes_document_id pointing at the
-- prior one (Section 19's existing version/supersedes pattern,
-- reused as-is — no new versioning concept needed) and
-- generated_document_id repointed at the new row. The old PDF and its
-- link stay exactly as issued — never edited or deleted in place,
-- same "never break a link someone already has" discipline as
-- everywhere else this session.

-- ============================================================
-- Quote Extras — normalized, not a JSON blob (Extra Panels/Inverter/
-- Cabling/Walkway/Handrail/Safety Line/Other in the live payload)
-- ============================================================

create table quote_extras (
  quote_extra_id  uuid primary key default gen_random_uuid(),
  quote_id        uuid not null references quotes(quote_id),
  name            text not null,        -- e.g. 'Extra Panels', 'Cabling', 'Other' — free text
  quantity        numeric(14,3),
  rate            numeric(14,2),
  amount          numeric(14,2) not null,
  details         text,
  is_lump_sum     boolean not null default false
);

create index on quote_extras (quote_id);

-- ============================================================
-- Customer Activity Log — one unified log, replacing the live system's
-- two disconnected logging paths (a call/WA/visit tap from the
-- Sales Follow-up dashboard vs. a "Share on WhatsApp" tap from Quote
-- Generator itself never touching the same log — confirmed real gap,
-- system-understanding doc §3 "WhatsApp"). Every touch, from either
-- surface, writes here.
-- ============================================================

create table customer_activity_log (
  activity_id     uuid primary key default gen_random_uuid(),
  customer_id     uuid not null references customers(customer_id),
  salesperson_id  uuid not null references employees(employee_id),
  action          text not null check (action in ('call','whatsapp','visit','quote_generated','stage_change','temperature_change','status_change')),
  detail          text,
  quote_id        uuid references quotes(quote_id),
  created_at      timestamptz not null default now()
);

create index on customer_activity_log (customer_id);
create index on customer_activity_log (created_at);

-- ============================================================
-- Sales Targets
-- ============================================================

create table sales_targets (
  target_id       uuid primary key default gen_random_uuid(),
  salesperson_id  uuid not null references employees(employee_id),
  period_start    date not null,
  period_end      date not null,
  target_amount   numeric(14,2),
  target_calls    integer,
  target_quotes   integer,
  created_by      uuid references employees(employee_id),
  created_at      timestamptz not null default now(),
  unique (salesperson_id, period_start, period_end)
);

-- ============================================================
-- Views — computed, never stored (same discipline as bom_category_cost, Section 59)
-- ============================================================

create view customer_quote_rollup as
select
  q.customer_id,
  count(*)                                          as times_quoted,
  max(q.created_at)                                  as last_quote_at,
  (array_agg(q.quote_id order by q.created_at desc))[1]  as latest_quote_id
from quotes q
group by q.customer_id;

-- Replaces the live system's stored Times Quoted / Latest Quote URL
-- columns on the Clients tab — always current, can never drift from
-- the real Quotes data the way a cached column can.

create view salesperson_daily_activity as
select
  a.salesperson_id,
  date(a.created_at)   as activity_date,
  count(*) filter (where a.action = 'call')              as calls,
  count(*) filter (where a.action = 'whatsapp')           as whatsapp_sent,
  count(*) filter (where a.action = 'visit')               as visits,
  count(*) filter (where a.action = 'quote_generated')      as quotes_generated
from customer_activity_log a
group by a.salesperson_id, date(a.created_at);

-- Direct replacement for buildDailyReport_ in the live Sales Follow-up
-- backend — same numbers, computed live instead of assembled by hand
-- on every request.

-- ============================================================
-- What this migration does NOT do
-- ============================================================
-- No OCR/business-card-scan handling (an integration concern, not a
-- schema one — the extracted fields land in the same `quotes`/
-- `leads` columns either way, confirmed by the field shapes the live
-- OCR proxy already returns). No WhatsApp/email sending logic (deep
-- links and Gmail compose links are generated at the application
-- layer from data already here). No RLS yet — same standing item as
-- 0035; this migration's tables are shaped so that "a salesperson
-- sees only their own leads/quotes/customers unless role is CEO/Sales
-- Head" (Section 68's row-level rule, still open) can be written
-- correctly once RLS itself is designed.
