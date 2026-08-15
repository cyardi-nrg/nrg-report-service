-- ProjectPulse — Bank Reconciliation (Tally vs. Bank Statement)
-- Follows 0002-0017. Consolidated from docs/projectpulse-handover.md
-- Section 47.

-- ============================================================
-- A different reconciliation than tally_ledger_entries already does
-- ============================================================

-- tally_ledger_entries (0006) already reconciles Tally against NRG's own
-- financial_obligations/payment_receipts — "did we receive what we're
-- owed." That's a project-facing question. Bank reconciliation is a
-- different, accounts-facing one: "does our book (Tally) agree with what
-- the bank actually shows," independent of any project. Real gaps this
-- catches that the existing reconciliation can't: bank charges/interest
-- never entered in Tally, a cheque recorded as received in Tally that
-- hasn't cleared the bank yet, a bank-side error.

create table bank_statement_transactions (
  bank_transaction_id     uuid primary key default gen_random_uuid(),
  source_document_id      uuid references documents(document_id),  -- the uploaded bank statement (PDF/CSV/Excel)
  transaction_date        date not null,
  narration                text,            -- the bank's own description text, as printed
  debit_amount              numeric(14,2),
  credit_amount              numeric(14,2),
  balance_after                numeric(14,2),
  reference_number               text,        -- cheque no. / UTR / UPI ref, as it appears on the statement
  matched_tally_entry_id           uuid references tally_ledger_entries(tally_entry_id),
  match_status                       text not null default 'unmatched'
                                      check (match_status in ('unmatched','suggested','confirmed','discrepancy')),
  match_confidence                     numeric(3,2),
  ai_confidence                         numeric(3,2),
  extraction_status                      text not null default 'ai_extracted'
                                          check (extraction_status in ('ai_extracted','confirmed','corrected')),
  created_at                               timestamptz not null default now()
);

create index on bank_statement_transactions (match_status);

-- Same shape decision as payment_receipts/tally_ledger_entries: AI
-- extracts the statement, suggests a match to a tally_ledger_entry by
-- amount + date proximity + reference number, accounts confirms or flags
-- 'discrepancy' — never auto-applied. 'discrepancy' is distinct from
-- 'unmatched' for the same reason it is on tally_ledger_entries: it means
-- something was actually compared and didn't line up (wrong amount, bank
-- charge with no Tally counterpart), not "hasn't been looked at yet."

-- ============================================================
-- The screen accounts actually wants: one place both sides disagree
-- ============================================================

create view bank_reconciliation_gaps as
select
  'bank_only'          as gap_type,   -- on the bank statement, not yet in Tally
  bst.bank_transaction_id as entry_id,
  bst.transaction_date      as entry_date,
  bst.narration               as description,
  coalesce(bst.credit_amount, 0) - coalesce(bst.debit_amount, 0) as amount,
  bst.match_status              as status
from bank_statement_transactions bst
where bst.match_status in ('unmatched', 'discrepancy')

union all

select
  'tally_only'    as gap_type,        -- in Tally, not yet reflected on the bank statement (e.g. an outstanding cheque)
  tle.tally_entry_id as entry_id,
  tle.entry_date        as entry_date,
  tle.particulars          as description,
  coalesce(tle.credit_amount, 0) - coalesce(tle.debit_amount, 0) as amount,
  tle.match_status            as status
from tally_ledger_entries tle
where tle.voucher_type in ('payment', 'receipt')  -- bank-relevant vouchers only — a journal entry has nothing to clear against a bank statement
  and tle.match_status in ('unmatched', 'discrepancy')
  and not exists (
    select 1 from bank_statement_transactions bst2
    where bst2.matched_tally_entry_id = tle.tally_entry_id
  );

-- This view is the "button" — accounts opens it and sees exactly what's
-- unresolved on either side, instead of eyeballing two statements
-- side by side by hand. Matched, confirmed rows on both tables never
-- show up here at all — only what still needs a human decision.
