-- ProjectPulse — Quote Rate Flexibility, Material Brand Tracking, and the
-- BOM Recommendation Engine
-- Follows 0002-0012. Consolidated from docs/projectpulse-handover.md
-- Section 40.

-- ============================================================
-- Vendor quote rates aren't always apples-to-apples
-- ============================================================

-- Some quoted rates include transport, some don't; some include
-- loading/unloading (e.g. GI pipes), some don't. Comparing raw rate
-- alone silently favours whichever vendor excluded the most from their
-- number, not whichever is actually cheaper landed.

alter table vendor_quote_items add column includes_transport boolean;
alter table vendor_quote_items add column includes_loading_unloading boolean;
alter table vendor_quote_items add column notes text;

-- Null on all three means "not specified" — a real, common case for a
-- rate taken down over a phone call, not a data-entry failure. The
-- comparison screen should show these flags next to the rate rather
-- than silently ranking cheapest-first as if every quote were on equal
-- terms.

-- ============================================================
-- Material brand — needed to sell what's actually in stock
-- ============================================================

-- Real gap: NRG has Adani 620W panels sitting in stock, but sales
-- keeps selling Waree 620W instead, because nothing surfaces which
-- brand is actually on the shelf. category + canonical_name (0002)
-- could already encode brand inside canonical_name as free text, but
-- that makes "what brands do I have of this wattage" a string-parsing
-- problem instead of a query.

alter table materials add column make text;

-- e.g. category='Solar Panels', canonical_name='620W', make='Adani' vs
-- make='Waree' — two distinct materials rows already, per the existing
-- unique(category, canonical_name) constraint... except that constraint
-- doesn't include make, so two makes at the same wattage would collide
-- on canonical_name today. Widen it:

alter table materials drop constraint materials_category_canonical_name_key;
alter table materials add constraint materials_category_canonical_name_make_key
  unique (category, canonical_name, make);

-- ============================================================
-- BOM Recommendation Engine — learn from real historical usage
-- ============================================================

-- Distinct from Section 33's sheet-driven generation (which drives
-- NRG's existing, already-trusted SPP formula sheet for standard
-- systems). This one learns from what was actually sent, returned, and
-- used at site on real completed projects — catching real-world
-- patterns (routing losses, wastage, over-ordering habits) a fixed
-- formula never will. Both can coexist.

alter table boms drop constraint boms_origin_check;
alter table boms add constraint boms_origin_check
  check (origin in ('uploaded_workbook','system_calculated','recommendation_engine'));

-- bom_item_variance (0005) never exposed material_id — needed here to
-- benchmark per material. Additive column at the end of the select
-- list; existing consumers of the view are unaffected.

create or replace view bom_item_variance as
with movement as (
  select
    bom_item_id,
    sum(quantity) filter (where movement_type = 'issued_to_site') as dispatched_quantity,
    sum(quantity) filter (where movement_type = 'returned_to_warehouse') as returned_quantity
  from material_transactions
  where bom_item_id is not null
  group by bom_item_id
),
cost as (
  select
    bom_item_id,
    sum(attributed_cost) filter (where movement_type = 'issued_to_site')
      - sum(attributed_cost) filter (where movement_type = 'returned_to_warehouse') as actual_cost
  from material_transaction_cost
  where bom_item_id is not null
  group by bom_item_id
)
select
  b.bom_item_id,
  b.bom_id,
  bm.project_id,
  b.category,
  b.description,
  b.unit,
  b.planned_quantity,
  coalesce(m.dispatched_quantity, 0) as dispatched_quantity,
  coalesce(m.returned_quantity, 0) as returned_quantity,
  coalesce(m.dispatched_quantity, 0) - coalesce(m.returned_quantity, 0) as used_quantity,
  b.planned_quantity - (coalesce(m.dispatched_quantity, 0) - coalesce(m.returned_quantity, 0)) as quantity_variance,
  b.estimated_cost,
  coalesce(c.actual_cost, 0) as actual_cost,
  coalesce(c.actual_cost, 0) - b.estimated_cost as cost_variance,
  b.material_id
from bom_items b
join boms bm on bm.bom_id = b.bom_id
left join movement m on m.bom_item_id = b.bom_item_id
left join cost c on c.bom_item_id = b.bom_item_id;

create view material_consumption_benchmark as
select
  b.material_id,
  m.category,
  m.canonical_name,
  m.make,
  count(distinct v.bom_id) as project_sample_size,
  sum(v.used_quantity) as total_used_quantity,
  sum(bm.kw_capacity) as total_kw_capacity,
  sum(v.used_quantity) / nullif(sum(bm.kw_capacity), 0) as used_qty_per_kw,
  sum(v.planned_quantity) / nullif(sum(bm.kw_capacity), 0) as planned_qty_per_kw
from bom_item_variance v
join bom_items b on b.bom_item_id = v.bom_item_id
join boms bm on bm.bom_id = v.bom_id
join projects p on p.project_id = bm.project_id
join materials m on m.material_id = b.material_id
where bm.kw_capacity > 0
  and p.status = 'commissioned'
group by b.material_id, m.category, m.canonical_name, m.make;

-- Scoped to projects.status = 'commissioned' deliberately — a project
-- still mid-dispatch would show artificially low used_quantity and
-- skew the benchmark low. used_qty_per_kw (not planned_qty_per_kw) is
-- the number a new project's recommendation should be built from —
-- that's the whole point, actual usage over planned. project_sample_size
-- should drive the recommendation's own ai_confidence: a benchmark from
-- 1-2 projects is a guess, from 10+ is a real pattern. Recommending a
-- BOM from this is: recommended_quantity = used_qty_per_kw ×
-- new_project's kw_capacity, written as ordinary bom_items rows with
-- extraction_status = 'ai_extracted' and boms.origin =
-- 'recommendation_engine' — reviewed and confirmed the same as
-- everything else, never auto-applied without a human look.
