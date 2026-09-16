-- NRG SolarConnect — Fix financial_obligation_reconciliation's pending math
-- Follows 0002-0078.
--
-- Owner: "scanned a check...it is now showing in the money tab.... but
-- the outstanding amount is not reducing...it has just scanned and put
-- over there."
--
-- Two real bugs in the original view (0006-era):
--
-- 1. pending_amount = invoiced_amount - received_amount. This business
--    almost never generates a real sales_invoice per obligation line
--    (GEDA/Meter/Strengthening/NRG Revenue are collected as one lump
--    quoted amount, not separately invoiced) — invoiced_amount reads 0
--    for nearly every obligation, so pending read 0 regardless of how
--    much was actually still owed. Fixed to bill against
--    GREATEST(quoted_amount, invoiced_amount) — the real invoice still
--    wins if one exists and is larger, but a never-invoiced obligation
--    correctly bills at its quoted amount.
--
-- 2. received_amount only ever counted a payment_receipts row with a
--    matching financial_obligation_id. Nothing in the real app —
--    finalizePayment (scan/actions.ts) or confirmPaymentReceipt
--    (finance/actions.ts) — ever sets that column on a real payment; a
--    customer's cheque pays toward the project's total, not one
--    specific obligation line. So received_amount, and therefore every
--    figure derived from it (this view, project_financial_summary,
--    the Money tab's top summary, Finance's per-project table, the
--    Pending screen's "Money still to collect"), read 0 for every real
--    confirmed payment ever made in the app.
--
-- Fixed by pooling a project's total confirmed payment_receipts
-- (regardless of financial_obligation_id) and applying it as a
-- waterfall across that project's obligations, oldest (created_at)
-- first — standard FIFO payment application, not an invented
-- allocation. Each obligation absorbs payment up to its own billed
-- amount before the remainder spills to the next; sums back to exactly
-- the project's real total received/pending either way.
--
-- Column list and names are unchanged — every existing SELECT (project_
-- financial_summary, money-tab.tsx, finance/page.tsx, pending/page.tsx)
-- keeps working without any app-code change.

create or replace view financial_obligation_reconciliation as
with inv as (
  select financial_obligation_id, sum(amount) as invoiced_amount
  from sales_invoice_items
  where financial_obligation_id is not null
  group by financial_obligation_id
),
proj_received as (
  select project_id, sum(amount) as total_received
  from payment_receipts
  where match_status = 'confirmed' and project_id is not null
  group by project_id
),
billed as (
  select fo.financial_obligation_id, fo.project_id, fo.obligation_type, fo.payable_to, fo.settlement_method, fo.status,
         fo.quoted_amount, fo.created_at,
         coalesce(inv.invoiced_amount, 0) as invoiced_amount,
         greatest(coalesce(fo.quoted_amount, 0), coalesce(inv.invoiced_amount, 0)) as billed_amount
  from financial_obligations fo
  left join inv on inv.financial_obligation_id = fo.financial_obligation_id
),
ordered as (
  select b.*,
    coalesce(sum(b.billed_amount) over (
      partition by b.project_id order by b.created_at, b.financial_obligation_id
      rows between unbounded preceding and 1 preceding
    ), 0) as billed_before_this
  from billed b
)
select
  o.financial_obligation_id,
  o.project_id,
  o.obligation_type,
  o.payable_to,
  o.settlement_method,
  o.status,
  o.quoted_amount,
  o.invoiced_amount,
  least(o.billed_amount, greatest(coalesce(pr.total_received, 0) - o.billed_before_this, 0)) as received_amount,
  o.billed_amount - least(o.billed_amount, greatest(coalesce(pr.total_received, 0) - o.billed_before_this, 0)) as pending_amount
from ordered o
left join proj_received pr on pr.project_id = o.project_id;
