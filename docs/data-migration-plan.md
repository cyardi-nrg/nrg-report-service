# Google Sheets → SolarConnect Data Migration — Plan

Status: **planning only, per owner's instruction — not yet executed.**
Written 2026-08-21. Covers moving NRG's real, live operational data out of
the current Apps Script / Google Sheets system and into the SolarConnect
Supabase schema without creating duplicates, losing history, or silently
dropping business rules the sheets encode informally.

---

## 1. Governing principles (non-negotiable)

1. **Dry run before write, every time.** Every source sheet gets exported,
   mapped, and staged into a report the owner reviews *before* anything
   lands in a production table. No sheet goes straight to `insert`.
2. **No bypass path.** Imported data goes through the exact same
   business-rule gates a human using the app would hit — the material
   match/confirm queue (migration 0057), fuzzy customer matching, the
   real quote-numbering sequence, the two-stage BOM approval. A "bulk
   import mode" that skips these is exactly how the sheets got into their
   current state (duplicate materials, four disconnected client lists) —
   not repeating that.
3. **Additive, never destructive.** A row that already exists (matched by
   a natural key or a fuzzy match against already-seeded reference data)
   gets skipped or merged — via the schema's existing
   `merged_into_material_id` / `merged_into_project_id` /
   `merged_into_customer_id` audit-trail pattern — never duplicated.
4. **Every imported row is traceable.** Each import batch gets one
   synthetic `documents` row ("Legacy Import — <source> — <date>"), and
   every row it produces sets `source_document_id` to it — satisfying the
   schema's `source_document_id not null` rule everywhere it applies, and
   giving a real undo path (find everything from one bad import batch).
5. **Tally is the source of truth for money, not the sheets.** Where a
   sheet's financial figure disagrees with Tally, Tally wins — sheets get
   imported as historical record, not as the reconciled figure.
6. **Historical limitations get surfaced, not hidden.** Where the sheets
   genuinely don't have data a screen expects (e.g. no per-dispatch
   material log for old projects — see §5), the resulting UI shows an
   honest "not available for this project" rather than a fabricated zero.

---

## 2. What's already done (no action needed)

Panel/kW-band pricing, structure height rates, inverter rate bands, AMC
rate cards, and the Service Desk employee/complaint-type seed data are
**already migrated** (migrations 0048, 0051, 0053) — verified line-by-line
against real screenshots and confirmed live in Supabase. These don't need
re-work.

---

## 3. Real source inventory (from the actual Apps Script codebase, not guessed)

