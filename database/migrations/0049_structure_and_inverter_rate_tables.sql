-- NRG SolarConnect — Move structure-height and inverter cost tables out of
-- hardcoded application code into editable database tables, same reasoning
-- as quote_panel_rates/quote_kw_band_rates (0036/0048): the owner needs to
-- change these numbers themselves without a code deploy, the same way the
-- old system's rates lived in an editable sheet tab.
--
-- Seeded with the numbers already in the app's (pre-existing, hardcoded)
-- lib/pricing.ts — carried over from the live dashboard's cost-side BOM
-- calculator. Unlike 0048's panel/kW-band numbers, these were NOT
-- confirmed against an owner-supplied screenshot — flagged here so
-- they're the first thing to verify/edit from the new Rates screen.

create table quote_structure_height_rates (
  rate_id          uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
  height_m         numeric(6,2) not null,
  rate             numeric(14,2) not null,
  updated_at       timestamptz not null default now(),
  unique (organization_id, height_m)
);

create table quote_inverter_rate_bands (
  band_id          uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
  min_kw           numeric(10,2) not null,
  max_kw           numeric(10,2) not null,
  rate             numeric(14,2) not null,
  updated_at       timestamptz not null default now(),
  check (max_kw > min_kw)
);

create index on quote_inverter_rate_bands (organization_id);

insert into quote_structure_height_rates (organization_id, height_m, rate) values
  ('00000000-0000-0000-0000-000000000001', 0, 0),
  ('00000000-0000-0000-0000-000000000001', 1, 2000),
  ('00000000-0000-0000-0000-000000000001', 2, 3500),
  ('00000000-0000-0000-0000-000000000001', 3, 4500),
  ('00000000-0000-0000-0000-000000000001', 4, 5500),
  ('00000000-0000-0000-0000-000000000001', 5, 6500);

insert into quote_inverter_rate_bands (organization_id, min_kw, max_kw, rate) values
  ('00000000-0000-0000-0000-000000000001',  0.00,   3.00, 16250),
  ('00000000-0000-0000-0000-000000000001',  3.00,   4.00, 22000),
  ('00000000-0000-0000-0000-000000000001',  4.00,   5.00, 27000),
  ('00000000-0000-0000-0000-000000000001',  5.00,   6.00, 28600),
  ('00000000-0000-0000-0000-000000000001',  6.00,   7.00, 30000),
  ('00000000-0000-0000-0000-000000000001',  7.00,   9.00, 49000),
  ('00000000-0000-0000-0000-000000000001',  9.00,  11.00, 51000),
  ('00000000-0000-0000-0000-000000000001', 11.00,  15.00, 64000),
  ('00000000-0000-0000-0000-000000000001', 15.00, 999.00, 67000);
