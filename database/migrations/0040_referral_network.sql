-- NRG SolarConnect — Referral Network (Trade-Contact Partner CRM)
-- Follows 0002-0039. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 83.
--
-- Source read for this migration: the full, current `referral_network.html`
-- (nrg-cover, 1164 lines, read completely) — a dedicated single-page CRM
-- for external referral partners (electrical consultants, MEP, architects,
-- PMCs, structural/civil, plumbing consultants, bath/ceramic shops,
-- builders) with three views (contact list, 30-day visit planner,
-- WhatsApp broadcast) and a business-card-scan-to-form AI fill feature.
-- Its backend (Apps Script Web App v4, its own SCRIPT_URL, distinct from
-- every other tool read this session) could not be located/opened via
-- Drive search — this migration was first written from the frontend's
-- full request/response contract alone. The owner then pasted the
-- complete backend source directly (same unblock as Havells Quotes,
-- Section 84), confirming every column below and one real discovery:
-- the live sheet has NO separate visit-log or WhatsApp-log storage at
-- all. logVisit()/logWA() both just string-concatenate a bracketed line
-- ("[Visit dd-MMM-yy - CY] note text", "[WA dd-MMM-yy - CY] template
-- name") onto the END of the single free-text Notes cell (column 13),
-- forever growing one blob per contact that mixes real hand-typed notes
-- with an auto-appended activity trail. `referral_visit_log`/
-- `referral_wa_log` below are a deliberate upgrade, not a faithful
-- reproduction — same "turn a text blob into real rows" fix already
-- applied to Sales Follow-up's touch counts (Section 79) and Prospect
-- List's two disconnected logs (Section 81). Importing history means
-- parsing each contact's live Notes cell for that bracket convention:
-- every `[Visit ...]`/`[WA ...]` line becomes one row in the matching
-- log table (date/by from the bracket, the rest as note/template_name);
-- whatever text is left over — the part a person actually typed — is
-- what should import into the new `notes` column, not the raw blob.
--
-- Also confirms a sixth live no-auth endpoint, same "Execute as Me /
-- Anyone" pattern as Quote Generator, Prospect List, and Client
-- Engagement — full partner PII (name, phone, email, address) readable
-- and, worse, WRITABLE by anyone with the URL, no token, no login. Adds
-- to the running list real RLS needs to close.
--
-- Real integration point already in hand from the Prospect CRM deep read
-- (0038): `syncSiteContactsToReferral_()` in Prospect List's
-- `ProjectScript.js` writes into this SAME spreadsheet automatically
-- whenever a project/hotel/hospital site contact (civil incharge, PMC,
-- architect, electrical/plumbing consultant, main contractor) is added,
-- deduped by stripped-digits mobile number. That is why this schema's
-- `contact_type` vocabulary lines up almost exactly with
-- `prospect_site_contacts.role` — they are two views onto the same real
-- population of trade contacts, one auto-fed, one hand-curated. The
-- `source_site_contact_id` column below makes that link real instead of
-- coincidental, without forcing every referral contact to have one (most
-- of the richer fields here — firm, product interest, temperature,
-- visit/WhatsApp history — only exist because a human enriched the
-- record; a raw auto-synced row has none of that yet).

-- ============================================================
-- Referral Contacts — no natural anchor-table FK (not a customer, not
-- an employee, not tied to one project), so it gets organization_id
-- directly, same reasoning as quote_kw_band_rates (0036/Section 79).
-- ============================================================

create table referral_contacts (
  contact_id              uuid primary key default gen_random_uuid(),
  organization_id         uuid not null references organizations(organization_id),
  name                    text not null,
  firm                    text,
  contact_type            text not null
                          check (contact_type in ('elec_consultant','mep','architect','pmc','structural','civil','plumbing_consultant','bath_shop','ceramic_shop','builder','other')),
  product_interest        text not null default 'solar' check (product_interest in ('solar','heat_pump','both')),
  phone                   text,   -- stored digits-only by convention, matching the live sync's own stripped-digits dedup key
  email                   text,
  area                    text,
  city                    text not null default 'Vadodara',
  address                 text,
  met_at                  text,   -- which project site this person was met on, if any — free text, same as the live field
  temperature             text not null default 'cold' check (temperature in ('hot','warm','cold')),
     -- real mutable CRM state, set at add/edit time and optionally
     -- overridden by a visit log entry — same category of field as
     -- customer_pipeline.temperature (Section 79), not something to
     -- derive by aggregation
  added_by                uuid references employees(employee_id),
  notes                   text,
  active                  boolean not null default true,   -- soft delete only; the live UI has no hard delete, only Deactivate/Activate
  source_site_contact_id  uuid references prospect_site_contacts(contact_id),
     -- set when this row originated from Prospect CRM's automatic
     -- syncSiteContactsToReferral_() rather than a manual Add Contact /
     -- business-card scan; null for everything hand-added
  created_at              timestamptz not null default now(),
  unique (organization_id, phone)
);

create index on referral_contacts (organization_id);
create index on referral_contacts (contact_type);
create index on referral_contacts (source_site_contact_id);

-- ============================================================
-- Visit log and WhatsApp log — kept as two small append-only logs
-- rather than one generic log table, because their shapes genuinely
-- differ (a visit carries a free-text note and an optional temperature
-- override; a WhatsApp send carries which template was used) and
-- neither needs the other's columns. last_visited_at / last_wa_sent_at
-- are deliberately NOT columns on referral_contacts — MAX() over these
-- two logs is trivial and always correct, so storing a duplicate
-- "last touched" timestamp on the contact row would be exactly the
-- kind of drift-prone denormalization this schema avoids everywhere
-- else (see referral_contact_status view below).
-- ============================================================

create table referral_visit_log (
  visit_id           uuid primary key default gen_random_uuid(),
  contact_id         uuid not null references referral_contacts(contact_id),
  note               text,
  temperature_after  text check (temperature_after in ('hot','warm','cold')),   -- null = visit logged with no temperature change, matching the live "No change" option
  visited_by         uuid references employees(employee_id),
  visited_at         timestamptz not null default now()
);

create index on referral_visit_log (contact_id);

create table referral_wa_log (
  wa_log_id      uuid primary key default gen_random_uuid(),
  contact_id     uuid not null references referral_contacts(contact_id),
  template_name  text not null,   -- e.g. 'Introduction / Stay in Touch', 'Referral Ask' — the template TEXT itself is UI copy, not schema, same call already made for Client Engagement (0039)
  sent_by        uuid references employees(employee_id),
  sent_at        timestamptz not null default now()
);

create index on referral_wa_log (contact_id);

-- ============================================================
-- Status view — visit_status mirrors the live UI's visitStatus()
-- function exactly (VISIT_INTERVAL_DAYS = 30, "due soon" = last 7 of
-- those 30 days, never-visited counts as overdue) so a tenant's
-- overdue-visit count can never silently drift from what the app shows.
-- ============================================================

create view referral_contact_status as
select
  c.contact_id,
  lv.last_visited_at,
  lw.last_wa_sent_at,
  case
    when lv.last_visited_at is null then 'overdue'
    when now() - lv.last_visited_at > interval '30 days' then 'overdue'
    when now() - lv.last_visited_at > interval '23 days' then 'due_soon'
    else 'ok'
  end as visit_status
from referral_contacts c
left join lateral (
  select max(visited_at) as last_visited_at
  from referral_visit_log v where v.contact_id = c.contact_id
) lv on true
left join lateral (
  select max(sent_at) as last_wa_sent_at
  from referral_wa_log w where w.contact_id = c.contact_id
) lw on true;

-- ============================================================
-- Entitlement — its own module_key. Functionally independent of
-- sales_quotes/sales_followup/havells_quotes (a tenant can run this
-- CRM with zero quoting modules enabled, and a pure-solar tenant with
-- no heat pump line simply never sets product_interest to
-- 'heat_pump'/'both' — the schema doesn't assume both product lines
-- exist), so it earns a real boundary rather than riding on an
-- existing key the way Client Engagement rode on 'service' (0039).
-- ============================================================

insert into module_entitlements (organization_id, module_key, tier) values
  ('00000000-0000-0000-0000-000000000001', 'referral_network', 'advanced');
