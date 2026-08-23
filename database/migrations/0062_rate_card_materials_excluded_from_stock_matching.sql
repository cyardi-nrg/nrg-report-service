-- NRG SolarConnect — Rate-card pricing placeholders are not stock items
-- Follows 0002-0061.

-- ============================================================
-- The real problem: one materials table, two different jobs
-- ============================================================

-- lib/pricing.ts's wattageRangeFor() is ported verbatim from the
-- owner's real spreadsheet (bandKeyForWatt(): 715W -> "700-720", 620W
-- -> "600-630", 550W -> "525-565") — the Quote engine genuinely prices
-- panels by wattage BAND, not exact wattage, and that's correct and
-- unchanged by this migration. The Rates screen's "+ Add new panel
-- make/wattage" form (addPanelMaterial) creates a materials row per
-- band+brand purely so quote_panel_rates has something to point a
-- rate_id at — e.g. "Solar Panel 600-630W · Waaree" with 0 real stock,
-- never meant to be a physical, purchasable, stockable SKU.
--
-- The bug: suggest_material_matches (0057) searches ALL of `materials`
-- with no distinction, so these rate-card placeholders show up as
-- candidates in Scan/Stock's material-match/confirm flow right next to
-- real physical inventory (owner-reported: a Waaree 615W panel already
-- in stock at 120 Nos didn't get matched because a same-scoring
-- "Solar Panel 600-630W · Waaree" rate-card row — 0 stock, never
-- transacted — ranked ahead of it, or got picked instead). A panel is
-- bought and stocked at one exact wattage, never a range; the owner's
-- own distinction: a range is fine for genuine capacity BANDS (ACDB/
-- inverter pricing, already handled separately via
-- quote_inverter_rate_bands' numeric min_kw/max_kw — never touches
-- materials at all), never for a physical stock item.

alter table materials add column is_rate_card_only boolean not null default false;

-- Every existing Solar Panel material created via the Rates screen's
-- "Solar Panel NNN-NNNW · Brand" convention is exactly this — a
-- pricing placeholder, never a real purchased/stocked SKU. Real
-- physical stock materials (however they got created — Scan, manual
-- Log Material, anything) use ordinary product naming and never
-- collide with this pattern.
update materials set is_rate_card_only = true
where category = 'Solar Panel' and canonical_name ~ '^Solar Panel \d+-\d+W · .+$';

create index on materials (is_rate_card_only);

-- ============================================================
-- Fix: exclude rate-card-only rows from the match/confirm suggestion
-- pool. Nothing about the Rates screen or quote_panel_rates changes —
-- page.tsx still reads every category='Solar Panel' material
-- regardless of this flag, so pricing is untouched.
-- ============================================================

create or replace function suggest_material_matches(p_raw_text text, p_category_hint text default null, p_limit int default 5)
returns table (material_id uuid, category text, canonical_name text, make text, default_unit text, score real)
language sql stable
as $$
  select
    m.material_id, m.category, m.canonical_name, m.make, m.default_unit,
    greatest(
      similarity(m.canonical_name, p_raw_text),
      coalesce((select max(similarity(a, p_raw_text)) from unnest(m.aliases) a), 0)
    ) as score
  from materials m
  where m.merged_into_material_id is null
    and not m.is_rate_card_only
    and (p_category_hint is null or m.category = p_category_hint)
  order by score desc
  limit p_limit;
$$;
