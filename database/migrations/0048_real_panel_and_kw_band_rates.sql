-- NRG SolarConnect — Replace 0047's fallback-code panel rates with the
-- real, current numbers from the live Quote Generator pricing sheet
-- (owner-supplied screenshots, DCR + NDCR tabs), and seed
-- quote_kw_band_rates for the first time — it had no source at all
-- until now (the kW-band table is identical across both DCR/NDCR tabs).
--
-- Two real corrections vs. 0047's fallback-derived guess:
--   1. DCR's fifth brand is 'Pahal', not 'Green Brilliance' — Green
--      Brilliance is NDCR-only in the real sheet.
--   2. Several Waaree/Rayzon DCR figures were off by a few hundred
--      rupees vs. the code fallback (which the followup dashboard's own
--      comment already flagged as just-a-fallback, not the live sheet).
--
-- Materials are renamed from a single representative wattage (605W /
-- 585W / 560W) to the real column band (700-720W / 600-630W / 575-599W
-- / 525-565W) — unambiguous, matches the sheet headers exactly, and
-- adds the 700-720W band this org actually sells (Avaada).
--
-- Safe to fully replace: 0 quotes exist yet, so nothing references
-- 0047's materials/rates.

delete from quote_panel_rates
where material_id in (select material_id from materials where category = 'Solar Panel');

delete from materials where category = 'Solar Panel';

insert into materials (category, canonical_name, default_unit, organization_id)
select 'Solar Panel', t.name, 'Nos', '00000000-0000-0000-0000-000000000001'
from (values
  ('Solar Panel 700-720W · Avaada'),

  ('Solar Panel 600-630W · Adani'),
  ('Solar Panel 600-630W · Waaree'),
  ('Solar Panel 600-630W · Goldi'),
  ('Solar Panel 600-630W · Rayzon'),
  ('Solar Panel 600-630W · Pahal'),
  ('Solar Panel 600-630W · Green Brilliance'),
  ('Solar Panel 600-630W · Future Solar'),

  ('Solar Panel 575-599W · Adani'),
  ('Solar Panel 575-599W · Waaree'),
  ('Solar Panel 575-599W · Goldi'),
  ('Solar Panel 575-599W · Rayzon'),
  ('Solar Panel 575-599W · Pahal'),
  ('Solar Panel 575-599W · Green Brilliance'),

  ('Solar Panel 525-565W · Adani'),
  ('Solar Panel 525-565W · Waaree'),
  ('Solar Panel 525-565W · Goldi'),
  ('Solar Panel 525-565W · Rayzon'),
  ('Solar Panel 525-565W · Pahal'),
  ('Solar Panel 525-565W · Green Brilliance')
) as t(name);

-- rate_per_watt = sheet's ₹/kW figure ÷ 1000 (same unit conversion as 0047).
insert into quote_panel_rates (material_id, rate_type, rate_per_watt)
select m.material_id, r.rate_type, r.rate_per_watt
from materials m
join (values
  ('Solar Panel 700-720W · Avaada',           'DCR',  24.50),
  ('Solar Panel 700-720W · Avaada',           'NDCR', 14.60),

  ('Solar Panel 600-630W · Adani',            'DCR',  28.50),
  ('Solar Panel 600-630W · Adani',            'NDCR', 15.50),
  ('Solar Panel 600-630W · Waaree',           'DCR',  28.00),
  ('Solar Panel 600-630W · Waaree',           'NDCR', 14.50),
  ('Solar Panel 600-630W · Goldi',            'DCR',  26.50),
  ('Solar Panel 600-630W · Goldi',            'NDCR', 14.50),
  ('Solar Panel 600-630W · Rayzon',           'DCR',  26.00),
  ('Solar Panel 600-630W · Rayzon',           'NDCR', 13.50),
  ('Solar Panel 600-630W · Pahal',            'DCR',  25.50),
  ('Solar Panel 600-630W · Green Brilliance', 'NDCR', 13.00),
  ('Solar Panel 600-630W · Future Solar',     'NDCR', 13.10),

  ('Solar Panel 575-599W · Adani',            'DCR',  27.50),
  ('Solar Panel 575-599W · Adani',            'NDCR', 16.20),
  ('Solar Panel 575-599W · Waaree',           'DCR',  27.00),
  ('Solar Panel 575-599W · Waaree',           'NDCR', 14.80),
  ('Solar Panel 575-599W · Goldi',            'DCR',  26.00),
  ('Solar Panel 575-599W · Goldi',            'NDCR', 14.50),
  ('Solar Panel 575-599W · Rayzon',           'DCR',  25.50),
  ('Solar Panel 575-599W · Rayzon',           'NDCR', 14.50),
  ('Solar Panel 575-599W · Pahal',            'DCR',  24.00),
  ('Solar Panel 575-599W · Green Brilliance', 'NDCR', 14.20),

  ('Solar Panel 525-565W · Adani',            'DCR',  26.00),
  ('Solar Panel 525-565W · Adani',            'NDCR', 15.50),
  ('Solar Panel 525-565W · Waaree',           'DCR',  25.50),
  ('Solar Panel 525-565W · Waaree',           'NDCR', 14.50),
  ('Solar Panel 525-565W · Goldi',            'DCR',  24.50),
  ('Solar Panel 525-565W · Goldi',            'NDCR', 14.00),
  ('Solar Panel 525-565W · Rayzon',           'DCR',  22.50),
  ('Solar Panel 525-565W · Rayzon',           'NDCR', 14.00),
  ('Solar Panel 525-565W · Pahal',            'DCR',  22.00),
  ('Solar Panel 525-565W · Green Brilliance', 'NDCR', 13.80)
) as r(canonical_name, rate_type, rate_per_watt) on r.canonical_name = m.canonical_name
where m.category = 'Solar Panel';

-- kW-band adjustments — identical across DCR and NDCR in the source sheet,
-- so one table, no rate_type split (matches quote_kw_band_rates' schema,
-- which has none). Same ₹/kW → ₹/watt ÷1000 conversion.
insert into quote_kw_band_rates
  (organization_id, min_kw, max_kw, above_panel_rate_per_watt, margin_rate_per_watt, discount_rate_per_watt)
values
  ('00000000-0000-0000-0000-000000000001',   1.00,   2.99, 14.00, 7.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',   3.00,   5.99, 11.50, 5.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',   6.00,   9.99, 13.00, 5.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',  10.00,  14.99, 11.00, 5.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',  15.00,  24.99, 10.00, 5.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',  25.00,  49.99,  8.00, 4.00, 4.00),
  ('00000000-0000-0000-0000-000000000001',  50.00, 100.00,  7.00, 4.00, 4.00),
  ('00000000-0000-0000-0000-000000000001', 100.01, 150.00,  6.50, 3.75, 4.00),
  ('00000000-0000-0000-0000-000000000001', 150.01, 200.00,  5.00, 3.25, 4.00),
  ('00000000-0000-0000-0000-000000000001', 200.01,1000.00,  5.00, 3.00, 4.00);
