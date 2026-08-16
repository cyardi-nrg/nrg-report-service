-- NRG SolarConnect — A PO's Delivery Challan and Invoice Reconcile Into
-- One Purchase, Never Three
-- Follows 0002-0026. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 67.

-- ============================================================
-- The real risk: PO -> inward DC -> Invoice describe ONE physical
-- receipt, not three separate purchases
-- ============================================================

-- Real, concrete scenario: order 100m of DC Cable 6 sq mm on a PO.
-- The vendor's own inward delivery challan arrives first, sometimes
-- for a slightly different quantity than ordered (100-120m, since
-- cable ships in fixed bundle lengths) — that's the moment the
-- material physically enters the warehouse. Days later, the invoice
-- arrives for the same shipment, often at a further-adjusted final
-- quantity (110m) and the actual agreed rate. Three documents, one
-- real event. Nothing before this migration stopped each of them from
-- independently creating its own 'purchased' material_transactions
-- row — a PO doesn't (material_open_orders, Section 3, already covers
-- that correctly), but a DC-triggered row and a later invoice-
-- triggered row for the *same* shipment both fit
-- material_transactions.source_document_id's existing comment
-- ("Purchase Invoice / Delivery Challan / ...") with nothing to say
-- "these two describe the same receipt." Left alone, that's 100m (DC)
-- + 110m (invoice) = 210m credited to stock for a shipment that
-- actually put 110m on the shelf.

-- ============================================================
-- Fix: one 'purchased' row per physical receipt. Whichever document
-- arrives second reconciles into that row, never inserts a new one.
-- ============================================================

alter table material_transactions add column invoice_document_id uuid references documents(document_id);
alter table material_transactions add column invoice_match_status text
  default 'pending_invoice'
  check (invoice_match_status in ('pending_invoice', 'suggested', 'confirmed'));
alter table material_transactions add column invoiced_quantity numeric(14,3);
alter table material_transactions add column quantity_variance numeric(14,3)
  generated always as (invoiced_quantity - quantity) stored;

-- Meaningful only for movement_type = 'purchased' — same convention
-- already used for rate/vendor_id ("populated for 'purchased'; null
-- for issue/return", Section 19), not a new enforced pattern.

-- Whichever of DC or Invoice is AI-extracted first creates the single
-- 'purchased' row as today: quantity = what that document states,
-- rate = what it states (often null on a DC — plenty of vendors don't
-- print pricing on a delivery challan at all, only on the invoice),
-- invoice_match_status defaults 'pending_invoice'.
--
-- When the second document (almost always the invoice) is extracted,
-- it does NOT create a new row. AI matches it against an existing
-- 'purchased' row via purchase_order_item_id (strongest signal — the
-- specific open PO line still awaiting invoice) or, with no PO,
-- vendor_id + material_id + date proximity among rows still
-- invoice_match_status = 'pending_invoice'. Same AI-suggests/human-
-- confirms pattern as everywhere else in this schema
-- (payment_receipts.match_status, project_costs.assignment_status):
-- a match starts 'suggested', a human confirms it, invoice_match_status
-- moves to 'confirmed'. On confirm:
--   - rate is set/updated to the invoice's rate (it was provisional or
--     null before — filling it in is not overwriting real evidence,
--     it's completing it).
--   - invoiced_quantity is set to the invoice's stated quantity —
--     kept in its own column, deliberately never overwriting quantity
--     itself. quantity stays exactly what the DC recorded at physical
--     receipt, permanently — the warehouse's own count of what came
--     off the truck, never silently corrected after the fact.
--   - quantity_variance falls out automatically (generated column) —
--     the bundle-size gap between what the DC said arrived and what
--     the invoice finally bills for, visible, never hidden inside a
--     single mutated number.

create or replace view material_stock as
select
  material_id,
  coalesce(sum(case when movement_type = 'purchased' then coalesce(invoiced_quantity, quantity) end), 0)
    - coalesce(sum(quantity) filter (where movement_type = 'issued_to_site'), 0)
    + coalesce(sum(quantity) filter (where movement_type = 'returned_to_warehouse'), 0)
    - coalesce(sum(quantity) filter (where movement_type = 'sold_direct'), 0)
    + coalesce(sum(quantity) filter (where movement_type = 'stock_adjustment'), 0) as current_stock
from material_transactions
group by material_id;

-- coalesce(invoiced_quantity, quantity) for 'purchased' specifically —
-- once an invoice reconciles, its quantity is the better-known true
-- figure (a DC's printed number is often nominal; a bundle actually
-- gets counted/weighed at invoicing), so stock should reflect that,
-- not silently stay pinned to the DC's original estimate. Before
-- reconciliation, invoiced_quantity is null and this falls back to
-- quantity exactly as before — no behavior change until an invoice
-- actually arrives.

create or replace view material_purchase_running_avg as
select
  transaction_id,
  material_id,
  transaction_date,
  coalesce(invoiced_quantity, quantity) as quantity,
  rate,
  sum(coalesce(invoiced_quantity, quantity)) over w as cumulative_quantity,
  sum(coalesce(invoiced_quantity, quantity) * rate) over w as cumulative_value,
  (sum(coalesce(invoiced_quantity, quantity) * rate) over w)
    / nullif(sum(coalesce(invoiced_quantity, quantity)) over w, 0) as weighted_avg_rate
from material_transactions
where movement_type = 'purchased' and rate is not null
window w as (partition by material_id order by transaction_date, transaction_id);

-- Same reasoning, one level deeper: the weighted-average purchase rate
-- (Section 31, the rate every BOM/margin/cost-per-watt figure in this
-- schema ultimately traces back to) should weight by the true received
-- quantity too, not an unreconciled DC estimate. rate is not null still
-- gates this exactly as before — a DC-only row with no rate yet simply
-- doesn't contribute until the invoice fills rate in.

-- ============================================================
-- A genuinely new, useful report this makes possible: goods
-- received but not yet invoiced
-- ============================================================

create view pending_invoice_purchases as
select
  mt.transaction_id,
  mt.material_id,
  m.category,
  m.canonical_name,
  mt.vendor_id,
  p.name as vendor_name,
  mt.quantity as received_quantity,
  mt.rate,
  mt.transaction_date as received_date,
  current_date - mt.transaction_date as days_outstanding,
  mt.invoice_match_status
from material_transactions mt
join materials m on m.material_id = mt.material_id
left join partners p on p.partner_id = mt.vendor_id
where mt.movement_type = 'purchased' and mt.invoice_match_status != 'confirmed';

-- A real accounts-payable gap this schema never had a way to surface:
-- material physically received, sitting in stock, with no invoice
-- reconciled against it yet — the exact receipts a vendor might be
-- late billing for, or NRG SolarConnect might be late matching. Purchase/
-- Accounts-visible, same reporting pattern as everything else on
-- Reports (Section 52).
