-- ============================================================
-- Seed havells_products (0041) with the real catalog that has been
-- hardcoded in lib/havells.ts (PRODUCTS) since that module was built —
-- the table existed with zero rows and zero code ever inserted into it,
-- so havells_quote_line_items.product_id was always left null even
-- though the FK exists specifically for this. Values are the same
-- verbatim catalog already cross-checked against havells_quote_v2.html
-- and HeatPumpQuote_Code.gs v5.1 (see lib/havells.ts's own header).
-- ============================================================

insert into havells_products (organization_id, product_code, product_name, product_type, capacity_label, mrp)
values
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPUWKW20', 'AHP20 All-in-One 200L', 'all_in_one', '200L', 186690),
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPUWKW30', 'AHP30 All-in-One 300L', 'all_in_one', '300L', 217590),
  ('00000000-0000-0000-0000-000000000001', 'GHWAPHSWS200', 'HP20 Split 200L', 'split', '200L', 203490),
  ('00000000-0000-0000-0000-000000000001', 'GHWAPHSWS300', 'HP30 Split 300L', 'split', '300L', 232590),
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPUREW40', 'HP40 Split 400L', 'split', '400L', 250190),
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPURFW50', 'HP50 Split 500L', 'split', '500L', 341590),
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPERKG18', 'CHP18 Commercial 18kW', 'commercial', '18kW', 415290),
  ('00000000-0000-0000-0000-000000000001', 'GHHVHPERKG36', 'CHP36 Commercial 36kW', 'commercial', '36kW', 744190)
on conflict (organization_id, product_code) do nothing;
