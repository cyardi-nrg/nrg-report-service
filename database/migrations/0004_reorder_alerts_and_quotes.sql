-- NRG SolarConnect — Reorder Alerts, Vendor Quotes, Price Comparison
-- Follows 0002_core_schema.sql and 0003_purchase_orders_and_inventory.sql.
-- Consolidated from docs/nrg-solarconnect-handover.md Section 30.

-- ============================================================
-- Vendor_Quotes / Vendor_Quote_Items
-- ============================================================

create table vendor_quotes (
  vendor_quote_id      uuid primary key default gen_random_uuid(),
  vendor_id            uuid not null references partners(partner_id),
  source_document_id   uuid references documents(document_id),  -- the uploaded quote (PDF/photo/email)
  quote_date           date,
  valid_until          date,
  terms                text,          -- payment/delivery terms, as extracted, free text
  is_selected          boolean not null default false,   -- did this quote win the reorder decision
  purchase_order_id    uuid references purchase_orders(purchase_order_id),  -- set once this quote converts into an actual PO
  created_at           timestamptz not null default now()
);

create table vendor_quote_items (
  vendor_quote_item_id  uuid primary key default gen_random_uuid(),
  vendor_quote_id       uuid not null references vendor_quotes(vendor_quote_id),
  material_id           uuid not null references materials(material_id),
  quantity              numeric(14,3),
  rate                  numeric(14,2) not null,
  ai_confidence         numeric(3,2),
  created_at            timestamptz not null default now()
);

create index on vendor_quote_items (vendor_quote_id);
create index on vendor_quote_items (material_id);

-- Every uploaded quote is stored permanently, selected or not — unselected
-- quotes still feed price history and future cost estimation.

-- ============================================================
-- Reorder alerting
-- ============================================================

alter table materials
  add column reorder_responsible_employee_id uuid references employees(employee_id);
  -- optional specific owner for this material's alerts; falls back to a
  -- general purchase-role broadcast at the application layer if null

create table reorder_alerts (
  reorder_alert_id             uuid primary key default gen_random_uuid(),
  material_id                  uuid not null references materials(material_id),
  detected_at                  timestamptz not null default now(),
  stock_at_detection           numeric(14,3) not null,
  reorder_level_at_detection   numeric(14,3) not null,
  status                       text not null default 'open'
                                check (status in ('open','acknowledged','ordered','dismissed')),
  resolved_by                  uuid references employees(employee_id),
  resolved_at                  timestamptz,
  created_at                   timestamptz not null default now()
);

create index on reorder_alerts (material_id);
create index on reorder_alerts (status);

-- This table is what stops reminders from repeating for the same unresolved
-- shortage: a scheduled job checks material_stock.current_stock <=
-- materials.reorder_level, and only inserts a new row (and sends a
-- notification — email/WhatsApp/push, application-layer, not the DB's job)
-- when no 'open'/'acknowledged' alert already exists for that material.
-- Clears to 'ordered' automatically once a purchase_orders row is created
-- for that material, or 'dismissed' by a human.

-- ============================================================
-- Last purchase price + quote comparison
-- ============================================================

create view material_last_purchase as
select distinct on (material_id)
  material_id,
  vendor_id,
  rate,
  transaction_date
from material_transactions
where movement_type = 'purchased'
order by material_id, transaction_date desc;

create view material_quote_comparison as
select
  vqi.material_id,
  vq.vendor_id,
  vq.vendor_quote_id,
  vqi.rate as quoted_rate,
  vq.quote_date,
  vq.valid_until,
  vq.is_selected,
  lp.rate as last_purchase_rate,
  lp.transaction_date as last_purchase_date,
  vqi.rate - lp.rate as delta_vs_last_purchase
from vendor_quote_items vqi
join vendor_quotes vq on vq.vendor_quote_id = vqi.vendor_quote_id
left join material_last_purchase lp on lp.material_id = vqi.material_id
order by vqi.material_id, vqi.rate;

-- material_quote_comparison is the reorder-time screen: every quote line for
-- a material next to what it was last actually bought for, delta already
-- computed, cheapest first.
