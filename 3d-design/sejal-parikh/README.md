# Mrs. Sejal Parikh Residence — 42.48 kWp terrace solar: layout revision + 3D

Version: **3D v1 · layout revision v2 (2026-10-29)** · NRG Technologists

Standalone deliverable. **Not wired into the SolarConnect app yet.**

## Layout revision (2D)

| File | What it is |
|---|---|
| `Sejal-Parikh_Layout-Revision_v2.png` | **Current.** Before/after on the client drawing. The 4 leftmost modules of row 4 (next to the fresh-air unit, its 2250 CFM duct and the HVAC cut-out) are removed. 1 module is added at the east end of rows 2, 3, 4 and 5. **Total stays 59 × 720 Wp = 42.48 kWp.** Rows: 11, 13, 13, 6, 10, 6. |
| `Sejal-Parikh_Layout-Revision_v2_detail.png` | Large annotated "after" drawing. |
| `Sejal-Parikh_Layout-Revision_v1*.png` | Superseded (3 removed + 4 added = 60). Kept for reference. |

## 3D (in `output/`)

| File | What it is |
|---|---|
| `Sejal-Parikh_3D-Viewer_v1.html` | Interactive 3D model in a single file that works offline. Drag to rotate, scroll or pinch to zoom. Views: Aerial / Top / Structure / Terrace / Fresh-air unit / Ground. **▶ Walk-around** plays the tour. **AC & services** shows or hides the equipment. |
| `Sejal-Parikh_Walkaround_1080p_v1.mp4` | 52 s walk-around. Sequence: aerial, 360° orbit, top view (north up), down between rows 3 and 4 to show the 4 ft front legs, fresh-air-unit area, closing aerial. |
| `Sejal-Parikh_Walkaround_720p-WhatsApp_v1.mp4` | Same video at 720p, for WhatsApp. |
| `stills/Sejal-Parikh_3D_0X-<view>_v1.png` | 7 still renders (1920×1080). |

## Inputs used

- **Client drawing** "MRS. SEJAL PARIKH RESIDENCE WITH 59 NO OF 720 W SOLAR PANELS" (single A4 PDF), turned 90° so north is up.
  - Scale comes from its 13'-6" dimension: 301 px = 4.115 m. A panel cell then measures 1.31 m, which matches a 1303 mm module.
  - The terrace outline, the 6 rows and the equipment positions are measured from it.
- **Owner:**
  - north is at the top
  - ground + 1 floor
  - elevated structure
  - parapet 4 ft (1.22 m)
  - front leg 4 ft (1.22 m)
  - delete 4 modules near the blower and add one at the right of the 4 rows (see the revision above)

## Assumptions to verify (all at the top of the site-data block in `src/viewer.template.html`)

1. **Terrace level about 7.0 m:** 0.6 m plinth plus 2 floors of 3.2 m.
2. **Tilt 15°, facing south.** With the 4 ft front leg, the back leg comes out at about 1.68 m (about 5.5 ft). The rafter, 2 purlins per row, a brace per frame, and 300 × 300 mm pedestals are all representative.
3. **Module size 2384 × 1303 × 35 mm** (a typical 720 Wp module).
4. **Equipment heights are typical, not surveyed.** That covers the VRF units, the split-AC outdoor units, the heat pumps, the fresh-air unit and its shed.
5. **The house facade, windows, garden and compound wall are representative.** The drawing shows only the terrace.
6. **No inverter is shown.** Its location isn't on the drawing.

## Rebuild

```bash
cd 3d-design/sejal-parikh
node build.mjs                 # -> output/Sejal-Parikh_3D-Viewer_v1.html  (three.js + logo from ../jain-granite/src)
node render.mjs --stills       # stills
node render.mjs --video        # 1080p video (~45 min on this cloud machine)
node render.mjs --only 12,35   # quick test frames
```

The viewer framework (controls, camera path, overlay, capture) is shared with `../jain-granite`. Only the site-data, scene, views, camera-path and caption blocks are specific to this site.
