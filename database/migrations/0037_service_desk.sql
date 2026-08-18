-- NRG SolarConnect — Service Desk: Tickets + AMC, Rebuilt as One Module
-- Follows 0002-0036. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 80.
--
-- Replaces the live "Service Desk" Apps Script project (docs/
-- system-understanding-2026-08-16.md, deep-read-service-desk.md) — the
-- largest, most business-critical, most actively-used of the five
-- live tools. Gated behind module_entitlements (0035) module_key =
-- 'service'.
--
-- The single biggest structural fix in this migration: the live
-- system ran THREE separate, disagreeing customer/warranty universes
-- — Service Desk's own synced CUSTOMERS tab (fed from three different
-- external portals), Sales' Clients tab, and NRG SolarConnect's own
-- `customers`/`projects`. Three independent warranty calculators
-- existed because of this, each answering slightly differently. Here
-- there is exactly one `customers` table (Section 19) and one
-- `projects` table for anything NRG installed — a service ticket
-- references them directly, and warranty is a single computed view
-- (below), not logic duplicated three times.

-- ============================================================
-- Customer merge/dedup — the live system's multi-source customer sync
-- (three external portals, upsert + insert-only paths with different
-- semantics) produces real duplicate customer records; a manual
-- dedup/repair tool already existed for exactly this reason
-- (duplicateAudit.js). Same repair pattern already used for materials
-- (Section 60) and projects (Section 69) — added here because Service
-- Desk's sync process is what actually surfaces the need.
-- ============================================================

alter table customers add column merged_into_customer_id uuid references customers(customer_id);
create index on customers (merged_into_customer_id);

-- ============================================================
-- Warranty — ONE computed answer, replacing three disagreeing
-- implementations found in the live source (SyncCustomers.js,
-- SyncMissing.js, and code.js's getWarrantyDetail() each used a
-- different rule and a different output shape). The live rule that
-- actually gates real business logic (chargeable-visit detection,
-- quote triggers) is: 1 year if the project has a GEDA reference,
-- else 5 years — that's the rule kept here, as the only rule, applied
-- live off commissioning_reports.commissioning_date (Section 37) —
-- no separate warranty-tracking table needed, the install date
-- already exists.
-- ============================================================

create view project_warranty_status as
select
  p.project_id,
  p.customer_id,
  cr.commissioning_date as install_date,
  exists (
    select 1 from project_external_references per
    where per.project_id = p.project_id
      and per.reference_type in ('geda_residential','geda_commercial')
  ) as is_geda_sourced,
  case when exists (
    select 1 from project_external_references per
    where per.project_id = p.project_id
      and per.reference_type in ('geda_residential','geda_commercial')
  ) then 1 else 5 end as warranty_years,
  (cr.commissioning_date + (case when exists (
    select 1 from project_external_references per
    where per.project_id = p.project_id
      and per.reference_type in ('geda_residential','geda_commercial')
  ) then 1 else 5 end) * interval '1 year')::date as warranty_end_date,
  cr.commissioning_date is not null
    and current_date <= (cr.commissioning_date + (case when exists (
      select 1 from project_external_references per
      where per.project_id = p.project_id
        and per.reference_type in ('geda_residential','geda_commercial')
    ) then 1 else 5 end) * interval '1 year')::date as is_under_warranty
from projects p
left join commissioning_reports cr
  on cr.project_id = p.project_id and cr.extraction_status = 'confirmed';

-- Deliberately null (not a default "in warranty" or "out of warranty"
-- guess) when there's no confirmed commissioning date — a ticket for a
-- system with no confirmed install date should show "warranty
-- unknown", never silently assume either answer. Same "missing must
-- never silently read as a specific value" discipline as
-- margin_data_complete (Section 64).

