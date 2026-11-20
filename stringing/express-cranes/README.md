# Express Cranes — 75 kWp shed roof: string layout (landscape)

Version: **v1 (2026-11-20)** · NRG Technologists

120 × Adani 625 Wp on the **south shed** (gable, ridge east–west, 10° slopes, ≈ 12 m high), **landscape**
(long side along the ridge), 4 groups L1–L4 of 5 rows × 6 · **6 strings × 20**. Geometry from the 3D model
`3d-design/express-cranes/` v1 (owner's SolarEdge screenshot): shed 16.6 × 28.1 m; walkways in the L1|L2 and
L3|L4 gaps, along the ridge and down the west side; ladder on the west wall, south end.

## Deliverables (latest first)

| File | What it is |
|---|---|
| `Express-Cranes_Stringing-Landscape_v1.png` | String layout S1–S6 with + / − ends, column-turn jumpers (J), walkway crossings (X), ADANI label corner on every panel, string schedule |

## How the strings run

- 5 panels up the slope per column, joined side by side; each full string is 4 columns, so + and − both land
  on the walkway edge.
- **S1 (L1) and S3 (L2)** are mirror images across the L1|L2 walkway (+ opposite +, − opposite −); likewise
  **S4 (L3) and S6 (L4)** across the L3|L4 walkway — each pair can share an MPPT through a + Y and a − Y.
- Each group has 30 panels, so columns 5–6 of L1 + L2 make **S2** and of L3 + L4 make **S5**, each crossing its
  walkway once (cable under the grating). Their ends are at column 6, away from the other ends.
- North-face strings S1–S3 and south-face strings S4–S6 are never mixed on one MPPT.
- 16 column-turn jumpers (≈ 2.5 m each) and 2 walkway crossings (≈ 1.5 m), 4 sq mm.

## Still to confirm

Inverter make / model and position (for MPPT allocation, home runs, tray and BOM); panel datasheet (values
scaled from Adani's 620 W sheet).

```bash
cd stringing/express-cranes && python3 express_stringing.py
```
