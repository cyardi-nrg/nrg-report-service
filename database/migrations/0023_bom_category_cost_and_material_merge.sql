-- NRG SolarConnect — BOM Cost Per Watt by Category (Panel vs. Everything Else),
-- and a Repair Path for Duplicate Material Names
-- Follows 0002-0022. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 59-60.

-- ============================================================
-- Rs/Watt by category, and panel cost split from everything else
-- ============================================================

-- Real ask: "how many rupees per watt is GI Structure coming to, how
-- many is ACDB/DCDB, DC Cable, AC Cable..." — the same Rs/Watt framing
-- the original SPP workbook already carries at the whole-project level
-- (Section 10's "category costs, margin estimation" from the header
-- block), but never broken out per category as its own queryable
-- number. bom_items already carries category, planned_quantity and
-- planned_rate per line item (Section 19) — this was always
-- computable, just never written as a view.

create view bom_category_cost as
select
  bi.bom_id,
  bi.category,
  sum(bi.planned_quantity * bi.planned_rate) as category_cost,
  b.kw_capacity,
  round(
    sum(bi.planned_quantity * bi.planned_rate) / nullif(b.kw_capacity * 1000, 0),
  2) as rs_per_watt
from bom_items bi
join boms b on b.bom_id = bi.bom_id
group by bi.bom_id, bi.category, b.kw_capacity;

-- The real motivating case: "Waree panel might cost Rs 15/W, the rest
-- of the project Rs 7/W, so Rs 22/W total. Swap to a cheaper panel at
-- Rs 13/W and the rest doesn't change — now it's Rs 20/W." That
-- comparison needs panel cost isolated from every other category
-- summed together, not read off N separate category rows by hand.

create view bom_panel_vs_rest_cost as
select
  bi.bom_id,
  b.kw_capacity,
  sum(bi.planned_quantity * bi.planned_rate) filter (where bi.category = 'Solar Panels') as panel_cost,
  sum(bi.planned_quantity * bi.planned_rate) filter (where bi.category != 'Solar Panels') as rest_cost,
  round(
    sum(bi.planned_quantity * bi.planned_rate) filter (where bi.category = 'Solar Panels')
      / nullif(b.kw_capacity * 1000, 0),
  2) as panel_rs_per_watt,
  round(
    sum(bi.planned_quantity * bi.planned_rate) filter (where bi.category != 'Solar Panels')
      / nullif(b.kw_capacity * 1000, 0),
  2) as rest_rs_per_watt
from bom_items bi
join boms b on b.bom_id = bi.bom_id
group by bi.bom_id, b.kw_capacity;

-- 'Solar Panels' matches the exact category string confirmed against
-- the real SPP sheet's 15-category taxonomy (Section 19/44). Both
-- views use planned_rate, same as everything else in this schema
-- (Section 45) — never the SPP sheet's own price column, which is
-- exactly why this cost figure is trustworthy where the sheet's own
-- total isn't (Section 44 found three real formula bugs in that
-- sheet's own subtotals).

-- The itemization concern behind this ask — "don't club GI Structure
-- into one line, I need the 8-10 real components under it" — needed no
-- schema change to answer: bom_items already stores one row per line
-- item as it comes off the sheet (GI Pipe 60x40, GI Pipe 40x40,
-- Rebarring Chemical, nut-bolts, etc. are already separate materials
-- rows under category = 'GI Pipe Panel Structure', Section 44's bug
-- review confirms the real sheet already itemizes this deep). Nothing
-- in this schema ever clubbed them — bom_category_cost above just sums
-- what was already itemized, by category, for the Rs/Watt reading;
-- the itemized rows underneath remain fully visible on the BOM itself.

-- ============================================================
-- Repairing a material that got entered under the wrong name
-- ============================================================

-- Real, distinct problem from aliases (Section 27/39): aliases handles
-- matching a name variant AI has *seen before* against the right
-- material. It doesn't help when someone creates a genuinely new
-- materials row for something that already exists — "Growatt 50kW"
-- already on file, someone later enters "Solar Lian 50kW" (a
-- mishearing/typo, not a different product) as a brand-new row.
-- Prevention is a workflow change, not schema: New Material entry (and
-- the bulk stock-statement import below) should fuzzy-match the typed
-- name against existing canonical_name + aliases first and surface
-- "did you mean Growatt 50kW?" before creating anything — the same
-- AI-suggests/human-confirms pattern already used everywhere else in
-- this schema, applied one step earlier, at creation time instead of
-- only at invoice-matching time. No new column needed for that half —
-- it's an application behavior change against the existing aliases
-- field.

-- What still needed a column: repairing a duplicate that already
-- happened. Once two materials rows exist for the same real product,
-- someone needs to merge them without losing the transaction history
-- either row has already accumulated.

alter table materials add column merged_into_material_id uuid references materials(material_id);

-- An audit trail, not a live redirect other queries need to know about.
-- The merge itself is an application-level operation done once, at the
-- moment MP confirms two rows are the same material:
--   1. Append the duplicate's canonical_name (and its own aliases) into
--      the surviving row's aliases — the wrong name is now recognized
--      automatically if it ever comes in again.
--   2. Re-point every table with a material_id foreign key
--      (material_transactions, bom_items, vendor_quote_items,
--      vendor_inquiries, stock_adjustments) from the duplicate's
--      material_id to the surviving one — so all history stays intact
--      under one material_id, not split across two.
--   3. Set merged_into_material_id on the duplicate row, pointing at
--      the survivor.
-- Everything downstream (material_stock, bom_category_cost above,
-- material_last_purchase, every other view keyed on material_id) keeps
-- working unchanged after step 2 — no view needs to know merges exist.
-- merged_into_material_id only exists so a picker/search screen can
-- filter merged rows out (where merged_into_material_id is null) and
-- so anyone auditing a transaction later can see why a material_id
-- that once existed no longer shows up as selectable.
