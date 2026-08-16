# Sales/Service Migration Plan — GAS + Sheets → NRG SolarConnect

**Status:** Draft — architecture confirmed against real code/data, baseline audit in progress.
**Scope:** This document covers migrating NRG's live Sales/Service tools (Apps Script + Google Sheets + three Railway microservices) onto the same Postgres foundation as `docs/nrg-solarconnect-handover.md`. It does not re-cover that document's own schema decisions — see that file for Projects/Inventory/BOM. This one is specifically about *how the already-live Sales/Service system gets moved without breaking it*.

---

## 1. What's actually live today (confirmed by reading the real code and real data, not assumed)

Five Apps Script projects, each bound to Google Sheets as its real database, all reached through one shared front door:

| Tool | Real size | What it does | Shares live data with | Risk to move |
|---|---|---|---|---|
| **Service Desk** | ~5,000 lines, 2 UIs (ticketing + AMC dashboard) | Service tickets, engineer assignment, AMC (Annual Maintenance Contract) quotes/renewals, daily digest + renewal-check triggers, WhatsApp notifications | Reaches into 2 external customer-record spreadsheets (national portal, GEDA); shares a client-master spreadsheet with Quote Generator | **Highest** — most complex, most daily-active, most named staff |
| **Quote Generator** | ~1,800 lines, 15 shipped versions | Sales quote builder, business-card OCR, PDF proposal generation, email/WhatsApp send | **Same live spreadsheet + Drive folder as Sales Follow-up** | **High — coupled** |
| **Sales Follow-up** | ~1,200 lines | JSON API behind a follow-up dashboard: call/WhatsApp/visit logging, deal stage, CEO-only special-discount override | **Same live spreadsheet + Drive folder as Quote Generator** | **High — coupled** |
| **Prospect List** | ~2,500 lines | Cold-outreach CRM, daily sequence-engine trigger, RERA/MCA scraper (currently stubs, not real automation yet) | Self-contained spreadsheet | Low — cleanest first mover |
| **Solar Bill Analyser** | Smallest, explicitly documented as standalone | Bill OCR → savings/payback PDF for lead generation | Self-contained | Lowest — safest first mover |

Plus the infrastructure around them:
- **`nrg-cover`** (Node/Express, Railway) — the real login/home screen for the whole team. WhatsApp-based device approval (no OTP cost), a locked per-role permissions matrix (`CEO`/`Sales`/`Service`/`Office Sales`/`Office Backend`/`Purchase`, view+edit at `none`/`own`/`all`), 10 named staff accounts. Every module is a pill on this home screen routing to a URL — some served by `nrg-cover` itself, some by Apps Script `/exec` web apps.
- **Three Python microservices on Railway** — `nrg-pdf-server` (quote/service/AMC/Havells PDFs), `elec_bill` (solar bill analysis PDFs), `nrg-report-services` (payback/project report PDFs). Called via `UrlFetchApp` from Apps Script (with an HTML-based fallback if the Python service is down — already-existing resilience worth keeping) or directly from `nrg-cover`'s pages.
- **Auth**: every Apps Script web app is deployed `ANYONE_ANONYMOUS` — publicly reachable, gated entirely by an HMAC-signed token (`APP_SECRET` shared secret) that `nrg-cover` mints and appends as `?t=...`. This is a real, working SSO bridge — and also the thing that should eventually be replaced by real RLS-backed auth (already an open item on the SolarConnect side, Next Session item 4).

**The one hard coupling to respect:** Quote Generator and Sales Follow-up read/write the exact same spreadsheet and the exact same Drive folder. They move together, or not at all — splitting them mid-transition means one side's writes silently stop showing up in the other's view.

---

## 2. The commitments driving every decision below

Stated directly by the owner, and non-negotiable for how this plan is built:

1. **No goof-ups.** A salesperson who gave a quote must always be able to find that quote and its PDF link. A client-facing link that worked yesterday must work after migration.
2. **Historical data must transfer without loss or mismatch** — not just "the file still opens," but the actual data (which client, which amount, which date, which proposal) has to land correctly, not just intact-but-shuffled.
3. **Keep the UI.** People are used to this. No retraining, no new login, no new bookmark.
4. **No big-bang cutover.** Everything currently works; nothing forces a deadline. Migrate at the pace that proves itself safe, not a calendar date.

---

## 3. Why #1 is achievable — verified directly, not assumed

Pulled three real quote PDFs from live production data (June–July 2026) and checked them against live Google Drive: all three still open, still contain the correct content, still live in the same folder, still shared exactly as issued (`role: reader, type: anyone`). There are 255 of these links in the Quotes tab alone.

The reason this is safe by construction: a link like `drive.google.com/uc?export=download&id=<fileId>` is addressed by a **permanent Google Drive file ID** — it has nothing to do with the Google Sheet or the Apps Script code that generated it. Migrating the *data* (Sheets → Postgres) never has to touch Drive. The rule that keeps this true through the whole migration:

- **Never** delete, move, re-share, or regenerate an existing PDF as part of migration.
- **Copy link text programmatically**, from the raw cell value, never retyped or rebuilt from a template.
- **Verify, don't assume** — every migrated link gets checked against live Drive before that row is considered "migrated," not just copied and trusted.

## 4. Why #2 needs a *second*, different kind of check

A link resolving proves the *file* survived. It says nothing about whether the *data* is right — whether a migrated quote is still attached to the correct client, whether an amount got dropped or duplicated, whether two similarly-named clients' historical proposals got cross-attributed. Two separate verification passes, not one:

- **Link-resolution audit** (Section 5) — does every stored document link still open, and is it still shared correctly.
- **Field-level reconciliation** — for every migrated row, does the new record's client name, amount, date, and proposal content match the source row exactly. This is a diff, row by row, against the original Sheet — not a sample, not a spot-check for anything client-facing (money, contracts, historical proposals). Built the same way as every other AI-extraction step in SolarConnect's own design: machine does the comparison, a human confirms discrepancies, nothing gets silently accepted.

## 5. Baseline audit — complete

Full report: `docs/document-link-baseline-audit-2026-08-16.md`. 100% read-only — nothing moved, renamed, re-shared, or deleted. 446 distinct document links found across the two live spreadsheets, cross-checked against two Drive folders (1,057 + 46 files, fully enumerated).

**Most urgent finding — not a migration risk, a *live* one:** 5 quote links are already broken today, all recent (June–August 2026), all on active or won deals — including **Dr. Sanket Saraiya, marked "won,"** whose proposal link has been dead since at least this audit. This has nothing to do with migration; it's happening right now under the current system. Recommend the sales team check these 5 before anything else:

| Client | Quote date/ref | Deal status |
|---|---|---|
| Chaitanya Yardi | 6/17/2026, NRG/26-27/RES/019 | active |
| Dr. Sanket Saraiya | 6/30/2026, NRG/26-27/NDC/006 | **won** |
| Jaydutt Shah | 7/2/2026, NRG/26-27/NDC/008 | active |
| Sandip Mistry | 7/13/2026, NRG/26-27/NDC/012 | active |
| Krishna Hospital & ICU | 8/4/2026, NRG/26-27/NDC/049 | active |

**Second finding — systemic, not random:** every 2020–2021 "Historical" (bulk-imported legacy) quote sampled — 13 of 13 — has **no public sharing** at all, unlike every 2022+ quote sampled (which all have `anyone: reader`, the correct client-facing setting). There's a sharp before/after boundary, not a scattered pattern, so this is treated as very likely affecting all 93 Historical-tab links, though only 13 were directly confirmed. Practical meaning: if a client received one of these ~2020-2021 links back then, clicking it today already shows a Google "you need permission" screen — again, a pre-existing gap, not something migration would cause, but exactly the failure mode the migration plan exists to prevent going forward.

**Everything else checked came back clean:** all 1,057 files in the Quote Generator's output folder resolve and 7 sampled across its 2022–2026 span all have correct public sharing; all 46 Solar Bill Analyser reports (its entire lifetime output — the tool is 8 days old) check out; Prospect List's CRM was read in full and stores no Drive document links at all (only Maps links) — nothing to audit there.

**Coverage is honest, not padded:** Source 1 (Quote Gen/Sales Follow-up) got 100% existence checking. Source 2 (AMC/Service Desk — confirmed to be the same spreadsheet, "NRG Service Desk," used by both) only got ~21% (40 of 191 links) directly checked — no failures found in that slice, but 79% remains unverified, and a failure rate similar to Source 1's ~4% could exist undetected there. The full report names every gap explicitly rather than implying more coverage than was actually done.

## 6. Phased approach

| Phase | What happens | What's still true |
|---|---|---|
| **0** | Nothing live touched. Sheets/Drive/Apps Script keep running exactly as today. | Full production system, unchanged. |
| **1** | Build the Postgres-backed replacement for one module, against a *copy* of real data. | Old system is still the only one anyone uses. |
| **2** | Field-level reconciliation + link audit on the copy — every migrated row diffed against source. | New module isn't live yet; this is where mistakes get caught for free. |
| **3** | Shadow/pilot run — new module live for one person or one non-critical case, old module still system of record for everyone else. | Both systems running; old one still authoritative. |
| **4** | Cut over person by person via the existing `nrg-cover` pill/routing (Section 7) — never an all-at-once flip. | Old Sheets/Apps Script frozen as a read-only archive, never deleted. |

**Order:** Solar Bill Analyser and Prospect List first (self-contained, lowest blast radius, prove the pattern). Quote Generator + Sales Follow-up move together, later, once the pattern is proven. Service Desk last — most complex, most business-critical, most people depend on it daily.

## 7. Navigation — no new front door

See `docs/nrg-solarconnect-handover.md` Section 77: NRG SolarConnect becomes a "Projects" pill on `nrg-cover`'s existing home screen, gated by the same role matrix every other module already uses there. As each Sales/Service module migrates, its pill's `MODULE_URLS` entry in `nrg-cover` points at the new Next.js route instead of the old GAS `/exec` URL — one config-line change per module, per person if needed during a shadow phase, invisible to anyone not yet cut over. `nrg-cover` itself is live production infrastructure — this file gets proposed as an exact diff when a module is actually ready, never edited live speculatively.

---

## Open questions for next session

1. **Immediate, not migration-related:** confirm the 5 broken quote links (Section 5) with the sales team — especially Dr. Sanket Saraiya's "won" deal — and decide whether to re-fix sharing on the ~93 Historical-tab (2020–2021) quotes now, independent of any migration timeline.
2. Finish the AMC/Service Desk link audit to full coverage (currently ~21%) before that module's own migration phase starts — it's the highest-risk module, so its baseline should be the most complete, not the least.
3. Which module goes first — Solar Bill Analyser or Prospect List (both are safe first movers; pick based on which the team would notice/benefit from soonest).
4. Real RLS-backed auth vs. carrying forward the shared-secret HMAC token scheme, at least for the transition period.
5. Whether Service Desk's two external customer-record spreadsheet reads (national portal, GEDA sync) need their own migration path or can keep reading from Sheets indefinitely even after Service Desk itself moves.