-- ============================================================
-- Assignment rules — a real, editable table instead of the live
-- system's static complaint-type -> engineer map, duplicated verbatim
-- in server code and again in client-side JS (confirmed real
-- duplication, deep-read-service-desk.md landmine #11).
-- ============================================================

create table service_assignment_rules (
  rule_id            uuid primary key default gen_random_uuid(),
  complaint_type     text not null unique,
     -- free text, app-level reference list: 'inverter_not_working' |
     -- 'low_generation' | 'wifi_monitoring' | 'commissioning_small' |
     -- 'commissioning_large' | 'follow_up' | 'physical_damage' | 'other'
  default_severity        text not null check (default_severity in ('high','medium','low')),
  primary_engineer_id       uuid references employees(employee_id),
  secondary_engineer_id      uuid references employees(employee_id),
  updated_at                  timestamptz not null default now()
);

-- ============================================================
-- Service Tickets
-- ============================================================

create table service_tickets (
  ticket_id          uuid primary key default gen_random_uuid(),
  ticket_number       text not null unique,   -- e.g. 'TKT-20260610-001', from next_document_number() (Section 37/0010), series_name = 'service_ticket'
  customer_id          uuid not null references customers(customer_id),
  project_id            uuid references projects(project_id),   -- null for a serviced system NRG didn't itself install/track as a project
  caller_name            text,
  caller_phone             text,
  caller_relation           text,          -- 'self' | 'family' | 'staff' | ... — free text
  complaint_type             text not null,   -- same reference list as service_assignment_rules.complaint_type
  complaint_detail             text,
  severity                      text not null check (severity in ('high','medium','low')),
  primary_engineer_id             uuid references employees(employee_id),
  secondary_engineer_id             uuid references employees(employee_id),
  status                              text not null default 'visit_pending'
                                       check (status in ('visit_pending','visited','resolved','pending_from_customer','pending_from_supplier')),
  parent_ticket_id                     uuid references service_tickets(ticket_id),   -- set for a genuine repeat complaint
  resolution_notes                      text,
  resolved_at                            timestamptz,
  created_by                              uuid references employees(employee_id),
  created_at                               timestamptz not null default now()
);

create index on service_tickets (customer_id);
create index on service_tickets (project_id);
create index on service_tickets (status);
create index on service_tickets (primary_engineer_id);

-- Commissioning readings: the live system's "Commissioning Readings"
-- modal (shown for complaint_type = commissioning_small/large) never
-- actually saved anywhere — confirmed dead, discarding real data
-- silently (deep-read-service-desk.md landmine #5). No new table for
-- this here — commissioning_reports (Section 37/0010) already exists
-- for exactly this data; the fix is wiring a commissioning-type ticket
-- to write into commissioning_reports at the application layer, not a
-- second parallel readings table.

create table ticket_timeline (
  timeline_id     uuid primary key default gen_random_uuid(),
  ticket_id       uuid not null references service_tickets(ticket_id),
  event_type      text not null check (event_type in ('created','status_change','reassigned','wa_sent','note')),
  notes           text,
  changed_by      uuid references employees(employee_id),
  created_at      timestamptz not null default now()
);

create index on ticket_timeline (ticket_id);

create table ticket_documents (
  ticket_document_id  uuid primary key default gen_random_uuid(),
  ticket_id           uuid not null references service_tickets(ticket_id),
  document_id         uuid not null references documents(document_id),
  role                text not null check (role in ('complaint_photo','resolution_photo','site_photo')),
  created_at          timestamptz not null default now()
);

create index on ticket_documents (ticket_id);

-- Replaces the live system's two separate, inconsistently-anchored
-- Drive folder conventions (a config-cached root folder for tickets,
-- vs. AMC's search-by-name-with-no-anchor pattern — confirmed real
-- divergence, landmine #15). Every photo here is an ordinary
-- `documents` row (Section 19) linked through this join table — one
-- storage convention, not two.

-- ============================================================
-- Service Quotes — Visit Charge / WiFi Setup / Parts & Repair, raised
-- against a ticket
-- ============================================================

create table service_quotes (
  service_quote_id  uuid primary key default gen_random_uuid(),
  quote_number       text not null unique,   -- series_name = 'service_quote'
  ticket_id           uuid not null references service_tickets(ticket_id),
  quote_type            text not null check (quote_type in ('visit_charge','wifi_setup','parts_repair')),
  discount               numeric(14,2) not null default 0,
  gst_percent              numeric(5,2) not null default 18,
  gst_amount                numeric(14,2) not null default 0,
  total                      numeric(14,2) not null,
  status                      text not null default 'draft' check (status in ('draft','sent','confirmed')),
  generated_document_id        uuid references documents(document_id),
  created_by                     uuid references employees(employee_id),
  created_at                      timestamptz not null default now(),
  confirmed_at                     timestamptz
);

create index on service_quotes (ticket_id);

create table service_quote_items (
  service_quote_item_id  uuid primary key default gen_random_uuid(),
  service_quote_id        uuid not null references service_quotes(service_quote_id),
  description               text not null,
  quantity                    numeric(14,3) not null,
  rate                          numeric(14,2) not null,
  amount                          numeric(14,2) not null
);

create index on service_quote_items (service_quote_id);

-- confirmQuotePayment (live system) is a manual staff checkbox, not a
-- real payment gateway — status = 'confirmed' here means exactly the
-- same thing: someone attested payment was received, not that a
-- payment processor verified it. Reopening the ticket to visit_pending
-- on confirmation is an application-layer action, not schema.

-- ============================================================
-- AMC (Annual Maintenance Contract)
-- ============================================================

create table amc_rates (
  amc_rate_id      uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
    -- tenant-level rate card config, same reasoning as
    -- quote_kw_band_rates (Section 79) — no anchor table to inherit from
  amc_type         text not null check (amc_type in ('service','cleaning')),
  frequency        text not null,
     -- 'quarterly_4v' | 'monthly_12v' | 'clean_1m_1y' | 'clean_2m_1y' |
     -- 'clean_1m_2y' | 'clean_2m_2y' — free text, matches the live
     -- system's real plan set exactly
  kw_min           numeric(10,2) not null,
  kw_max           numeric(10,2) not null,
  base_amount      numeric(14,2) not null,
  updated_at       timestamptz not null default now(),
  check (kw_max > kw_min)
);

create index on amc_rates (organization_id);

create table amc_quotes (
  amc_quote_id       uuid primary key default gen_random_uuid(),
  quote_number         text not null unique,   -- series_name = 'amc_quote', e.g. 'AMCQ-20260625-002'
  customer_id            uuid not null references customers(customer_id),
  project_id               uuid references projects(project_id),   -- null for a third-party (non-NRG-installed) system
  customer_mode              text not null default 'nrg' check (customer_mode in ('nrg','third_party')),
  amc_type                     text not null check (amc_type in ('service','cleaning')),
  frequency                      text not null,
  kw_capacity                      numeric(10,3),
  inverter_make                      text,     -- free text for third-party systems with no materials row; NRG-installed systems can also derive this from boms
  install_year                         integer,
  base_amount                            numeric(14,2) not null,
  discount_percent                         numeric(5,2) not null default 0,
  final_amount                               numeric(14,2) not null,
  status                                       text not null default 'draft' check (status in ('draft','sent','converted')),
  generated_document_id                          uuid references documents(document_id),
  logged_by                                        uuid references employees(employee_id),
  created_at                                        timestamptz not null default now()
);

create index on amc_quotes (customer_id);
create index on amc_quotes (project_id);

create table amc_contracts (
  amc_contract_id      uuid primary key default gen_random_uuid(),
  contract_number        text not null unique,   -- series_name = 'amc_contract'
  source_amc_quote_id      uuid not null references amc_quotes(amc_quote_id),
  customer_id                uuid not null references customers(customer_id),
  project_id                   uuid references projects(project_id),
  start_date                     date not null,
  end_date                         date not null,
  total_visits_entitled              integer not null,
  amount_paid                          numeric(14,2) not null,
  cancelled_at                           timestamptz,   -- set only on an explicit human cancellation decision — never on end_date passing, see below
  cancelled_by                             uuid references employees(employee_id),
  created_at                                 timestamptz not null default now(),
  check (end_date > start_date)
);

create index on amc_contracts (customer_id);
create index on amc_contracts (project_id);

-- Deliberately no stored 'active'/'expired'/'lapsed' status column.
-- The live AMC_REGISTER never actually transitioned a contract's
-- status once end_date passed — confirmed dead workflow (landmine
-- #5/#12, "no AMC resolved/closed workflow exists"). A stored status
-- would just be one more place to go stale; "is this contract active
-- right now" is a pure function of start_date/end_date/cancelled_at,
-- computed live below — it can never disagree with reality.

create view amc_contract_status as
select
  c.amc_contract_id,
  c.customer_id,
  c.project_id,
  c.end_date,
  c.cancelled_at,
  case
    when c.cancelled_at is not null then 'cancelled'
    when current_date > c.end_date then 'expired'
    else 'active'
  end as computed_status,
  c.end_date <= current_date + interval '2 months' and c.cancelled_at is null and current_date <= c.end_date
    as due_for_renewal
from amc_contracts c;

-- due_for_renewal replaces the live daily 9am trigger that only ever
-- wrote to an execution log and never actually notified anyone
-- (confirmed dead-in-practice, landmine #12/#4) — this makes "which
-- AMCs need renewal attention" a real, live query the UI can surface
-- directly, rather than depending on a trigger that has never sent a
-- real notification. Real renewal notification (email/WhatsApp) is an
-- application-layer follow-up, not schema.

create table amc_visits (
  amc_visit_id     uuid primary key default gen_random_uuid(),
  amc_contract_id  uuid not null references amc_contracts(amc_contract_id),
  visit_number     integer not null,
  visit_date       date not null,
  notes            text,
  logged_by        uuid references employees(employee_id),
  created_at       timestamptz not null default now(),
  unique (amc_contract_id, visit_number)
);

create index on amc_visits (amc_contract_id);

create table amc_visit_documents (
  amc_visit_document_id  uuid primary key default gen_random_uuid(),
  amc_visit_id            uuid not null references amc_visits(amc_visit_id),
  document_id               uuid not null references documents(document_id)
);

create index on amc_visit_documents (amc_visit_id);

-- "Next visit due" (a rolling last-visit-date + fixed interval
-- estimate in the live system, not real scheduling) is deliberately
-- left as an application-layer/reporting calculation off
-- amc_visits.visit_date + amc_contracts.frequency — it was never a
-- committed schedule in the live system either, just a heuristic
-- display, so it doesn't need a stored "next_visit_due" column here.

-- ============================================================
-- What this migration does NOT do
-- ============================================================
-- No WhatsApp/email send logic (application-layer, same deep-link
-- pattern used throughout). No real payment-gateway integration —
-- service_quotes.status/'confirmed' and amc_contracts remain
-- staff-attested, matching how payment confirmation already works
-- everywhere else in this schema (payment_receipts, Section 32/33).
-- No RLS yet — same standing item as every module so far; this
-- migration's tables are shaped so "an engineer sees their own
-- assigned tickets, Owner/Service Head sees all" can be written
-- correctly once RLS itself is designed. No fix for the live system's
-- almost-entirely-client-side permission enforcement (deep-read
-- landmine #1, "Admin only" comments with no actual server check) —
-- that gets fixed BY building real RLS, not by anything in this
-- migration alone; flagging it again here so it isn't lost among five
-- modules' worth of "still open" notes.