| Source | What it holds | Feeds |
|---|---|---|
| Quote Generator's own Sheet — **Quotes** tab | Every live solar quote, 55 real columns | `quotes`, `quote_extras` |
| Quote Generator's own Sheet — **Historical** tab | Older quotes, **different column layout than Quotes** (0=Date…10=kW, 16=Gross Cost, 17=Customer Payable, 19=Quote Ref, 22=Deal Status) | `quotes` (needs its own mapping, not reused from Quotes tab) |
| Quote Generator's own Sheet — **Clients** tab | Phone-keyed client record: latest quote date/ref/kW/cost, temperature, times quoted, follow-up status | `customers`, `customer_pipeline` (see open question, §4) |
| Quote Generator's own Sheet — **Leads** tab | Pre-quote pipeline, simple new→quoted status | `leads` |
| Quote Generator's own Sheet — **Payback Reports** tab | Date/Client/Phone/Email/kW/Cost/Monthly Savings/Payback Period/Report Type/Salesperson/Quote Ref/PDF Link | New `payback_reports` table (not yet built — see task #17) |
| Havells Quote Generator's Sheet | Heat pump quotes | `havells_quotes`, `havells_quote_line_items` |
| Service Desk / AMC shared Spreadsheet — **Customers** tab | Installed-customer record (a **fourth**, separate client list — see §4) | `customers`, `projects` |
| Service Desk / AMC shared Spreadsheet — tickets, AMC contracts/visits | Complaint history, AMC contract/visit log | `service_tickets`, `ticket_timeline`, `amc_contracts`, `amc_visits` |
| Sales Follow-up's own Clients + Activity Log | A **third**, independently-tracked client/activity system | `customer_pipeline`, `customer_activity_log` (see §4) |
| Prospect Intelligence sheets (companies/hotels/hospitals/builder projects) | Cold-outreach tracking | `prospect_companies`, `prospect_hotels`, `prospect_hospitals`, `prospect_builder_groups`, `prospect_builder_projects` |
| Referral Network sheet | Partner/consultant/PMC contacts | `referral_contacts`, `referral_visit_log` |
| GEDA Portal workbook — **GR**/**GI** tabs | Real milestone status per project, **residential and commercial/industrial tabs track genuinely different milestone vocabularies** | `project_milestones` (`geda_registration`, `discom_feasibility`, `ceig_inspection` tracks) |
| SPP Bill of Material sheets (one per project, "Engineering BOM") | Real per-project BOM line items, historically only a workbook-level Actual Qty/Rate — **no per-dispatch log** | `boms`, `bom_items` — see §5 for the real historical limitation |
| Panel Pricing / NDCR Panel Pricing tabs | **Already migrated** (0048) | — |
| Tally exports | Real accounting ledger | `tally_ledger_entries`, reconciliation against `financial_obligations` |
| Google Drive — ~300 project folders across two locations, with confirmed real duplicates | Project documents | `documents`, `projects.google_drive_folder_id` via `drive_folder_import_candidates` (table already exists, import queue not yet built) |

---

## 4. Open decision the owner needs to make before any customer/lead import runs

The real codebase confirmed **four separate, currently-unsynced
client/lead-tracking mechanisms**:

1. Quote Generator's own **Clients** tab (phone-keyed, quote-stage
   "temperature")
2. Quote Generator's own **Leads** tab (pre-quote pipeline)
3. Sales Follow-up's **own** Clients + Activity Log (call/follow-up
   activity — not written to by #1 or #2)
4. Service Desk/AMC's shared **Customers** tab (installed-customer
   record)

No code anywhere cross-writes between these four today. Before the
customer/lead import can run safely, this needs an explicit answer:

> **Does SolarConnect's single `customers`/`leads` table replace and
> unify all four, or do quote-stage temperature, follow-up activity, and
> installed-customer status genuinely need to stay separate concerns
> (mapped to separate SolarConnect tables/fields) even after migration?**

Guessing this wrong either silently merges genuinely distinct workflows,
or leaves the same real person as three or four different customer rows
— exactly the duplicate-inventory problem already solved for materials,
now for people. This is the single highest-leverage question to resolve
first.

---

## 5. Known, permanent historical limitation (surface, don't hide)

There is **no historical per-dispatch material-transaction log** — only
one workbook-level "Actual Qty/Rate" per BOM line, ever, for older
projects. That means historical (pre-SolarConnect) projects will
**permanently** only support Material/Cost *Variance* reporting, never
Excess/Short-Purchase or Unreturned-Material breakdowns, no matter how
carefully the import runs. The plan marks every such backfilled
`material_transactions` row by setting its `source_document_id` equal to
its `boms.source_document_id` (a real, already-designed convention) so
the UI can detect "this is a legacy aggregate" and show an honest
"detailed breakdown not available for this project" rather than a
fabricated zero.

---

## 6. Sequencing (dependency order)

1. **Reference/lookup data** — done (§2).
2. **Organizations / employees / partners** — mostly seeded already;
   reconcile against real staff roster and vendor list.
3. **Customers / leads** — blocked on the §4 decision. Once resolved:
   dedupe across all four sources by phone number (the one reliable
   natural key across all of them), using `customers.aliases` +
   fuzzy-match-before-create, same pattern as materials.
4. **Projects** — one row per real project; backfill `project_milestones`
   from the GEDA GR/GI workbook tabs where available (two different
   vocabularies per §3 — don't force one mapping onto both).
5. **Documents / Drive folders** — build the `drive_folder_import_candidates`
   review queue (table exists, UI doesn't yet) so the ~300 real folders
   with known duplicates get a human decision, not an automated guess.
6. **Materials / BOMs** — materials first (through the new match/confirm
   gate, §1 rule 2, so every SPP BOM's line items resolve against a
   canonical materials list instead of creating fresh duplicates per
   project); then BOMs/`bom_items`, `origin = 'uploaded_workbook'`.
7. **Material transactions (historical)** — one aggregate `purchased`
   transaction per BOM line at minimum, tagged per §5's legacy-marker
   convention; live/ongoing projects get the real per-dispatch log going
   forward through the app, not backfilled.
8. **Financial** — Tally export is the anchor; `financial_obligations`
   seeded from real Quote Cost Breakdown lines per project, then
   `sales_invoices`/`payment_receipts` reconciled against the Tally
   ledger (not the sheets) per §1 rule 5.
9. **Quotes / Service tickets / AMC / Prospect / Referral** — lowest
   schema risk (these modules are already fully built and tested this
   session); import last, since nothing else depends on them.

---

## 7. What execution will actually need from the owner (not now — when this is taken up)

- The §4 decision on client/lead unification.
- Either read access to each real Sheet/spreadsheet, or CSV exports of
  each tab named in §3.
- A recent Tally export (for financial reconciliation).
- Confirmation on quote numbering: continue the existing
  `NRG/{FY}/{TypeCode}/{seq}` sequence from its real current counter, or
  start SolarConnect's counter fresh and keep historical numbers as
  imported text only.
- A pass through the Drive folder duplicates (~300 folders, two
  locations) — likely a short human review session once the import
  queue UI exists.

None of this blocks tonight's work — it's what unblocks *execution*, once
the owner is ready to take this up.
