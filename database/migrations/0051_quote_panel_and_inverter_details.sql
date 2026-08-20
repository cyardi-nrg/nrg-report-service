-- NRG SolarConnect — quotes.panel_details, quotes.inverter_details
--
-- Real, free-text descriptive fields captured on every quote in the actual
-- Quote Generator (index.html v16) — "Panel Details" (auto-suggested from
-- wattage: 525-575W -> 'Mono PERC Bifacial', >575-650W -> 'N Type Topcon
-- Bifacial', editable) and "Inverter Details" (e.g. 'Solis 50kW 3PH,
-- string inverter'). 0036 modeled inverter_material_id but not these
-- descriptive strings — real fields the salesperson fills in and the
-- customer-facing PDF uses, not invented.

alter table quotes add column panel_details text;
alter table quotes add column inverter_details text;
