# Setup — the 3 things needed before this app can run for real

None of these can be created by Claude on your behalf — each is a real
account/credential tied to NRG's ownership. Each is a one-time, ~5-minute
task. Once you have all three, copy `.env.example` to `.env.local` and
fill in the values below.

## 1. Supabase (the database)

1. Go to [supabase.com](https://supabase.com) → Sign up (email or Google).
2. Click **New Project** → name it "NRG SolarConnect" → set a database
   password (write it down somewhere safe) → wait ~2 minutes for it to
   provision.
3. Once it's ready: **Project Settings → API**. Copy three values into
   `.env.local`:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon / public key** → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role key** (click "Reveal") → `SUPABASE_SERVICE_ROLE_KEY`
     — keep this one private, it bypasses all access rules.
4. Load the real schema: from a terminal with `psql` installed,
   `psql "<connection string from Project Settings -> Database>" -f database/migrations/0002_core_schema.sql`,
   then repeat in numeric order through `0045_employee_module_access.sql`
   (all 45 files, in `database/migrations/`). This exact chain was
   validated end-to-end on 2026-08-19 — every migration builds clean
   from empty on a fresh database.
5. Add yourself as the first employee row (SQL Editor in the Supabase
   dashboard):
   ```sql
   insert into employees (name, role, is_owner)
   values ('Your Name', 'owner', true)
   returning employee_id;
   ```
   Then create a Supabase Auth user for yourself (**Authentication →
   Users → Add User**, email + password), and link the two:
   ```sql
   update employees set auth_user_id = '<the auth user's UUID>'
   where employee_id = '<the employee_id from above>';
   ```
   That login/password is what you'll use to sign in to the app.

## 2. Google Cloud (so the app can read/write NRG's Drive files)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) →
   sign in with the Google account that owns NRG's Drive files.
2. **New Project** → name it anything (e.g. "NRG SolarConnect").
3. **APIs & Services → Library** → search "Google Drive API" → Enable.
4. **APIs & Services → Credentials → Create Credentials → Service
   Account** → name it anything → Done (skip the optional role/access
   steps).
5. Click into the new service account → **Keys → Add Key → Create new
   key → JSON** → a file downloads. Open it and copy two fields into
   `.env.local`:
   - `client_email` → `GOOGLE_SERVICE_ACCOUNT_EMAIL`
   - `private_key` → `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` (paste the
     whole thing including `-----BEGIN PRIVATE KEY-----`, quotes are
     fine)
6. In Google Drive, open (or create) the folder where new project
   folders should live → **Share** → paste the service account's email
   → give it **Editor** access → copy the folder's ID out of its URL
   (the part after `/folders/`) into `GOOGLE_DRIVE_ROOT_FOLDER_ID`.

## 3. OpenAI (so it can actually read a document)

1. Go to [platform.openai.com](https://platform.openai.com) → sign up.
2. **Settings → Billing** → add a payment method (this is the one paid
   step — each document read costs a small fraction of a rupee, but
   there's no free tier for API access).
3. **API keys → Create new secret key** → copy it into `OPENAI_API_KEY`.

## Running it

```
npm install
npm run dev
```

Then open http://localhost:3000 — you'll land on `/login`.

## Known gaps, honestly, as of 2026-08-19

- **PDF documents aren't read yet** — the AI classification/extraction
  code is proven against image uploads (JPEG/PNG, which covers most
  real site photos and phone-scanned documents) but PDFs need one more
  step (convert to image, or switch to OpenAI's native file input)
  before `readDocumentWithAI` will work on them. Flagged inline in
  `lib/ai-extraction.ts`.
- **Only one document type has a real field extractor** — CEIG
  electrical test records (`electrical_test_records`). Every other
  real document type (BOM, Delivery Challan, invoices, etc.) currently
  only gets classified (`documents.document_type` set), not
  type-specifically extracted. Each one needs its own extractor built
  the same way, matched against its own real table.
- **Row-Level Security is not enabled.** The schema is shaped for it
  (`organization_id`/`employees.role`/`is_owner` everywhere it's
  needed) but no policies exist yet — this app currently trusts that
  anyone who can sign in can see everything. Fine for a single-tenant,
  small-team pilot; not fine before this has real financial/PII data at
  any real scale. This is the same "still open" item the schema's own
  handover notes have flagged since early on.
- **No Projects/Stock/Reports screens yet** — only Login and Documents
  (upload + AI read) exist as real, working screens. The rest of what's
  in the Claude Design mockup (`nrg-solarconnect-dashboard.html`) is
  still a picture, not wired to this real app.
