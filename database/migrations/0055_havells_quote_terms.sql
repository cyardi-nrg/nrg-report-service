-- Havells Heat Pump Quotes were missing the real "Terms & Conditions"
-- block that the live havells_quote_v2.html always shows as an editable
-- textarea on every quote. Solar quotes already have this split into two
-- fields (payment_terms/document_requirements, 0036) because the real
-- solar form has two separate blocks that vary by quote type; the real
-- Havells form has exactly one combined block, with no per-client-type
-- variation in the source — so one column, one default template.

alter table havells_quotes add column terms_and_conditions text;
