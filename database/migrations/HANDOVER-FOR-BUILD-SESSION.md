# ProjectPulse — Handover to Build Session

This replaces any earlier handover you were given. The design session has moved on a lot since then — grounded against ~30 real NRG documents and spreadsheets, not just the original vision doc.

## What ProjectPulse is (unchanged, frozen)

A **Project Intelligence Repository** for NRG Technologists (solar EPC): store every project document, extract structured data with AI, connect it across documents, and generate measurable intelligence — not a CRM/ERP/PM tool. Stack: Next.js frontend → Supabase (Postgres) → Google Drive (document storage) → OpenAI (extraction). Full detail, principles, and the reasoning behind every table: `docs/projectpulse-handover.md` in the `nrg-report-service` repo (send that file over too, or pull it if you have repo access).

## What to do right now

1. Run `database/migrations/0002_core_schema.sql` (this directory) against your Supabase project — it's the next migration after your existing `0001_init.sql`. It creates, in dependency order: `employees`, `partners`, `customers`, `materials`, `customer_contacts`, `projects`, `documents`, `project_external_references`, `drive_folder_import_candidates`, `boms`, `bom_items`, `material_transactions`, and the `bom_item_variance` view.
2. That's a complete, self-consistent core schema — it'll apply cleanly. But it is **not the whole system**: `financial_obligations`, `project_milestones`, `vendor_quotes`, and the full `document_type` taxonomy are still being designed in the other chat. Don't build UI/business logic against tables that don't exist yet.
3. `documents` was drafted just now to unblock the FK dependencies from `boms`/`material_transactions` — treat its shape (esp. `document_type` as free text) as provisional, it'll likely get refined.

## Key decisions worth knowing before you build on top of this

- **`bom_items.category` and `documents.document_type` are free text, not enums.** NRG's real category/document-type lists are long and still growing (see the handover doc's Sections 22-24) — don't hardcode a fixed set in the DB layer; keep it as an app-level reference list.
- **`material_transactions` is one shared ledger** for both BOM variance tracking (project-level) and inventory (warehouse-level) — `purchased` rows with `project_id null` are warehouse inflow; `issued_to_site`/`returned_to_warehouse` rows are project-level movement. Don't build a separate inventory table.
- **`Projects` is one table for both business lines** (residential-subsidy and commercial/industrial), distinguished by `project_type`, not two parallel schemas.
- **A project can have multiple external reference numbers** (`project_external_references`) — NRG's own internal ref, GEDA registration number, DISCOM consumer number, etc. Never assume one `reference_number` field is enough.
- **Google Drive folder linking**: `projects.google_drive_folder_id` is the durable link — never derive it from folder name (real folder names follow at least 5 inconsistent patterns). New projects should auto-create their Drive folder via a service account. NRG's ~300 existing project folders need a human-reviewed import (`drive_folder_import_candidates`) — there are confirmed duplicate folders for the same project across two existing Drive locations, so this can't be a blind automatic match.
- **Never store secrets in a plain column** — monitoring-portal credentials, API keys, etc. go through Supabase Vault or equivalent, not a `text` field on `projects`.
- **No historical material-transaction data exists to import.** NRG confirmed there's no separate dispatch/purchase log — the BOM workbook's single "Actual Qty Used"/"Actual Rate" columns per line are the only record. When backfilling a historical project, create **one synthetic `material_transactions` row per `bom_items` row** (`movement_type = 'issued_to_site'`, quantity/rate from those Actual columns), with `source_document_id` set to the **same document as `boms.source_document_id`** (not a separate Delivery Challan). That's the signal that distinguishes "backfilled aggregate" from real per-dispatch data later — no extra column needed. Don't leave historical rows with zero transactions; `bom_item_variance` would then show a false "0 used" instead of "not tracked at this granularity."

## Still pending in the design chat

Financial Obligations (multi-party reconciliation: NRG revenue vs. GEDA/DISCOM pass-through charges), Project_Milestones (multi-track: DISCOM feasibility, GEDA registration, CEIG inspection, physical site work — each with its own vocabulary), Vendor Quotes, BOM Recommendation Engine, Inventory reorder logic, Marketing module. Check back for updated migrations as those land.
