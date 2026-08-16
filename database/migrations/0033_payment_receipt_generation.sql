-- ProjectPulse — Generate a Signed Payment Receipt in One Click
-- Follows 0002-0032. Consolidated from docs/projectpulse-handover.md
-- Section 74.

-- ============================================================
-- Real ask: Purchase/Accounts should be able to generate a formal
-- receipt the moment a payment is confirmed, not type one up by hand
-- ============================================================

-- Same "the system produces it, a human adjusts and prints" pattern
-- already established for Delivery Challans and Commissioning Reports
-- (Section 37/0010) — everything a payment receipt needs to say is
-- already sitting in payment_receipts (Section 32) the moment a
-- payment is matched and confirmed: amount, payment_date,
-- payment_method, payer_name, reference_number, and — via
-- financial_obligation_id — what the payment is actually towards.
-- Nothing to re-key by hand; the only human step is print, sign,
-- hand/send to the client.

create table payment_receipt_documents (
  payment_receipt_document_id  uuid primary key default gen_random_uuid(),
  receipt_number                text not null unique,   -- e.g. 'PR/26-27/00031', built from next_document_number() (Section 37) — 'PR' is just a new series_name, no schema change to that function
  payment_receipt_id             uuid not null references payment_receipts(payment_receipt_id),
  project_id                      uuid not null references projects(project_id),
  amount                           numeric(14,2) not null,
  received_from                    text not null,          -- payer name as printed on the receipt — payment_receipts.payer_name, or the customer name if that's blank
  payment_method                    text,
  received_date                      date not null,
  towards                             text,                 -- what the payment is for, pulled from the linked financial_obligations row at generation time (e.g. "10% Advance — Solar Rooftop Installation")
  generated_document_id               uuid references documents(document_id),  -- the generated PDF, logged as a Document like any other
  created_by                           uuid references employees(employee_id),
  created_at                            timestamptz not null default now(),
  unique (payment_receipt_id)
);

create index on payment_receipt_documents (project_id);

-- unique(payment_receipt_id) is deliberate — one signed receipt per
-- confirmed payment, not two. Reprinting the same receipt later (a
-- copy got lost, the client needs it again) reuses this same row and
-- the same receipt_number; it never generates a second one for the
-- same payment. Generation should be gated on payment_receipts.
-- match_status = 'confirmed' (Section 32) — an AI-suggested,
-- unconfirmed payment match has no business becoming a formal signed
-- document that leaves the building; only confirmed data should ever
-- turn into a real, client-facing artifact, same discipline as every
-- other generated document in this schema.

-- 'payment_receipt' joins the existing free-text document_type
-- reference list (Section 36) — same reasoning as every other type
-- there, no constraint to change.
