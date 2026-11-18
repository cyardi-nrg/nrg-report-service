# Sangani Skyz — G+12, 48 flats: stringing per flat, DC and AC cable schedule

Version: **v1 (2026-11-18)** · NRG Technologists

192 × 545 Wp = 104.64 kWp, **4 panels per flat** (2.18 kWp, subsidy limit) · one string of 4 per flat into one
**Solaryaan 2 kW** single-phase inverter per flat · all 48 inverters inside the **staircase cabin** on the
terrace · AC down the staircase shaft to the meters **beside the staircase on the ground floor** (terrace ≈ 42 m up).

Panel layout from the approved 2D layout v1.2 (proposal v1.1, 545 Wp): blocks B1–B5 numbered from the south,
raised GI at 2 m (B1, B2), 3.5 m (B3, B4), 4 m (B5), 10° south. 3D v1.4, proposal v1.1 and the walk-around
video were made in the "3D design and walkthrough videos" session (not filed in `3d-design/` yet).

## Deliverables (latest first)

| File | What it is |
|---|---|
| `Sangani-Skyz_Stringing-Plan_v3.png` | All 48 strings (F01–F48) on the layout, + / − ends, per-flat DC and AC lengths |
| `Sangani-Skyz_Cable-Schedule_v3.xlsx` | Per flat: panels, DC + / − / jumper, ΔV, AC run, cabin sleeve, a column for the flat number; summary with order quantities and checks |
| `Sangani-Skyz_DC-Route-Samples_v3.png` | Routes drawn for F48, F18, F25, F21 with the length breakdown |
| `Sangani-Skyz_2D-layout_v1.2.jpg` | The approved layout the geometry is read from |
| `_v1`, `_v2` files | earlier versions (v1 straight-line routes; v2 west / east sleeves) |

## Totals (v3)

| Item | Net | Order |
|---|---|---|
| DC 2.5 sq mm Cu, red (+) | 824 m + 11 m jumpers | 880 m |
| DC 2.5 sq mm Cu, black (−) | 866 m + 11 m jumpers | 930 m |
| AC 2.5 sq mm Cu 2-core | 48 × 52 m = 2,496 m | 2,630 m |
| MC4 pairs | 54 | 60 |

## Owner decisions

- 45 flats are 2 × 2 squares (+ and − on the side facing the cabin); B5 north row uses 1 × 4 strings;
  3 flats span neighbouring blocks (F08: B5 → B4W, F24: B4W → B3W → B2, F17: B4E → B3E).
- DC routing: rafter → edge purlin → across onto the cabin / lift room wall → along the wall → sleeve.
  B1 cables hop onto B2. Cabin entry **only from the north, west or south** (24 S, 20 N, 4 W).
- DC and AC both **2.5 sq mm** (B1 flats F39–F41, F46–F48 have 3.1–3.5 % DC drop; AC ≈ 2.9 %).
- Flat numbers per string to be fixed on site (column in the schedule).

## Rebuild

```bash
cd stringing/sangani-skyz
python3 sangani_stringing.py              # plan + schedule
python3 sample_routes.py F48 F18 F25 F21  # route samples
```
Inputs (heights, sleeves, cable sizes) are at the top of `sangani_stringing.py` and `routes.py`;
geometry in `geom.py`.
