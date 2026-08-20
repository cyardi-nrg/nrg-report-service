-- NRG SolarConnect — Seed real panel materials + selling rates for the
-- Quote Generation module, and the panel/inverter brand rosters it needs.
--
-- These are NOT invented numbers. They are the live Quote Generator's own
-- FALLBACK_PANEL_RATES table (the rates it falls back to whenever the
-- 'Panel Pricing'/'NDCR Panel Pricing' sheet tabs haven't loaded yet) —
-- read directly out of nrg-cover's nrg_followup_dashboard.html, which
-- mirrors Quote Generator's real cost-side formulas for its own margin
-- calculator. Real production numbers, just not the LIVE sheet-editable
-- ones — an admin should be able to override these from a rates screen
-- once that's built; until then these are exactly what the old system
-- used when live rates weren't available either.
--
-- Wattage band → rate tier: >=600W = high, 575-599W = mid, <575W = low.
-- One representative wattage per band per brand is seeded as a material;
-- each gets both a DCR and an NDCR row in quote_panel_rates (a material
-- carries both — quote_panel_rates.unique(material_id, rate_type) is
-- exactly this: one panel material, one rate per type).

insert into materials (category, canonical_name, default_unit, organization_id)
select 'Solar Panel', name, 'Nos', '00000000-0000-0000-0000-000000000001'
from (values
  ('Solar Panel 605W · Adani'),
  ('Solar Panel 585W · Adani'),
  ('Solar Panel 560W · Adani'),
  ('Solar Panel 605W · Waaree'),
  ('Solar Panel 585W · Waaree'),
  ('Solar Panel 560W · Waaree'),
  ('Solar Panel 605W · Goldi'),
  ('Solar Panel 585W · Goldi'),
  ('Solar Panel 560W · Goldi'),
  ('Solar Panel 605W · Rayzon'),
  ('Solar Panel 585W · Rayzon'),
  ('Solar Panel 560W · Rayzon'),
  ('Solar Panel 605W · Green Brilliance'),
  ('Solar Panel 585W · Green Brilliance'),
  ('Solar Panel 560W · Green Brilliance')
) as t(name)
on conflict (category, canonical_name) do nothing;

insert into materials (category, canonical_name, default_unit, organization_id)
select 'Inverter', name, 'Nos', '00000000-0000-0000-0000-000000000001'
from (values
  ('Solaryaan'), ('Ksolare'), ('Growatt'), ('Goodwe'), ('Sofar'), ('Solax')
) as t(name)
on conflict (category, canonical_name) do nothing;

-- The source table's numbers are the live system's ₹/kW rate (its own
-- variable name: panelRateKw). This schema's rate_per_watt column is
-- exactly what its name says — ₹/watt, not ₹/kW — so every figure below
-- is the source value ÷ 1000. Same real rates, expressed in this
-- column's actual unit.
insert into quote_panel_rates (material_id, rate_type, rate_per_watt)
select m.material_id, r.rate_type, r.rate_per_watt
from materials m
join (values
  ('Solar Panel 605W · Adani',            'DCR',  28.50),
  ('Solar Panel 585W · Adani',             'DCR',  27.50),
  ('Solar Panel 560W · Adani',              'DCR',  26.00),
  ('Solar Panel 605W · Adani',             'NDCR', 16.50),
  ('Solar Panel 585W · Adani',              'NDCR', 16.20),
  ('Solar Panel 560W · Adani',               'NDCR', 15.50),

  ('Solar Panel 605W · Waaree',            'DCR',  28.00),
  ('Solar Panel 585W · Waaree',             'DCR',  26.50),
  ('Solar Panel 560W · Waaree',              'DCR',  25.00),
  ('Solar Panel 605W · Waaree',             'NDCR', 15.00),
  ('Solar Panel 585W · Waaree',              'NDCR', 14.80),
  ('Solar Panel 560W · Waaree',               'NDCR', 14.50),

  ('Solar Panel 605W · Goldi',             'DCR',  26.50),
  ('Solar Panel 585W · Goldi',              'DCR',  26.00),
  ('Solar Panel 560W · Goldi',               'DCR',  24.50),
  ('Solar Panel 605W · Goldi',              'NDCR', 14.80),
  ('Solar Panel 585W · Goldi',               'NDCR', 14.50),
  ('Solar Panel 560W · Goldi',                'NDCR', 14.00),

  ('Solar Panel 605W · Rayzon',            'DCR',  26.00),
  ('Solar Panel 585W · Rayzon',             'DCR',  25.50),
  ('Solar Panel 560W · Rayzon',              'DCR',  23.00),
  ('Solar Panel 605W · Rayzon',             'NDCR', 14.80),
  ('Solar Panel 585W · Rayzon',              'NDCR', 14.50),
  ('Solar Panel 560W · Rayzon',               'NDCR', 14.00),

  ('Solar Panel 605W · Green Brilliance',  'DCR',  25.00),
  ('Solar Panel 585W · Green Brilliance',   'DCR',  24.00),
  ('Solar Panel 560W · Green Brilliance',    'DCR',  22.00),
  ('Solar Panel 605W · Green Brilliance',   'NDCR', 14.50),
  ('Solar Panel 585W · Green Brilliance',    'NDCR', 14.20),
  ('Solar Panel 560W · Green Brilliance',     'NDCR', 13.80)
) as r(canonical_name, rate_type, rate_per_watt) on r.canonical_name = m.canonical_name
where m.category = 'Solar Panel'
on conflict (material_id, rate_type) do update set rate_per_watt = excluded.rate_per_watt;
