-- NRG SolarConnect — Company Profile & Quote-Type Terms (single source of truth)
-- Follows 0002-0064.
--
-- A full audit of the app's hardcoded business content (triggered by the
-- owner directly: "I do not want to go into the details of where that
-- thing has been coded... I just want everything editable in the admin
-- page, and the changes automatically reflect everywhere") found the
-- company's own name/address/GSTIN duplicated byte-for-byte across two
-- document letterhead files, four different hardcoded phone numbers
-- across five files (two of which — 75740 00252 vs 7574000265 — look
-- like a typo of each other), a marketing client list that reads
-- differently depending on which file you're looking at, and two
-- independent Terms & Conditions blocks (solar quotes, Havells quotes)
-- that were plain code constants — real content, but only editable by a
-- developer touching source and redeploying.
--
-- Two tables, not one: company_profile is genuinely singleton (one row
-- per organization — there's only one NRG), while payment terms,
-- document requirements and T&Cs vary BY QUOTE TYPE (the owner's own
-- correction: "payment terms are different for residential and for
-- industrial projects") — a real one-to-many relationship, not another
-- jsonb blob on the singleton row.

create table company_profile (
  organization_id       uuid primary key references organizations(organization_id),
  legal_name            text not null,
  address               text not null,
  gstin                 text not null,
  website               text,
  footer_motto          text,              -- "Quality | Commitment | Value" — shown on every generated document
  founding_year         integer,           -- tenure claims ("40+ years") are computed from this at render time, never re-typed
  client_references     text[] not null default '{}',  -- the name-drop list (ONGC, L&T, Taj Hotels...) used in referral/marketing messages — one list, not one per file
  phones                jsonb not null default '{}'::jsonb,     -- {"office": "...", "sales_mobile": "...", ...} — named, open-vocabulary (same free-text-key convention as message_templates.module_key), since different messages legitimately call different numbers
  heat_pump_savings_pct numeric(4,1),      -- the "saves up to X% on water heating" claim — was inconsistently 70 vs 75 across files, now one number
  havells_warranty      jsonb,             -- {"compressor_years": 7, "tank_years": 5, "comprehensive_years": 2}
  havells_terms_and_conditions text,       -- verbatim from havells_quote_v2.html's #termsText default (lib/havells.ts DEFAULT_TERMS_AND_CONDITIONS)
  bank_details          jsonb,             -- {"account_name","account_number","ifsc","bank_name","branch"} — the owner flagged this directly; nothing hardcoded anywhere used it before, so this starts empty for the owner to fill in
  updated_at            timestamptz not null default now()
);

-- Real current values, seeded verbatim from the audited source files so
-- nothing changes for anyone until the owner actually edits something in
-- the new admin screen. The phone-number and 70%-vs-75% discrepancies are
-- deliberately NOT silently resolved here — one value each is picked
-- (the more frequently-used one) and left for the owner to correct via
-- the UI, since guessing which was the "real" number isn't this
-- migration's call to make.
insert into company_profile (
  organization_id, legal_name, address, gstin, website, footer_motto, founding_year,
  client_references, phones, heat_pump_savings_pct, havells_warranty, havells_terms_and_conditions, bank_details
) values (
  '00000000-0000-0000-0000-000000000001',
  'NRG Technologists Pvt Ltd',
  '989/6, G.I.D.C. Makarpura, Vadodara, Gujarat 390010',
  '24AABCN8993K1ZV',
  'nrgtechnologists.com',
  'Quality | Commitment | Value',
  1985,
  array['ONGC','L&T','Taj Hotels','Ultratech','ABB','Schneider Electric'],
  jsonb_build_object(
    'office', '7574000265',
    'sales_mobile', '9824652624',
    'havells', '7574000252',
    'bill_analyser', '9824653094'
  ),
  70,
  jsonb_build_object('compressor_years', 7, 'tank_years', 5, 'comprehensive_years', 2),
  '1. All prices shown are inclusive of 18% GST. Total payable is the final amount.
2. Quotation valid for 15 days from date of issue.
3. 50% advance required to confirm order; balance before delivery.
4. Estimated delivery: 7-10 working days after order confirmation.
5. Plumbing material and plumbing labour billed separately at actuals.
6. Warranty as per Havells India Ltd. standard terms and conditions.
7. Prices subject to revision without prior notice.',
  null
);

comment on table company_profile is
  'Single source of truth for company identity/contact/marketing/legal content that used to be duplicated across document letterheads and message-composing code. One row per organization. Edited at Admin > Company Profile.';

-- ============================================================
-- Payment terms / document requirements / T&Cs, by quote type — ported
-- verbatim from lib/pricing.ts's PAYMENT_TERMS / DOC_REQUIREMENTS /
-- DEFAULT_TERMS_AND_CONDITIONS constants (the solar quote's own T&Cs
-- don't vary by quote type in the real source, so it's stored once per
-- row anyway for a consistent editing surface — nothing stops the owner
-- from diverging it per type later).
-- ============================================================

create table quote_type_terms (
  organization_id       uuid not null references organizations(organization_id),
  quote_type            text not null,     -- 'residential' | 'commercial_industrial' | 'apartment_common' | 'extension' | 'ndcr' — matches lib/pricing.ts's QUOTE_TYPE_CODES exactly
  payment_terms         text[] not null default '{}',
  document_requirements text[] not null default '{}',
  terms_and_conditions  text,
  updated_at            timestamptz not null default now(),
  primary key (organization_id, quote_type)
);

comment on table quote_type_terms is
  'Payment terms / required documents / T&Cs, one row per solar quote type — real content that varies by type (residential vs commercial/industrial), previously hardcoded in lib/pricing.ts. Edited at Admin > Company Profile.';

insert into quote_type_terms (organization_id, quote_type, payment_terms, document_requirements, terms_and_conditions) values
('00000000-0000-0000-0000-000000000001', 'residential',
  array['50% advance with order confirmation','40% against proforma invoice / before dispatch','10% against installation & commissioning','Structure amount payable against structure installation'],
  array['Recent electricity (light) bill','Cancelled cheque'],
  '1. Prices are valid for 30 days from the date of this quotation.
2. Payment as per agreed payment schedule above.
3. Installation subject to site readiness and structural feasibility.
4. Meter charges payable as per actual invoice raised by the Discom.
5. Any civil or roof work required will be charged extra.
6. Force majeure conditions may affect delivery timelines.
7. This quotation covers only the items listed above; any changes are subject to revision.'),
('00000000-0000-0000-0000-000000000001', 'commercial_industrial',
  array['25% advance with documents','25% against GEDA approval / document verification','40% against proforma invoice / before dispatch','10% against installation & commissioning','Structure amount payable against structure installation'],
  array['Recent electricity bill','Proof of ownership of land — Index / Tax bill / Land allotment letter / Property card / Rent or lease agreement (if any)','Registration certificate / Memorandum of Association (MOA) / Partnership deed / Trust deed (if any)','PAN card of company or PAN card of owner','Aadhaar card of owner','Passport-size photograph','GST registration certificate of company','Board resolution letter','Undertaking (Rs. 300 stamp paper)','Incorporation certificate','DG set approval (if applicable)'],
  '1. Prices are valid for 30 days from the date of this quotation.
2. Payment as per agreed payment schedule above.
3. Installation subject to site readiness and structural feasibility.
4. Meter charges payable as per actual invoice raised by the Discom.
5. Any civil or roof work required will be charged extra.
6. Force majeure conditions may affect delivery timelines.
7. This quotation covers only the items listed above; any changes are subject to revision.'),
('00000000-0000-0000-0000-000000000001', 'apartment_common',
  array['25% advance with documents','25% against GEDA approval / document verification','40% against proforma invoice / before dispatch','10% against installation & commissioning','Structure amount payable against structure installation'],
  array['Recent electricity (light) bill','NOC from society','Cancelled cheque'],
  '1. Prices are valid for 30 days from the date of this quotation.
2. Payment as per agreed payment schedule above.
3. Installation subject to site readiness and structural feasibility.
4. Meter charges payable as per actual invoice raised by the Discom.
5. Any civil or roof work required will be charged extra.
6. Force majeure conditions may affect delivery timelines.
7. This quotation covers only the items listed above; any changes are subject to revision.'),
('00000000-0000-0000-0000-000000000001', 'extension',
  array['50% advance with order confirmation','40% against proforma invoice / before dispatch','10% against installation & commissioning'],
  array['Recent electricity (light) bill','Cancelled cheque'],
  '1. Prices are valid for 30 days from the date of this quotation.
2. Payment as per agreed payment schedule above.
3. Installation subject to site readiness and structural feasibility.
4. Meter charges payable as per actual invoice raised by the Discom.
5. Any civil or roof work required will be charged extra.
6. Force majeure conditions may affect delivery timelines.
7. This quotation covers only the items listed above; any changes are subject to revision.'),
('00000000-0000-0000-0000-000000000001', 'ndcr',
  array['50% advance with order confirmation','40% against proforma invoice / before dispatch','10% against installation & commissioning','Structure amount payable against structure installation'],
  array['Recent electricity bill','Proof of ownership of land — Index / Tax bill / Land allotment letter / Property card / Rent or lease agreement (if any)','Registration certificate / Memorandum of Association (MOA) / Partnership deed / Trust deed (if any)','PAN card of company or PAN card of owner','Aadhaar card of owner','Passport-size photograph','GST registration certificate of company','Board resolution letter','Undertaking (Rs. 300 stamp paper)','Incorporation certificate','DG set approval (if applicable)'],
  '1. Prices are valid for 30 days from the date of this quotation.
2. Payment as per agreed payment schedule above.
3. Installation subject to site readiness and structural feasibility.
4. Meter charges payable as per actual invoice raised by the Discom.
5. Any civil or roof work required will be charged extra.
6. Force majeure conditions may affect delivery timelines.
7. This quotation covers only the items listed above; any changes are subject to revision.');
