# NRG SolarConnect → Sellable Modules: Productization Plan

> **Version:** v1.0 · **Date:** 2026-11-08 · **Status:** Draft for owner review. No code changed.
> **Based on:** a read of the live app repo `cyardi-nrg/nrg-solar-connect-app` (568 files, migrations up to 0173) plus this repo's handover docs. Every number below comes from that code, not from estimates.

---

## 1. The idea in one paragraph

Today SolarConnect is one app running one company (NRG). The goal is to sell it to other solar EPCs and installers as **modules they can pick from**: Sales, Service, Projects, Purchase/Inventory, Finance, plus a few add-ons. The good news: the database was designed for this from migration 0035 onward (`organizations`, `module_entitlements`), and the app already has per-person module access. The bad news: **nothing stops one company's logged-in users from seeing another company's data yet**, and NRG's name, people, bank formats and Gujarat-specific rules are written straight into the code in many places. This plan covers how to close those gaps without disturbing NRG's live use.

---

## 2. What already exists (the foundation is real)

| Piece | Where | State |
|---|---|---|
| `organizations` table, NRG = org #1 | migration 0035 | ✅ Exists |
| `organization_id` on the 5 "anchor" tables (employees, partners, customers, materials, projects) | 0035 | ✅ Exists |
| `module_entitlements` (which modules a *company* has bought) | 0035 | ⚠️ Table exists, but **the app never reads it** (0 references in code) |
| `employee_module_access` (which modules a *person* can open) | 0045, `lib/module-access.ts`, `middleware.ts` | ✅ Working, enforced in middleware |
| `company_profile` (name, address, GSTIN, bank, phones) | 0065 | ✅ Exists, but many files still hardcode NRG text instead of reading it |
| Route → module map (`MODULE_PATH_MAP`) | `lib/module-access.ts` | ✅ Clean, a good basis for packaging |
| Row-Level Security | 0074 and later | ⚠️ Turned on, but every policy is `to authenticated using (true)`: any logged-in user can read every row |

---

## 3. The real blockers, ranked by how badly they'd hurt

### Blocker 1: Data isolation (must be fixed before any second company's data goes into a shared database)
- **Every RLS policy allows every logged-in user to read and write everything.** 0074 did this on purpose as a safe overnight fix, and about 20 later migrations copied the same pattern (`directory_contacts`, `service_inverters`, `tally_sync_queue`, `attendance`, `design_lab`, …). If Company B's salesperson logs in, the database will happily hand over NRG's customers, margins and bank transactions.
- **Some tables have no route to a company at all.** Examples: `document_number_sequences` (two companies would share invoice/DC numbering), `bank_statement_transactions`, `inverter_serials`, `customer_import_candidates`. Others only reach a company through a *nullable* link (e.g. `project_costs` "general" rows with no project, `prospect_*` through `created_by`).
- One leak of one company's customer list or margins to a competitor would end the product. This is the single most important item.

### Blocker 2: Company-level module switch isn't enforced
`module_entitlements` is never read. Middleware only checks the *person's* access. So "Company B bought only Service" can't be enforced today. Nav (`lib/nav-groups.ts`), middleware and the Admin → Access screen all need to respect the company switch first, then the person switch.

### Blocker 3: NRG is hardcoded into the code
| Hardcode | Files |
|---|---|
| `NRG_ORGANIZATION_ID` constant, used for inserts | 33 |
| "NRG Technologists" / "nrgtechnologists" text | 49 / 6 |
| "Vadodara" | 13 |
| Named staff (Rutvi / Jatin / Mahesh), incl. `lib/rutvi-report.ts`, `lib/sales-backend-people.ts` | 14 |
| Telegram chat IDs, one Google Drive root folder, Tally secret (all in **environment variables**, so one value per deployment) | ~30 files read these |

### Blocker 4: Gujarat / India-specific logic
| Thing | Files | Comment |
|---|---|---|
| GEDA / DISCOM (MGVCL etc.) / subsidy | 64 (20 in Projects) | **A selling point** for Gujarat EPCs, a blocker elsewhere |
| Tally integration | 43 | Most Indian SMEs use Tally, so this is a feature. Make it optional. |
| IDFC bulk-payment format | 13 | NRG's own bank. Needs a "bank format" setting. |
| Havells quotes | 28 | NRG's dealership. **Don't sell as is.** Either keep it NRG-only or turn it into a generic "Product Quotes" module. |

