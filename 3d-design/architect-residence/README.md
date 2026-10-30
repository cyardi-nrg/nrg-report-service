# Architect's Residence (G+1) — 15-module rooftop solar: 3D model + views

Version: **3D v2 (2026-10-30)** · NRG Technologists

**v2 changes (owner: "reduce the number of legs; the ones on the lower terrace take on the wall and the parapet only"):**

- **Elevated array:** no legs on the lower terrace any more. Two E–W steel beams (front and back) carry the rafters. Each beam rests on a post on the west parapet (about 8–10 ft, knee-braced, X-braced north–south) and a short post on the terrace-room wall. That makes 4 support points, and the terrace floor under it is clear.
- **Terrace-room array:** cut from 18 legs to 6 (3 frames × front and back), carrying the same two-beam layout.
- v1 files stay in `output/` for reference.

Standalone deliverable. **No video yet** (owner: "do not make video right now"). Not wired into the SolarConnect app.

## Files

| File | What it is |
|---|---|
| `output/Architect-Residence_3D-Viewer_v2.html` | Interactive 3D model in a single file that works offline. Drag to rotate, scroll or pinch to zoom. Views: Aerial / Top / Elevated array / Terrace / Ground. **Structure** shows or hides the module frames. **▶ Walk-around** plays an in-viewer tour (no video file). |
| `output/stills/Architect-Residence_3D_NN-<view>_v2.png` | 11 still renders (1920×1080): 4 aerials, top view (labelled and clean), under the elevated array, on the open terrace, approach, south and east elevations. |
| `Architect-Residence_3D-Views-Overview_v2.png` | All 11 views on one sheet. |

## Inputs used

- **Owner's design screenshots:** a top view plus 4 oblique views from the owner's solar design tool. The layout is measured from the top view, taking north as up.
  - **Scale:** one module bay (1134 mm module + 20 mm gap) measures 69.5 px, which gives 60.2 px/m.
  - **Roof:** about 10.6 m (E–W) × 12.4 m (N–S).
  - **Terrace room:** about 6.1 × 4.9 m, in the south-east part of the roof.
  - **6 modules (2 rows × 3, portrait)** on an elevated structure over the main roof, south-west.
  - **9 modules (2 rows × 5, portrait)** on the terrace-room roof. One bay in the north row (2nd from west) is left open, as in the design.
  - **Both groups sit at the same level,** as in the obliques. That puts the elevated array about 3.4 m above the main roof. Since v2 it is carried from the parapet and the terrace-room wall.
- **Owner:** 2-storeyed residence of an architect.

## Assumptions to verify (all at the top of the site-data block in `src/viewer.template.html`)

1. **Main roof slab about 6.85 m** (G+1), with a 0.9 m (3 ft) parapet.
2. **Terrace room about 3.0 m** above the main roof.
3. **Module size and wattage:** assumed 2278 × 1134 mm. Wattage is not known yet, so the system kWp is not stated.
4. **Tilt 10°, facing south.** Module lower edge is 0.45 m above the terrace-room roof.
5. **House facade is a representative contemporary design** (stone feature wall, box window, timber louvres) and not the actual house. Garden and compound wall are representative too.
6. **No inverter or other services are shown.** Their positions aren't in the screenshots.

## Rebuild

```bash
cd 3d-design/architect-residence
node build.mjs                 # -> output/Architect-Residence_3D-Viewer_v2.html  (three.js + logo from ../jain-granite/src)
node render.mjs --stills       # stills
node render.mjs --video        # walk-around video (~40 min) — only when asked
```
