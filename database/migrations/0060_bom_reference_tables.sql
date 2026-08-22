-- NRG SolarConnect — Reference Tables: owner-editable BOM lookup data
-- Follows 0002-0059.
--
-- Distinct from /reference-finder (customer-reference lookup for
-- sales, untouched) — this is the real, separate feature the owner
-- confirmed: the numeric lookup tables that drive BOM generation
-- (currently hardcoded in lib/bom-generator.ts) made visible to
-- everyone and editable by the owner, without a code deploy. Matches
-- the real ReferenceTables.dc.html mockup exactly: only the GI 60×40mm
-- pipe-quantity grid is editable; GI 40×40mm is a formula, shown
-- read-only, not stored here.
--
-- Everything else bom-generator.ts hardcodes (residential baseplate/
-- anchor/chapla/khilla/legs/strings/DC-cable/MC4 tables, inverter
-- tiers, flat rates, the industrial function's confirmed formulas and
-- its Nilamber-Bellissimo-scaled constants) is real but NOT shown in
-- the mockup — left as-is, a real phase-2 candidate using this same
-- mechanism, not built here since there's no confirmed UI for it yet.

create table bom_gi_60x40_quantities (
  quantity_id      uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
  band_min_panels  int not null,
  band_max_panels  int not null,
  height_m         numeric(3,1) not null,
  quantity_m       numeric(6,2) not null,
  updated_at       timestamptz not null default now(),
  unique (organization_id, band_min_panels, height_m)
);

-- Real values, from the confirmed grid in ReferenceTables.dc.html —
-- identical to the RES_GI60_BY_HEIGHT constant lib/bom-generator.ts
-- has hardcoded (same source, now the database instead of code).
insert into bom_gi_60x40_quantities (organization_id, band_min_panels, band_max_panels, height_m, quantity_m) values
  ('00000000-0000-0000-0000-000000000001', 5, 7, 0, 0),
  ('00000000-0000-0000-0000-000000000001', 5, 7, 1, 13.2),
  ('00000000-0000-0000-0000-000000000001', 5, 7, 2, 16.8),
  ('00000000-0000-0000-0000-000000000001', 5, 7, 3, 20.4),
  ('00000000-0000-0000-0000-000000000001', 5, 7, 4, 24.4),
  ('00000000-0000-0000-0000-000000000001', 5, 7, 5, 28.4),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 0, 0),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 1, 21.6),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 2, 25.2),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 3, 28.8),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 4, 32.8),
  ('00000000-0000-0000-0000-000000000001', 8, 13, 5, 36.8),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 0, 0),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 1, 34.2),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 2, 37.8),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 3, 41.4),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 4, 45.4),
  ('00000000-0000-0000-0000-000000000001', 14, 18, 5, 49.4),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 0, 0),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 1, 46.8),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 2, 50.4),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 3, 54.0),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 4, 58.0),
  ('00000000-0000-0000-0000-000000000001', 19, 30, 5, 62.0);
