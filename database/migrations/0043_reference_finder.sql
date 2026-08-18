-- NRG SolarConnect — Reference Finder (Find Comparable Installed
-- Customers to Share as References)
-- Follows 0002-0042. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 86.
--
-- Source: `nrg_reference_finder.html` (nrg-cover, 549 lines, read in
-- full). No dedicated backend at all — its own header comment says so
-- directly: "Same Apps Script that serves Leads & Followup — sheet
-- stays fully private," calling a new `?api=customers` query param on
-- the exact Quote Generator/Sales Follow-up deployment already fully
-- modeled in 0036. That handler, `getCustomers_()`, was read during the
-- original Quote Generator deep-read and flagged then as reading a
-- "third, separate spreadsheet" (`FINAL_CLIENT_SHEET_ID`) — re-fetching
-- that ID now (owner's own instructions: "check the github... see what
-- is being used") shows its real title is **"NRG Service Desk"**, and
-- its `CE_LOG` tab is the exact tab already migrated into
-- `customer_engagement_log` (0039). So the "third spreadsheet" isn't
-- new, unmodeled ground after all — it's Service Desk's own `CUSTOMERS`
-- tab, already the `customers` table (0002) plus `project_confirmed_bom`
-- (0024) and `commissioning_reports` (0010). No new tables needed here.
--
-- What the frontend actually asks each customer row for: name,
-- contact/phone, address, area, business type (Doctor/Hotel/Industry/
-- School/Apartment/Residential/Large Residential — its quick-filter
-- pills, read directly off the page), total kW installed, panel make,
-- inverter make, install date — then aggregates by customer name,
-- taking the total kW across every system and the descriptive fields
-- (area/biz/address/panel/inverter/install date) from whichever single
-- system was that customer's LARGEST (`buildAgg()`'s own `_mx` logic,
-- read line by line) — not their most recent.
--
-- One real, genuine gap this surfaces: `customers` has `area` (0002)
-- but nothing carrying the live system's business-type taxonomy
-- (Doctor/Hotel/Industry/School/Apartment/Residential/SPP Residential —
-- confirmed real values, not guessed, taken from the live page's own
-- filter pills and matching logic). `projects.project_type` is far too
-- coarse (`residential_subsidy`/`commercial_industrial`) to answer "is
-- this customer a doctor's clinic" — a real, distinct fact worth
-- capturing at the customer level, added below the same free-text way
-- as `materials.category`/`documents.document_type`.

alter table customers add column business_type text;
  -- e.g. 'Doctor', 'Hotel', 'Industry', 'School', 'Apartment',
  -- 'Residential', 'SPP Residential' — free text, not an enum, same
  -- reasoning as everywhere else this taxonomy could keep growing;
  -- nullable, since most historical customers won't have this filled
  -- in until someone does a one-time pass, same as any other backfill

-- ============================================================
-- The directory itself — a view, not a table. Every fact it reports
-- (kW, panel/inverter make, install date) already lives somewhere real
-- (boms/bom_items/materials/commissioning_reports); storing a second
-- copy here would just be one more place those numbers could drift,
-- the exact discipline every module before this one has followed.
--
-- "Representative" system per customer (area/panel/inverter/install
-- date) is picked by largest kw_capacity among their commissioned,
-- confirmed-BOM projects, matching buildAgg()'s own logic exactly —
-- not the most recent install, the biggest one, since a bigger
-- reference is the more persuasive one to share.
-- ============================================================

create view customer_reference_directory as
with customer_systems as (
  select
    p.customer_id,
    p.project_id,
    pcb.kw_capacity,
    cr.commissioning_date,
    (select m.make from bom_items bi
       join materials m on m.material_id = bi.material_id
       where bi.bom_id = pcb.bom_id and bi.category = 'Solar Panels'
       limit 1) as panel_make,
    (select m.make from bom_items bi
       join materials m on m.material_id = bi.material_id
       where bi.bom_id = pcb.bom_id and bi.category ilike '%inverter%'
       limit 1) as inverter_make
       -- 'Solar Panels' is a confirmed exact category string (Section
       -- 59/0023); no equally-confirmed exact string for Inverter
       -- surfaced in any prior deep read, so this one matches loosely
       -- on purpose rather than risk silently missing every inverter
  from projects p
  join project_confirmed_bom pcb on pcb.project_id = p.project_id
  left join commissioning_reports cr on cr.project_id = p.project_id
  where p.status = 'commissioned'
),
totals as (
  select customer_id,
    sum(kw_capacity) as total_kw_installed,
    count(*) as system_count
  from customer_systems
  group by customer_id
),
biggest as (
  select distinct on (customer_id)
    customer_id, panel_make, inverter_make, commissioning_date as install_date
  from customer_systems
  order by customer_id, kw_capacity desc nulls last
)
select
  c.customer_id,
  c.name,
  c.primary_contact_number,
  c.address,
  c.area,
  c.business_type,
  coalesce(t.total_kw_installed, 0) as total_kw_installed,
  coalesce(t.system_count, 0) as system_count,
  b.panel_make,
  b.inverter_make,
  b.install_date
from customers c
left join totals t on t.customer_id = c.customer_id
left join biggest b on b.customer_id = c.customer_id;

-- ============================================================
-- No new module_entitlements row. Reference Finder introduces no new
-- data and no new write path — it's a read-only report over data that
-- already exists the moment projects_inventory + a commissioned project
-- exist, surfaced specifically for Sales (the live page's own eyebrow
-- label is "Sales Help", its back-link is `/sales-help`). Same
-- reasoning already used for Client Engagement (0039) riding on an
-- existing key rather than inventing a boundary the real coupling
-- doesn't have: this rides on 'sales_followup', since a tenant without
-- Sales Follow-up enabled has no real use for "find me a reference
-- customer to share."
-- ============================================================
