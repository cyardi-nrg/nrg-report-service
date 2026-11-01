# Design Lab worker — on your Mac  (v1.10.0, 1 Nov 2026)

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
| 3 | Roof & shade report; panel layout engine — 3 options per quote (best generation / nearest the inverter / biggest roofs), shade check, units a year, DC cable, drawings + comparison; flat roofs prefer portrait (less purlin pipe) | **done (v1.2–1.3)** — structure drawings next |
| 4 | 3D: an interactive 3D file (opens offline in any browser — send it to the client) + 5 pictures; the 40-second walk-around video (1080p + a WhatsApp copy under 16 MB), queued for tonight | **done (v1.3)** |
| 4b | Structure drawings: an A3 sheet per panel table (side elevation, plan, member schedule, member checks — a failing override is drawn and marked FAILS); sheet roofs get the aluminium-piece sheet | **done (v1.4)** |
| 4c | Expected generation month by month — NREL SAM (PySAM, PVWatts v8) hour by hour on a PVGIS typical year for the site, each roof face simulated on its own; a chart per option; SAM's yearly units used everywhere | **done (v1.5)** |
| 5a | Stringing: strings of 20 (roofs filled in whole strings), 5-row landscape groups so + and − land on the walkway side, MPPT voltage / current checks (Voc at 5 °C, Vmp 70 °C → 5 °C), single 4 sq mm runs ×2 vs Y-connector + 6 sq mm ×1 — the cheaper wins; stringing layout + string schedule; DC cable and MC4 sets into the BOM | **done (v1.6)** |
| 5b | Walkway (between the row groups), cable tray (array → roof edge → down the wall), earthing (3 pits DC / AC / LA, lightning arresters by kW), AC cable to the meter — three drawings, lengths into the BOM | **done (v1.6)** |
| 5d | v1.7 (owner): Y pairs join where the SAME poles meet (one pole's ends side by side); strings of 18–20 (20 first); a mix of Y pairs and single strings, each pair priced on its own; one string length per MPPT; earth pits 3 m apart | **done (v1.7)** |
| 5c | **SLD** (stage “SLD”): A3 PDF + picture — strings, MPPTs, Y pairs, DCDB, ACDB with one incomer per inverter, breakers and Al cable sizes worked out from the inverter (same ladder that gave Jain 95 sq mm), voltage drops, design checks. **CEIG set** (stage “CEIG drawing set”): 01 SLD, 02 equipment, 03 earthing (with the IS 3043 pit section and details), 04 walkway, 05 cable tray, 06 stringing — A3, NRG title block, plus the whole set as one PDF. Strings are now spread evenly over the inverters | **done (v1.8)** |
| 5e | v1.8.1 (owner's review): strings follow one unbroken snake (no skipped or stray panels), cut into 18–20 with no long jumps; row groups filled with counts that string cleanly; neighbouring strings meet panel-to-panel so a Y joins one pole side by side; the wiring path is drawn and every panel numbered from the + end; every DC run sized by current, length and drop (aim < 2 %, max 3 %), AC cables likewise (fewest runs first) ; RULE: in every Y pair the + (red) ends of both strings sit side by side (v1.8.2); RULE: wherever two strings meet the ends are the same colour, never red next to black — Y pairs only at red meetings; any unavoidable spot is flagged (v1.8.3); names: S1, S2 … single strings, Y1-A / Y1-B the two strings of Y pair Y1 (v1.8.4); Y connectors wherever the panels allow (most pairs found by search, neighbouring strings cut to equal lengths, Y home run may stay 6 sq mm within the 3 % limit) (v1.8.5); 5 landscape rows the preference (4 only if 5 fits < 80 %), empty or all-shaded rows don’t count, row groups mirrored about the walkway so top and bottom strings face each other and Y-pair across it with both ends side by side (v1.8.6) | **done (v1.8.6)** |
| 5f | SLD: grid voltage, LT panel main breaker, fault level and the DG set (kVA, manual / ATS changeover, solar off on DG or a DG-PV controller) from the Design Lab's SLD form — drawn on the SLD and listed in the CEIG set | **done (v1.9)** |
| 3b | Panel placement: GI tables always portrait; Site questions → "Elevated structure" gives raised portrait tables of 3 + 2 rows with a walkway between, columns in line, above the parapet's shadow | **done (v1.10)** |

A job for a stage the Mac can't do yet simply **waits in the queue** and runs on its own once that phase is installed.

## One-time setup (about 15 minutes)

1. **Get the folder onto the Mac.** Install **GitHub Desktop** (free, desktop.github.com) and sign in.
   - File → Clone repository → `cyardi-nrg/nrg-report-service` → Clone.
   - At the top, switch the branch to `claude/3d-design-walkthrough-videos-pim15v`.
2. **Python:** nothing to install — the setup brings the worker its own private Python 3.12 (via Astral's free "uv").
3. **Have the keys ready.** Open Railway → the SolarConnect service → **Variables**. You will copy five values:
   `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_SERVICE_ACCOUNT_EMAIL`, `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY`,
   `GOOGLE_DRIVE_ROOT_FOLDER_ID` (and check `SUPABASE_URL` is the same as in the file).
4. **Run the setup.** Open **Terminal** and type (the path is where GitHub Desktop put it, usually `Documents/GitHub`):
   ```
   bash ~/Documents/GitHub/nrg-report-service/design-lab/worker/mac/install.sh
   ```
   - It installs what it needs inside that folder only.
   - It opens a settings file in TextEdit: paste the values, save, close TextEdit, press Return in Terminal.
   - It checks the connection (✓ Supabase, ✓ Google Drive, ✓ Heartbeat) and starts the worker.
5. **For AutoCAD DWG files** (DXF works without this): install the free **ODA File Converter** from
   opendesign.com/guestfiles/oda_file_converter (drag it into Applications). Or, if you use Homebrew: `brew install libredwg`.
6. **Nightly wake** (asks for your Mac password once):
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
