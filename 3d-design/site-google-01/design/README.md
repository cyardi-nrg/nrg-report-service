# Pluga Pumps & Motors — 300 kWp layout (design v3, 2026-10-31)

- `layout.py` (v3): computes the panel fit and writes `layout.json`, which feeds the drawing and the 3D (v5).
- `draw_layout.py` (v3): draws `../Pluga-Pumps_300kWp_Layout_v3.png`.

**Owner brief:**
- 300 kW total.
- South-facing roofs first; roof 1 north slope only for the balance.
- Inverters at roof 1's south-east corner, with the transformer next to them.
- Roofs 2, 4 and 6 are not used.
- Roofs 3 and 5 are single slopes; keep panels clear of their turbo ventilators.
- The new building's ventilators will be removed, so its full south roof can be used.

| Array | Modules | kWp | Faces |
|---|---|---|---|
| Roof 1 south (west of existing) | 112 | 70.0 | S |
| New building south roof (full) | 90 | 56.25 | S |
| Roof 3 (single slope, full, 6 vents clear) | 110 | 68.75 | S |
| Roof 5 (single slope, full, 3 vents clear) | 27 | 16.88 | S |
| Roof 1 north (balance, from the east end) | 141 | 88.13 | N |
| **Total** | **480** | **300.0** | |

**Assumed / to verify:**
- **Module:** 625 Wp, 2382 × 1134 mm, landscape, flush on the sheet.
- **Roof 3 heights:** 6.7–8 m.
- **Ventilator positions:** read from the satellite image.
- **Existing array:** about 90–95 kWp, estimated from the October bill's generation meter.
- **AC capacity:** the AC limit against the 225 kVA contract demand needs checking with MGVCL.

```bash
python3 design/layout.py && python3 design/draw_layout.py && node build.mjs && node render.mjs --stills
```
