-- NRG SolarConnect — Dispatch (Delivery Challan) and Material Return generation
-- Follows 0002-0068.
--
-- delivery_challans (0010) was schema'd with exactly the right header shape
-- (dc_number, project_id, dispatch_date, vehicle_or_driver, status, total_value,
-- eway_bill_number, generated_document_id, created_by) but no line-items table
-- ever existed for it, and no application code ever wrote delivery_challan_id or
-- bom_item_id onto material_transactions — so bom_item_variance's
-- dispatched_quantity/returned_quantity have read as 0 in production since day
-- one, even though real material has genuinely gone out to site. This migration
-- adds the missing line-items table so a real "Generate DC" flow (tick BOM items,
-- adjust quantity, print) can finally populate those columns.
--
-- Material Return gets the same treatment, its own header + line-items pair,
-- reusing the existing 'returned_to_warehouse' movement type on
-- material_transactions — no new movement type, no new column there. A return's
-- own transactions are found via material_transactions.source_document_id =
-- material_return_notes.generated_document_id, the same generated-document
-- pattern used everywhere else in this schema (quotes, POs, commissioning
-- reports) rather than a second parallel FK.

create table delivery_challan_items (
  delivery_challan_item_id uuid primary key default gen_random_uuid(),
  delivery_challan_id      uuid not null references delivery_challans(delivery_challan_id) on delete cascade,
  -- Nullable on purpose — a DC was never meant to be capped at or even
  -- require a BOM line (a real on-site shortfall can mean dispatching
  -- something the BOM never planned for at all).
  bom_item_id              uuid references bom_items(bom_item_id),
  material_id              uuid not null references materials(material_id),
  description              text not null,
  unit                     text not null,
  quantity                 numeric(14,3) not null check (quantity > 0),
  -- Informational only — printed on the DC / used for the e-way bill
  -- total_value threshold check. Real BOM costing stays weighted-average
  -- via material_transactions/material_transaction_cost, never re-derived
  -- from this line's own rate.
  rate                     numeric(14,2),
  resulting_transaction_id uuid references material_transactions(transaction_id),
  created_at               timestamptz not null default now()
);

create index on delivery_challan_items (delivery_challan_id);
create index on delivery_challan_items (bom_item_id);

create table material_return_notes (
  return_note_id         uuid primary key default gen_random_uuid(),
  return_note_number     text not null unique,
  project_id             uuid not null references projects(project_id),
  return_date            date not null default current_date,
  status                 text not null default 'issued' check (status in ('issued','cancelled')),
  notes                  text,
  generated_document_id  uuid references documents(document_id),
  created_by             uuid references employees(employee_id),
  created_at             timestamptz not null default now()
);

create table material_return_note_items (
  return_note_item_id      uuid primary key default gen_random_uuid(),
  return_note_id           uuid not null references material_return_notes(return_note_id) on delete cascade,
  bom_item_id              uuid references bom_items(bom_item_id),
  material_id              uuid not null references materials(material_id),
  description              text not null,
  unit                     text not null,
  quantity                 numeric(14,3) not null check (quantity > 0),
  resulting_transaction_id uuid references material_transactions(transaction_id),
  created_at               timestamptz not null default now()
);

create index on material_return_note_items (return_note_id);
create index on material_return_note_items (bom_item_id);

comment on table delivery_challan_items is 'Line items for a generated Delivery Challan — each one also produces a material_transactions issued_to_site row (resulting_transaction_id).';
comment on table material_return_notes is 'Header for a generated Material Return Note — mirrors delivery_challans, reuses returned_to_warehouse on material_transactions.';
comment on table material_return_note_items is 'Line items for a generated Material Return Note — each one also produces a material_transactions returned_to_warehouse row (resulting_transaction_id).';

