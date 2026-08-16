-- NRG SolarConnect — Direct (Non-Project) Sales and Stock Movements
-- Follows 0002-0007. NRG also stocks and sells product lines that never
-- go through the project/BOM/milestone apparatus — Havells heat pumps,
-- solar dryers, solar water heaters, sold at retail off existing stock
-- rather than installed as a tracked project. Confirmed: these need a
-- distinct stock-movement type and an invoice that can stand on its own
-- without a project, but do NOT need financial_obligations' quoted/
-- invoiced/received funnel — that stays project-only, unchanged.
--
-- materials.category/aliases (0002) already support new sized models
-- (e.g. "Heat Pump" / "200 LTR", "Heat Pump" / "300 LTR") as ordinary
-- new rows, added the same way any other material is — AI extraction
-- off a scanned invoice, matched or created via aliases. No change
-- needed there.

-- ============================================================
-- New stock-movement type: sold_direct
-- ============================================================

alter table material_transactions drop constraint material_transactions_movement_type_check;
alter table material_transactions add constraint material_transactions_movement_type_check
  check (movement_type in ('purchased','issued_to_site','returned_to_warehouse','sold_direct'));

-- 'sold_direct' is stock leaving without a project — distinct from
-- 'issued_to_site', which specifically means project-site dispatch and
-- feeds bom_item_variance. A sold_direct row always has project_id null
-- (already nullable) and bom_item_id null; material_stock/material_shortfall
-- (0003) already net every movement_type that isn't 'purchased' against
-- stock, so a sold_direct row reduces stock correctly with no further
-- view changes needed.

alter table material_transactions
  add column sales_invoice_item_id uuid references sales_invoice_items(invoice_item_id);

-- Always good to have, per NRG: links a sold_direct row back to exactly
-- which invoice line it was sold against, for traceability. Nullable —
-- only populated for sold_direct rows; purchased/issued_to_site/
-- returned_to_warehouse rows leave it null.

create index on material_transactions (sales_invoice_item_id);

-- ============================================================
-- sales_invoices: allow a direct sale with no project
-- ============================================================

alter table sales_invoices alter column project_id drop not null;
alter table sales_invoices add column customer_id uuid references customers(customer_id);

alter table sales_invoices add constraint sales_invoices_project_or_customer_check
  check (project_id is not null or customer_id is not null);

-- Project-linked invoices are unaffected — project_id is still set exactly
-- as before, customer_id stays null (the customer is reachable via
-- projects.customer_id). A direct sale sets customer_id instead and
-- leaves project_id null. financial_obligations deliberately keeps its
-- own project_id not null as-is: it models the multi-part quoted/
-- invoiced/received funnel (GEDA fees, DISCOM charges, goods/installation
-- split) that a straightforward retail sale doesn't need — sales_invoices
-- plus payment_receipts (project_id already nullable, 0006) is enough on
-- its own for a direct sale.
