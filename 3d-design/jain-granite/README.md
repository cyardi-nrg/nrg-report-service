# Jain Granite & Marble — 100 kWp rooftop: 3D views + walk-around video

Version: **v1 (2026-10-28)** · NRG Technologists

Standalone deliverable. **Not wired into the SolarConnect app yet**; that is a later step.

## What is in `output/`

| File | What it is |
|---|---|
| `Jain-Granite_3D-Viewer_v1.html` | Interactive 3D model in a single file that works offline. Open it in Chrome/Edge/Safari on a laptop or phone. Drag to rotate, scroll or pinch to zoom, right-drag or two fingers to pan. The view buttons are Aerial / Top / West / East / Walkway / Inverter / Ground. **▶ Walk-around** plays the guided tour. |
| `Jain-Granite_Walkaround_1080p_v1.mp4` | 58 s walk-around video (H.264, 1920×1080, plays on WhatsApp). Sequence: aerial establishing shot, 360° orbit, top view (north up, matches the layout photo), walk along the rooftop walkway, inverter / ACDB / earth pits, closing aerial. |
| `stills/Jain-Granite_3D_0X-<view>_v1.png` | 8 still renders (1920×1080) for the proposal / WhatsApp. |

## Inputs used

- **Client layout photo** (top = north): 4 blocks, 2 on each slope, each 5 × 8 modules in portrait. 160 modules in total.
- **Owner:** 100 kWp from 160 × 625 Wp panels. Warehouse height 8 m. Roof slopes east and west (ridge runs north–south).
- **CEIG drawing set v6** (branch `claude/solar-electrical-design-stringing-jqozkz`, `stringing/ceig/generate_ceig_drawings.py`). These positions come from that set:
  - Block positions, module size 2382 × 1134 mm, roof 29.8 × 36 m, ridge at 14.8 m.
  - Walkways W1 / W2 / WC / WA1 / WA2 (300 mm) and cable trays T1–T4.
  - ESE lightning arrester on a 5 m mast at the north end of the ridge.
  - Inverter (GoodWe GW80K-MT) with DCDB and ACDB on the east wall at ground level, plus 3 earth pits.
  - Roof ladder at the south-west corner.

## Assumptions to verify on site (all editable at the top of `src/viewer.template.html`)

1. **8 m is taken as the eave height.** The roof slope is assumed to be 1:10 (standard PEB), so the ridge comes out at about 9.5 m.
2. **Roof size (29.8 × 36 m) is scaled from the layout image, not measured.** It is the same estimate the CEIG sheets mark with `*`.
3. **Modules are flush-mounted** on short rails about 120 mm above the sheet, at the roof's own slope.
4. **Surroundings are representative, not surveyed:** rolling shutters, louvres, the compound wall, trees and the paved yard.
5. **Inverter location** is taken from the CEIG equipment layout. The earth pits are placed about 1.6 m off the east wall.

## Rebuild after changing anything

```bash
cd 3d-design/jain-granite
node build.mjs                    # -> output/Jain-Granite_3D-Viewer_v1.html (three.js r158 inlined)
node render.mjs                   # -> stills + 1080p MP4  (Playwright Chromium + ffmpeg)
node render.mjs --stills          # stills only
node render.mjs --video --size 1280x720   # smaller video
node render.mjs --only 12,36      # quick test frames at those seconds
```

Increase `VERSION` in `build.mjs`, `render.mjs` and the template together when you issue a new set.

## Files

- `src/viewer.template.html`: the model, materials, camera path, captions, viewer UI (v1)
- `src/vendor/three-r158.min.js`: three.js (MIT, see `three-LICENSE.txt`)
- `build.mjs`: inlines three.js into the template and writes the viewer
- `render.mjs`: renders the stills and video from the viewer in headless Chromium and pipes the frames to ffmpeg
