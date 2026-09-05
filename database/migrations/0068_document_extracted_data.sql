-- NRG SolarConnect — documents.extracted_data
-- Follows 0002-0067.
--
-- A scanned quote (a customer's own quote PDF, or NRG's own quote printed
-- and re-scanned) carries real panel count/wattage/system size — Generate
-- BOM's prefill (0067's session, generate-bom/page.tsx) only worked when
-- the project was created through the app's own Quotes → Follow-up →
-- "Add to Project" flow, which leaves a real quotes row with
-- generated_document_id pointing at the quote document. A document that
-- arrived by scanning instead has no such row, and the owner's own
-- point stands: "why scan if people are going to [re-type it]?"
--
-- Generic (not quote-specific) so any future document-type extractor
-- that only needs a few structured fields — not a whole extraction
-- table of its own — has somewhere real to put them, same reasoning as
-- material_transactions.calculation_basis (0002) being free-form.
alter table documents add column extracted_data jsonb;

comment on column documents.extracted_data is
  'Lightweight structured fields pulled by a type-specific AI extractor at scan time (lib/ai-extraction.ts) — currently only quote_proposal (panelCount, wattage, panelBrand, inverterBrand, systemSizeKw), read by Generate BOM as a fallback prefill source when no real quotes row exists for this project. Not a replacement for a real extraction table if a document type ever needs one.';