-- delete_project_cascade (0066) needs to know about all three new tables —
-- same treatment delivery_challans/material_transactions already get.
create or replace function delete_project_cascade(p_project_id uuid)
returns void
language plpgsql
as $$
begin
  if not exists (select 1 from projects where project_id = p_project_id) then
    raise exception 'Project % does not exist', p_project_id;
  end if;

  -- STEP 0 — clear inbound self/cross-project pointers so the OTHER row
  -- (a merge target, a reassigned document, a sibling ticket) survives.
  update projects set merged_into_project_id = null where merged_into_project_id = p_project_id;
  update documents set reassigned_from_project_id = null where reassigned_from_project_id = p_project_id;
  update drive_folder_import_candidates set suggested_project_id = null where suggested_project_id = p_project_id;
  update documents set supersedes_document_id = null
    where supersedes_document_id in (select document_id from documents where project_id = p_project_id);
  update service_tickets set parent_ticket_id = null
    where parent_ticket_id in (select ticket_id from service_tickets where project_id = p_project_id);
  -- A payment receipt can be matched to an invoice by number alone
  -- (payment_receipts.invoice_id) without itself being matched to a
  -- project yet — clear that pointer for every such receipt, not just
  -- this project's own, before its invoices are deleted below.
  update payment_receipts set invoice_id = null
    where invoice_id in (select invoice_id from sales_invoices where project_id = p_project_id);

  -- STEP 1 — social (social_posts cascades via its own ON DELETE CASCADE)
  delete from social_projects where project_id = p_project_id;

  -- STEP 2 — project-scoped leaves
  delete from project_document_exemptions where project_id = p_project_id;
  delete from project_external_references where project_id = p_project_id;
  delete from project_milestones where project_id = p_project_id;
  delete from commissioning_reports where project_id = p_project_id;
  delete from electrical_test_records where project_id = p_project_id;

  -- STEP 3 — service desk
  delete from ticket_timeline where ticket_id in (select ticket_id from service_tickets where project_id = p_project_id);
  delete from ticket_documents where ticket_id in (select ticket_id from service_tickets where project_id = p_project_id);
  delete from service_quote_items where service_quote_id in (
    select service_quote_id from service_quotes where ticket_id in (select ticket_id from service_tickets where project_id = p_project_id)
  );
  delete from service_quotes where ticket_id in (select ticket_id from service_tickets where project_id = p_project_id);
  delete from service_tickets where project_id = p_project_id;

  -- STEP 4 — AMC (contracts before quotes: amc_contracts.source_amc_quote_id is NOT NULL)
  delete from amc_visit_documents where amc_visit_id in (
    select amc_visit_id from amc_visits where amc_contract_id in (select amc_contract_id from amc_contracts where project_id = p_project_id)
  );
  delete from amc_visits where amc_contract_id in (select amc_contract_id from amc_contracts where project_id = p_project_id);
  delete from amc_contracts where project_id = p_project_id;
  delete from amc_quotes where project_id = p_project_id;

  -- STEP 5 — stock / materials. delivery_challan_items/material_return_note_items
  -- cascade-delete automatically once their own header row is deleted below, but
  -- their resulting_transaction_id FK has no cascade, so it's nulled first —
  -- otherwise deleting material_transactions a few lines down would hit a live
  -- FK from a row that's about to be cascade-deleted anyway.
  delete from material_match_queue where project_id = p_project_id;
  update material_match_queue set resulting_transaction_id = null
    where resulting_transaction_id in (select transaction_id from material_transactions where project_id = p_project_id);
  update delivery_challan_items set resulting_transaction_id = null
    where resulting_transaction_id in (select transaction_id from material_transactions where project_id = p_project_id);
  update material_return_note_items set resulting_transaction_id = null
    where resulting_transaction_id in (select transaction_id from material_transactions where project_id = p_project_id);
  delete from stock_adjustments where transaction_id in (select transaction_id from material_transactions where project_id = p_project_id);
  update material_transactions set replaces_transaction_id = null
    where replaces_transaction_id in (select transaction_id from material_transactions where project_id = p_project_id);
  update material_transactions set delivery_challan_id = null
    where delivery_challan_id in (select delivery_challan_id from delivery_challans where project_id = p_project_id);
  update material_transactions set bom_item_id = null
    where bom_item_id in (select bom_item_id from bom_items where bom_id in (select bom_id from boms where project_id = p_project_id));
  update material_transactions set sales_invoice_item_id = null
    where sales_invoice_item_id in (
      select invoice_item_id from sales_invoice_items where invoice_id in (select invoice_id from sales_invoices where project_id = p_project_id)
    );
  delete from material_transactions where project_id = p_project_id;
  delete from bom_items where bom_id in (select bom_id from boms where project_id = p_project_id);
  delete from boms where project_id = p_project_id;
  delete from delivery_challans where project_id = p_project_id;
  delete from material_return_notes where project_id = p_project_id;

  -- STEP 6 — finance. tally_ledger_entries/bank_statement_transactions are
  -- shared accounting-import tables, not project-owned — re-pointed to
  -- null rather than deleted, so unrelated bank/Tally history survives.
  update bank_statement_transactions set matched_tally_entry_id = null
    where matched_tally_entry_id in (select tally_entry_id from tally_ledger_entries where project_id = p_project_id);
  update tally_ledger_entries set project_id = null where project_id = p_project_id;
  delete from payment_receipt_documents where project_id = p_project_id;
  update tally_ledger_entries set matched_payment_receipt_id = null
    where matched_payment_receipt_id in (select payment_receipt_id from payment_receipts where project_id = p_project_id);
  delete from payment_receipts where project_id = p_project_id;
  update tally_ledger_entries set matched_financial_obligation_id = null
    where matched_financial_obligation_id in (select financial_obligation_id from financial_obligations where project_id = p_project_id);
  delete from sales_invoice_items where invoice_id in (select invoice_id from sales_invoices where project_id = p_project_id);
  delete from sales_invoices where project_id = p_project_id;
  delete from financial_obligations where project_id = p_project_id;
  delete from project_costs where project_id = p_project_id;

  -- STEP 7 — every remaining external pointer into this project's own
  -- documents. Nullable FKs are cleared; the handful that are NOT NULL
  -- (material_transactions.source_document_id, ticket_documents.document_id,
  -- amc_visit_documents.document_id) have no null escape hatch, so those
  -- referencing rows are deleted outright instead — by this point they're
  -- rows this project's own deletion has already made meaningless anyway.
  update purchase_orders set source_document_id = null where source_document_id in (select document_id from documents where project_id = p_project_id);
  update vendor_quotes set source_document_id = null where source_document_id in (select document_id from documents where project_id = p_project_id);
  update stock_statements set source_document_id = null where source_document_id in (select document_id from documents where project_id = p_project_id);
  update bank_statement_transactions set source_document_id = null where source_document_id in (select document_id from documents where project_id = p_project_id);
  update bill_analysis_reports set original_bill_document_id = null where original_bill_document_id in (select document_id from documents where project_id = p_project_id);
  update bill_analysis_reports set report_document_id = null where report_document_id in (select document_id from documents where project_id = p_project_id);
  update quotes set generated_document_id = null where generated_document_id in (select document_id from documents where project_id = p_project_id);
  update service_quotes set generated_document_id = null where generated_document_id in (select document_id from documents where project_id = p_project_id);
  update amc_quotes set generated_document_id = null where generated_document_id in (select document_id from documents where project_id = p_project_id);
  update material_match_queue set source_document_id = null where source_document_id in (select document_id from documents where project_id = p_project_id);
  update material_transactions set invoice_document_id = null where invoice_document_id in (select document_id from documents where project_id = p_project_id);
  delete from material_transactions where source_document_id in (select document_id from documents where project_id = p_project_id);
  delete from ticket_documents where document_id in (select document_id from documents where project_id = p_project_id);
  delete from amc_visit_documents where document_id in (select document_id from documents where project_id = p_project_id);

  -- STEP 8
  delete from documents where project_id = p_project_id;

  -- STEP 9
  delete from projects where project_id = p_project_id;
end;
$$;
