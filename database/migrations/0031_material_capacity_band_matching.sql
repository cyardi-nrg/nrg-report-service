-- NRG SolarConnect — Capacity-Banded Products (ACDB/DCDB, Inverters) Need
-- Range Matching, Not Exact-Value Matching
-- Follows 0002-0030. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 71.

-- ============================================================
-- Real, concrete failure mode: NRG orders "30kW ACDB," the vendor's
-- actual product is rated "25-40kW ACDB" — same real product, two
-- different-looking numbers
-- ============================================================

-- Confirmed real risk, distinct from (and upstream of) the purchase
-- reconciliation problem 0027 already solved: a PO gets raised
-- against a required capacity (30kW ACDB) that doesn't exist as an
-- exact SKU — vendors sell ACDB/DCDB (and some inverters) rated by
-- band, not by NRG's specific per-project number. If materials.
-- canonical_name only ever stores NRG's requirement ("ACDB 30kW")
-- rather than the real product's actual rating ("ACDB 25-40kW"), two
-- real problems follow: MP can end up creating a materials row for a
-- SKU that doesn't actually exist anywhere a vendor sells it, and an
-- invoice later describing the vendor's real, ranged product has
-- nothing to text-match against — the aliases mechanism (Section 27)
-- handles spelling variants of the *same* number ("Growatt 50kW" vs.
-- "Group work 50 kilo"), not a single value against a range that
-- covers it, which is a different kind of mismatch entirely.

-- purchase_order_item_id linking (0027) is the primary, already-built
-- defense once a PO exists — an invoice matched to its own open PO
-- line never needs to re-resolve the material from text at all, no
-- matter how the vendor describes their product. This migration
-- covers the case 0027 doesn't: creating or matching a capacity-banded
-- material with no PO link yet to lean on — the first time NRG buys a
-- given band, or an ad-hoc purchase with no PO at all.

alter table materials add column rated_capacity_min_kw numeric(10,3);
alter table materials add column rated_capacity_max_kw numeric(10,3);

-- Both null for materials that don't have this concept at all — cables
-- (sq mm), panels (Wp), most hardware. Populated only for genuinely
-- band-rated categories (ACDB, DCDB, and any inverter model a vendor
-- rates by range rather than one figure). canonical_name should record
-- the real product's own band ("ACDB 25-40kW"), matching how the
-- vendor/manufacturer actually names it — not NRG's specific ordered
-- requirement — same principle Section 27 already established for
-- panels/inverters (canonical_name is the product's real identity, not
-- a project's requirement for it).

-- Matching a required capacity against this is a plain range query —
-- given category = 'ACDB' and a required 30kW, find materials where
-- 30 is between rated_capacity_min_kw and rated_capacity_max_kw — no
-- new view needed, same reasoning as the aliases fuzzy-match itself
-- (Section 27/60): this is app/AI-layer matching logic against
-- existing columns, not a schema object. Two places it applies:
--   1. At BOM/PO creation — when a driver input or Engineering BOM
--      calls for "30kW ACDB," the picker suggests the existing banded
--      material whose range covers 30, instead of inviting MP to
--      type/create a new "30kW" row that doesn't correspond to a real
--      product.
--   2. As AI-extraction's fallback match for a receiving document with
--      no purchase_order_item_id to anchor to — parse the vendor's own
--      stated rating off the invoice/DC and match by range overlap
--      against existing materials, same suggest/confirm pattern as
--      everywhere else, before falling back to creating a new row.
-- materials.merged_into_material_id (Section 60) remains the repair
-- path if a phantom exact-value row already got created before this
-- existed — merge it into the real banded product once identified.
