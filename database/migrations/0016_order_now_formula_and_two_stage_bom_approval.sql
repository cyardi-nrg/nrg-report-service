-- ProjectPulse — Correct "Order Now" Formula, Two-Stage BOM Approval
-- Follows 0002-0015. Consolidated from docs/projectpulse-handover.md
-- Section 43. employees (0002) already covers the editable People roster
-- (name/role/phone/email/active) — no schema change needed there.

-- ============================================================
-- "Order Now" belongs in the view, not ad-hoc UI arithmetic
-- ============================================================

-- material_shortfall (0003) computes shortfall = requirement - (stock +
-- open orders) — useful, but doesn't fold in reorder_level at all.
-- Confirmed real formula for "Order Now": In Stock + Order Placed +
-- Min Level - On Hand Orders. Adds a column rather than replacing
-- shortfall — both are real, different questions ("how far under
-- committed demand" vs. "including my safety buffer, do I still cover
-- it").

create or replace view material_shortfall as
select
  m.material_id,
  m.category,
  m.canonical_name,
  m.default_unit,
  m.reorder_level,
  coalesce(s.current_stock, 0) as current_stock,
  coalesce(o.open_order_quantity, 0) as open_order_quantity,
  coalesce(r.outstanding_requirement, 0) as outstanding_requirement,
  coalesce(r.outstanding_requirement, 0) - (coalesce(s.current_stock, 0) + coalesce(o.open_order_quantity, 0)) as shortfall,
  (coalesce(s.current_stock, 0) + coalesce(o.open_order_quantity, 0) + coalesce(m.reorder_level, 0))
    - coalesce(r.outstanding_requirement, 0) as order_now
from materials m
left join material_stock s on s.material_id = m.material_id
left join material_open_orders o on o.material_id = m.material_id
left join material_requirement r on r.material_id = m.material_id;

-- order_now negative -> order it. Positive/zero -> covered, even after
-- counting the safety buffer. This is the one column the Stock
-- dashboard's "Order Now" should actually read from — not a
-- recalculation in the UI layer that can drift from what the schema
-- says.

-- ============================================================
-- Two-stage BOM approval before it drives ordering
-- ============================================================

-- Confirmed flow for a sheet-generated BOM: engineer creates and
-- confirms (already covered — extraction_status='confirmed',
-- confirmed_by/confirmed_at, Section 19), then the owner has a second,
-- separate sign-off before it's allowed to actually drive purchasing.
-- Only once both are set should the BOM's planned_quantity count
-- toward material_requirement.

alter table boms add column owner_approved_by uuid references employees(employee_id);
alter table boms add column owner_approved_at timestamptz;

create or replace view material_requirement as
select
  bi.material_id,
  sum(bi.planned_quantity - coalesce(issued.qty, 0)) as outstanding_requirement
from bom_items bi
join boms b on b.bom_id = bi.bom_id
join projects p on p.project_id = b.project_id
left join (
  select bom_item_id, sum(quantity) as qty
  from material_transactions
  where movement_type = 'issued_to_site'
  group by bom_item_id
) issued on issued.bom_item_id = bi.bom_item_id
where p.status = 'active'
  and bi.material_id is not null
  and b.extraction_status = 'confirmed'
  and (b.origin = 'uploaded_workbook' or b.owner_approved_at is not null)
group by bi.material_id;

-- The extra condition is scoped deliberately: an uploaded workbook is
-- already a human-authored document (Principle 1), so it only needs
-- the existing single confirmation — requiring a second owner sign-off
-- on top would be redundant and would silently break every historical
-- BOM already relying on the old gate. The second tick is specifically
-- for boms.origin IN ('system_calculated','recommendation_engine') —
-- the sheet-driven and recommendation-engine paths this session just
-- built, where nobody has actually looked at a human-prepared document
-- yet.
