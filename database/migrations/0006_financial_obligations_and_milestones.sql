-- NRG SolarConnect — Financial Obligations and Project Milestones
-- Follows 0002-0005. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 32. These are the last two core tables that had only ever
-- been described in prose (Sections 6, 15, 16, 21) — prerequisites for
-- dashboards, margin/cash-flow reporting, and Timeline Intelligence.

-- ============================================================
-- Financial Obligations
-- ============================================================

create table financial_obligations (
  financial_obligation_id  uuid primary key default gen_random_uuid(),
  project_id               uuid not null references projects(project_id),
  obligation_type          text not null,
                            -- e.g. 'nrg_revenue_goods' | 'nrg_revenue_installation' | 'nrg_revenue_addon' |
                            -- 'geda_registration' | 'discom_feasibility_charge' | 'meter_charges' |
                            -- 'discom_strengthening_charge' | 'service_visit_charge' | 'discount' | 'other'
                            -- free text, app-level reference list — new pass-through charge types may appear
                            -- as NRG expands to other states/DISCOMs
  payable_to               text not null check (payable_to in ('nrg','discom','geda','ceig','other_third_party')),
  settlement_method        text not null
                            check (settlement_method in ('via_nrg_invoice','via_nrg_debit_note','direct_by_customer')),
                            -- direct_by_customer: some charges never touch NRG's invoice at all (confirmed by a real PO)
  quoted_amount            numeric(14,2),
  status                   text not null default 'quoted'
                            check (status in ('quoted','invoiced','partially_paid','paid','pending','cancelled')),
  source_document_id       uuid references documents(document_id),   -- the Quote/PO line this was seeded from
  reference_receipt_no     text,   -- for direct/debit-note-settled items: the DGVCL/GEDA receipt number
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now()
);

create index on financial_obligations (project_id);

create table sales_invoices (
  invoice_id            uuid primary key default gen_random_uuid(),
  project_id            uuid not null references projects(project_id),
  source_document_id    uuid not null references documents(document_id),
  invoice_type          text not null
                         check (invoice_type in ('quote','proforma_invoice','tax_invoice','debit_note','service_invoice')),
  invoice_number        text,
  invoice_date          date,
  total_amount          numeric(14,2),
  ai_confidence         numeric(3,2),
  extraction_status     text not null default 'ai_extracted'
                         check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at            timestamptz not null default now()
);

create index on sales_invoices (project_id);

create table sales_invoice_items (
  invoice_item_id          uuid primary key default gen_random_uuid(),
  invoice_id               uuid not null references sales_invoices(invoice_id),
  description              text not null,      -- e.g. "24.6 KW Solar Power Pack", "Installation (Solar Rooftop)"
  hsn_sac_code             text,               -- 85414300 (goods, 5% GST) vs 998717 (installation, 18%) vs 998729 (visit charge, 18%)
  gst_rate                 numeric(5,2),
  amount                   numeric(14,2) not null,
  financial_obligation_id  uuid references financial_obligations(financial_obligation_id),  -- which obligation this line settles
  created_at               timestamptz not null default now()
);

create index on sales_invoice_items (invoice_id);
create index on sales_invoice_items (financial_obligation_id);

create table payment_receipts (
  payment_receipt_id       uuid primary key default gen_random_uuid(),
  project_id               uuid references projects(project_id),        -- nullable until matched
  source_document_id       uuid references documents(document_id),      -- receipt book / cheque photo / UPI screenshot
  financial_obligation_id  uuid references financial_obligations(financial_obligation_id),
  invoice_id               uuid references sales_invoices(invoice_id),  -- set directly when the receipt names an invoice no.
  amount                   numeric(14,2) not null,
  payment_date             date,
  payment_method           text check (payment_method in ('cash','cheque','upi','neft','rtgs','other')),
  payer_name               text,           -- as extracted — the fuzzy-match anchor when there's no invoice reference
  reference_number         text,           -- transaction ID / RRN / cheque number, as available
  match_status             text not null default 'unmatched'
                            check (match_status in ('unmatched','suggested','confirmed','disputed')),
  match_confidence         numeric(3,2),
  ai_confidence            numeric(3,2),
  created_at               timestamptz not null default now()
);

create index on payment_receipts (project_id);
create index on payment_receipts (financial_obligation_id);
create index on payment_receipts (match_status);

-- match_status is the answer to most UPI/Paytm screenshots carrying no
-- invoice reference: AI proposes a match by amount+date+payer name
-- ('suggested', with match_confidence), and only 'confirmed' rows count
-- as real received money — same pattern as drive_folder_import_candidates
-- and reorder_alerts.

