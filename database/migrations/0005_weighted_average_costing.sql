-- ProjectPulse — Weighted-Average Costing for Pooled Warehouse Stock
-- Follows 0002-0004. Consolidated from docs/projectpulse-handover.md Section 31.
--
-- Fixes a real gap: bom_item_variance.actual_cost (0002) only counted
-- material purchased directly for one project's BOM, so it silently
-- showed 0/undercounted for material drawn from shared warehouse stock
-- (the normal case for bulk items like cable). This adds weighted-average
-- cost attribution, using the average AS OF each issue's date so a
-- completed project's reported cost doesn't drift as new purchases land.

create view material_purchase_running_avg as
select
  transaction_id,
  material_id,
  transaction_date,
  quantity,
  rate,
  sum(quantity) over w as cumulative_quantity,
  sum(quantity * rate) over w as cumulative_value,
  (sum(quantity * rate) over w) / nullif(sum(quantity) over w, 0) as weighted_avg_rate
from material_transactions
where movement_type = 'purchased' and rate is not null
window w as (partition by material_id order by transaction_date, transaction_id);

create view material_transaction_cost as
select
  it.transaction_id,
  it.material_id,
  it.bom_item_id,
  it.project_id,
  it.movement_type,
  it.transaction_date,
  it.quantity,
  coalesce(it.rate, avg_rate.weighted_avg_rate) as effective_rate,
  it.quantity * coalesce(it.rate, avg_rate.weighted_avg_rate) as attributed_cost
from material_transactions it
left join lateral (
  select p.weighted_avg_rate
  from material_purchase_running_avg p
  where p.material_id = it.material_id
    and p.transaction_date <= it.transaction_date
  order by p.transaction_date desc, p.transaction_id desc
  limit 1
) avg_rate on true
where it.movement_type in ('issued_to_site', 'returned_to_warehouse');

-- coalesce(it.rate, ...) matters specifically for Section 28's historical
-- backfill: a legacy 'issued_to_site' row carries the workbook's own Actual
-- Rate directly, and that must win outright rather than triggering a
-- weighted-average lookup against purchase history that, for an old
-- project, may not exist at all. Real per-dispatch issues going forward
-- have no rate of their own and fall through to the weighted-average
-- lookup automatically.

-- Replaces bom_item_variance from 0002 with the corrected version. Column
-- list (names/order/types) is unchanged, so create-or-replace is valid.

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
  coalesce(c.actual_cost, 0) - b.estimated_cost as cost_variance
from bom_items b
join boms bm on bm.bom_id = b.bom_id
left join movement m on m.bom_item_id = b.bom_item_id
left join cost c on c.bom_item_id = b.bom_item_id;

-- Two related design decisions from this session that need NO schema
-- change, noted here for context:
--
-- 1. Document-to-project linking should never trust which Drive folder a
--    file was uploaded into (a person will misfile things) — AI content
--    classification (client name, consumer number, project reference)
--    determines the project match regardless of folder, flagging a
--    mismatch if the folder disagrees. This is an extraction-pipeline
--    rule, not a table.
--
-- 2. A single bulk purchase order split across many client sites (e.g. a
--    100kW panel order across 15 projects) is already handled by the
--    existing shape of material_transactions: one warehouse-level
--    'purchased' row, followed by many separate 'issued_to_site' rows
--    (one per project, each with its own quantity and, for serialized
--    items, its own slice of serial_numbers). material_stock,
--    material_requirement, and material_shortfall (0003) already
--    aggregate correctly across any number of projects drawing from one
--    purchase — nothing new needed.
