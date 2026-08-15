-- ProjectPulse — Vendor Inquiries (WhatsApp)
-- Follows 0002-0018. Consolidated from docs/projectpulse-handover.md
-- Section 49.

-- ============================================================
-- A record of who was asked, even though WhatsApp gives no callback
-- ============================================================

-- wa.me click-to-chat opens one prefilled WhatsApp conversation per tap —
-- there's no bulk-send and no delivery/read receipt without the paid
-- WhatsApp Business API, which is out of scope here. So this table
-- records only what ProjectPulse actually knows: an inquiry was
-- initiated, to this vendor, for this material, with this message, by
-- this person, at this time. Not "delivered," not "read" — just "asked."

create table vendor_inquiries (
  vendor_inquiry_id   uuid primary key default gen_random_uuid(),
  material_id          uuid references materials(material_id),
  vendor_id             uuid not null references partners(partner_id),
  message_text            text not null,     -- the actual message sent, for the record
  sent_by                  uuid references employees(employee_id),
  sent_at                    timestamptz not null default now(),
  channel                     text not null default 'whatsapp'
                                check (channel in ('whatsapp', 'phone', 'email', 'other'))
);

create index on vendor_inquiries (material_id);
create index on vendor_inquiries (vendor_id);

-- Selecting 3-5 vendors and sending to each is 3-5 rows here, one per
-- vendor — not a single "batch" row, since each is genuinely a separate
-- wa.me tap/conversation with its own vendor and (potentially edited)
-- message text.

-- Real value: before sending a fresh round of inquiries, Purchase can
-- see who's already been asked about a given material recently, instead
-- of re-asking the same 3 vendors every time out of habit. A simple
-- "already asked" flag on the vendor picker — no new pattern, just a
-- query against this table filtered by material_id and a recency window,
-- left to the build session to wire into the UI.
