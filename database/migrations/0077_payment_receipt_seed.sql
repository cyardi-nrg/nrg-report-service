-- NRG SolarConnect — Payment Receipt generation, data seed only
-- Follows 0002-0076.
--
-- Owner clarification: "sales people can't generate payment receipts...
-- only purchase/accounts can see the payment...check our bank account
-- and confirm that payment has been received...and then generate a
-- receipt. It should also be possible to send a whatsapp to a
-- particular member of the client team with a standard message and a
-- pdf of the receipt attached."
--
-- No schema change needed — payment_receipt_documents (header table),
-- documents.document_type (free text, no CHECK constraint) and
-- next_document_number (auto-seeds its own series row on first use)
-- were already in place, just never wired up to any app code. This
-- migration is the two pieces of real data the new
-- generatePaymentReceipt action (app/(app)/finance/actions.ts) and its
-- WhatsApp send button (projects/[id]/money-tab.tsx) depend on:
--
-- 1. Mahesh Parmar (MP — the real "Purchase" person the Pending
--    screen's own role model already names, app/(app)/pending/
--    pending-board.tsx's 'Purchase · MP') gets an explicit 'finance'
--    module grant. 'finance' is a STRICT_MODULES key (deny-by-default,
--    lib/module-access.ts) — before this, nobody but the owner
--    (Chaitanya Yardi, is_owner) could reach /finance or its actions at
--    all, which is correct for Sales (KP/RV, who get no grant here) but
--    also meant Purchase/Accounts' own real day-to-day job — checking
--    the bank, confirming receipts, generating receipts — had nobody
--    but the owner able to do it.
-- 2. A 'Payment Receipt' WhatsApp template under the existing
--    'purchase' module_key (already used by the real "Vendor Inquiry"
--    template) — admin-editable from Admin > WhatsApp Messages like
--    every other one, rather than a string hardcoded into the page.

insert into employee_module_access (employee_id, module_key, granted_by, granted_at)
select e.employee_id, 'finance', o.employee_id, now()
from employees e
cross join (select employee_id from employees where is_owner = true limit 1) o
where e.name = 'Mahesh Parmar'
on conflict (employee_id, module_key) do nothing;

insert into message_templates (organization_id, module_key, channel, audience, name, body, allow_attachment, active)
select '00000000-0000-0000-0000-000000000001', 'purchase', 'individual_wa_me', 'customer', 'Payment Receipt',
  'Dear {customer_name},' || chr(10) || chr(10) ||
  'We acknowledge receipt of {amount} towards {towards}.' || chr(10) || chr(10) ||
  'Receipt No: {receipt_number}' || chr(10) ||
  'Receipt PDF: {receipt_url}' || chr(10) || chr(10) ||
  'Thank you,' || chr(10) || 'NRG Technologists',
  true, true
where not exists (
  select 1 from message_templates where module_key = 'purchase' and name = 'Payment Receipt'
);
