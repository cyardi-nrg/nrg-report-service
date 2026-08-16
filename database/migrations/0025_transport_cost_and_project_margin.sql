-- ProjectPulse — Transportation/Fabricator/Electrical Contractor Cost,
-- and Margin/Profitability (Finally Defined, With Completeness Flagging)
-- Follows 0002-0024. Consolidated from docs/projectpulse-handover.md
-- Section 64.

-- ============================================================
-- Total project cost, confirmed: the BOM itself, plus exactly three
-- things — Transportation, Fabricator, Electrical Contractor
-- ============================================================

-- Real, specific answer to "what goes into total project cost besides
-- the BOM": Transportation, Fabricator cost, and Electrical Contractor
-- cost — those three, on top of material. Everything else is already
-- inside the BOM's own actual cost. project_costs.cost_type (Section
-- 38) already had 'transport'/'fabrication'/'installation_subcontract'
-- — 0024's first pass lumped fabrication and installation_subcontract
-- into one "Installation" line, then this round names them for what
-- they actually are: Fabricator and Electrical Contractor, two
-- separate real cost lines, not one blended figure. cost_type stays
-- free text (Section 38's own reasoning — no check constraint to
-- change), this is a vocabulary correction, not a schema one.

create or replace view project_transportation_cost as
select
  pc.project_id,
  sum(pc.amount) as transportation_cost,
  round(sum(pc.amount) / nullif(psb.kw_capacity * 1000, 0), 2) as transportation_rs_per_watt
from project_costs pc
join project_size_band psb on psb.project_id = pc.project_id
where pc.assignment_status = 'assigned' and pc.cost_type = 'transport'
group by pc.project_id, psb.kw_capacity;

create or replace view project_fabricator_cost as
select
  pc.project_id,
  sum(pc.amount) as fabricator_cost,
  round(sum(pc.amount) / nullif(psb.kw_capacity * 1000, 0), 2) as fabricator_rs_per_watt
from project_costs pc
join project_size_band psb on psb.project_id = pc.project_id
where pc.assignment_status = 'assigned' and pc.cost_type = 'fabrication'
group by pc.project_id, psb.kw_capacity;

create or replace view project_electrical_contractor_cost as
select
  pc.project_id,
  sum(pc.amount) as electrical_contractor_cost,
  round(sum(pc.amount) / nullif(psb.kw_capacity * 1000, 0), 2) as electrical_contractor_rs_per_watt
from project_costs pc
join project_size_band psb on psb.project_id = pc.project_id
where pc.assignment_status = 'assigned' and pc.cost_type = 'installation_subcontract'
group by pc.project_id, psb.kw_capacity;

-- 'installation_subcontract' is the existing cost_type value being
-- read as "Electrical Contractor" here — same value, correcting only
-- what it's called in the report, not the data underneath. Whichever
-- name the build session actually stores (worth settling to
-- 'electrical_contractor' outright when this gets built, so the label
-- and the stored value finally match), the view logic is unaffected.

-- 'vendor_bill'/'other' still need somewhere to go — confirmed rare
-- ("most costs already included" once material + these three are
-- counted), but a real one landing here uncounted would still make
-- total_cost silently wrong by whatever it's worth. Kept as a
-- background catch-all, folded into the total, not surfaced as a
-- named line unless it's actually nonzero.

create or replace view project_other_project_cost as
select
  pc.project_id,
  sum(pc.amount) as other_cost,
  round(sum(pc.amount) / nullif(psb.kw_capacity * 1000, 0), 2) as other_rs_per_watt
from project_costs pc
join project_size_band psb on psb.project_id = pc.project_id
where pc.assignment_status = 'assigned' and pc.cost_type in ('vendor_bill', 'other')
group by pc.project_id, psb.kw_capacity;

-- project_cost_per_watt_benchmark (0024) unioned in one "Installation"
-- row; now unions Transportation, Fabricator, Electrical Contractor,
-- and Other as four separate rows, same column shape as before.

create or replace view project_cost_per_watt_benchmark as
select
  psb.project_id, psb.size_band, psb.kw_capacity,
  bcc.category, bcc.rs_per_watt
from project_size_band psb
join bom_category_cost bcc on bcc.bom_id = psb.bom_id
union all
select
  psb.project_id, psb.size_band, psb.kw_capacity,
  'Transportation' as category,
  coalesce(ptc.transportation_rs_per_watt, 0) as rs_per_watt