### Blocker 5: Two migration folders that disagree
This repo (`nrg-report-service`) has migrations only up to **0082**. The app repo has them up to **0173**. Before anything is packaged, one place has to be the single source of truth for the schema, and that should be the app repo. The copy here should be marked as historical.

---

## 4. Proposed module packaging (from what each screen actually touches)

I mapped which database tables every screen reads and writes. That map shows a shared **core** that every module needs, and modules that sit on top of it.

### Core (always included, not sold separately)
Company profile, People, Access, Devices, Message templates, Document numbering, Documents/Drive, **Customers + Contacts**, and a thin **Sites/Installations** record (today's `projects` row).
> Why `projects` is core: Service (warranty status, inverters, commissioning), Follow-up (won deals), Social, Design Lab and Dispatch all read `projects`. A company that buys only Service still needs a list of "systems we installed". So the *record* is core; the *execution features* (BOM, dispatch, milestones) are the paid Projects module.

### Sellable modules

| Module | Screens (today's routes) | Region coupling | Sell-readiness |
|---|---|---|---|
| **Service** | `/service`, `/amc`, `/engagement`, inverters, help | Low (GEDA in 2 of 32 files) | 🟢 **Best first product.** Every EPC has an installed base, AMC is recurring revenue, the logic is universal. |
| **Sales** | `/quotes`, `/followup`, `/leads`, `/payback`, `/reference-finder`, `/rates` | Medium (subsidy/DISCOM in quotes) | 🟢 Strong second. Pricing is already table-driven (`quote_*_rates`). Needs NRG text removed from the quote PDF. |
| **Lead-gen add-ons** | `/prospect`, `/referral`, `/bill-analyser` | Low | 🟡 Cheap add-ons for the Sales pack |
| **Projects** | `/projects` (BOM, dispatch, commissioning, testing letters), `/design-lab`, reports | **High** (GEDA/CEIG milestone tracks in 20 of 44 files) | 🟡 Sell to Gujarat EPCs first; make milestone tracks configurable for other states |
| **Purchase & Inventory** | `/stock`, `/materials`, `/purchase`, `/procurement`, `/vendors` | Low | 🟢 Fairly universal; depends on Projects for BOM-driven requirement, so **degrade gracefully** without it (manual requirement) |
| **Finance** | `/finance` (Tally, bank & GST recon), `/payments` (salary, TDS, payment advice) | High (Tally, IDFC, TDS) | 🔴 Last. Most sensitive data, most India- and NRG-specific. Sell to Tally users only. |
| **Team add-ons** | `/tasks`, `/attendance`, `/social` | Low | 🟡 Small add-ons |
| **Not for sale (NRG only)** | `/havells`, Rutvi/Sales-backend reports | n/a | Keep behind an NRG-only switch |

### Places where modules reach into each other (each needs an "if the other module is off" fallback)
- Follow-up → reads `projects`, `financial_obligations` (Finance)
- Service → reads `commissioning_reports` (Projects)
- Dispatch → reads `service_tickets` (Service)
- Procurement → reads `boms` (Projects)
- Social → reads `boms`, `projects`
- Design Lab → reads `quotes`, `leads` (Sales)

---

## 5. The big decision: one shared system, or a separate copy per customer?

| | **A. Separate copy per customer** (own Supabase project + own deployment) | **B. One shared multi-tenant system** |
|---|---|---|
| Risk of leaking data between companies | **Close to zero.** Separate databases. | Depends entirely on RLS being perfect across ~150 tables |
| Work before the first sale | Small: remove hardcodes, enforce module switch | Large: rewrite every RLS policy and test it |
| Cost per customer | Higher: one more paid Supabase project and deployment per customer (check current Supabase pricing) | Lower |
| Updates | Deploy to N copies (scriptable) | Deploy once |
| Fits env-var config (Drive, Telegram) | Yes, as it works today | No, needs per-company settings tables |

**Recommendation: start with A for the first 1–5 customers, design everything so B is possible later.**
Reasoning: it gets you selling months earlier, makes a data leak between companies almost impossible, and every fix needed for A (removing NRG hardcodes, enforcing the module switch, a settings table) is also needed for B. Nothing is wasted. Move to B only when the number of copies is genuinely painful to maintain (roughly 5–10 customers).

---

## 6. Phased roadmap

Each phase leaves NRG's live system working. Nothing is a big-bang switch.

### Phase 0: Decide and validate (about 2 weeks, no code)
1. Talk to 3–5 friendly EPCs (ideally Gujarat, where GEDA/DISCOM logic is an advantage). Ask what they use today and what they'd pay for Service only, or Sales only.
2. Settle the decisions in §8 below.
3. Legal basics: who owns the code (NRG Technologists, or a new entity?), a customer agreement, data-ownership and privacy terms.
4. Product name and brand: "SolarConnect" without "NRG"? White-label with the customer's own logo?

### Phase 1: "De-NRG" the code (also good for NRG, low risk)
1. Make the app repo the single schema source; mark this repo's `database/migrations` as historical.
2. Replace the `NRG_ORGANIZATION_ID` constant (33 files) with "the signed-in person's organization" read from their `employees` row.
3. Add an `organization_settings` table for what's in env vars today: Drive root folder, Telegram chats, Tally on/off, bank payment format, region (state / DISCOM list).
4. Replace hardcoded "NRG Technologists" / Vadodara text (49 files) with `company_profile` reads. Most PDF/letterhead code already has `lib/company-profile.ts` to use.
5. Replace named-staff logic (Rutvi/Jatin/Mahesh, 14 files) with role or permission flags.
6. **Enforce `module_entitlements`** in middleware, nav and Admin → Access: company switch first, then person switch.
7. Add "module off" fallbacks for the cross-module reads listed in §4.

**Test for Phase 1:** NRG notices nothing. A blank second organization in a test copy shows no NRG name anywhere.

### Phase 2: First pilot customer (Option A: separate copy)
1. A scripted "new customer" setup: create the Supabase project, run migrations, seed the company profile and first admin, enable the purchased modules.
2. Onboarding import: customers, installed sites, AMC contracts from their Excel files (extend the existing `/admin/data-migration`).
3. Pilot with **Service only**, free or at a discount for about 2 months, in exchange for feedback.
4. Write down every place their process differs from NRG's. That list is the real product backlog.

### Phase 3: Real isolation (needed before Option B, and good practice even for A)
1. Add `organization_id` to every table that has no reliable route to a company (§3, Blocker 1).
2. Write real RLS: `organization_id = the signed-in user's organization` on every table.
3. Per-company document numbering.
4. An automated test that signs in as Company B and confirms it can read **zero** of Company A's rows, on every table. Run it on every migration.

### Phase 4: Commercial machinery (only once there are paying customers)
Billing and invoicing, self-serve trial signup, a support channel, per-customer backups, usage monitoring.

---

## 7. Pricing: hypotheses to test, not decisions

These are starting points to try out in Phase 0 conversations. They are **not researched figures.**
- Price per module per month, with a bundle discount (for example Sales + Service + Projects).
- Core plus a set number of users included; extra users charged.
- A one-time onboarding fee covering the data import and setup.
- Service is easy to justify on value: it protects AMC renewals, which are recurring revenue the customer is losing today.

---

## 8. Decisions needed from the owner

1. **Deployment model:** start with a separate copy per customer (recommended), or go straight to one shared system?
2. **First module to sell:** Service (recommended), or Sales?
3. **First market:** Gujarat EPCs only (GEDA/DISCOM is an advantage), or national from the start?
4. **Brand:** sell as "SolarConnect", white-label, or a new name?
5. **Ownership:** sell from NRG Technologists, or set up a separate company or product line?
6. **Havells:** keep NRG-only, or generalize into a "Product Quotes" module?
7. **Who builds and supports it:** after a sale, who answers the customer's calls?

---

## 9. Suggested immediate next step

Once §8 is answered, the first build task is **Phase 1, step 6: enforce `module_entitlements`**. It's small, it's invisible to NRG (NRG already has every module), and it's what makes "sell just one module" actually work. Per the working agreement, the current versions of `middleware.ts`, `lib/module-access.ts`, `lib/nav-groups.ts`, `app/(app)/layout.tsx` and `app/(app)/admin/access/*` will be requested and confirmed before anything is changed.
