-- NRG SolarConnect — Material Match/Confirm Queue
--
-- Real, critical business risk the owner flagged directly: a purchase bill
-- or material-out scan might name the same physical item completely
-- differently from how it's already in inventory ("40x40 GI Pipe" vs.
-- "GI Pipe 40x40mm") — if that silently creates a second materials row,
-- stock position, reorder alerts, and the bank-facing Monthly Stock
-- Statement all go quietly wrong, with no error to catch it.
--
-- material_transactions.material_id is already NOT NULL (confirmed live),
-- so it already can't hold an unresolved mention — this queue is the
-- staging area a raw name sits in UNTIL a human confirms which existing
-- material it means, or explicitly creates a new one. Nothing writes to
-- material_transactions except through that resolution.

create extension if not exists pg_trgm;

create index if not exists materials_canonical_name_trgm_idx on materials using gin (canonical_name gin_trgm_ops);

create table material_match_queue (
  match_queue_id      uuid primary key default gen_random_uuid(),
  raw_text            text not null,          -- exactly as it appeared on the bill/challan
  context             text not null default 'purchase',  -- free text: 'purchase' | 'issued_to_site' | 'returned_to_warehouse' | 'sold_direct'
  category_hint       text,                    -- optional, narrows the match search if known
  quantity            numeric(14,3) not null,
  rate                numeric(14,2),
  unit                text,
  vendor_id           uuid references partners(partner_id),
  project_id          uuid references projects(project_id),   -- required for issued_to_site/returned_to_warehouse context
  transaction_date     date not null default current_date,
  source_document_id   uuid references documents(document_id),
  resolution_status    text not null default 'pending'
                        check (resolution_status in ('pending', 'matched_existing', 'created_new')),
  resolved_material_id uuid references materials(material_id),
  resolved_by          uuid references employees(employee_id),
  resolved_at          timestamptz,
  resulting_transaction_id uuid references material_transactions(transaction_id),
  created_by           uuid references employees(employee_id),
  created_at            timestamptz not null default now()
);

create index on material_match_queue (resolution_status);

-- Best-match suggestion: max trigram similarity of raw_text against a
-- material's canonical_name OR any of its aliases. Category-scoped when a
-- hint is given (narrows false positives across unrelated categories that
-- happen to share words), unscoped otherwise.
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
    and (p_category_hint is null or m.category = p_category_hint)
  order by score desc
  limit p_limit;
$$;
