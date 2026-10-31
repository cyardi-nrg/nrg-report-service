# Pluga Pumps & Motors — 300 kWp layout (design v5 / drawing v4 / 3D v6, 2026-10-31)

- `layout.py` (v5): computes the panel fit and writes `layout.json`, which feeds the drawing and the 3D (v6).
- `draw_layout.py` (v4): draws `../Pluga-Pumps_300kWp_Layout_v4.png`.

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
| New building south roof (skylights kept free, turbovents removed) | 54 | 33.75 | S |
| Roof 3 south half + roof 5 (one slope, 9 vents clear) | 88 | 55.0 | S |
| Roof 1 north (balance, from the east end) | 226 | 141.25 | N |
| **Total** | **480** | **300.0** | |

Owner corrections:
- **Roof 3 is a gable.** Its south half and all of roof 5 form one south slope. Its north half faces north and is not used (reserve of about 48 modules).
- **New building:** skylights kept free.

**Assumed / to verify:**
- **Module:** 625 Wp, 2382 × 1134 mm, landscape, flush on the sheet.
- **Roof 3 heights:** ridge 8 m, north eave about 6.65 m, roof 5 south edge about 5.86 m (1:10 slope).
- **Skylight positions:** from drawing R3; the 7 × 4 block grid loses some modules around them.
- **Ventilator positions:** read from the satellite image.
- **Existing array:** about 90–95 kWp, estimated from the October bill's generation meter.
- **AC capacity:** the AC limit against the 225 kVA contract demand needs checking with MGVCL.

```bash
python3 design/layout.py && python3 design/draw_layout.py && node build.mjs && node render.mjs --stills
```
