-- NRG SolarConnect — Multi-Tenant Foundation: Built for NRG Now, Sellable
-- Later Without a Rewrite
-- Follows 0002-0034. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 78.

-- ============================================================
-- Real ask: NRG needs this live for itself, starting as soon as
-- possible, single-tenant in practice. But the owner also wants the
-- OPTION — not the obligation — to sell this later to other solar EPCs,
-- tiered by module (a customer might take only Service, or Service +
-- Sales, or everything). Retrofitting tenant isolation onto a schema
-- that already holds real customer/project data is expensive and risky
-- — every table needs a column added, every existing row needs a
-- correct value backfilled, and every access rule needs re-auditing.
-- Adding it now, before real data piles up and before the Sales/Service
-- tables even exist yet, costs almost nothing. Full white-labeling —
-- custom per-tenant branding, a public signup flow, Stripe/billing, an
-- admin console for managing other companies' accounts — is explicitly
-- NOT built here. There is no second customer yet; building that
-- machinery now means guessing at requirements nobody has stated.
-- Only the two things expensive to bolt on later go in now: tenant
-- isolation, and a per-tenant module on/off switch.
-- ============================================================

create table organizations (
  organization_id  uuid primary key default gen_random_uuid(),
  name             text not null,
  status           text not null default 'active' check (status in ('active','trial','suspended')),
  created_at       timestamptz not null default now()
);

-- NRG itself is tenant #1 — this is the system's one real customer
-- today, not a placeholder row.
insert into organizations (organization_id, name) values
  ('00000000-0000-0000-0000-000000000001', 'NRG Technologists Pvt Ltd');

-- ============================================================
-- Module entitlements — the literal "tick a module, they pay for it"
-- mechanism the owner described. One row per organization per module;
-- a missing row means that module is off for that tenant. module_key
-- is deliberately free text, not a fixed enum — same reasoning as
-- bom_items.category (Section 19): a new module (the Sales/Service
-- rebuild this unblocks, and whatever comes after) just needs a new
-- row here, never a schema change.
-- ============================================================

create table module_entitlements (
  entitlement_id   uuid primary key default gen_random_uuid(),
  organization_id  uuid not null references organizations(organization_id),
  module_key       text not null,
     -- 'projects_inventory' (everything in Sections 1-77 — BOM/Stock/
     -- Purchase/Documents/Financials/Milestones) | 'service' (Service
     -- Desk: tickets + AMC) | 'sales_quotes' (Quote Generator) |
     -- 'sales_followup' (Sales Follow-up / pipeline) | 'prospect_crm'
     -- (Prospect List) | 'bill_analyser' (Solar Bill Analyser)
  tier             text not null default 'basic' check (tier in ('basic','advanced')),
  enabled_by       uuid references employees(employee_id),
  enabled_at       timestamptz not null default now(),
  unique (organization_id, module_key)
);

-- NRG gets every module at the top tier — they aren't a customer of
-- this switch, they're the reason it exists.
insert into module_entitlements (organization_id, module_key, tier) values
  ('00000000-0000-0000-0000-000000000001', 'projects_inventory', 'advanced'),
  ('00000000-0000-0000-0000-000000000001', 'service',            'advanced'),
  ('00000000-0000-0000-0000-000000000001', 'sales_quotes',       'advanced'),
  ('00000000-0000-0000-0000-000000000001', 'sales_followup',     'advanced'),
  ('00000000-0000-0000-0000-000000000001', 'prospect_crm',       'advanced'),
  ('00000000-0000-0000-0000-000000000001', 'bill_analyser',      'advanced');

-- ============================================================
-- Tenant scoping on the ANCHOR tables only — not every table in the
-- schema. employees / partners / customers / materials / projects are
-- the true roots; everything else (documents, boms, bom_items,
-- material_transactions, financial_obligations, project_milestones,
-- and every Sales/Service table still to be built) reaches an
-- organization by following its existing foreign key up to one of
-- these five. A child table's tenant is "whichever organization its
-- project/customer/material belongs to," never a second, independently-
-- set copy of the same fact — so there is exactly one place per row
-- that can disagree with itself.
-- ============================================================

alter table employees add column organization_id uuid references organizations(organization_id);
alter table partners  add column organization_id uuid references organizations(organization_id);
alter table customers add column organization_id uuid references organizations(organization_id);
alter table materials add column organization_id uuid references organizations(organization_id);
alter table projects  add column organization_id uuid references organizations(organization_id);

update employees set organization_id = '00000000-0000-0000-0000-000000000001';
update partners  set organization_id = '00000000-0000-0000-0000-000000000001';
update customers set organization_id = '00000000-0000-0000-0000-000000000001';
update materials set organization_id = '00000000-0000-0000-0000-000000000001';
update projects  set organization_id = '00000000-0000-0000-0000-000000000001';

alter table employees alter column organization_id set not null;
alter table partners  alter column organization_id set not null;
alter table customers alter column organization_id set not null;
alter table materials alter column organization_id set not null;
alter table projects  alter column organization_id set not null;

-- Backfill-then-constrain, not a column default: a default would let a
-- future insert silently land on NRG's tenant if the app forgot to set
-- it. Every future insert must supply organization_id explicitly, from
-- the signed-in user's own session — there is no "silently inherit the
-- first customer" fallback by design.

create index on employees (organization_id);
create index on partners  (organization_id);
create index on customers (organization_id);
create index on materials (organization_id);
create index on projects  (organization_id);

-- materials.unique(category, canonical_name) (0002) has to become
-- per-organization — "DC Cable 4 sq mm" is a perfectly valid category
-- name for any solar EPC, not something unique to NRG; a second tenant
-- must be able to have their own row with that exact same name.
alter table materials drop constraint materials_category_canonical_name_key;
alter table materials add constraint materials_org_category_canonical_name_key
  unique (organization_id, category, canonical_name);

-- ============================================================
-- What this does NOT do (deliberately, per the owner's own framing —
-- "whatever needs to be done now, please add it now, most of the rest
-- we'll build later")
-- ============================================================
-- No RLS policies yet — real Row-Level Security enforcing "an
-- employee only ever sees their own organization's rows" is still
-- Next Session item 4, same open item flagged since Section 68. This
-- migration makes that policy possible to write correctly (the column
-- to check now exists everywhere it needs to); it does not write it.
-- No per-tenant branding/theming, no signup flow, no billing/Stripe
-- integration, no admin console for managing other organizations, no
-- per-tenant custom domain. None of that has a real second customer to
-- design against yet — building it now would be guessing.
