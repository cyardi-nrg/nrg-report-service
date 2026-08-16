# NRG Sales/Service System — Full Understanding

**Date:** 2026-08-16. **Method:** every `.gs`/`.html` file in all five live Apps Script projects and every file in the four backend repos (`nrg-cover`, `nrg-pdf-server`, `elec_bill`, `nrg-report-services`) read in full — not sampled, not structurally skimmed. Two very large HTML files (`nrg_followup_dashboard.html`, `prospect_intelligence_v2.html`) were read directly for ~70% of their length with the remainder confirmed by an exhaustive grep of every function/backend-call, since both are highly repetitive card-rendering code past that point — this is disclosed, not hidden. Everything else was read top to bottom, confirmed against actual line counts. Full per-project reports live in the session scratchpad; this document is the synthesis.

**This document exists because the first-pass structural survey (earlier the same day) undercounted real data by 4.2x and missed entire tabs.** Reading actual source code, not sampled exports, is what closes that gap. Treat this as the trustworthy baseline going forward.

---

## 1. What this system actually is, in one picture

Nine independently-deployed Google Apps Script backends (each Sheets-as-database) are fronted by one shared login portal — `nrg-cover`, a Node/Express app on Railway — which mints a signed HMAC token and hands each person off to whichever module their role permits. Three separate stateless Python microservices generate PDFs on request; **none of the three ever touches Google Drive or a database** — every one returns `{pdf_base64, filename}` over HTTP and it's Apps Script, on the other end, that decodes the bytes and does the actual `DriveApp` save. This is a consistent pattern across all three, confirmed by reading every line of all three services — worth knowing precisely because it means **PDF generation and PDF persistence are two separable concerns**, which matters for how a migration could be staged.

The five Apps Script projects break into two real business domains:

- **Sales**: Quote Generator + Sales Follow-up (share one live spreadsheet — the tightest coupling in the whole system) generate and track quotes; Prospect List does cold outreach; Solar Bill Analyser is a standalone lead-gen tool.
- **Service**: Service Desk handles tickets and AMC contracts — the largest, most complex, most business-critical piece.

`nrg-cover` itself hosts or routes to **sixteen HTML tools** beyond the five GAS projects — some are pure client-side calculators with no backend at all (EMI/FD comparisons, system sizing), most are thin single-page apps that treat a dedicated GAS `/exec` deployment as their entire backend. **Nine distinct GAS deployment URLs are hardcoded across `nrg-cover`'s files** — more than the five projects reviewed as primary targets, meaning the real footprint of "things that would need to migrate" is bigger than the five named projects alone.

---

## 2. Each business process, understood end to end

**Service ticketing** (Service Desk): a complaint becomes a ticket via a static complaint-type→engineer lookup table (no workload awareness), moves through a status lifecycle, and is closed out with a mandatory photo + notes. WhatsApp notifications are deep-links a staff member must tap — nothing sends itself. A "Commissioning Readings" form in the UI looks live but **silently discards everything typed into it** — it never calls the server at all.

**AMC (Annual Maintenance Contracts)**: quote → convert-to-active → visit logging → a renewal reminder that, despite having a daily trigger and a UI badge, **only writes to an execution log — no customer or staff notification is ever actually sent.** Renewal follow-up today is 100% a human remembering to check a filter in the UI.

**Quote generation**: fully dynamic pricing read live from two spreadsheet tabs (add a panel brand or wattage band with zero code change), business-card OCR that proxies through `nrg-cover`'s `/ocr` to avoid ever putting an Anthropic key in Apps Script, and a PDF pipeline with a genuine fallback — if the Railway PDF service is down, an entirely separate ~600-line inline HTML-to-PDF generator kicks in automatically. Good resilience, but it means **two independently-maintained PDF templates must be kept visually in sync by hand.**

