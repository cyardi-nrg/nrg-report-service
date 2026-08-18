-- NRG SolarConnect — Per-Employee Module Access (Not Fixed Teams), and
-- Closing the employees/auth Reconciliation Gap
-- Follows 0002-0044. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 88.
--
-- Two things the owner asked for directly, both real and both overdue:
--
-- 1. "The entire team's names, login IDs, and passwords, and what all
--    modules they have access to should be in a sheet where I can add
--    a module or remove a module... rather than have a set sales team
--    or a purchase team... sometimes for one particular person there
--    are two or three things which might overlap." Fixed team/role
--    buckets (Owner/Sales/Service/Purchase — Section 48's own
--    role-to-screen table) were always a UI/navigation convenience, not
--    a real access model, and the owner just said so directly: a real
--    person can need Sales + Service, or Purchase + a bit of Tasks, and
--    a five-bucket role list can't express that. This migration adds a
--    genuinely flexible mechanism instead — one row per (employee,
--    module) — with zero fixed categories.
--
-- 2. The "known architectural gap" flagged all the way back in Section
--    40 of the very first build brief — this session's auth/`profiles`
--    concept and `employees` were never reconciled — is what's actually
--    behind "some modules have no login check." `employees` has no link
--    to any real identity provider at all today, so there has never
--    been anything for a login gate to check. Closed here.
--
-- ============================================================
-- No password column, deliberately — this is not a partial answer to
-- "login IDs and passwords," it's the secure version of the same ask.
-- `auth_user_id` links to Supabase Auth's own `auth.users` (or an
-- equivalent identity provider) — password hashing, sessions, resets,
-- and MFA are that system's job, never a plaintext or even hashed
-- password column here. This is the exact rule already stated in 0002
-- ("Never store secrets in a plain column") applied to the one kind of
-- secret that matters most. `login_id` is the separate, human-facing
-- piece the owner actually needs for the "sheet" — a short staff code
-- (CY/RC/AP/... — the same codes already seen live across Tasks,
-- Referral Network, and Sales Follow-up) an admin can read and match
-- against a name, independent of whatever email/auth-provider identity
-- sits behind it.
-- ============================================================

alter table employees
  add column login_id text unique,
  add column auth_user_id uuid unique;

-- ============================================================
-- Admin capability — a real, immediate follow-up from the owner: an
-- "admin assistant" other than the owner needs to (1) review/edit every
-- WhatsApp template one by one, (2) control module access for everybody
-- else, and (3) see financial data — which the owner explicitly wants
-- restricted to "only me or the admin." This is also the first time
-- "Owner" itself gets a real, checkable flag rather than free-text role
-- matching — every prior Owner-only gate in this schema (cost/margin
-- visibility, Section 39/63/64; pipeline-project pricing, Section 68)
-- has only ever been described in prose as "Owner-only," never backed
-- by an actual column. is_owner closes that ambiguity at the same time
-- is_admin answers the new request; going forward both gates read as
-- `is_owner or is_admin`, one rule, checked consistently everywhere
-- instead of re-deciding "who counts as Owner" per screen.
--
-- Deliberately a flat boolean, not a third table — the owner described
-- one bundled admin capability (templates + access management +
-- financials together), not three separately grantable ones. If a real
-- need for finer separation shows up later (someone who edits templates
-- but shouldn't see margin, say), that's a genuine future refinement,
-- not something to guess at now.
-- ============================================================

alter table employees
  add column is_owner boolean not null default false,
  add column is_admin boolean not null default false;

-- Application/RLS rule this schema now makes checkable (not yet
-- enforced — same standing item as everywhere else this session):
--   • edit message_templates                    → is_owner or is_admin
--   • grant/revoke another employee's            → is_owner or is_admin
--     employee_module_access row
--   • cost/margin/pipeline-pricing visibility     → is_owner or is_admin
--     (Section 39/63/64/68 — was "Owner-only" in prose; now the same
--     rule, backed by a real column, extended to include Admin per the
--     owner's explicit instruction)

-- ============================================================
-- Module access — one row per (employee, module) they're allowed into.
-- A missing row means no access, same "absence is the off state"
-- convention as module_entitlements (Section 78) — deliberately the
-- same shape, one level down: module_entitlements is "does this TENANT
-- have Service at all," employee_module_access is "does THIS PERSON,
-- within a tenant that already has it, get to open it." No
-- organization_id column here — employee_id already anchors to
-- `employees`, one of the five true anchor tables (Section 78), so
-- tenant scoping is inherited transitively, same rule as every other
-- child table in this schema.
--
-- module_key reuses the exact module_entitlements vocabulary —
-- 'projects_inventory' | 'service' | 'sales_quotes' | 'sales_followup'
-- | 'prospect_crm' | 'bill_analyser' | 'referral_network' |
-- 'havells_quotes' | 'tasks' — free text, not a hard enum, same
-- reasoning as everywhere else this vocabulary is used. The app layer
-- should refuse to grant a module to an employee whose organization
-- doesn't itself have that module in module_entitlements — a real rule,
-- but a cross-table one that belongs in application logic (same
-- deliberate choice already made for the ₹25,000 approval threshold and
-- every other business rule in this schema that isn't a hard constraint).
-- ============================================================

create table employee_module_access (
  employee_id   uuid not null references employees(employee_id),
  module_key    text not null,
  granted_by    uuid references employees(employee_id),
  granted_at    timestamptz not null default now(),
  primary key (employee_id, module_key)
);

create index on employee_module_access (module_key);

-- `employees.role` (0002, free text — "Sales Person", "Electrical
-- Supervisor") is NOT replaced or removed by this table — it answers a
-- different question. role is what already drives the narrower,
-- already-decided field-level visibility rules elsewhere in this schema
-- (Owner-only cost/margin, Section 39; Owner/named Sales Head sees every
-- pipeline project, Section 68) — those stay exactly as designed.
-- employee_module_access answers the coarser, new question this section
-- is about: which of the ~9 module screens can this person even
-- navigate to. The two mechanisms are complementary, not competing —
-- don't collapse them into one.

-- ============================================================
-- What this migration does and does not close, stated plainly. It
-- makes real per-module login enforcement buildable — the identity link
-- and the access list both now exist, so a route guard or a real RLS
-- policy has something concrete to check (`auth_user_id` = the
-- requesting session, `employee_module_access` = what they're allowed
-- to see). It does NOT itself add that enforcement — the same honest
-- boundary already drawn for the multi-tenant foundation (Section 78):
-- schema first, policies second, still an open item (Next Session #44).
--
-- It also does NOT close the specific no-auth holes already confirmed
-- live this session (Quote Generator, elec_bill's /ocr-bill, Prospect
-- List, Client Engagement, Referral Network, Tasks) — those are running
-- on the OLD Apps Script stack, entirely outside this Postgres schema,
-- and stay open until either that code is patched directly or that
-- traffic is actually cut over onto the system this table belongs to.
-- What this migration guarantees is that the NEW system doesn't get
-- built the same way — every module here launches with a real place to
-- check "is this person logged in, and are they allowed into this
-- module," not the client-side-only theater found live in Service Desk
-- (Section 80) and everywhere else this was checked.
-- ============================================================
