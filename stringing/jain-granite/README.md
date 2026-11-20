# Jain Granite & Marble — 100 kWp shed roof: stringing, layout drawings, CEIG set, BOM

Version: **v1 (2026-11-18)** · NRG Technologists

160 × Adani AB-G12R-132-625 TOPCon (625 Wp) · 1 × GoodWe GW80K-MT · roof slopes east and west (ridge north–south),
modules **landscape** (long side along the ridge) · 8 strings × 20 · inverter, DCDB and ACDB on the east wall at
ground level (north-east) · ladder at the south-west · earth pits EP-1 DC, EP-2 AC, EP-3 LA.

3D model and walk-around video: `3d-design/jain-granite/`.

## Deliverables (latest first)

| File | What it is |
|---|---|
| `ceig/Jain-Granite_L01_Panel-Layout-Wiring-Y_v2.pdf` | **Layout L-01:** panel layout + wiring with **Y-connectors** (S1+S3, S2+S4, S5+S7, S6+S8 joined in the gaps), mounting-set points (384 sets) and the ADANI label corner on every module, Detail A (Y-connection) and Detail B (panel placing) |
| `ceig/Jain-Granite_L02_Walkway-Layout_v1.pdf` | **Layout L-02:** walkways W1, W2, WC, WA1, WA2 (75.5 m, order 79 m) with the Y positions |
| `ceig/Jain-Granite_L03_Cable-Tray-Lengths-Y_v1.pdf` | **Layout L-03:** 50 × 50 tray (75.9 m), 6 sq mm home run per MPPT (≈ 336 m), 4 sq mm leads + jumpers, Y sets, MC4 count |
| `ceig/Jain-Granite_01_SLD_v7.pdf` … `06_Stringing-Layout_v7.pdf` | CEIG set (NRG format): SLD, equipment, earthing, walkway, cable tray, stringing — **no-Y design** (4 sq mm home run per string) |
| `ceig/Jain-Granite_BOM_Stringing-Tray-Walkway_v2.xlsx` | BOM for the **no-Y** design (still to be redone for Y) |
| `jain-granite-stringing-v11.png` | Stringing sketch, no-Y, with earthing |
| `jain-landscape-vs-portrait-v3.png` | Landscape (current) vs portrait: sets, joints, cable, cost at ₹85 / ₹167 sets |
| older `_v1` files | kept for reference |

## Rebuild

```bash
cd stringing/jain-granite/ceig
python3 generate_ceig_drawings.py     # CEIG sheets 01–06
python3 generate_layout_y.py          # L-01 / L-02 / L-03 (Y-connectors)
python3 build_bom.py                  # BOM (no-Y)
node render_pdf.js                    # HTML → A3 PDF
```

## To verify on site

Roof size 29.8 × 36 m and the gaps are scaled from the layout photo (marked `*`); module electricals scaled from
Adani's 620 W datasheet; Y-connectors must be rated ≥ 40 A and the same make as the module connectors.
