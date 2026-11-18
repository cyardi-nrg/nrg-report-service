# Design Lab: plan

Version: **v1 (2026-11-01)** · NRG Technologists · status: **plan for owner approval, nothing built yet**

## What it is

The Design Lab is one end-to-end solar design flow inside NRG SolarConnect, **visible only to the owner**. It brings together four pieces of work that exist today as separate tools:

| Today | Where | What it does now |
|---|---|---|
| 3D design | `3d-design/` (this branch) | Roof identification, panel layout options, shade check, 3D viewer, stills, walk-around video |
| Electrical design + stringing | `stringing/` (merged from `claude/solar-electrical-design-stringing-jqozkz`) | Stringing plans, CEIG set (SLD, equipment, earthing, walkway, cable tray, stringing), L-01/02/03 layouts, BOM (xlsx), portrait vs landscape costing |
| Structure design | **not in this repo yet; location to be confirmed by the owner** | |
| Bill analysis | done by hand for Pluga Pumps | Sizing from the electricity bill |

**The key problem:** each tool is written around one site's numbers (Jain Granite's are hard-coded in `generate_ceig_drawings.py`). The Design Lab replaces this with one **project file** per site that every stage reads and adds to. Pluga Pumps already works this way for its first stages: `roofs.json` → `layout.json` → drawings + 3D.

## The flow (owner's order)

Each stage ends with an **approval gate**. The owner approves, or asks for changes, before the next stage starts. Every output is versioned (v1, v2, …).

| # | Stage | Owner gives | Design Lab produces | Exists today? |
|---|---|---|---|---|
| 1 | **Project + site** | Google Maps screenshot (satellite, north up, scale bar visible) and site photos. Marks the **inverter, meter and transformer** positions on the screenshot. | Scale from the scale bar; marked site plan | Partly: Pluga (scale, inverter/transformer marked by hand) |
| 2 | **Questionnaire** (asked automatically when a screenshot is uploaded) | Residential / commercial / industrial; building height or floors; roof type per roof (flat RCC / sloping sheet / mixed); parapet height; staircase cabin, water tank and lift room heights; roofs not to use; existing solar; electricity bill (PDF) | A complete project file, with nothing assumed silently | Asked ad hoc in chat today |
| 3 | **Sizing from the bill** | The bill | Consumption (grid + existing solar), tariff and settlement rules (e.g. HT monthly settlement, ₹1.99 surplus, ₹1.50 banking), contract-demand limit, **recommended kWp**, savings | Pluga, by hand |
| 4 | **Roof design** | Confirms or corrects the roof outlines, slopes, ridges, heights, ventilators and skylights | Numbered roofs with slope arrows. Setbacks from edges and ridges. Obstacles (ventilators, skylights, cabins, tanks) kept clear. **Shade check** (21 Dec, 9 am – 3 pm) from cabins, tanks, parapets and neighbouring buildings. A **usable-area map**. 3D of the buildings. | Pluga: roofs, obstacles, shade check, 3D |
| 5 | **Panel placement** | Module (W, size), fill order or options | Layout options (upright or sideways per band, walkways, priorities), kWp, yield, cable estimate, comparison sheet | Pluga: 3 options |
| 6 | **Structure** | Mounting type (flush rails / elevated, leg heights / wall-parapet supported) | Structure layout and member quantities | Sejal Parikh / architect residence (3D only); structure design tool to be brought in |
| 7 | **Stringing + BOM** | Inverter choice (or picks from a suggested list) | Strings / MPPT, Y-connectors or home runs, tray route and lengths, earthing, LA, **BOM** (DC cable, MC4, tray, walkway, structure) | Jain only (hard-coded) |
| 8 | **3D views + video** | Approves views | Interactive 3D, stills, walk-around video, WhatsApp copy | Yes, general enough to reuse |
| 9 | **SLD + CEIG set** | | SLD, equipment, earthing, walkway, cable tray, stringing sheets (PDF) | Jain only (hard-coded) |

## How it is built

- **Project file** (`project.json`): one per site, the single source of truth.
  - Site: screenshot, scale, marks.
  - Questionnaire answers and bill.
  - Roofs and obstacles, with heights.
  - Layout, structure, strings, BOM, and the version of each stage.
  - Every drawing, the BOM and the 3D are generated from it, so they always agree. (This is what the Jain tools already do internally: the BOM and the drawings share one geometry.)
- **Design engine** (`design-lab/engine/`): the existing tools, generalised to read the project file.
  - Python: geometry, shade check, panel packing, stringing, BOM, drawings, SLD.
  - Node: 3D viewer, stills, video.
- **In the app** (`/design-lab`, owner only):
  - Access through the existing `employees.is_owner` flag.
  - Screens:
    - project list
    - screenshot upload and marking (inverter, meter, transformer, roofs, ventilators, skylights)
    - questionnaire
    - one screen per stage, with **Approve / Request changes**
  - Supabase tables: `design_projects` and `design_stage_versions` (stage, version, project JSON, file IDs).
  - Files go into the project's Drive folder (*Engineering Drawings*).
  - A design can be linked to a SolarConnect project, quote or lead.
- **Heavy work runs outside the web app.** The shade check (about 1 minute), PDF drawings and video rendering (headless Chromium + ffmpeg) can't run in normal Next.js serverless functions. The plan is a small **design worker** service, like NRG's existing Railway microservices, that the app calls. Results go to Supabase and Drive.
- **AI assist** (later, optional):
  - Read the bill PDF automatically, using the app's existing extraction pipeline.
  - Suggest roof outlines, ventilators and skylights from the screenshot, for the owner to correct. The Pluga work showed these always need owner confirmation; for example, the ventilator positions had to be corrected.

## Phasing

| Phase | Where | Work |
|---|---|---|
| **A: one engine, in this repo** | `design-lab/` | 1. Merge the stringing work (**done**) and the structure design (once located). 2. Define the `project.json` schema. 3. Generalise the 3D, packing and shade tools (from Pluga) and the stringing, BOM and CEIG tools (from Jain) to read it. 4. Run one real project end to end: **Pluga Pumps** (stages 1–5 done; continue with the chosen option → structure → stringing + BOM → 3D → SLD). 5. Re-run **Jain Granite** through the engine and check it reproduces the existing CEIG set. |
| **B: app integration** | live SolarConnect app | `/design-lab` screens, the owner-only gate, Supabase tables, Drive storage, the design worker. **Needs the live app code** (the `app/` folder in this repo is an early skeleton; see below). |
| **C: AI assist** | app + worker | Bill auto-read; roof, ventilator and skylight suggestions. |

## Open questions for the owner

1. **Structure design:** where is it? Another branch, another chat or session, or files you have?
2. **Live app code:** this repo's `app/` has only Documents and Login. Which repository or branch has the current SolarConnect code (projects, quotes, BOM, etc.)? Phase B needs it.
3. **Design worker:** OK to run the heavy work as a separate small service (Railway, like the existing microservices)?
4. **Pilot:** use **Pluga Pumps** as the first end-to-end project once the client picks an option, and **Jain Granite** as the check against existing drawings?
