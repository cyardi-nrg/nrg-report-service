# Design Lab worker — on your Mac  (v1.1.0, 31 Oct 2026)

The Design Lab in SolarConnect only *asks* for heavy work (shade check, panel layouts, drawings, 3D, the
walk-around video). This small program on your MacBook does that work and files the results back into the
project's Google Drive folder and the Design Lab, where you approve them.

- It picks up a job only when its time has come: "Now", or **tonight after 9 PM / 10 PM** (the video's default).
- While a job runs, the Mac is kept awake. If a night job is due within 4 hours, the Mac is kept awake until it starts.
- Results arrive as drawings in the project's Drive **Design** folder (SLD / CEIG sheets in **CEIG**) and as a new
  version of that stage, waiting for your ✓ Approve.
- It costs nothing to run, uses your Mac only, and needs internet.

## What it can do (built in phases)

| Phase | What | Status |
|---|---|---|
| 1 | The worker itself: queue, night window, Drive filing, versions, "Mac online" in the Design Lab | **done (this version)** |
| 2 | AutoCAD DWG / DXF → plan picture with its scale + suggested roof outlines (roofs are drawn in the Design Lab) | **done (v1.1)** |
| 3 | Panel layout engine (options, shade check, generation), structure drawings | |
| 4 | 3D views and the overnight walk-around video | |
| 5 | Stringing, walkway, earthing, cable tray, SLD, CEIG set — made general from the Jain Granite programs | |

A job for a stage the Mac can't do yet simply **waits in the queue** and runs on its own once that phase is installed.

## One-time setup (about 15 minutes)

1. **Get the folder onto the Mac.** Install **GitHub Desktop** (free, desktop.github.com) and sign in.
   - File → Clone repository → `cyardi-nrg/nrg-report-service` → Clone.
   - At the top, switch the branch to `claude/3d-design-walkthrough-videos-pim15v`.
2. **Have the keys ready.** Open Railway → the SolarConnect service → **Variables**. You will copy five values:
   `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_SERVICE_ACCOUNT_EMAIL`, `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY`,
   `GOOGLE_DRIVE_ROOT_FOLDER_ID` (and check `SUPABASE_URL` is the same as in the file).
3. **Run the setup.** Open **Terminal** and type (the path is where GitHub Desktop put it, usually `Documents/GitHub`):
   ```
   bash ~/Documents/GitHub/nrg-report-service/design-lab/worker/mac/install.sh
   ```
   - It installs what it needs inside that folder only.
   - It opens a settings file in TextEdit: paste the values, save, close TextEdit, press Return in Terminal.
   - It checks the connection (✓ Supabase, ✓ Google Drive, ✓ Heartbeat) and starts the worker.
4. **For AutoCAD DWG files** (DXF works without this): install the free **ODA File Converter** from
   opendesign.com/guestfiles/oda_file_converter (drag it into Applications). Or, if you use Homebrew: `brew install libredwg`.
5. **Nightly wake** (asks for your Mac password once):
   ```
   sudo pmset repeat wakeorpoweron MTWRFSU 20:55:00
   ```
   At night keep the MacBook **plugged in with the lid open**. A closed lid always sleeps.

That's it. In the Design Lab, the list page shows **"Mac: online"** while the worker is running.

## Everyday

- **Updates:** in GitHub Desktop press **Fetch origin → Pull**. The worker restarts itself within a minute
  (or log out and in).
- **See what it is doing:** `tail -f ~/Documents/GitHub/nrg-report-service/design-lab/worker/logs/worker.log`
- **Check the setup again:** `cd ~/Documents/GitHub/nrg-report-service/design-lab/worker && .venv/bin/python3 worker.py --selftest`
- **Stop it for good:** `bash ~/Documents/GitHub/nrg-report-service/design-lab/worker/mac/uninstall.sh`
  (and `sudo pmset repeat cancel` to stop the nightly wake)

## Safety

The `.env` file holds keys that can read and write the whole database and Drive. It stays on your Mac only
(it is never uploaded to GitHub) and is readable only by your user account. Don't email it or put it in Drive.
