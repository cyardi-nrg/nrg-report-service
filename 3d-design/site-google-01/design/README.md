# Pluga Pumps & Motors — 300 kWp layout: 3 options (layout v6 · drawings v5 · 3D v7, 2026-11-01)

- `layout.py` (v6): calculates the panel fit for every roof and the 3 options, and writes `layout.json`. Runs in about 1 minute, mostly the shade check.
- `draw_layout.py` (v5): draws `../Pluga-Pumps_300kWp_Option-{1,2,3}_v5.png` and `../Pluga-Pumps_300kWp_Options-Compared_v5.png`.
- 3D: `../output/Site-Google-01_3D-Viewer_v7.html` (Option 1 / 2 / 3 buttons, or `?opt=N`). Stills are `..._<view>-optN_v7.png`.

## Owner brief (cumulative)

- **System:** 300 kW (480 × 625 Wp).
- **Equipment:** inverters at roof 1's south-east corner, with the transformer next to them.
- **Roofs not used:** 2, 4 and 6.
- **Roof 3 and roof 5:**
  - Roof 3 is a gable. Its south half and all of roof 5 form one south slope; its north half faces north (not used).
  - Skylights on roofs 3 and 5 are kept free: three strips running down the slope, read off the satellite image.
  - Turbo ventilators are kept clear, at their measured positions (they are **not** in one line).
- **New building:**
  - Turbovents removed; skylights (drawing R3) kept free.
  - Panels are placed upright or sideways, band by band, whichever fits more.
- **Shade:** panels in the new building's winter shadow are removed. Check: 21 Dec, 9 am – 3 pm solar time, every 30 min, all 4 corners of each panel.

## Capacity per roof (shade-checked)

Roof 1 south 112 · roof 1 north 392 · new building south 74 · new building north 171 · roof 3 south half + roof 5: 43.

## Options

| | Option 1 | Option 2 | Option 3 |
|---|---|---|---|
| Fill order | south-facing → new bldg north → roof 1 north | south-facing → roof 1 north | roof 1 S + N → new bldg S → roof 3/5 |
| Roof 1 south | 112 | 112 | 112 |
| New building south | 74 | 74 | — |
| Roof 3 S half + roof 5 | 43 | 43 | — |
| New building north | 171 | — | — |
| Roof 1 north | 80 | 251 | 368 |
| South / north kWp | 143.1 / 156.9 | 143.1 / 156.9 | 70.0 / 230.0 |
| Energy (kWh/yr, est.) | 439,818 | 439,818 | 435,050 |
| DC string cable (est.) | ≈ 5,160 m | ≈ 3,860 m | ≈ 3,640 m |
| Depends on the new building | yes (both roofs) | yes (south roof) | no |

Yield assumed: 1,500 kWh/kWp for south and 1,435 for north, both at a 1:10 roof slope. Cable estimate: each string's + and − run, measured along the eaves to the inverters.
