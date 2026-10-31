# Site from a Google Maps screenshot (site-google-01): step 1, roofs identified

Version: **v3 (2026-10-31)** · NRG Technologists · client: **Pluga Pumps & Motors Pvt. Ltd., Savli** (from the drawings)

**v3 changes (owner corrections and the new building):**

- **Roof 1:** ridge is in the centre, with a narrow vent band.
- **Roof 3:** eave 8 m.
- **Roof 5:** only as wide as roof 3.
- **Roofs 2, 4 and 6: not for solar** (grey hatch).
- **New building** (under construction; the blue frame in the photos) added west of roofs 3 + 5. Taken from drawings `src/ref-master-layout-R8.pdf` (262711-AR-A-00-101 R8) and `src/ref-new-building-R3.pdf` (262711-AR-T-01-101 R3), plus photos `src/photo-new-building-*.jpg`:
  - 28.2 × 46 m PEB, east wall against roof 3, extending about 15 m north of roof 3.
  - **South roof:** 11.00 → 12.35 m, falling south.
  - **North roof:** about 10.4 → 7.50 m, falling north.
  - A wall light fills the step at ridge line E, 14.4 m from the south edge.
  - It stands taller than roof 3 (8 m) on that roof's west side, so **roofs 3 and 5 get afternoon shade.**
- `Site-Google-01_Roofs-Identified_v3.png` extends the canvas west to show the new building beyond the screenshot.

**v2 changes, from the owner's north-side photo (`src/photo-roof1-from-north.jpg`):**

- **Roof 1 ridge confirmed** as running E–W. The ridge carries half-round ridge ventilators plus turbo ventilators just below it; these replace the v1 louvred monitor. Adds a view from the north, like the photo.
- **Roof 6 confirmed** as a lean-to over the loading door, falling north. Heights from the photo: about 5.5 m low, about 6.3 m high.
- **Open question:** a blue steel frame stands above roof 1's ridge in the photo, with people on it. It isn't modelled yet.

Step 1 only: roofs and slopes identified, numbered 1–6, plus a 3D of the buildings. **No new panels yet.** The owner marks where panels should go next. Client name not given yet.

## Files

| File | What it is |
|---|---|
| `Site-Google-01_Roofs-Identified_v3.png` (v1 kept) | The satellite screenshot with roofs 1–6 outlined. Arrows point down the slope, the line is the ridge, and the existing solar is boxed. A legend gives sizes and slope type. |
| `Site-Google-01_Step1-Overview_v3.png` | The marked screenshot plus all 8 3D views on one sheet. |
| `output/Site-Google-01_3D-Viewer_v3.html` | Interactive 3D in a single file that works offline. Views: Aerial SE / NW, Top, South, West. **Roof numbers** shows or hides the coloured discs. |
| `output/stills/Site-Google-01_3D_NN-<view>_v3.png` | 10 still renders, including the view from the north and the new building. |
| `src/google-satellite.webp` | The owner's screenshot (north up). |
| `src/photo-roof1-from-north.jpg` | The owner's photo of roof 1 from the north side. |
| `src/roofs.json` | Roof outlines (px on the screenshot), type, ridge position and assumed heights. This is the single source for the drawing and the 3D. |

## How it was read

- **Scale:** the Google scale bar is 20 m = 215 px (measured in pixels), so 10.75 px/m.
- **Roof 1, main shed:** about 75 × 46 m. Gable roof with its ridge running E–W at about 26 m from the north edge, with a ridge vent; it slopes north and south.
  - **Existing solar:** on the south slope, about 3 groups × 3 rows. About 189 modules are drawn, which is an estimate from the image; **count to confirm**.
- **Roof 2, north-west shed:** about 21 × 17 m.
- **Roof 3, west shed:** about 20 × 27 m, with translucent sheets.
  - Roofs 2 and 3 are taken as gables with ridges running E–W. **Their slope direction needs confirming.**
- **Roof 4:** link lean-to between roofs 3 and 1, falling west.
- **Roof 5:** south-west lean-to, falling south.
- **Roof 6:** north lean-to along roof 1's north wall, falling north.

## Assumptions (in `src/roofs.json` and the site-data block of the template)

- **Eave heights:**
  - roof 1: 8 m
  - roofs 2 and 3: 6.5 m
  - lean-tos 4–6: 4.3–6 m
- **Roof slope:** 1:10.
- **Not represented:** walls, doors and surroundings are representative only. Small rooftop items can't be seen at this resolution (about 9 cm per pixel in the screenshot, but the image itself is softer than that).

## Rebuild

```bash
cd 3d-design/site-google-01
node build.mjs && node render.mjs --stills
```
