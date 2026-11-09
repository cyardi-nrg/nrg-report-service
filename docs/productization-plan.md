# SolarConnect → Sellable Modules: Productization Plan

> **Version:** v1.1 · **Date:** 2026-11-08 · **Status:** Owner decisions recorded (§2). No code changed yet.
> **Changes from v1.0:** owner's decisions added (§2); the "one shared system" option dropped in favour of a separate copy per customer; new sections on the new company (§6), keeping support manageable for one person (§7), and a customer-interview kit for picking the first module (Appendix A). The roadmap (§8) was rewritten to match.
> **Based on:** a read of the live app repo `cyardi-nrg/nrg-solar-connect-app` (568 files, migrations up to 0173) plus this repo's handover docs. Every number below comes from that code, not from estimates.

---

## 1. The idea in one paragraph

Today the app runs one company (NRG). The goal is to sell it, under the name **SolarConnect** and through a **new company**, to other **Gujarat solar EPCs**. Each customer gets **their own separate copy** and chooses which modules they want: Sales, Service, Projects, Purchase/Inventory, Finance, plus add-ons. The database already has the pieces needed to switch modules on and off per company, and the app already controls module access per person. The work is mostly removing NRG from the code, building a one-command setup for each new customer, and keeping the support load small enough for one person.

---

## 2. Owner decisions (2026-11-08)

| # | Question | Decision | What it means for the build |
|---|---|---|---|
| 1 | Shared system or separate copies? | **A separate copy per customer.** "Else no one will buy it." | Every customer gets their own database, their own Google Drive and their own login. No customer's data ever sits in the same database as another's. Rewriting RLS for isolation between companies **is no longer a blocker to selling** (see §3). |
| 2 | First module to sell? | **Depends on what clients want** | Phase 0 interviews decide it (Appendix A). Phase 1 makes *every* module switchable on/off, so any of them can be first. |
| 3 | First market | **Gujarat EPCs** | GEDA / DISCOM / Gujarat subsidy / Tally logic stays as a **selling point**. No need to make it work for other states yet. |
| 4 | Brand | **SolarConnect** | "NRG" is removed from the product's name and screens. Each customer's own name and logo come from their `company_profile`. NRG's copy keeps showing NRG. |
| 5 | Who sells it | **A new company** | Code ownership, accounts and billing must move to the new company (§6). **NRG becomes customer #1 of the new company.** |
| 6 | Havells | **NRG only** | The Havells module and its NRG-specific rules ship switched off and hidden for every other customer. |
| 7 | Support | **The owner, personally** | One person supporting N copies. Setup, updates, backups and health checks must be **automated and scripted**, and customers must be able to fix routine things themselves (§7). |

---

## 3. What "separate copy per customer" removes, and what it doesn't

**Removed:** the biggest risk in v1.0. Company B can never see NRG's data, because it is in a different database. The `using (true)` RLS policies and the tables with no company link (`document_number_sequences`, `bank_statement_transactions`, `inverter_serials`, …) no longer leak across companies.

**Still needed:**
- **Security inside one copy.** The `anon` lockdown from 0074 stays. Real per-person rules (a salesperson sees only their own pipeline, cost/margin only for owner/admin) are still worth doing later, but they're the same work NRG needs anyway, not a selling blocker.
- **One codebase for everyone.** Copies must not drift into separate versions. Every customer runs the same code; only *settings and data* differ. This is what makes support by one person possible.
- **Removing NRG from the code.** Unchanged from v1.0, now the main work (§4).

---

## 4. Blockers that remain, ranked

### 4.1 Module on/off per company isn't enforced
`module_entitlements` exists but the app never reads it (0 references in code). Middleware only checks the *person's* access (`employee_module_access`). Needed: middleware, nav (`lib/nav-groups.ts`), the hub and Admin → Access all respect "has this company bought it" first, then "has this person been granted it". **This is what makes selling individual modules possible.**

### 4.2 NRG is hardcoded into the code
| Hardcode | Files | Fix |
|---|---|---|
| `NRG_ORGANIZATION_ID` constant | 33 | Each copy has one organization, so read it once from the database (or a setting) instead of a constant |
| "NRG Technologists" / "nrgtechnologists" text | 49 / 6 | Read from `company_profile` (`lib/company-profile.ts` already exists) |
| "Vadodara" | 13 | `company_profile.address` |
| "NRG SolarConnect" as the product name | several | "SolarConnect" |
| Named staff (Rutvi / Jatin / Mahesh), incl. `lib/rutvi-report.ts`, `lib/sales-backend-people.ts` | 14 | Turn into permission flags or settings (e.g. the existing `sales_followup_all` grant), not names in code |
| NRG logo and brand files in `public/brand`, `lib/brand-logo.ts` | — | Logo uploaded per customer, stored in their Drive or Supabase storage |

