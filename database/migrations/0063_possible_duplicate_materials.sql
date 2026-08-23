-- NRG SolarConnect — Proactive "possible duplicate materials" finder
-- Follows 0002-0062.

-- ============================================================
-- The real risk with a naive similarity-only approach
-- ============================================================

-- Plain trigram similarity on canonical_name alone is NOT enough to
-- flag possible duplicates safely — two genuinely DIFFERENT, real SKUs
-- can score very high just from shared boilerplate wording:
--   'Adani Solar 620Wp Mono PERC Module (DCR)' vs
--   'Adani Solar 620Wp Mono PERC Module (Non-DCR)'       -> 0.90 similarity
--   'Waaree 615Wp ... (Non-DCR)' vs 'Waaree 610Wp ... (Non-DCR)' -> 0.88
-- DCR vs Non-DCR is a real, subsidy-eligibility-relevant distinction;
-- different panel wattages are different physical SKUs. A naive
-- threshold would put these false positives at the TOP of the list
-- (they score far higher than genuine near-duplicates like "20KW
-- Ksolar Inverter" vs "Ksolare KS-M3-20K..." at 0.43) and risk the
-- owner merging two materially different items.
--
-- Fix: for Solar Panel specifically, extract wattage and DCR/Non-DCR
-- status as hard gates — a pair is never flagged as a possible
-- duplicate if BOTH sides have an extractable wattage/status and they
-- disagree, no matter how similar the surrounding text. Similarity
-- score still decides ranking among what's left.

create table material_duplicate_dismissals (
  dismissal_id     uuid primary key default gen_random_uuid(),
  material_id_a    uuid not null references materials(material_id),
  material_id_b    uuid not null references materials(material_id),
  dismissed_by     uuid references employees(employee_id),
  dismissed_at     timestamptz not null default now(),
  check (material_id_a < material_id_b),
  unique (material_id_a, material_id_b)
);
-- Pair stored with material_id_a always the smaller uuid — normalizes
-- the pair regardless of which side the function returns first, so
-- "already dismissed" and the unique constraint both just work.

create or replace function find_possible_duplicate_materials(p_limit int default 30)
returns table (
  material_id_a uuid, name_a text, stock_a numeric,
  material_id_b uuid, name_b text, stock_b numeric,
  category text, score real
)
language sql stable
as $$
  with annotated as (
    select
      m.material_id, m.canonical_name, m.category,
      substring(lower(m.canonical_name) from '([0-9]{3,4})wp?') as wattage,
      case
        when m.canonical_name ~* '(non-?dcr|ndcr)' then 'NDCR'
        when m.canonical_name ~* '\ydcr\y' then 'DCR'
        else null
      end as dcr_status
    from materials m
    where m.merged_into_material_id is null and not m.is_rate_card_only
  )
  select
    a.material_id, a.canonical_name, coalesce(sa.current_stock, 0),
    b.material_id, b.canonical_name, coalesce(sb.current_stock, 0),
    a.category, similarity(a.canonical_name, b.canonical_name) as score
  from annotated a
  join annotated b on b.category = a.category and b.material_id > a.material_id
  left join material_stock sa on sa.material_id = a.material_id
  left join material_stock sb on sb.material_id = b.material_id
  where similarity(a.canonical_name, b.canonical_name) >= 0.2
    and (a.wattage is null or b.wattage is null or a.wattage = b.wattage)
    and (a.dcr_status is null or b.dcr_status is null or a.dcr_status = b.dcr_status)
    and not exists (
      select 1 from material_duplicate_dismissals d
      where d.material_id_a = least(a.material_id, b.material_id)
        and d.material_id_b = greatest(a.material_id, b.material_id)
    )
  order by score desc
  limit p_limit;
$$;

-- 0.2 threshold matches MATCH_FLOOR's neighborhood (0057) and sits
-- comfortably below every real near-duplicate case found in trial
-- testing (0.24-0.43) while excluding true noise.
