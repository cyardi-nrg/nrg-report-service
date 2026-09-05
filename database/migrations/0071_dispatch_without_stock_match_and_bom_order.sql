-- NRG SolarConnect — Dispatch without requiring a stock match; real BOM order
-- Follows 0002-0070.
--
-- Two real owner reports fixed here:
--
-- 1. "cant generate DDC... lets not have the restriction of setting it
--    off against material in stock for now... just give warning...not in
--    stock... else till my entire stock is set up... i wont be able to
--    use DC." delivery_challan_items.material_id and
--    material_return_note_items.material_id were `not null` (0069),
--    which meant a BOM line with no matching materials-catalog row could
--    never be dispatched or returned at all — the match queue built into
--    Dispatch (dispatch/new/match-materials-panel.tsx) is still there for
--    whoever wants to link a line to real inventory, but it's no longer
--    a hard gate. An unmatched line's material_transactions/stock-ledger
--    entry is simply skipped (there's no material to move in the
--    ledger); the DC/return note itself still lists and prints it.
--
-- 2. "keep the DC selection also in the same order as the BOM." Neither
--    the BOM tab's own query nor Dispatch's ever had a real tie-breaker
--    within a category — `.order('category')` alone (or no ORDER BY at
--    all, Dispatch's case) leaves same-category row order to whatever a
--    given query plan happens to return, which isn't guaranteed to match
--    between two different queries over the same rows. sort_order is the
--    BOM's own generation-time sequence (bom-generator.ts's fixed item
--    order), persisted once and read back everywhere a BOM's items are
--    listed — BOM tab, printed BOM, and Dispatch all order by it now, so
--    "same order as the BOM" is structural, not coincidental.

alter table delivery_challan_items alter column material_id drop not null;
alter table material_return_note_items alter column material_id drop not null;

alter table bom_items add column sort_order integer;
create index on bom_items (bom_id, sort_order);

-- Backfill for BOMs generated before this column existed — an approximation
-- (category, then description) since the original generation sequence
-- wasn't persisted for them; every BOM generated from here on gets its
-- real sequence written at save time (generate-bom/actions.ts).
with ranked as (
  select bom_item_id, row_number() over (partition by bom_id order by category, description) as rn
  from bom_items
  where sort_order is null
)
update bom_items b set sort_order = r.rn
from ranked r
where r.bom_item_id = b.bom_item_id;

-- bom_item_variance (0013) needs sort_order added to its select list so
-- Dispatch (and anything else reading the view) can order by it — every
-- other column/join here is unchanged from 0013's definition.
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
  b.material_id,
  b.sort_order
from bom_items b
join boms bm on bm.bom_id = b.bom_id
left join movement m on m.bom_item_id = b.bom_item_id
left join cost c on c.bom_item_id = b.bom_item_id;