from project_size_band psb
left join project_transportation_cost ptc on ptc.project_id = psb.project_id
union all
select
  psb.project_id, psb.size_band, psb.kw_capacity,
  'Fabricator' as category,
  coalesce(pfc.fabricator_rs_per_watt, 0) as rs_per_watt
from project_size_band psb
left join project_fabricator_cost pfc on pfc.project_id = psb.project_id
union all
select
  psb.project_id, psb.size_band, psb.kw_capacity,
  'Electrical Contractor' as category,
  coalesce(pec.electrical_contractor_rs_per_watt, 0) as rs_per_watt
from project_size_band psb
left join project_electrical_contractor_cost pec on pec.project_id = psb.project_id
union all
select
  psb.project_id, psb.size_band, psb.kw_capacity,
  'Other' as category,
  coalesce(poc.other_rs_per_watt, 0) as rs_per_watt
from project_size_band psb
left join project_other_project_cost poc on poc.project_id = psb.project_id;

-- ============================================================
-- Margin/profitability — deferred since Section 37/38, now defined
-- ============================================================

-- Real definition, finally given: profit against both the quote NRG
-- gave and what was actually invoiced, since they legitimately diverge
-- (change orders, negotiated discounts) and neither alone tells the
-- whole story. Cost side is BOM actual cost plus exactly the three
-- named costs above — the confirmed, complete list of what sits
-- outside the BOM itself.

-- material_actual_cost below is boms.actual_total_cost, which was
-- already exactly right for this before this migration existed:
-- bom_item_variance.actual_cost (Section 5) already attributes cost
-- against used_quantity = dispatched_quantity − returned_quantity —
-- the real, net quantity that actually left the warehouse and stayed
-- on this project through completion, not the originally planned
-- quantity — at the real weighted-average rate from actual purchase
-- transactions (material_transaction_cost, Tally/scanned-invoice-fed).
-- Nothing needed to change for margin to reflect what a project
-- actually consumed, not what its BOM originally planned.

create view project_invoiced_revenue as
select
  si.project_id,
  sum(si.total_amount) as invoiced_revenue
from sales_invoices si
where si.invoice_type = 'tax_invoice' and si.extraction_status = 'confirmed'
group by si.project_id;

-- tax_invoice specifically, not quote/proforma/debit_note/service_invoice
-- — real money actually billed to the customer, the "invoice value"
-- half of what was asked for. Confirmed only, same reasoning as
-- project_confirmed_bom: an AI-extracted, unreviewed invoice shouldn't
-- feed a profit figure.

-- ============================================================
-- Margin is only trustworthy if nothing feeding it is silently
-- missing — flag gaps instead of quietly treating them as zero
-- ============================================================

-- Real, sharp risk with a coalesce(..., 0) pattern in a margin
-- calculation specifically: a cost that's missing because nobody's
-- captured it yet (a material never dispatched/costed, a transport,
-- fabricator or electrical contractor bill never uploaded) reads
-- identically to one that's genuinely zero. That's not a neutral gap
-- here — it silently understates total_cost and overstates margin, in
-- exactly the direction that flatters the business. Flagged instead of
-- hidden, one flag per cost source so it's clear exactly what's
-- missing, not just that something is.

create view project_margin_completeness as
select
  pcb.project_id,
  pcb.bom_id,
  (
    select count(*) from bom_item_variance biv
    where biv.bom_id = pcb.bom_id
      and biv.planned_quantity > 0
      and (biv.actual_cost is null or biv.dispatched_quantity = 0)
  ) as material_lines_missing_cost,
  exists (
    select 1 from project_costs pc
    where pc.project_id = pcb.project_id and pc.assignment_status = 'assigned' and pc.cost_type = 'transport'
  ) as has_transportation_cost,
  exists (
    select 1 from project_costs pc
    where pc.project_id = pcb.project_id and pc.assignment_status = 'assigned' and pc.cost_type = 'fabrication'
  ) as has_fabricator_cost,
  exists (
    select 1 from project_costs pc
    where pc.project_id = pcb.project_id and pc.assignment_status = 'assigned' and pc.cost_type = 'installation_subcontract'
  ) as has_electrical_contractor_cost
from project_confirmed_bom pcb;

