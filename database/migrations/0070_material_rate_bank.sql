-- NRG SolarConnect — Material Rate Bank
-- Follows 0002-0069.
--
-- A stopgap price reference for BOM costing — the owner's own framing:
-- "initially we will have to do this... till we build a list of
-- comparative quotes and PO rates." Real BOM costing is meant to come
-- from actual purchase history (material_purchase_running_avg /
-- material_weighted_avg_rate_as_of, 0005) once enough of it exists; this
-- exists because most industrial BOM line items (inverter makes/sizes,
-- ACDB, GI pipe, cable, ...) have no purchase history yet and were
-- reading either a single flat guess or a scaled-from-one-project
-- estimate. Same anchor as the rest of the schema: an inverter make/size,
-- an ACDB spec, etc. is an ordinary `materials` row (real physical
-- SKUs, unlike the Solar Panel wattage-BAND rate-card placeholders,
-- 0062) — this table just adds a price to it.
--
-- Insert-only, never updated in place — "how do we make sure the latest
-- rate is used, not an earlier one" is answered by never letting an old
-- rate silently become the new one; a fresh row is the only way to
-- change a price, and it's always dated and attributed.

create table material_rate_bank (
  rate_id       uuid primary key default gen_random_uuid(),
  material_id   uuid not null references materials(material_id),
  rate          numeric(14,2) not null,
  source_note   text,   -- free text: "PO from ABC Solar, 12 Aug 2026" / "Vendor quote — XYZ" / "SPP Bill of Material sheet"
  uploaded_by   uuid references employees(employee_id),
  created_at    timestamptz not null default now()
);

create index on material_rate_bank (material_id, created_at desc);

comment on table material_rate_bank is 'Manually-uploaded reference rates for BOM costing (inverter/ACDB/GI pipe/cable/...), a stopgap until enough real purchase history exists. Insert-only — the latest row per material_id is the one in effect, see material_rate_bank_current.';

-- The one thing that actually answers "what rate, from where, as of
-- when" for a line item's own "?" info button — never re-derived by the
-- app from raw rows, so there's exactly one place this logic lives.
create view material_rate_bank_current as
select distinct on (b.material_id)
  b.rate_id, b.material_id, b.rate, b.source_note, b.uploaded_by, b.created_at,
  m.category, m.canonical_name, m.make, m.default_unit,
  e.name as uploaded_by_name
from material_rate_bank b
join materials m on m.material_id = b.material_id
left join employees e on e.employee_id = b.uploaded_by
order by b.material_id, b.created_at desc;