### 4.3 Settings that are environment variables today
Drive root folder, Telegram chat IDs, Tally secret, email sender. With separate copies these *can* stay as per-deployment environment variables, but setting 20+ variables by hand for each customer will go wrong sooner or later. The setup script (§8, Phase 2) must fill them in from one customer settings file.

### 4.4 NRG-only features to switch off for others
- **Havells**: the module, its 28 files, Havells fields in `company_profile`, quote cover assets.
- **IDFC bulk payment format** (13 files): only works for IDFC customers. Keep it, but show it only when the customer's bank is IDFC; other banks are added as customers ask.
- **NRG-specific reports** (Rutvi report, sales-backend people).

### 4.5 Two migration folders that disagree
This repo stops at **0082**; the app repo is at **0173**. With separate copies, the migrations are what build each new customer's database, so there must be exactly **one** source. That should be the app repo. This repo's copy gets marked as historical.

---

## 5. Module packaging (from what each screen actually reads and writes)

### Core (always included)
Company profile, People, Access, Devices, Message templates, Document numbering, Documents/Drive, **Customers + Contacts**, and a basic **Sites/Installations** list (today's `projects` row).
> `projects` is core because Service (warranty, inverters, commissioning), Follow-up, Social, Design Lab and Dispatch all read it. A Service-only customer still needs a list of "systems we installed". The paid **Projects** module is the execution side: BOM, dispatch, milestones, testing letters.

### Sellable modules

| Module | Screens (routes) | Notes |
|---|---|---|
| **Service** | `/service`, `/amc`, `/engagement`, inverters, help | Least tied to NRG (GEDA in 2 of 32 files). AMC renewals are recurring revenue. A strong candidate to sell first. |
| **Sales** | `/quotes`, `/followup`, `/leads`, `/payback`, `/reference-finder`, `/rates` | Pricing is already table-driven. Gujarat subsidy logic is a plus. Quote PDF needs NRG text removed. |
| **Lead-gen add-ons** | `/prospect`, `/referral`, `/bill-analyser` | Add-ons to Sales |
| **Projects** | `/projects`, `/dispatch`, `/design-lab`, `/reports` | GEDA/CEIG milestone tracks (20 of 44 files) suit Gujarat EPCs |
| **Purchase & Inventory** | `/stock`, `/materials`, `/purchase`, `/procurement`, `/vendors` | Needs a manual "requirement" path when Projects is off (BOM-driven requirement only works with it) |
| **Finance** | `/finance`, `/payments` | Tally users only. Most sensitive data; bank formats vary. Probably sold last. |
| **Team add-ons** | `/tasks`, `/attendance`, `/social` | Small add-ons |
| **NRG only** | `/havells`, NRG-specific reports | Never offered to others (decision 6) |

### Where modules reach into each other (each needs a fallback for when the other module is off)
- Follow-up → reads `projects`, `financial_obligations` (Finance)
- Service → reads `commissioning_reports` (Projects)
- Dispatch → reads `service_tickets` (Service)
- Procurement → reads `boms` (Projects)
- Social → reads `boms`, `projects`
- Design Lab → reads `quotes`, `leads` (Sales)

---

## 6. The new company: what has to move (decision 5)

Not legal advice. These are the practical items to settle with a CA/lawyer before the first sale.

1. **Who owns the code.** The app was built for and at NRG Technologists. The new company needs a written assignment or licence of the code from NRG Technologists. Without it, ownership of what's being sold is unclear.
2. **NRG becomes customer #1.** Once the new company owns SolarConnect, NRG Technologists uses its copy as a customer, ideally with a simple agreement so the arrangement is clean if either company changes hands.
3. **Accounts in the new company's name:**
   - GitHub organization (move `nrg-solar-connect-app` there, or fork it so NRG's history stays put)
   - Supabase organization, one project per customer
   - Hosting (Railway or similar), one service per customer
   - A Google Cloud service account for Drive, ideally connected to **each customer's own Google Drive**, so their documents stay theirs
   - OpenAI/Anthropic API billing: which company pays for each customer's AI usage, and is it passed through in the price?
   - Domain (e.g. `customername.solarconnect.in`) and email sender
4. **Customer agreement:** what's included, uptime expectations, the customer owns their data, what happens to the data if they stop paying (export, then delete), and fair-use limits on AI.
5. **GST invoicing** from the new company for subscriptions.

---

## 7. Keeping support manageable for one person (decision 7)

With one person supporting every customer, each copy must cost close to zero effort to run. Concretely:

| Area | Requirement |
|---|---|
| **New customer setup** | One script: create the Supabase project, run all migrations, seed company profile and first admin, switch on purchased modules, set environment variables from one settings file, deploy. Target: under an hour, mostly waiting. |
| **Updates** | One command pushes the same code version and new migrations to every copy, in order: NRG first, then the others. A list of which copy runs which version. Never hand-edit one customer's copy. |
| **Backups** | The existing nightly Supabase → Drive backup (`.github/workflows/backup-supabase.yml`) runs for every copy, into that customer's own Drive. |
| **Health check** | A daily automated check across all copies (site up, last backup succeeded, cron digests ran), sent to the owner on Telegram. The app already uses Telegram for this. |
| **Self-service** | Customer admins do routine things themselves: add/remove staff, module access per person, templates, rates, company details. All of these admin screens exist already. |
| **Help** | The in-app help pages (`/projects/help`, `/service/help`) become the first stop. Add short "how do I…" pages per module. |
| **Support boundary** | Written into the agreement: what support covers (bugs, how-to) and what costs extra (custom features, data clean-up, training visits). |
| **Customer count** | Grow slowly. Each new customer's first month is when most questions come in. Onboard one at a time. |

---

## 8. Phased roadmap (rewritten for v1.1)

Every phase leaves NRG's live system working. Nothing is switched over all at once.

### Phase 0: Validate (about 2–3 weeks, no code)
1. Interview 3–5 Gujarat EPCs using **Appendix A**. That decides which module goes first (decision 2) and roughly what to charge.
2. Start setting up the new company and the code-ownership agreement (§6). The paperwork takes longest, so start early.

### Phase 1: Make the code product-ready (works in NRG's copy, NRG notices nothing)
1. Make the app repo the only schema source; mark this repo's `database/migrations` as historical.
2. **Enforce `module_entitlements`** in middleware, nav, hub and Admin → Access (§4.1).
3. Add a fallback for each cross-module read when the other module is off (§5).
4. Replace `NRG_ORGANIZATION_ID` (33 files) with a single lookup.
5. Replace hardcoded NRG text, address and logo with `company_profile` (§4.2), and rename the product to "SolarConnect".
6. Turn named-staff logic into permission flags (14 files).
7. Put Havells, IDFC and NRG-only reports behind switches that are off by default (§4.4).

**Test for Phase 1:** a blank test copy with a made-up company "ABC Solar" shows no trace of NRG anywhere: screens, PDFs, WhatsApp messages or emails.

### Phase 2: The customer-copy machinery (§7)
1. Setup script for a new customer.
2. Update script for all copies, plus a record of which copy runs which version.
3. Per-customer backups and the daily health check.
4. Onboarding import from the customer's Excel files (customers, sites, AMC contracts, rates), building on `/admin/data-migration`.

### Phase 3: First pilot customer
1. A friendly Gujarat EPC, with the module(s) Phase 0 pointed to.
2. Free or discounted for about 2 months in exchange for honest feedback.
3. Write down every place their process differs from NRG's. That list is the real backlog.

### Phase 4: Sell
Pricing finalized, the agreement in place, the next customers onboarded one at a time.

### Later (not needed to sell)
Per-person security rules inside a copy (salesperson sees own pipeline only, etc.), other states, other bank formats, a self-serve trial.

---

## 9. Pricing: hypotheses to test in Phase 0, not decisions

- Price per module per month, with a bundle discount.
- Core plus a set number of users; extra users charged.
- A one-time setup fee covering the data import and onboarding. With one person doing support, this fee pays for the busiest month.
- AI usage (document reading, OCR) either included up to a limit or passed through at cost.

---

## 10. Immediate next step

**Phase 1, step 2: enforce `module_entitlements`.** It's small, invisible to NRG (NRG has every module), and needed whichever module ends up first. Files involved: `middleware.ts`, `lib/module-access.ts`, `lib/nav-groups.ts`, `app/(app)/layout.tsx`, `app/(app)/hub/[category]/page.tsx`, `app/(app)/admin/access/*`. Per the working agreement, the current versions get confirmed with the owner before anything is changed.

---

## Appendix A: Customer interview kit (decides "which module first")

Talk to the owner or operations head of 3–5 Gujarat EPCs. About 30 minutes each. Listen more than pitch.

**Their business**
1. Roughly how many installations a year? Residential, commercial or both?
2. How many staff in sales, service, projects/site, purchase, accounts?
3. How many systems have you installed in total? How many are under AMC?

**Where it hurts today**
4. How do you track service complaints today: WhatsApp, Excel, a register, software?
5. How do you remember AMC renewals? Have you lost renewals because nobody followed up?
6. How do you make a quote: Excel, Word, software? How long does one take?
7. How do you track a lead from first call to order?
8. How do you track GEDA / DISCOM / CEIG paperwork for each project?
9. How do you know what's in stock and what to order for the next project?
10. Do you use Tally? Who enters data into it?

**Willingness to pay**
11. If one of those problems disappeared tomorrow, which one would you pick?
12. What do you pay today for any software (Tally, CRM, anything)?
13. Would you pay monthly for just that one thing? Roughly how much would feel fair?
14. Who in your company would decide, and who would use it every day?

**What to write down after each interview:** their top pain (Q11), the module that solves it, the price they mentioned, and anything they do differently from NRG. After 3–5 interviews, the module that keeps coming up in Q11 is the one to sell first.