**Sales follow-up**: a JSON API (no bundled UI of its own — the actual dashboard reviewed here is `nrg-cover`'s `nrg_followup_dashboard.html`) with a genuinely-enforced, server-side CEO-only override for special discounts — the one place in the entire sales stack where a role check actually can't be bypassed by editing client-side JavaScript.

**Cold-outreach prospecting** (Prospect List): the code implements an elaborate 8-month drip-sequence engine with dedup, batching, and stage progression — but **the live data shows this machinery is essentially dormant.** 3,690 companies, 99.6% bulk-imported; only 15 ever went through the real sequencing flow; all 180 scheduled touch-steps are permanently stuck "Pending" because nothing ever marks them sent. What's actually driving the past week of real activity (507 logged touches, 5 salespeople) is a newer, simpler activity log that isn't connected to any of that automation. The RERA/MCA "scrapers" are confirmed pure stubs — they log a message and do nothing else, despite having real trigger schedules that make them look active.

**Solar Bill Analyser**: the cleanest, most self-contained tool in the whole system — genuinely does what it appears to do, with no dead code or dormant automation found.

---

## 3. What must be fixed before — or regardless of — any migration

Ranked by how much damage each one could do if left alone:

1. **Quote Generator has no authentication at all.** `ANYONE_ANONYMOUS`, no token check anywhere. Anyone with the URL (visible in page source) can read every client's name/phone/email/address, submit a quote with an arbitrary discount (the ₹4,000/kW cap is client-side JavaScript only), or trigger a real Gmail send from the company account with attacker-controlled content.
2. **`elec_bill`'s `/ocr-bill` is an unauthenticated free proxy to a paid Anthropic API call.** Anyone who finds the URL can burn NRG's Anthropic spend indefinitely — no rate limit, no size cap, no auth.
3. **A live function-name collision in Service Desk**: `getPdfServerUrl()` is defined twice, in two different files, with conflicting return values. Apps Script silently lets the later-loaded definition win for every caller. This should be verified against the actual live deployment, not just source — it's possible AMC PDF generation is already hitting a malformed URL today.
4. **The single most dangerous data-corruption risk in the sales stack**: Sales Follow-up's CEO-discount/PDF-regeneration code reads Quote Generator's spreadsheet by **hardcoded column position** (`row[54]`, `row[46]`, etc.) rather than by header name — the only place in an otherwise careful codebase that does this. Add, remove, or reorder one column in Quote Generator's `HEADERS` array and this feature starts silently reading/writing the wrong cells, with no error.
5. **Permission checks in Service Desk are almost entirely client-side theater.** Functions commented `// Admin only: CY, KP, RV` contain **no such check in their actual body** — any caller with a valid-looking token can invoke them directly, regardless of role.
6. **`nrg-cover`'s pending-login-approval state is pure in-memory** and is lost on every redeploy. Not catastrophic (affected users just retry), but worth knowing before treating this system as more durable than it is.
7. **Business constants — salesperson rosters, the bank account number, brand colors — are duplicated 3 to 8 times each across different files and are already out of sync** (a Havells salesperson exists nowhere else; three services each independently define slightly different brand color hex values). Every one of these is a place where "the real value" depends on which file you happened to read.

None of these seven are migration-caused. They're true right now, today, independent of anything discussed in this session. Worth deciding with the sales/service team which get fixed immediately versus folded into the migration itself.

---

## 4. What looks automated but isn't (the "dormant vs. real" list)

- Prospect List's entire sequence/batch/stage-progression engine (§2).
- AMC renewal reminders (writes to a log only, notifies nobody).
- RERA/MCA scrapers (pure stubs).
- `nrg-report-services`'s own README claims "no quote search" and "no Drive persistence" — **both are false**; the code for both exists and works. The README is stale, not the system.
- The Commissioning Readings form in Service Desk's ticket UI (collects data, saves nothing).

---

## 5. Corrected scale of the data itself

From the earlier same-day audit correction: **1,853 distinct Drive document links**, not 446 — Quote Gen/Sales Follow-up alone has 1,397 (including a Clients tab with 121 links that the first pass never even opened), AMC/Service Desk has 456. Existence/permission re-verification against this corrected population is still pending — tracked in `docs/sales-service-migration-plan.md`.

---

## 6. What this means for the migration plan

- **PDF generation and PDF persistence are separable** — the three Python services could migrate independently of the Apps Script layer that currently uploads their output to Drive, since they already don't touch Drive themselves.
- **Quote Generator + Sales Follow-up's coupling is worse than "shared spreadsheet"** — it's shared spreadsheet *plus* one side reading the other's columns by raw position. Migrating this pair needs the column-index fragility fixed as part of the move, not carried forward as-is.
- **A migration that "just re-implements the code" would be wrong in at least two places** — Prospect List's dormant automation and the AMC renewal reminder both look like real requirements from the code alone, but the real requirement (confirmed from actual usage) is much simpler. Building to the code, not the usage, would over-build both.
- **Security must not be carried forward as-is.** Today's system works only because the URLs aren't published, not because access is actually controlled. A migrated system that keeps "obscurity" as its only defense would be reproducing a known gap on purpose.

This document, together with `docs/sales-service-migration-plan.md` and `docs/document-link-baseline-audit-2026-08-16.md`, is the complete picture as understood today.
