-- NRG SolarConnect — delete_project_cascade()
-- Follows 0002-0065.
--
-- The owner needs a real way to delete a project outright — trial/test
-- projects created while taking the app for a spin (three separate
-- "Capiq Engineering" rows from repeated test uploads was the concrete
-- complaint) clutter the real list with no way to remove them. A plain
-- `delete from projects` fails outright: every migration since 0002 adds
-- FKs into projects.project_id with no ON DELETE clause (Postgres default
-- is NO ACTION), and 25 more tables reach a project indirectly through
-- documents.document_id, boms.bom_id, service_tickets.ticket_id,
-- amc_contracts.amc_contract_id, sales_invoices.invoice_id, and
-- material_transactions.transaction_id. A full dependency map was pulled
-- from every migration file (0002 through 0065; there is no 0001) before
-- writing this — every table/column name below was verified directly
-- against its `create table` / `alter table ... add column` statement,
-- not guessed.
--
-- Genuinely project-owned data (documents, boms, milestones, tickets,
-- AMC, quotes/invoices/receipts raised for this project, stock
-- transactions posted against it) is deleted outright. Shared/inbox
-- tables that merely reference a project in passing — tally_ledger_entries
-- and bank_statement_transactions (accounting import rows, not
-- project-owned) — are re-pointed to null instead of deleted, since
-- deleting a project shouldn't erase unrelated bank/Tally history.
-- Cross-project pointers (a merge, a document reassigned away from this
-- project, a repeat-complaint ticket linking back) are cleared first so
-- the OTHER row survives untouched.
--
-- Runs as a single plpgsql function body, which Postgres executes as one
-- transaction — if any statement here hits an FK violation (a table this
-- migration missed, or a real row nobody expected), the whole call rolls
-- back and nothing is deleted. That's the actual safety net for a
-- hand-written cascade this wide, not any claim of exhaustive coverage.
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

  -- STEP 5 — stock / materials
  delete from material_match_queue where project_id = p_project_id;
  update material_match_queue set resulting_transaction_id = null
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

comment on function delete_project_cascade(uuid) is
  'Owner-only, called from app/(app)/projects/[id]/actions.ts deleteProjectPermanently. Deletes a project and every row genuinely owned by it (documents, boms, milestones, tickets, AMC, invoices/receipts/quotes raised for it, stock transactions posted against it); re-points shared accounting-import rows (tally_ledger_entries, bank_statement_transactions) to null instead of deleting them. Runs as one transaction — any unexpected FK violation rolls the whole call back.';
