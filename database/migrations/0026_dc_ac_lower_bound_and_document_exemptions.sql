-- ProjectPulse — DC:AC Ratio Gets a Lower Bound Too, Required
-- Documents Gap Can Be Marked Not Required Per Project, and Cost
-- Above Panel Cost on the Size-Band Benchmark
-- Follows 0002-0025. Consolidated from docs/projectpulse-handover.md
-- Section 66.

-- ============================================================
-- DC:AC ratio was only ever checked one direction
-- ============================================================

-- bom_capacity_check (0021) only ever flagged oversized (ratio > 1.4).
-- Real, confirmed acceptable band: 0.9 to 1.4 — a ratio noticeably
-- below 0.9 means the inverter is oversized relative to the array,
-- which is its own real inefficiency (money spent on inverter
-- capacity the panels can't use), not something the original design
-- had any way to flag. A mockup review caught this directly: Devansh
-- Textiles' 1.13 was being read as a flagged number because the
-- report's Doc-consistency flag and its DC:AC number sat in the same
-- column with no visual separation — the ratio itself was correct and
-- fine all along, but the report never had a lower bound to actually
-- confirm that with, and the two checks weren't visually distinct
-- either (a UI-only fix, alongside this one).

create or replace view bom_capacity_check as
select
  b.bom_id,
  b.project_id,
  b.panel_wattage,
  b.panel_count,
  b.kw_capacity as dc_capacity_kw,
  b.inverter_capacity_kw as ac_capacity_kw,
  round(b.kw_capacity / nullif(b.inverter_capacity_kw, 0), 2) as dc_ac_ratio,
  (b.kw_capacity / nullif(b.inverter_capacity_kw, 0)) > 1.4 as oversized,
  (b.kw_capacity / nullif(b.inverter_capacity_kw, 0)) < 0.9 as undersized
from boms b
where b.inverter_capacity_kw is not null;

-- Both flags independent, same as before — a BOM is either oversized,
-- undersized, or neither (the OK band, 0.9-1.4 inclusive-ish at the
-- edges); never both at once by construction. The Generate BOM
-- screen's live readout (Section 56) now checks both edges the same
-- way, flagging the moment the ratio crosses either one.

-- ============================================================
-- Required Documents Gap needs a real "not required for this
-- project" state, or a genuinely inapplicable document sits open
-- forever
-- ============================================================

-- Required Documents Gap (Section 36) was deliberately a query, not
-- stored state: an app-level checklist per project_type, checked off
-- against whichever document_types have actually been uploaded for a
-- project. That was fine as long as every project of a given type
-- genuinely needs every document on that type's checklist — real,
-- confirmed case that breaks it: some applications genuinely don't
-- need a standard document (DG Set approval only applies if there's a
-- diesel generator on site; some KYC documents only apply to certain
-- applicant types). With no way to say "not applicable here," that
-- document sits open on the gap report permanently, for a reason
-- nobody can see just by looking at the report.

create table project_document_exemptions (
  exemption_id  uuid primary key default gen_random_uuid(),
  project_id    uuid not null references projects(project_id),
  document_type text not null,   -- same free-text values as documents.document_type (Section 36)
  reason        text not null,   -- why this one doesn't apply here — required, not optional
  marked_by     uuid references employees(employee_id),
  marked_at     timestamptz not null default now(),
  unique (project_id, document_type)
);

create index on project_document_exemptions (project_id);

-- The Required Documents Gap query now excludes a document_type for a
-- project if either a real documents row exists for it (already
-- uploaded) OR an exemption row exists (confirmed not applicable) —
-- same "gap" definition as before, just two ways to close one instead
-- of one. reason is required, not optional, so a tick is always
-- explainable later, not a silent dismissal — same principle as
-- declared_quantity's note (Section 65) and stock_adjustments.reason
-- (Section 54): an override is fine, an unexplained one isn't.

-- ============================================================
-- Cost Above Panel Cost — real ask, needed its own aggregate, not
-- just per-category rows
-- ============================================================

-- Real ask on the Cost Benchmark by Project Size report (Section 63):
-- below the Total row, also show what everything except the panel
-- costs — "cost above panel cost." Same reasoning already established
-- for bom_panel_vs_rest_cost (0023) at the single-project level, but
-- that view doesn't carry size_band or feed size_band_standard_cost's
-- averaging — needed here as its own aggregate, not computed by
-- summing category averages (same trap already avoided for the plain
-- Total row: summing GI Structure's average and Strut Channel's
-- average would double-count structure cost, so Total was always the
-- average of each project's own total, never a sum of category
-- averages — Cost Above Panel needs the identical treatment).

create view project_total_cost_per_watt as
select
  pcpwb.project_id,
  pcpwb.size_band,
  pcpwb.kw_capacity,
  sum(pcpwb.rs_per_watt) as total_rs_per_watt,
  sum(pcpwb.rs_per_watt) filter (where pcpwb.category != 'Solar Panels') as non_panel_rs_per_watt,
  pmc.margin_data_complete
from project_cost_per_watt_benchmark pcpwb
join project_margin_completeness pmc on pmc.project_id = pcpwb.project_id
group by pcpwb.project_id, pcpwb.size_band, pcpwb.kw_capacity, pmc.margin_data_complete;

-- margin_data_complete (0025) is reused here as-is — its definition
-- never actually referenced revenue, only whether every cost input
-- (material lines, transport, fabricator, electrical contractor) is
-- present, so it's exactly the right completeness signal for a
-- cost-only aggregate too, not something margin-specific.

create view size_band_total_standard_cost as
select
  size_band,
  round(avg(total_rs_per_watt), 2) as avg_total_rs_per_watt,
  round(avg(non_panel_rs_per_watt), 2) as avg_non_panel_rs_per_watt,
  count(*) as complete_project_count
from project_total_cost_per_watt
where margin_data_complete
group by size_band;

-- Averages only over complete projects, same as size_band_standard_cost
-- (Section 64's correction) — an incomplete project's understated cost
-- must never silently pull the slab's standard Total or Cost Above
-- Panel Cost figure down. complete_project_count travels with it for
-- the same "thin evidence" reason as size_band_standard_cost's own
-- project_count.
