-- NRG SolarConnect — Lead capture fields to match the real, currently-live
-- Leads workflow (contact person, referral channel/person, site address,
-- free-text notes). 0036's `leads` table only carried the bare minimum
-- (name/phone/source/status) — these are the fields the existing app's
-- lead-capture form actually collects on every new lead.

alter table leads add column contact_person text;      -- engineer/purchase/PMC contact at the site, when the lead itself is a company
alter table leads add column ref_through text;          -- referral channel: 'BNI' | 'Old Customer' | 'Friend' | 'SMS' | 'WhatsApp' | 'Instagram' — app-level list, free text like `source`
alter table leads add column reference_person text;     -- who referred them, by name
alter table leads add column address text;               -- site / area
alter table leads add column notes text;                  -- what they want, roof, urgency, anything said on the call
