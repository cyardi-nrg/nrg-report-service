-- NRG SolarConnect — Purchase Orders and Inventory Shortfall
-- Follows 0002_core_schema.sql. Consolidated from
-- docs/nrg-solarconnect-handover.md Section 29.
--
-- Adds Open Order tracking (distinct from a completed 'purchased'
-- material_transactions row) and the derived stock/requirement/shortfall
-- views that answer: "what do I have, what's on order, and what do I
-- need to buy now that a project's BOM has been extracted?"

-- ============================================================
-- Purchase_Orders / Purchase_Order_Items
-- ============================================================

create table purchase_orders (
  purchase_order_id   uuid primary key default gen_random_uuid(),
  vendor_id            uuid not null references partners(partner_id),
  source_document_id   uuid references documents(document_id),  -- the NRG-to-vendor PO document itself
  order_date           date,
  status               text not null default 'open'
                        check (status in ('open','partially_received','received','cancelled')),
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now()
);

create table purchase_order_items (
  purchase_order_item_id uuid primary key default gen_random_uuid(),
  purchase_order_id       uuid not null references purchase_orders(purchase_order_id),
  material_id              uuid not null references materials(material_id),
  ordered_quantity         numeric(14,3) not null,
  rate                     numeric(14,2),
  created_at               timestamptz not null default now()
);

create index on purchase_order_items (purchase_order_id);
create index on purchase_order_items (material_id);

-- received_quantity is deliberately NOT a stored column here — it's derived
-- by summing material_transactions rows that reference the line (same
-- "compute, don't store" pattern as bom_item_variance).

-- ============================================================
-- Alterations to tables from 0002
-- ============================================================

alter table material_transactions
  add column purchase_order_item_id uuid references purchase_order_items(purchase_order_item_id);
  -- populated only when a 'purchased' row is receiving against an open PO line

alter table material_transactions
  add column serial_numbers text[];
  -- for serialized items (panels, inverters): the specific serial(s) this row covers.
  -- Null for bulk materials (cable, pipe, etc).

alter table materials
  add column reorder_level numeric(14,3);
  -- business judgment, entered directly by a user — not AI-extracted

-- ============================================================
-- Derived views — current stock, open orders, outstanding BOM
-- requirement, and the resulting shortfall per material
-- ============================================================

create view material_stock as
select
  material_id,
  coalesce(sum(quantity) filter (where movement_type = 'purchased'), 0)
    - coalesce(sum(quantity) filter (where movement_type = 'issued_to_site'), 0)
    + coalesce(sum(quantity) filter (where movement_type = 'returned_to_warehouse'), 0) as current_stock
from material_transactions
group by material_id;

create view material_open_orders as
select
  poi.material_id,
  sum(poi.ordered_quantity - coalesce(received.qty, 0)) as open_order_quantity
from purchase_order_items poi
join purchase_orders po on po.purchase_order_id = poi.purchase_order_id
left join (
  select purchase_order_item_id, sum(quantity) as qty
  from material_transactions
  where movement_type = 'purchased' and purchase_order_item_id is not null
  group by purchase_order_item_id
) received on received.purchase_order_item_id = poi.purchase_order_item_id
where po.status in ('open','partially_received')
group by poi.material_id;

create view material_requirement as
-- outstanding BOM demand: planned quantity not yet dispatched, across active projects
select
  bi.material_id,
  sum(bi.planned_quantity - coalesce(issued.qty, 0)) as outstanding_requirement
from bom_items bi
join boms b on b.bom_id = bi.bom_id
join projects p on p.project_id = b.project_id
left join (
  select bom_item_id, sum(quantity) as qty
  from material_transactions
  where movement_type = 'issued_to_site'
  group by bom_item_id
) issued on issued.bom_item_id = bi.bom_item_id
where p.status = 'active' and bi.material_id is not null
group by bi.material_id
having sum(bi.planned_quantity - coalesce(issued.qty, 0)) > 0;

create view material_shortfall as
select
  m.material_id,
  m.category,
  m.canonical_name,
  m.default_unit,
  m.reorder_level,
  coalesce(s.current_stock, 0) as current_stock,
  coalesce(o.open_order_quantity, 0) as open_order_quantity,
  coalesce(r.outstanding_requirement, 0) as outstanding_requirement,
  coalesce(r.outstanding_requirement, 0) - (coalesce(s.current_stock, 0) + coalesce(o.open_order_quantity, 0)) as shortfall
from materials m
left join material_stock s on s.material_id = m.material_id
left join material_open_orders o on o.material_id = m.material_id
left join material_requirement r on r.material_id = m.material_id;

-- material_shortfall.shortfall > 0  -> what needs to be purchased right now,
--   driven automatically by whatever's in bom_items for active projects.
-- material_stock.current_stock < materials.reorder_level -> general low-stock
--   alert, independent of any specific project.
