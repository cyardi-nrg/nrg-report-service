-- NRG SolarConnect — Client Engagement (Warranty Re-engagement Outreach)
-- Follows 0002-0038. Consolidated from docs/nrg-solarconnect-handover.md
-- Section 82.
--
-- Replaces the live "Client Engagement" Apps Script project — read in
-- full (both its files, ~230 lines total, no HTML — that lives
-- separately in nrg-cover's nrg_client_engagement.html). Turned out to
-- be the smallest live tool of the six read so far: a thin 3-endpoint
-- shim over the exact same spreadsheet Service Desk already owns
-- (`CUSTOMERS` read, `CE_LOG` read+append) — no warranty logic, no
-- template library, no time triggers, and confirmed zero outbound
-- calls of any kind (no `UrlFetchApp` anywhere in the source). Every
-- piece of real intelligence (warranty-expiry math, the seasonal
-- WhatsApp template picker, composing a report) lives entirely in the
-- front-end HTML, not this backend.
--
-- This also closes a real gap flagged in Section 80: Service Desk's
-- own deep read found `CE_LOG` referenced nowhere in Service Desk's 8
-- files, with live, recent entries, "suggesting an active parallel
-- process... not part of what was asked to be read" at the time. That
-- process is this one. `customer_engagement_log` below is its
-- replacement.

create table customer_engagement_log (
  engagement_id  uuid primary key default gen_random_uuid(),
  customer_id    uuid not null references customers(customer_id),
  channel        text not null check (channel in ('call','whatsapp')),
  template_used  text,   -- which seasonal/outreach message template was used, if any — free text, the template library itself is a UI/content concern, not schema
  logged_by      uuid references employees(employee_id),
  created_at     timestamptz not null default now()
);

create index on customer_engagement_log (customer_id);
create index on customer_engagement_log (created_at);

-- Deliberately not its own module_entitlements row separate from
-- 'service' — unlike Quote Generator/Sales Follow-up (Section 79),
-- which the live system deploys as two genuinely independent Apps
-- Script projects, Client Engagement's own backend confirmed it isn't
-- even data-isolated from Service Desk (it reads/writes the identical
-- spreadsheet, by its own admission only "code-isolated," a claim its
-- own header comment made and this read confirmed is misleading at
-- the data layer). Gating it under the existing 'service' entitlement
-- (0035) matches the real coupling rather than pretending a boundary
-- exists that the live system itself doesn't have.

-- ============================================================
-- Warranty-expiry math and the seasonal WhatsApp template picker are
-- NOT reproduced here — deliberately. The live tool recomputes
-- warranty client-side, in the browser, from raw customer data on
-- every page load; this schema already has a single, correct,
-- server-side answer for that question — project_warranty_status
-- (Section 80/0037) — which the UI for this module should simply
-- query instead of recreating the same three-implementation confusion
-- that migration already fixed once. The template library itself
-- (which message text goes with which season/reason) is presentation
-- content, not a schema concern — it can live as static UI copy or a
-- simple config table later if it needs to be admin-editable, neither
-- of which blocks building this module today.
-- ============================================================
