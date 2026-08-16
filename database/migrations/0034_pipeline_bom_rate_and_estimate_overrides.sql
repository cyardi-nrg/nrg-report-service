-- ProjectPulse — Rate Needs to Be Editable Too, Not Just Quantity, and
-- Transportation/Fabricator/Electrical Contractor Need an Overridable
-- Estimate
-- Follows 0002-0033. Consolidated from docs/projectpulse-handover.md
-- Section 75.

-- ============================================================
-- Rate, not just quantity — a real cost decision needs both
-- ============================================================

-- Real, direct correction: editing only bom_items.planned_quantity on
-- a pipeline BOM (Section 73) doesn't answer "how much does this
-- change the cost" — quantity times rate does. No schema change here
-- at all: bom_items.planned_rate (Section 19) already exists, already
-- carries the same extraction_status/confirmed_by/confirmed_at
-- correction machinery as planned_quantity. The gap was purely that
-- the mockup only exposed an editable control for quantity — rate
-- needs the identical treatment, same row, same Save action.

-- ============================================================
-- Missing line items — add them, don't estimate around them
-- ============================================================

-- Real, confirmed problem, caught directly by building out a fuller
-- example: a BOM missing real categories (Lightning Arrestor, MC4
-- Connectors, Earthing Pits, Misc hardware — all genuine categories in
-- NRG's own real 15-category taxonomy, Section 44) understates true
-- cost, sometimes by enough to flip a deal from profitable to a loss.
-- No schema change needed — bom_items already supports adding an
-- ordinary new row for any category at any time (category is free
-- text, Section 19); this was purely a UI gap on the pipeline BOM
-- table specifically, which needs a "+ Add Line Item" action the same
-- as any other BOM.

-- ============================================================
-- Transportation/Fabricator/Electrical Contractor need their own
-- overridable estimate, not just the size-band standard
-- ============================================================

-- pipeline_project_margin_estimate (Section 68) stands in for these
-- three with the size-band benchmark average, since no real bills
-- exist yet for an unconfirmed order — right as a default, but Owner
-- needs to be able to replace any of the three with a better number
-- for *this specific* deal (an actual quote a fabricator gave over the
-- phone, a transporter's known rate for this route) rather than always
-- accepting the generic average.

alter table boms add column estimated_transportation_cost numeric(14,2);
alter table boms add column estimated_fabricator_cost numeric(14,2);
alter table boms add column estimated_electrical_contractor_cost numeric(14,2);

-- Header-level fields on boms, same pattern as order_value/kw_capacity
-- (Section 19) — one number per BOM, not a line item. Null by default,
-- meaning "no better number than the size-band standard yet."

create or replace view pipeline_project_margin_estimate as
select
  psb.project_id,
  psb.size_band,
  psb.kw_capacity,
  b.order_value as quoted_price,
  bpvr.panel_cost as material_panel_cost,
  bpvr.rest_cost as material_rest_cost,
  bpvr.panel_cost + bpvr.rest_cost as material_cost_estimate,
  coalesce(b.estimated_transportation_cost, round(coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2)) as estimated_transportation_cost,
  coalesce(b.estimated_fabricator_cost, round(coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2)) as estimated_fabricator_cost,
  coalesce(b.estimated_electrical_contractor_cost, round(coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2)) as estimated_electrical_contractor_cost,
  round(
    bpvr.panel_cost + bpvr.rest_cost
    + coalesce(b.estimated_transportation_cost, coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
    + coalesce(b.estimated_fabricator_cost, coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
    + coalesce(b.estimated_electrical_contractor_cost, coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
  , 2) as estimated_total_project_cost,
  round(
    b.order_value - (
      bpvr.panel_cost + bpvr.rest_cost
      + coalesce(b.estimated_transportation_cost, coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
      + coalesce(b.estimated_fabricator_cost, coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
      + coalesce(b.estimated_electrical_contractor_cost, coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
    )
  , 2) as estimated_margin,
  round(
    100.0 * (b.order_value - (
      bpvr.panel_cost + bpvr.rest_cost
      + coalesce(b.estimated_transportation_cost, coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
      + coalesce(b.estimated_fabricator_cost, coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
      + coalesce(b.estimated_electrical_contractor_cost, coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000)
    )) / nullif(b.order_value, 0)
  , 2) as estimated_margin_pct,
  (b.estimated_transportation_cost is not null or sbsc_t.avg_rs_per_watt is not null) as has_transportation_benchmark,
  (b.estimated_fabricator_cost is not null or sbsc_f.avg_rs_per_watt is not null) as has_fabricator_benchmark,
  (b.estimated_electrical_contractor_cost is not null or sbsc_e.avg_rs_per_watt is not null) as has_electrical_contractor_benchmark
from project_size_band psb
join project_confirmed_bom pcb on pcb.project_id = psb.project_id
join boms b on b.bom_id = pcb.bom_id
join bom_panel_vs_rest_cost bpvr on bpvr.bom_id = pcb.bom_id
left join size_band_standard_cost sbsc_t on sbsc_t.size_band = psb.size_band and sbsc_t.category = 'Transportation'
left join size_band_standard_cost sbsc_f on sbsc_f.size_band = psb.size_band and sbsc_f.category = 'Fabricator'
left join size_band_standard_cost sbsc_e on sbsc_e.size_band = psb.size_band and sbsc_e.category = 'Electrical Contractor';

-- coalesce(b.estimated_*_cost, size-band standard) — Owner's own
-- number wins when entered, the benchmark fills in when it isn't. The
-- has_*_benchmark flags now also account for this: a manual override
-- counts as "has a number to work with" exactly like a real size-band
-- data point does, since either one means this line isn't silently
-- defaulting to zero (the actual thing those flags exist to catch,
-- Section 68). material_cost_estimate is unaffected by any of this —
-- it always comes straight from the BOM's own line items
-- (bom_panel_vs_rest_cost, Section 59), edited quantity and rate
-- included, live, no override column needed there since editing
-- bom_items directly already is the override.
