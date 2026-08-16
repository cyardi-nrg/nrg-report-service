-- ProjectPulse — Owner-Only Cost-Per-Watt Benchmark, Across Projects,
-- Bucketed by System Size
-- Follows 0002-0023. Consolidated from docs/projectpulse-handover.md
-- Section 63.

-- ============================================================
-- A different report from Section 59/60's per-project panel:
-- this one compares projects, to build a standard rate card
-- ============================================================

-- Section 59 put Rs/Watt-by-category on a single project's BOM tab —
-- right for "what did *this* project actually cost." Real, separate
-- ask this time: "give me a complete list of projects, grouped into
-- size slabs (15-25kW, 25-50kW, 50-100kW, 100-200kW, 200-500kW,
-- 500kW+), side by side, Rs/Watt per category for each, and a
-- standardized cost per slab for pricing future projects." That's a
-- cross-project comparison — it can only live on Reports, owner-only,
-- same as Project Margin (Section 39).

-- Which BOM represents "the real cost" when a project has more than
-- one version (boms.version, Section 19)? The latest *confirmed* one —
-- an ai_extracted, unreviewed BOM has no business feeding a company-wide
-- standard rate.

create view project_confirmed_bom as
select distinct on (b.project_id)
  b.project_id, b.bom_id, b.kw_capacity, b.version
from boms b
where b.extraction_status = 'confirmed'
order by b.project_id, b.version desc;

-- Size band is bucketed here, not stored anywhere — it's a pure
-- function of kw_capacity, same reasoning as every other computed
-- figure in this schema (Principle: compute, don't store). Bands are
-- the exact slabs given: lower bound inclusive, upper bound exclusive.
-- 'Under 15 kW' is a catch-all for the small residential jobs below
-- the smallest named slab, so nothing silently disappears from the
-- report.

create view project_size_band as
select
  project_id, bom_id, kw_capacity,
  case
    when kw_capacity < 15 then 'Under 15 kW'
    when kw_capacity < 25 then '15-25 kW'
    when kw_capacity < 50 then '25-50 kW'
    when kw_capacity < 100 then '50-100 kW'
    when kw_capacity < 200 then '100-200 kW'
    when kw_capacity < 500 then '200-500 kW'
    else '500 kW+'
  end as size_band
from project_confirmed_bom;

-- ============================================================
-- GI Structure vs. Aluminum Structure — already two categories,
-- nothing to split
-- ============================================================

-- Section 45/44 already established GI Pipe Panel Structure and Strut
-- Channel Structure (Aluminium) as two separate, mutually-exclusive
-- bom_items.category values — a project uses one or the other, driven
-- by structure_type. bom_category_cost (0023) already produces them as
-- two separate rows with no change needed here; this report just reads
-- both categories out the same as any other.

-- ============================================================
-- Installation cost — the real gap. Section 59's per-project panel
-- was material-only; a standard rate card needs labour too.
-- ============================================================

-- project_costs (Section 38, cost_type already includes 'fabrication'
-- and 'installation_subcontract') is exactly the missing half.
-- Confirmed ('assigned') costs only — an unassigned or still-general
-- bill hasn't actually been attributed to this project yet, so it
-- can't count toward its Rs/Watt.

create view project_installation_cost as
select
  pc.project_id,
  sum(pc.amount) as installation_cost,
  round(sum(pc.amount) / nullif(psb.kw_capacity * 1000, 0), 2) as installation_rs_per_watt
from project_costs pc
join project_size_band psb on psb.project_id = pc.project_id
where pc.assignment_status = 'assigned'
group by pc.project_id, psb.kw_capacity;

-- Deliberately not the deferred Margin view (Section 37/38) — no
-- revenue anywhere in this. It's the cost side only, same boundary
-- Section 59 already drew, just now including labour alongside
-- material so "standard cost per watt" actually means the full build
-- cost, not material cost with installation missing.

-- ============================================================
-- One view per (project, category) row — the direct source for
-- "projects side by side, size band as a tab, category as a row"
-- ============================================================

create view project_cost_per_watt_benchmark as
select
  psb.project_id,
  psb.size_band,
  psb.kw_capacity,
  bcc.category,
  bcc.rs_per_watt
from project_size_band psb
join bom_category_cost bcc on bcc.bom_id = psb.bom_id
union all
select
  psb.project_id,
  psb.size_band,
  psb.kw_capacity,
  'Installation' as category,
  coalesce(pic.installation_rs_per_watt, 0) as rs_per_watt
from project_size_band psb
left join project_installation_cost pic on pic.project_id = psb.project_id;

-- The report itself pivots this app-side: one tab per size_band,
-- projects as columns, category (Solar Panels / Inverter / GI Pipe
-- Panel Structure / Strut Channel Structure / ACDB / DCDB / DC Cable /
-- AC Cable / ... / Installation) as rows. No SQL pivot needed — this
-- view already has every number the report reads, one row at a time.

-- ============================================================
-- The standard: what to charge/budget per watt, by size band
-- ============================================================

create view size_band_standard_cost as
select
  size_band,
  category,
  round(avg(rs_per_watt), 2) as avg_rs_per_watt,
  round(min(rs_per_watt), 2) as min_rs_per_watt,
  round(max(rs_per_watt), 2) as max_rs_per_watt,
  count(*) as project_count
from project_cost_per_watt_benchmark
group by size_band, category;

-- avg is the number to actually quote from; min/max and project_count
-- travel with it so a slab resting on one or two projects reads as
-- thin evidence, not a settled number — a band with project_count = 1
-- is a data point, not yet a standard.
