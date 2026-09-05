# Restoring NRG SolarConnect from a backup

The backup itself runs automatically every night
(`.github/workflows/backup-supabase.yml`) and lands as a `.dump` file in
the Google Drive folder set up for it. Restoring is a deliberate,
manual action — never automated — because it can overwrite live data.
Read this whole page before running anything.

## One-time setup (do this before you need it, not during an outage)

1. **Get the direct database connection string.**
   Supabase dashboard → your project → Project Settings → Database →
   Connection string → copy the **URI** under "Direct connection" (not
   the "Transaction pooler" one — `pg_dump`/`pg_restore` need a plain
   session). It looks like:
   `postgresql://postgres:[PASSWORD]@db.ssloazmdlaofujafcsjo.supabase.co:5432/postgres`

2. **Add these as GitHub repository secrets** (Settings → Secrets and
   variables → Actions, on `cyardi-nrg/nrg-report-service`):
   - `SUPABASE_DB_URL` — the connection string from step 1
   - `GOOGLE_SERVICE_ACCOUNT_EMAIL` / `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY`
     — the same values already used by the app (Vercel/host env vars)
   - `GOOGLE_DRIVE_BACKUP_FOLDER_ID` — a **Shared Drive** folder ID the
     service account can write into. Same rule as every other Drive
     write this app does: it must be a Shared Drive folder, not a
     personal "My Drive" folder shared as Editor — service accounts
     have no personal storage quota and writes to a personal folder
     fail outright.

3. Trigger the workflow once by hand (Actions tab → "Backup Supabase" →
   "Run workflow") and confirm a `.dump` file actually lands in the
   Drive folder before trusting the nightly schedule.

## Restoring

1. **Download the `.dump` file** you want to restore from the Drive
   backup folder — pick the most recent one, or an older one if you're
   recovering from something that corrupted data a few days back (like
   tonight's `quote_kw_band_rates` duplication — a dump from before
   that happened would have clean data, though the safer fix for a
   known, isolated bug like that is a targeted SQL fix, not a full
   restore).

2. **Decide full restore vs. targeted fix.** A full restore replaces
   *everything* — every table, every row — with the dump's contents.
   Anything written to the live database after that dump was taken is
   lost unless you reconcile it by hand afterwards. For a single
   corrupted table or a handful of bad rows, prefer fixing those rows
   directly (as was done tonight) over a full restore. Reach for a full
   restore only for actual data loss / corruption across the board, or
   rebuilding a fresh project from scratch.

3. **Full restore, into the SAME project** (only if you accept losing
   everything written since the dump):

   ```bash
   # Get the direct connection string the same way as setup step 1.
   export SUPABASE_DB_URL="postgresql://postgres:[PASSWORD]@db.xxxxx.supabase.co:5432/postgres"

   # --clean drops existing objects first so the restore isn't fighting
   # already-existing tables; --if-exists avoids errors on a fresh project.
   pg_restore --dbname="$SUPABASE_DB_URL" --clean --if-exists --no-owner --no-privileges nrg-solarconnect-2026-xx-xxTxx-xx-xx-xxxZ.dump
   ```

4. **Full restore, into a NEW/different Supabase project** (the safer
   way to test a restore actually works, or to recover onto a fresh
   project if the original one is unusable): create the new project
   first, get ITS direct connection string, then run the same
   `pg_restore` command against that connection string instead. Point
   the app's `NEXT_PUBLIC_SUPABASE_URL` / anon key / service role key at
   the new project once the restore is confirmed good.

5. **After ANY restore**, re-run this session's RLS lockdown migration
   (`database/migrations/0074_rls_baseline_lockdown.sql`) if you
   restored into a brand-new project — `pg_restore` brings back the
   tables and data, but a fresh project needs that migration applied
   too (an existing project you restored INTO already has it, since
   `--clean` only drops what the dump recreates, not policies from a
   later migration... but this is exactly the kind of interaction worth
   double-checking with `select rowsecurity from pg_tables` before
   flipping any real traffic onto it. See that migration file for the
   query.)

## Why this instead of Supabase's own backups

Point-in-time recovery and scheduled backups are a paid-plan Supabase
feature. This reuses free-tier tools (`pg_dump`/`pg_restore`, GitHub
Actions' free scheduled runs, and Drive storage NRG already has) to get
the same safety net at no extra cost. It's coarser — once a day, not
continuous — so up to a day's data could be lost on last resort, but
it's a real, working safety net rather than none at all. Upgrading to
Supabase Pro later for point-in-time recovery is still worth
considering once the business can justify the cost.
