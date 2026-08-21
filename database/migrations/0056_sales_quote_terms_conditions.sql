-- Real solar rooftop quote PDFs (e.g. NRG/26-27/NDC/085, Capiq Engineering
-- 81.80kW) carry a distinct "TERMS & CONDITIONS" section, separate from
-- Payment Terms and Document Requirements (0036) — 7 fixed clauses
-- (price validity, payment-per-schedule, site-readiness, Discom meter
-- charges, extra civil/roof work, force majeure, scope-only). This was
-- never ported. One column, one default template — no per-quote-type
-- variation observed in the real source (same pattern as Havells, 0055).

alter table quotes add column terms_and_conditions text;
