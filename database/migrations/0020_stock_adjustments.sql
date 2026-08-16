-- ProjectPulse — Monthly Stock Adjustments (Physical Count vs. Book Stock)
-- Follows 0002-0019. Consolidated from docs/projectpulse-handover.md
-- Section 53.

-- ============================================================
-- Real bug caught while designing this: sold_direct never left stock
-- ============================================================

-- material_stock (0003) only ever netted purchased/issued_to_site/
-- returned_to_warehouse. 0008 added the 'sold_direct' movement type and
-- its own comment claimed "material_stock already nets every movement
-- type that isn't purchased" — but the view itself was never actually
-- updated to include it. A direct sale (heat pump, solar dryer, sold at
-- retail off existing stock, 0008) has been reducing nothing in
-- current_stock since 0008 shipped. Fixed here, folded into the same
-- recreate as the new stock_adjustment movement below.

-- ============================================================
-- A physical count will disagree with the book, every month
-- ============================================================

-- Real, recurring need: a monthly physical stock count against what
-- material_stock says should be on hand. The difference is real —
-- missing stock (shrinkage, miscount, damage written off) or, less
-- often, a surplus nobody logged. This needs to be recorded as its own
-- kind of movement, not force-fit into purchased/issued/returned, none
-- of which describe "we counted and it didn't match."

alter table material_transactions drop constraint material_transactions_movement_type_check;
alter table material_transactions add constraint material_transactions_movement_type_check
  check (movement_type in ('purchased','issued_to_site','returned_to_warehouse','sold_direct','stock_adjustment'));

-- Unlike every other movement_type, a stock_adjustment's quantity is
-- signed: negative for missing stock, positive for a surplus found.
-- That's a deliberate exception to the all-positive convention every
-- other movement_type follows — an adjustment is inherently "book vs.
-- reality," which can go either direction from one count, and forcing
-- it into two artificial movement types (shortage/surplus) would add
-- complexity for no real benefit over just summing a signed value.

create table stock_adjustments (
  stock_adjustment_id   uuid primary key default gen_random_uuid(),
  material_id            uuid not null references materials(material_id),
  adjustment_date          date not null default current_date,
  book_quantity             numeric(14,3) not null,   -- material_stock.current_stock at the moment of counting
  counted_quantity           numeric(14,3) not null,   -- actual physical count
  variance_quantity            numeric(14,3) generated always as (counted_quantity - book_quantity) stored,
  reason                         text,                  -- free text: 'physical count shrinkage', 'damaged', 'found extra', 'miscount correction'
  counted_by                      uuid references employees(employee_id),
  transaction_id                    uuid references material_transactions(transaction_id),
  created_at                          timestamptz not null default now()
);

create index on stock_adjustments (material_id);
create index on stock_adjustments (adjustment_date);

-- transaction_id is the material_transactions row (movement_type =
-- 'stock_adjustment', quantity = variance_quantity, signed) that this
-- count actually posted — stock_adjustments is the human-readable record
-- of the count itself (what was expected vs. what was found and why);
-- the transaction is what material_stock actually nets against. Written
-- together in one action — a physical count is a person typing in a
-- number they just counted, not an AI extraction with a confidence
-- score, so there's no separate draft/confirm stage needed here the way
-- there is everywhere else in this schema.

create or replace view material_stock as
select
  material_id,
  coalesce(sum(quantity) filter (where movement_type = 'purchased'), 0)
    - coalesce(sum(quantity) filter (where movement_type = 'issued_to_site'), 0)
    + coalesce(sum(quantity) filter (where movement_type = 'returned_to_warehouse'), 0)
    - coalesce(sum(quantity) filter (where movement_type = 'sold_direct'), 0)
    + coalesce(sum(quantity) filter (where movement_type = 'stock_adjustment'), 0) as current_stock
from material_transactions
group by material_id;

-- ============================================================
-- The report the monthly count is actually for
-- ============================================================

create view stock_adjustment_summary as
select
  sa.stock_adjustment_id,
  sa.material_id,
  m.category,
  m.canonical_name,
  sa.adjustment_date,
  sa.book_quantity,
  sa.counted_quantity,
  sa.variance_quantity,
  sa.reason,
  e.name as counted_by,
  lp.rate as last_purchase_rate,
  sa.variance_quantity * coalesce(lp.rate, 0) as variance_value
from stock_adjustments sa
join materials m on m.material_id = sa.material_id
left join employees e on e.employee_id = sa.counted_by
left join material_last_purchase lp on lp.material_id = sa.material_id;

-- variance_value puts a rupee figure on "missing stock," not just a
-- quantity — a monthly report grouping this by adjustment_date is the
-- actual deliverable: what went missing this month, how much it's
-- worth, and (from the reason column) whether there's a pattern instead
-- of just noise.
