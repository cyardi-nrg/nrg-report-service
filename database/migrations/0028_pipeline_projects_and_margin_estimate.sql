-- ProjectPulse — In-Talks (Pipeline) Projects: Should NRG Take This
-- Order, at This Quoted Price?
-- Follows 0002-0027. Consolidated from docs/projectpulse-handover.md
-- Section 68.

-- ============================================================
-- Real ask: the same BOM-costing machinery, before the order is won,
-- to decide whether it's worth winning
-- ============================================================

-- Everything built so far (BOM generation, Section 45; Cost per Watt,
-- Section 59; the size-band standard cost, Section 63; Margin,
-- Section 64) answers "what did this project actually cost" for a
-- project NRG already has. Real, distinct need: before the order is
-- confirmed, generate the same BOM off the same driver inputs, price
-- it at real current purchase rates, and compare against the quoted
-- price — the exact manual exercise NRG is doing by hand today, too
-- slowly, to decide whether an order is worth taking.

alter table projects drop constraint projects_status_check;
alter table projects add constraint projects_status_check
  check (status in ('in_talks', 'active', 'commissioned', 'on_hold', 'cancelled'));

-- 'in_talks' — a prospective project: a real customer, a real site
-- (electricity bill, site drawings/layout already uploadable today,
-- documents.project_id has never cared what stage a project is in),
-- but no confirmed order yet. Deliberately the same projects table,
-- not a separate one — a pipeline project graduates to 'active' the
-- moment the order is won, same row, same documents, same BOM,
-- nothing to migrate.

-- ============================================================
-- Confirmed: everything needed already exists except one view
-- ============================================================

-- BOM generation (Section 45) already works for any project_id
-- regardless of status — no change needed. Material cost already
-- comes from bom_category_cost/bom_panel_vs_rest_cost (Section 59,
-- 0023), which price a BOM's planned_quantity at planned_rate
-- (material_weighted_avg_rate_as_of, Section 33) — real, current
-- purchase-history rates, with no dependency on this project having
-- ever actually purchased or dispatched anything. That's exactly
-- right for a project that hasn't been won yet: quantities come from
-- the BOM, rates come from what NRG is actually paying right now.

-- What a pipeline project genuinely can't have yet: real Transportation/
-- Fabricator/Electrical Contractor costs (project_costs, Section 64) —
-- nothing's been purchased or subcontracted for an order that isn't
-- confirmed. This is exactly what the Cost Benchmark by Project Size
-- (Section 63) was built for, even though it wasn't originally framed
-- this way: size_band_standard_cost's average Transportation/
-- Fabricator/Electrical Contractor Rs/Watt, for this project's own
-- size band, standing in for real bills that don't exist yet.

create view pipeline_project_margin_estimate as
select
  psb.project_id,
  psb.size_band,
  psb.kw_capacity,
  b.order_value as quoted_price,
  bpvr.panel_cost as material_panel_cost,
  bpvr.rest_cost as material_rest_cost,
  bpvr.panel_cost + bpvr.rest_cost as material_cost_estimate,
  round(coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2) as estimated_transportation_cost,
  round(coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2) as estimated_fabricator_cost,
  round(coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000, 2) as estimated_electrical_contractor_cost,
  round(
    bpvr.panel_cost + bpvr.rest_cost
    + coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
    + coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
    + coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
  , 2) as estimated_total_project_cost,
  round(
    b.order_value - (
      bpvr.panel_cost + bpvr.rest_cost
      + coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
      + coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
      + coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
    )
  , 2) as estimated_margin,
  round(
    100.0 * (b.order_value - (
      bpvr.panel_cost + bpvr.rest_cost
      + coalesce(sbsc_t.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
      + coalesce(sbsc_f.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
      + coalesce(sbsc_e.avg_rs_per_watt, 0) * psb.kw_capacity * 1000
    )) / nullif(b.order_value, 0)
  , 2) as estimated_margin_pct,
  (sbsc_t.avg_rs_per_watt is not null) as has_transportation_benchmark,
  (sbsc_f.avg_rs_per_watt is not null) as has_fabricator_benchmark,
  (sbsc_e.avg_rs_per_watt is not null) as has_electrical_contractor_benchmark
from project_size_band psb
join project_confirmed_bom pcb on pcb.project_id = psb.project_id
join boms b on b.bom_id = pcb.bom_id
join bom_panel_vs_rest_cost bpvr on bpvr.bom_id = pcb.bom_id
left join size_band_standard_cost sbsc_t on sbsc_t.size_band = psb.size_band and sbsc_t.category = 'Transportation'
left join size_band_standard_cost sbsc_f on sbsc_f.size_band = psb.size_band and sbsc_f.category = 'Fabricator'
left join size_band_standard_cost sbsc_e on sbsc_e.size_band = psb.size_band and sbsc_e.category = 'Electrical Contractor';

-- Reuses four existing views wholesale — project_size_band (Section
-- 63), project_confirmed_bom (Section 63), bom_panel_vs_rest_cost
-- (Section 59), size_band_standard_cost (Section 63) — genuinely one
-- new view for this whole capability, not a new subsystem. Not scoped
-- to status = 'in_talks' specifically: works for any project with a
-- confirmed BOM, which also makes it a natural "what we estimated vs.
-- what actually happened" comparison once a project is won and
-- Section 64's real project_margin has real numbers to compare
-- against.

-- has_*_benchmark flags mirror Section 63/64's own completeness
-- discipline: if a size band has no standard cost data point yet for
-- one of the three, that term silently defaults to 0 in the estimate
-- above via coalesce — same understating-cost risk margin_data_complete
-- (0025) already exists to catch, just one step earlier here, before a
-- BOM even has real bills to check. An estimate resting on a size band
-- with no benchmark data yet is a guess dressed as a number; these
-- flags are what stops it from being presented as one.

-- ============================================================
-- Confirmed: existing operational views already exclude pipeline
-- projects correctly, no change needed
-- ============================================================

-- material_requirement (0016) already filters `where p.status =
-- 'active'` — an 'in_talks' project's BOM was never going to
-- accidentally drive Order Now or reserve warehouse stock for an
-- order that isn't confirmed yet. Same for every other view keyed off
-- project status. Nothing to fix here; worth stating explicitly so a
-- build session doesn't go looking for a guard that already exists.
