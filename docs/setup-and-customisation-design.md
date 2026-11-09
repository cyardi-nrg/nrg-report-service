# SolarConnect: Easy Setup, Customer Branding, and Custom Features Without Forking

> **Version:** v1.0 · **Date:** 2026-11-09 · **Status:** Design proposal for owner review. No code changed.
> **Answers three owner questions:** (1) how a new customer gets set up, as close to "by themselves" as possible; (2) how each customer gets their own logo, colours, details, letterheads and quote cover; (3) how to build one customer's special request without touching the others, while still being able to change everyone at once.
> **Companion to:** `docs/productization-plan.md` v1.1. **Revises** that plan's hosting idea (§1 below explains why).
> **Based on:** the live app repo `cyardi-nrg/nrg-solar-connect-app` (`main`, confirmed current by the owner on 2026-11-09).

---

## The core principle behind all three answers

> **One code. Many settings. A separate database for each customer.**

Every customer runs the **same code**. What makes ABC Solar's app look and behave like *theirs* is **data**: their settings, logo, colours, templates and switches, all stored in *their* database. Change the code once and everyone gets it. Change one customer's settings and only they see it. There is **never** a separate copy of the code per customer. That is what would make "change all at once" impossible, and with one person doing support it would become unmanageable within a few customers.

---

## Part 1: Setup the customer can (mostly) do themselves

### 1.1 The honest starting point: the customer should never see Supabase, GitHub or hosting

Creating a Supabase account, naming a project, copying keys into GitHub secrets, setting 20+ environment variables: a solar EPC owner will get stuck at step 2, and you'll get the phone call. Even a perfect step-by-step guide doesn't fix this, because the steps involve keys and passwords that are easy to paste wrong and dangerous to get wrong.

**Recommendation: the new company owns all the technical accounts, and a script does the technical setup automatically.** The customer only does things that are genuinely about *their business*: company details, logo, team, their Google Drive, their data.

| Thing | Who owns it | Who does the setup |
|---|---|---|
| Supabase (the database) | New company's Supabase organization, **one separate project per customer** | Automatic (Supabase's management API can create projects and run SQL) |
| The app itself (hosting) | New company, **one deployment shared by all customers** (§1.2) | Nobody per customer: it's already running |
| Web address | New company's domain, e.g. `abcsolar.solarconnect.in` | Automatic |
| GitHub | New company only. **Customers never touch it.** | — |
| AI key (OpenAI/Anthropic) | New company; usage is covered in the price | Already set, once |
| Email sending | New company's sender, e.g. "ABC Solar via SolarConnect" | Already set, once |
| Telegram alerts | **One SolarConnect bot** owned by the new company | Customer adds the bot to their group (§1.5) |
| Google Drive (their documents) | **The customer** | Customer, with a guided step and a "Test" button (§1.4) |
| Their data | **The customer**, contractually | Nightly backup into *their own* Drive, so they always hold a full copy |

**Does this still meet "it has to be separate"?** Yes, where it matters:
- Each customer's data is in **its own database**, never mixed with anyone else's.
- Their documents are in **their own Google Drive**.
- The existing nightly backup (`daily-backup`) writes a full copy of their data **into their own Drive**, so even if they leave, they walk away with everything.
- What they *don't* get is a login to the technical accounts, and almost no customer wants one. If a larger customer insists on owning the Supabase account, that can be a premium option (§1.6).

### 1.2 Change to the hosting idea: one app, many databases

v1.1 of the plan said "a separate copy per customer", meaning a separate database **and** a separate deployment of the app. Separate deployments make your third question ("change all at once") hard: 10 customers means 10 deployments to update, 10 sets of environment variables to keep right, 10 places for something to drift.

**Better: one deployment of the app, which connects to the right customer's database based on the web address.**

```
abcsolar.solarconnect.in ──┐                         ┌──> ABC Solar's database   (separate Supabase project)
nrg.solarconnect.in ───────┼──> ONE SolarConnect app ─┼──> NRG's database         (separate Supabase project)
xyzenergy.solarconnect.in ─┘   (same code for all)    └──> XYZ Energy's database  (separate Supabase project)
```