-- material_lines_missing_cost counts planned line items that either
-- never got dispatched at all, or got dispatched but never picked up a
-- real cost — either way, that line's contribution to
-- boms.actual_total_cost is silently absent, not zero. The three
-- has_*_cost flags are existence checks, not amount checks: a project
-- can legitimately have a small bill in any of these, but zero
-- captured rows is far more likely to mean "not uploaded yet" than
-- "genuinely free" — flagged individually so the owner sees exactly
-- which of the three is missing, not just that the total looks
-- incomplete.

create view project_margin as
select
  pcb.project_id,
  pcb.bom_id,
  pcb.kw_capacity,
  b.order_value as quoted_revenue,
  pir.invoiced_revenue,
  b.actual_total_cost as material_actual_cost,
  coalesce(ptc.transportation_cost, 0) as transportation_cost,
  coalesce(pfc.fabricator_cost, 0) as fabricator_cost,
  coalesce(pec.electrical_contractor_cost, 0) as electrical_contractor_cost,
  coalesce(poc.other_cost, 0) as other_cost,
  coalesce(b.actual_total_cost, 0) + coalesce(ptc.transportation_cost, 0)
    + coalesce(pfc.fabricator_cost, 0) + coalesce(pec.electrical_contractor_cost, 0)
    + coalesce(poc.other_cost, 0) as total_cost,
  b.order_value - (coalesce(b.actual_total_cost, 0) + coalesce(ptc.transportation_cost, 0)
    + coalesce(pfc.fabricator_cost, 0) + coalesce(pec.electrical_contractor_cost, 0)
    + coalesce(poc.other_cost, 0)) as margin_quoted,
  round(100.0 * (b.order_value - (coalesce(b.actual_total_cost, 0) + coalesce(ptc.transportation_cost, 0)
    + coalesce(pfc.fabricator_cost, 0) + coalesce(pec.electrical_contractor_cost, 0)
    + coalesce(poc.other_cost, 0))) / nullif(b.order_value, 0), 2) as margin_pct_quoted,
  pir.invoiced_revenue - (coalesce(b.actual_total_cost, 0) + coalesce(ptc.transportation_cost, 0)
    + coalesce(pfc.fabricator_cost, 0) + coalesce(pec.electrical_contractor_cost, 0)
    + coalesce(poc.other_cost, 0)) as margin_invoiced,
  round(100.0 * (pir.invoiced_revenue - (coalesce(b.actual_total_cost, 0) + coalesce(ptc.transportation_cost, 0)
    + coalesce(pfc.fabricator_cost, 0) + coalesce(pec.electrical_contractor_cost, 0)
    + coalesce(poc.other_cost, 0))) / nullif(pir.invoiced_revenue, 0), 2) as margin_pct_invoiced,
  pmc.material_lines_missing_cost,
  pmc.has_transportation_cost,
  pmc.has_fabricator_cost,
  pmc.has_electrical_contractor_cost,
  (pmc.material_lines_missing_cost = 0 and pmc.has_transportation_cost
    and pmc.has_fabricator_cost and pmc.has_electrical_contractor_cost) as margin_data_complete
from project_confirmed_bom pcb
join boms b on b.bom_id = pcb.bom_id
join project_margin_completeness pmc on pmc.project_id = pcb.project_id
left join project_transportation_cost ptc on ptc.project_id = pcb.project_id
left join project_fabricator_cost pfc on pfc.project_id = pcb.project_id
left join project_electrical_contractor_cost pec on pec.project_id = pcb.project_id
left join project_other_project_cost poc on poc.project_id = pcb.project_id
left join project_invoiced_revenue pir on pir.project_id = pcb.project_id;

-- margin_data_complete is the one flag the UI actually needs — false
-- means show the number in red/amber with what's missing named, not
-- hide it outright: an incomplete-but-directionally-useful figure is
-- still worth seeing, as long as it's never mistaken for a finished
-- one. Same latest-confirmed-BOM basis as project_size_band (Section
-- 63) — margin is only as trustworthy as the cost/quantity figures
-- behind it, so it inherits the same "confirmed only" gate. Owner-only,
-- unchanged boundary (Section 39): shown per project directly on that
-- project's own BOM tab (Section 59's Cost per Watt panel gets
-- Transportation/Fabricator/Electrical Contractor/Margin rows added —
-- confirmed real ask: margin belongs on the BOM screen itself, not a
-- separate tab), and rolled up to finally fill in the "Project Margin
-- & Profitability" Reports card that's been a placeholder since
-- Section 37.