create view financial_obligation_reconciliation as
select
  fo.financial_obligation_id,
  fo.project_id,
  fo.obligation_type,
  fo.payable_to,
  fo.settlement_method,
  fo.status,
  fo.quoted_amount,
  coalesce(inv.invoiced_amount, 0) as invoiced_amount,
  coalesce(pay.received_amount, 0) as received_amount,
  coalesce(inv.invoiced_amount, 0) - coalesce(pay.received_amount, 0) as pending_amount
from financial_obligations fo
left join (
  select financial_obligation_id, sum(amount) as invoiced_amount
  from sales_invoice_items
  where financial_obligation_id is not null
  group by financial_obligation_id
) inv on inv.financial_obligation_id = fo.financial_obligation_id
left join (
  select financial_obligation_id, sum(amount) as received_amount
  from payment_receipts
  where financial_obligation_id is not null and match_status = 'confirmed'
  group by financial_obligation_id
) pay on pay.financial_obligation_id = fo.financial_obligation_id;

create view project_financial_summary as
select
  project_id,
  sum(quoted_amount) as total_quoted,
  sum(invoiced_amount) as total_invoiced,
  sum(received_amount) as total_received,
  sum(pending_amount) as total_pending
from financial_obligation_reconciliation
group by project_id;

-- Tally reconciliation — kept separate from payment_receipts rather than
-- forcing Tally's four voucher types (Payment/Receipt/Sales/Journal) into
-- that table's shape.

create table tally_ledger_entries (
  tally_entry_id                    uuid primary key default gen_random_uuid(),
  project_id                        uuid references projects(project_id),   -- nullable until matched, by customer name / narration
  source_document_id                uuid references documents(document_id), -- the uploaded Tally export
  entry_date                        date not null,
  voucher_type                      text check (voucher_type in ('payment','receipt','sales','journal','other')),
  voucher_number                    text,
  particulars                       text,     -- free-text narration — receipt numbers and TDS math live here, not in structured columns
  debit_amount                      numeric(14,2),
  credit_amount                     numeric(14,2),
  matched_financial_obligation_id   uuid references financial_obligations(financial_obligation_id),
  matched_payment_receipt_id        uuid references payment_receipts(payment_receipt_id),
  match_status                      text not null default 'unmatched'
                                     check (match_status in ('unmatched','suggested','confirmed','discrepancy')),
  created_at                        timestamptz not null default now()
);

create index on tally_ledger_entries (project_id);
create index on tally_ledger_entries (match_status);

-- 'discrepancy' is deliberately distinct from 'unmatched': it means AI
-- found a likely corresponding entry but the amounts/parties don't quite
-- agree — surface that, don't silently drop it.

-- ============================================================
-- Project Milestones
-- ============================================================

create table project_milestones (
  project_milestone_id  uuid primary key default gen_random_uuid(),
  project_id            uuid not null references projects(project_id),
  track                 text not null
                         check (track in ('geda_registration','discom_feasibility','ceig_inspection','site_installation')),
                         -- NOTE: no 'discom_subsidy' track — the subsidy pays directly to the customer, never
                         -- touching NRG, so it's out of scope entirely (confirmed decision)
  milestone_key         text not null,
                         -- free text, app-level reference list per (project_type, track) — e.g. site_installation's
                         -- real vocabulary is structure_fitting/panel_fitting/cement_grouting/inverter/acdb_dcdb/
                         -- earthing/la/discom_submit/meter_install/monitoring_setup; geda_registration differs for
                         -- residential vs. commercial project_type
  status                text not null default 'not_started'
                         check (status in ('not_started','in_progress','done')),
  completed_date         date,     -- nullable — some source documents are only a Y/N flag, not a date
  source_document_id     uuid references documents(document_id),
  vendor_id              uuid references partners(partner_id),   -- which fabrication/electrical vendor executed this stage, where applicable
  ai_confidence           numeric(3,2),
  extraction_status       text not null default 'ai_extracted'
                           check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at               timestamptz not null default now(),
  updated_at               timestamptz not null default now(),
  unique (project_id, track, milestone_key)
);

create index on project_milestones (project_id);
create index on project_milestones (track, status);

create view project_milestone_durations as
select
  project_id,
  track,
  milestone_key,
  completed_date,
  completed_date - lag(completed_date) over (partition by project_id, track order by completed_date) as days_since_previous_milestone
from project_milestones
where status = 'done' and completed_date is not null;

-- Assumes milestones within a track are substantially achieved in real
-- sequence (they're process gates — can't submit to GEB before
-- installation completes), so no separate stored "started_date" per
-- milestone is needed for duration reporting.