- **Data is still fully separate:** different databases, different Drives.
- **One code update reaches everyone at once** (Part 3).
- **Why it's practical in *this* app:** all 471 database calls in the code go through two functions in `lib/supabase/server.ts` (`createClient`, `createServiceRoleClient`). Today they read one database address from environment variables. They'd instead look up "which customer is this web address?" in a small **customer registry** (a separate database owned by the new company, holding each customer's database address and keys, encrypted). That's a focused change in a few files (`lib/supabase/*`, `middleware.ts`, the cron jobs), not a rewrite.
- **Trade-off, stated plainly:** if the one app is down, it's down for everyone. Mitigation: the hosting platform's automatic restarts, the daily health check (plan §7), and a status message.
- **Escape hatch:** a customer who insists on their own separate deployment can still have one, running the *same code*. This is a premium option, not the default.

> **Decision needed:** confirm "separate database per customer, one shared app" as the meaning of "separate". It keeps everything in decision 1, and makes setup and updates far easier.

### 1.3 What the customer actually experiences

**Step A: Sign up (5 minutes, on solarconnect.in)**
Company name, GSTIN, owner name, mobile, email, which modules they want. You approve (or a payment goes through).

**Step B: Automatic, no human involved (about 5–10 minutes of waiting)**
A setup script (the "provisioner") that you own:
1. Creates their Supabase project.
2. Runs every migration, so their database is identical to everyone else's.
3. Creates their organization row, switches on the modules they bought (`module_entitlements`) and creates the owner's login.
4. Adds their web address to the customer registry.
5. Sends the owner a WhatsApp/email: "Your SolarConnect is ready. Log in here."

**Step C: First-login setup wizard, inside their own app (about 30 minutes, the customer does it)**
A checklist with a progress bar. They can stop and continue later.

| # | Step | What they do | Already exists in the app? |
|---|---|---|---|
| 1 | Company details | Name, address, GSTIN, PAN, bank, phones, signature | ✅ `company_profile`, Admin → Company. Needs wizard packaging. |
| 2 | Logo and colours | Upload logo. The app **suggests colours picked from the logo**; they accept or adjust. | Logo: ✅ (`document_branding_assets`). Colours: ❌ (Part 2.2) |
| 3 | Google Drive | Connect their Drive and press **Test** (§1.4) | Partly. Drive works, but is set by environment variable today. |
| 4 | Team | Add staff (name, mobile, role) and tick modules per person | ✅ Admin → People / Access |
| 5 | Quote setup | Rates, terms, quote cover (Part 2.4) | Rates/terms ✅. Cover positions ❌. |
| 6 | Alerts (optional) | Add the SolarConnect Telegram bot to their group (§1.5) | ❌. Today it's one bot token plus chat IDs in environment variables. |
| 7 | Import data (optional) | Download Excel templates (customers, installed sites, AMC contracts), fill them in, upload | Partly: `/admin/data-migration` |

**Step D: Your involvement:** a 30-minute video call after Step C to check things and answer questions. That's the onboarding fee (plan §9).

### 1.4 Google Drive: the one technical step the customer must do

The app currently connects to Drive with a Google **service account** (a robot Google account) and one root folder set in an environment variable. Two ways to connect a customer's Drive:

| | **Option 1: Shared Drive + robot email** (works with today's code) | **Option 2: "Connect Google Drive" button** (new build) |
|---|---|---|
| Customer does | Creates a Shared Drive called "SolarConnect", adds the robot email (shown on screen, with a Copy button) as *Content manager*, pastes the Drive link, presses **Test** | Clicks "Connect Google Drive", signs in with Google, clicks Allow |
| Needs | **Google Workspace** (paid business Google). Shared Drives don't exist on free Gmail. | Works with ordinary Gmail too |
| Build effort | Small: move the root folder from environment variable to a setting, add the Test button | Medium: Google sign-in flow, plus Google's app review. The scope the app currently uses ("full Drive") is a *restricted* scope with a heavy review. A narrower scope ("only files this app created") avoids most of it, but needs code changes. **Check Google's current rules before committing.** |

**Recommendation:** start with **Option 1**, since it works today and many established EPCs already use Workspace. Ask in the Phase 0 interviews whether they use Gmail or Workspace. Build Option 2 only if enough of them are on plain Gmail.

### 1.5 Telegram alerts without each customer creating a bot

Today: one bot token and six chat IDs (`TELEGRAM_CHAT_SALES`, `…_SERVICE`, `…_PURCHASE`, `…_FINANCE`, `…_PROJECTS`, `…_DAILY_SUMMARY`) in environment variables. Asking a customer to create a bot with BotFather and find chat IDs is too technical.
**Instead:** one **SolarConnect bot**, owned by the new company. In the wizard, the customer adds `@SolarConnectBot` to their Telegram group and types the 6-digit code shown on screen. The bot records "this group = ABC Solar's Sales alerts". The chat IDs move from environment variables into a per-customer settings table.

### 1.6 If a customer insists on owning the accounts

Offer it as a premium "self-hosted" option: they create the Supabase account (from a screenshot guide) and invite the new company as a member, and the same provisioner then does everything else. It's still the same code and the same updates; just the account owner differs. Don't make this the default.

---

## Part 2: Each customer's look: logo, colours, details, letterheads, quote cover

### 2.1 What's already built

| Item | State today |
|---|---|
| Company name, address, GSTIN, PAN/CIN, bank, phones, T&Cs | ✅ `company_profile` + Admin → Company (migrations 0065, 0169) |
| Logo, payment QR, quote covers (residential/commercial), quote back pages | ✅ Replaceable from Admin → Company → Branding (`document_branding_assets`, `lib/document-branding.ts`). Falls back to NRG's images when a slot is empty. |
| App colours | ❌ Brand blue `#1f3bb8` typed directly into **100 files**. The shared colour setting in `lib/theme.ts` (`colors.brand`) is used in **0 files**. |
| Text position on the quote cover | ❌ Client name and kW are drawn at **fixed positions matched to NRG's cover graphic** (`lib/quote-document.ts`, e.g. name at x=158, y=434; kW at x=198, y=524; fixed colours `#0d1e5a` / `#228b22`). A different cover image puts the text in the wrong place. |
| NRG defaults | ❌ An empty branding slot falls back to **NRG's** logo and covers, so a new customer would see NRG branding until they upload theirs |

### 2.2 Colours (theme)

1. Each customer's database holds a small **theme**: primary colour, secondary/accent colour, and optionally a header style.
2. The app turns these into named colour slots (`--brand`, `--accent`, …) when a page loads.
3. A one-time sweep replaces the hardcoded `#1f3bb8` (100 files) and the other brand colours with those slots. Neutral greys and red/green status colours stay fixed; they're not brand colours.
4. In the wizard: upload logo → the app suggests 2–3 colours taken from it → the customer picks one, with a live preview.
5. Generated documents (quotes, DCs, receipts) use the same theme colours.

NRG's theme is set to today's exact colours, so **NRG sees no change.**

### 2.3 Letterheads (DC, BOM, receipts, testing letters, quotes)

All generated documents should share **one letterhead builder** that reads: logo, company name, address, GSTIN, phones, website, footer motto, theme colour. The data already exists in `company_profile`. The work is making sure every document uses it (49 files still contain the literal "NRG Technologists").
Offer **2–3 letterhead layouts** (logo left / logo centred / full-width band) as a setting, rather than letting customers design from scratch. Most companies want "my logo and my details, looking professional", not a design tool.

### 2.4 The quote cover page: your specific worry

The problem: the cover is a picture with text placed at exact spots for *your* picture. Another company's picture has the empty space somewhere else, or wants different text.

**Solution: the cover becomes "picture + a list of text boxes", and the customer places the boxes themselves.**

1. **Cover picture:** the customer uploads their own design (made in Canva, by a designer, or anywhere), A4 portrait, with blank space where the name and kW should go. *(Upload already works today.)*
2. **Text boxes, stored as data, not code:** for each box, the field (client name, kW, quote number, date, site address, salesperson…), position, font size, colour, bold, alignment and maximum width (text shrinks to fit, which `svgFitAttr` already does). NRG's current positions become NRG's saved layout, so NRG's covers come out identical.
3. **Visual editor in Admin:** the uploaded cover shown on screen with the boxes on top. The customer **drags** each box into place, picks size and colour, and sees a live preview with a sample name ("Mr. Ramesh Patel, 10.00 kW"). A **"Generate sample PDF"** button shows exactly what a client would receive.
4. **No cover picture yet?** The customer picks one of **3–4 ready-made SolarConnect cover designs** (residential / commercial styles). These use their logo and theme colour automatically, so they have a professional cover on day one.
5. **Different covers per quote type:** keep today's residential/commercial split, and allow one per quote type if a customer wants it.
6. **Back pages** (components, warranty, portfolio, back cover): already replaceable images. Add "use our generic page" options, and let a customer **turn individual pages off**.

**Two requests to treat differently:**
- "I want different *wording* in the quote" (letter text, terms, scope list) → editable text per quote type, the same pattern as `quote_type_terms` today.
- "I want a completely different quote *layout*" → that's a new **quote template** (Part 3, layer 3), built once and selectable by any customer. Never a one-off copy of the code.

---

## Part 3: Custom requests for one customer, and changes for everyone

### 3.1 Five layers, cheapest first

When a customer asks for something, handle it at the **lowest layer that works**:

| Layer | What it is | Example requests | Code change? | Who changes it |
|---|---|---|---|---|
| **1. Settings** | Values in their database, edited on admin screens | Logo, colours, rates, T&Cs, WhatsApp wording, approval limit, document number format, which back pages to include | None | Customer |
| **2. Switches (feature flags)** | A built feature that's **off by default** and switched on per customer | "We want AMC visits to need a photo", "we don't use GEDA tracking", Havells (NRG only), IDFC bank file | Built once; switching on is a setting | You, from your console |
| **3. Templates** | Several versions of a document/screen; customer picks one | Quote layout A/B/C, letterhead style, cover designs, BOM printout style | Built once, available to all | Customer picks |
| **4. Custom fields** | Customer adds their own extra fields to customers / projects / tickets / leads | "We also need to record the society name", "we track the roof type" | None after a one-time build | Customer (or you) |
| **5. New feature** | Genuinely new capability | "Integrate with our Zoho books", a new report | Yes, but **in the main code, behind a switch**, never a separate copy | You (paid) |

**The rule for layer 5:** a customer's special feature is built **into the one shared code**, switched **on only for them**. Everyone else has it **off** and never sees it. Later, if another customer wants it, you switch it on for them too, and it becomes a product feature you can sell again. That's how "custom for one" and "change for all" live together.

### 3.2 How to decide on a request

1. Can it be done with existing settings? → Show them where. Free.
2. Is it a small switch on existing behaviour? → Build as a switch. Small fee or free.
3. **Would at least one other customer plausibly want it?**
   - Yes → build it into the product behind a switch. Charge a development fee; it stays yours to sell.
   - No, and it's large or strange → **say no, politely**, or offer an export (Excel/CSV) so they can do it elsewhere. With one person supporting everything, every one-off feature is maintenance forever.
4. Write the rules into the customer agreement: what's included, what's charged, and that **everything built stays part of SolarConnect** (the new company's code), even when one customer paid for it.

### 3.3 What's already in the code that fits this model

- `module_entitlements` is already a switch table (per module). Extend the same idea to **per-feature switches** (`organization_features`: feature key, on/off, settings).
- `employee_module_access` already shows the pattern working one level down (per person).
- `document_branding_assets`, `company_profile`, `quote_type_terms` and `message_templates` already show settings and templates as data instead of code.
- Some NRG-specific behaviour is still in code: named staff (Rutvi/Jatin/Mahesh, 14 files), Havells, IDFC. These become switches as part of plan Phase 1.

### 3.4 Changing everything at once, safely

With one app and one code, **a code change reaches every customer on the next deploy.** The care needed is around the databases, since each customer has their own:

1. **Database changes (migrations) must be "add-only" first.** Add new columns/tables, never rename or delete in the same step. The code then works with both the old and new database shape.
2. **Order of a release:**
   1. Run the new migrations on **every customer database**, using a script that loops through the customer registry, records which version each database is on, and **stops at the first failure**.
   2. Then deploy the new app code once.
   3. Clean-up migrations (removing old columns) go in a later release.
3. **Rollout rings:** a demo customer first, then NRG (you'll notice problems fastest), then everyone else. A risky new feature ships **switched off**, gets switched on for NRG, then for others.
4. **A release log** customers can read ("What's new"): short, plain-language notes. It cuts down support calls.

### 3.5 What NOT to do (the trap)

- ❌ A copy of the code per customer ("ABC's version", "XYZ's version"). Within a year you can't fix a bug once; you fix it N times, differently.
- ❌ `if (customer === 'ABC Solar') { … }` in the code. Use a named switch (`feature: amc_photo_required`) instead, so it can be turned on for anyone.
- ❌ Making changes directly in one customer's database by hand. Changes go through settings screens or migrations, so every database stays the same shape.

---

## Part 4: What has to be built, in order

Each item keeps NRG's live system working and invisible to NRG unless stated.

| # | Work | Answers | Size |
|---|---|---|---|
| 1 | Enforce `module_entitlements` (plan Phase 1) | Selling individual modules | Small |
| 2 | Theme: colour slots, one-time sweep of 100 files' hardcoded colours, colour settings, logo → colour suggestion | Part 2.2 | Medium (mechanical) |
| 3 | One letterhead builder used by every document; remove literal NRG text (49 files) | Part 2.3 | Medium |
| 4 | Quote cover text boxes as data, plus a drag-and-place editor with sample PDF | Part 2.4 | Medium |
| 5 | Ready-made generic covers, back pages and logo, so a new customer never sees NRG's | Part 2.1, 2.4 | Small (plus design work) |
| 6 | Per-feature switches table; convert Havells, IDFC and named-staff logic to switches | Part 3 | Small–Medium |
| 7 | Move per-customer environment variables (Drive root, Telegram chats, Tally) into a settings table | Part 1.4, 1.5 | Small–Medium |
| 8 | Customer registry + "which database for this web address" in `lib/supabase/*`, middleware, cron jobs | Part 1.2 | Medium. **The most careful piece**, tested thoroughly on a copy before NRG moves. |
| 9 | Provisioner script (create Supabase project, migrations, seed, registry entry, owner login) | Part 1.3 Step B | Medium |
| 10 | Migration runner across all customer databases + release log | Part 3.4 | Small–Medium |
| 11 | First-login setup wizard with Drive **Test** button and Telegram bot linking | Part 1.3 Step C | Medium |
| 12 | Custom fields | Part 3.1 layer 4 | Medium (can wait for real demand) |
| 13 | Public signup page | Part 1.3 Step A | Small (can wait; you can do Step A by hand for the first customers) |

**Good news:** items 1–7 also improve NRG's own system (cleaner code, branding editable without a developer), so none of it is wasted even before the first sale.

---

## Decisions needed from the owner

1. **Hosting:** "separate database per customer, one shared app" (recommended), or a fully separate deployment per customer?
2. **Accounts:** the new company owns Supabase/hosting, and customers own their Drive and data (recommended). Or should customers own their Supabase accounts?
3. **Drive:** start with Shared Drive + robot email (Workspace customers only), and ask in interviews how many use Gmail?
4. **Quote cover:** customer uploads their own picture and drags text boxes into place, plus 3–4 ready-made designs. Agreed?
5. **Custom work policy:** built into the shared code behind a switch, charged, and owned by the new company. Agreed?
