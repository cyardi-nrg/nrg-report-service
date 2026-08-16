-- ProjectPulse — DC:AC Ratio (Panel Capacity vs. Inverter Capacity)
-- Follows 0002-0020. Consolidated from docs/projectpulse-handover.md
-- Section 56.

-- ============================================================
-- AC capacity never had a structured column — only DC did
-- ============================================================

-- boms.panel_wattage/panel_count/kw_capacity (Section 19) already
-- capture DC capacity as header-level fields. Inverter capacity never
-- got the same treatment — the mockup's Generate BOM screen only ever
-- had it as free text ("75kW · Growatt"), same field doing double duty
-- for make and capacity. DC:AC sizing is a real, standard solar design
-- check (oversizing the array relative to the inverter has real limits,
-- both electrical and per DISCOM rules) and needs a real number to check
-- against, not a string to eyeball.

alter table boms add column inverter_capacity_kw numeric(10,3);

-- Total AC nameplate capacity for the project — sum of every inverter
-- if there's more than one (the SPP sheet itself supports Inverter 1/2/3
-- per project, Section 44). Same header-level pattern as kw_capacity:
-- one number describing the BOM as a whole, not derived by summing
-- bom_items at query time, since inverter capacity isn't reliably
-- parseable out of a material's canonical_name.

create view bom_capacity_check as
select
  b.bom_id,
  b.project_id,
  b.panel_wattage,
  b.panel_count,
  b.kw_capacity as dc_capacity_kw,
  b.inverter_capacity_kw as ac_capacity_kw,
  round(b.kw_capacity / nullif(b.inverter_capacity_kw, 0), 2) as dc_ac_ratio,
  (b.kw_capacity / nullif(b.inverter_capacity_kw, 0)) > 1.4 as oversized
from boms b
where b.inverter_capacity_kw is not null;

-- 1.4 is the confirmed threshold — flag anything sizing the DC array
-- more than 1.4x the inverter's AC capacity. This is the same check
-- Section 40's Capacity Consistency Check report now also runs
-- (alongside its existing zero-tolerance government-document
-- cross-check, unrelated but shown on the same report) and what the
-- Generate BOM screen computes live as Panel/Inverter values are typed
-- in, before the BOM is even confirmed.
