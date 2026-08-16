-- ProjectPulse — Marking a Pipeline Project Lost, and Whether NRG
-- Should Have Matched the Price It Was Lost At
-- Follows 0002-0031. Consolidated from docs/projectpulse-handover.md
-- Section 72.

-- ============================================================
-- Lost is how a pipeline project leaves the active pipeline —
-- a status, not a deletion
-- ============================================================

-- Real ask: pipeline projects that didn't convert need to come off the
-- active "In Talks" list, and marking them lost is how that happens —
-- same reasoning as 'cancelled'/'on_hold' already being ordinary
-- status values rather than deletions (Section 2). material_requirement
-- (0016) and everything else gated on status = 'active' already
-- excludes 'lost' automatically, same as 'in_talks' (Section 68) —
-- nothing else needs to change for a lost project to stop showing up
-- anywhere it shouldn't.

alter table projects drop constraint projects_status_check;
alter table projects add constraint projects_status_check
  check (status in ('in_talks', 'active', 'lost', 'commissioned', 'on_hold', 'cancelled'));

-- ============================================================
-- What it was lost at — sales enters this if they know it, not
-- required
-- ============================================================

-- Real ask, and a real, useful number if it exists: the amount the
-- deal actually went for elsewhere (a competitor's price, or whatever
-- figure the customer said would have won it) — "if they have the
-- information," genuinely optional, sales doesn't always know it.

alter table projects add column lost_amount numeric(14,2);
alter table projects add column lost_recorded_by uuid references employees(employee_id);
alter table projects add column lost_at timestamptz;

-- lost_amount is deliberately separate from boms.order_value (Section
-- 19) — order_value is NRG's own quote, lost_amount is what the
-- market actually cleared at. Both need to exist side by side for the
-- comparison below to mean anything.

-- ============================================================
-- Should NRG have taken it at the price it was lost for?
-- ============================================================

-- Real ask, and the actual point of capturing lost_amount at all:
-- compare it against what the project would have cost NRG to build
-- (same size-band-benchmark-based estimate as pipeline_project_
-- margin_estimate, Section 68, which was never scoped to
-- status = 'in_talks' specifically) to see whether matching the
-- losing price would have been profitable or a loss NRG was right to
-- walk away from.

create view lost_project_analysis as
select
  ppme.project_id,
  ppme.size_band,
  ppme.kw_capacity,
  ppme.quoted_price as our_quoted_price,
  p.lost_amount,
  ppme.estimated_total_project_cost,
  p.lost_amount - ppme.estimated_total_project_cost as margin_if_matched_lost_price,
  round(
    100.0 * (p.lost_amount - ppme.estimated_total_project_cost) / nullif(p.lost_amount, 0)
  , 2) as margin_pct_if_matched_lost_price,
  (p.lost_amount - ppme.estimated_total_project_cost) > 0 as would_have_been_profitable_at_lost_price,
  ppme.has_transportation_benchmark,
  ppme.has_fabricator_benchmark,
  ppme.has_electrical_contractor_benchmark
from pipeline_project_margin_estimate ppme
join projects p on p.project_id = ppme.project_id
where p.status = 'lost' and p.lost_amount is not null;

-- Reuses pipeline_project_margin_estimate wholesale rather than
-- recomputing cost — the estimate doesn't care whether a project is
-- still 'in_talks' or has since moved to 'lost', it just needs a
-- confirmed BOM to price. where p.lost_amount is not null on purpose:
-- a project marked lost with no known lost-at figure still shows up
-- everywhere a lost project should, it just has nothing for this
-- specific comparison to run against — no fabricated number stands in
-- for one sales never had. would_have_been_profitable_at_lost_price is
-- the actual answer to "should we have taken it": true means NRG
-- likely left a winnable, profitable deal on the table by not pricing
-- closer to the competitor; false means walking away was the right
-- call.

-- Same access boundary as everywhere else pricing/margin shows up
-- (Section 39/64/68's correction) — Owner/Sales Head only. Sales
-- enters lost_amount (they're the ones with the market intel) but
-- doesn't see this analysis any more than they see a live pipeline
-- project's cost breakdown; entering a number and being shown the
-- conclusion drawn from it are two different permissions.
