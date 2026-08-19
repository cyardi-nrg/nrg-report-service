-- NRG SolarConnect — Vendor Contact Person, Quote Comparison Approval Workflow,
-- and a Stock Statement View Fix
-- Follows 0002-0013. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 41.

-- ============================================================
-- Vendor contact person
-- ============================================================

-- partners (0002) already carries name/category/contact_number/email/
-- gstin/address for vendors — no separate "vendors" table needed,
-- vendors are just partners with category = 'vendor'. The one real gap:
-- no field for the specific person to call at that vendor.

alter table partners add column contact_person text;

-- ============================================================
-- Quote comparison, sent for approval, PO raised on the spot
-- ============================================================

-- material_quote_comparison (0004) already compares every stored quote
-- for one material against the last price paid. What's missing: an
-- explicit batch — "these 2-4 vendor quotes are being compared for
-- this reorder decision" — and an approval gate before a quote can
-- turn into a PO. Today vendor_quotes.is_selected/purchase_order_id
-- (0004) let MP flip a quote straight to a PO with no owner sign-off
-- in between.

create table quote_comparison_requests (
  quote_comparison_request_id  uuid primary key default gen_random_uuid(),
  created_by                    uuid references employees(employee_id),
  status                         text not null default 'draft'
                                  check (status in ('draft','submitted','approved','rejected')),
  requested_at                    timestamptz,
  decided_by                      uuid references employees(employee_id),
  decided_at                      timestamptz,
  decision_notes                  text,
  created_at                       timestamptz not null default now()
);

alter table vendor_quotes
  add column comparison_request_id uuid references quote_comparison_requests(quote_comparison_request_id);

create index on vendor_quotes (comparison_request_id);

-- MP builds a request in 'draft' (scan/enter quotes from 2-4 vendors,
-- covering one or several materials in one batch), flips it to
-- 'submitted' when ready, the owner reviews the comparison and sets
-- 'approved' or 'rejected' with decision_notes. Only once 'approved'
-- should the app let is_selected be set and a purchase_orders row get
-- created from the winning vendor_quotes — that gate lives at the
-- application layer, this table just gives it something to check
-- against. Sending the comparison sheet for approval (email/WhatsApp/
-- push) is an app-layer job, same as reorder_alerts (0004) — the DB
-- only tracks state, it doesn't send anything.

-- ============================================================
-- Stock statement view fix: make wasn't there to be shown
-- ============================================================

-- materials.make (0013) landed after stock_statement_summary (0007)
-- was already written, so a statement couldn't distinguish Adani 545W
-- from Waree 545W within the same stock_group — exactly the level of
-- detail a real statement needs. Additive column at the end of the
-- select list.

-- Postgres's CREATE OR REPLACE VIEW only allows appending columns at the
-- end of the select list, never inserting one mid-list (it errors:
-- "cannot change name of view column ... to ...") — make goes last,
-- keeping every pre-existing column in its original position.
create or replace view stock_statement_summary as
select
  ss.statement_period, ss.status,
  m.stock_group, m.category, m.material_id, m.canonical_name,
  ssi.declared_quantity, ssi.rate, ssi.declared_quantity * ssi.rate as amount,
  m.make
from stock_statement_items ssi
join stock_statements ss on ss.stock_statement_id = ssi.stock_statement_id
join materials m on m.material_id = ssi.material_id;
