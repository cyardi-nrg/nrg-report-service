-- NRG SolarConnect — quotes.ref_through
--
-- The real Quote Generator's Quotes sheet HEADERS end with 'Structure
-- Height','Reference Person','Ref Through','Deal Status','Quote Ref' —
-- confirmed from the owner's pasted QuoteGenerator_Code.gs (v15) and
-- index.html (v16). Ref Through (BNI/Old Customer/Friend/SMS/WhatsApp/
-- Instagram/Market inquiry/Self generated/Other) is a real, separate
-- column from reference_person (who referred them, by name) — 0036 only
-- carried the latter.

alter table quotes add column ref_through text;
