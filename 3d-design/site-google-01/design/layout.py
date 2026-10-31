# Version: v5 (2026-10-31) — 300 kWp panel layout for Pluga Pumps & Motors, Savli (site-google-01).
# Owner brief: 300 kW; south-facing roofs first, then roof 1 north if required; inverter at the south-east
# (right-hand, south) corner of roof 1 with the transformer next to it. Roofs 2, 4, 6 not for solar.
# Coordinates: px on src/google-satellite.webp (north up), 10.75 px/m (scale bar). Output: design/layout.json
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = 10.75
MOD_WP, MOD_L, MOD_W, GAP = 625, 2.382, 1.134, 0.02        # ASSUMED module: 625 Wp TOPCon, landscape (long side E-W)
TARGET = 480                                              # 300 kWp / 625 Wp
BLOCK_C, BLOCK_R, WALK = 7, 4, 0.8                        # blocks of 7 x 4 modules, 0.8 m walkways
EDGE, RIDGE_CLR = 1.0, 2.6                                # clear of eaves / gables; clear of ridge vents + turbo vents

def m(px): return px / S

def grid(x0, x1, y0, y1, slope, from_top=True):
    """Modules in blocks inside the plan rect (metres). Rows run E-W; from_top fills from y0 (north) down."""
    dp = MOD_W * math.cos(slope)                          # plan depth of one landscape module on the slope
    cols, x = [], x0
    while True:                                           # column x-centres
        n = 0
        while n < BLOCK_C and x + MOD_L <= x1 + 1e-6: cols.append(x + MOD_L / 2); x += MOD_L + GAP; n += 1
        if n < BLOCK_C or x + WALK + MOD_L > x1: break
        x += WALK - GAP
    rows, y = [], y0
    while True:
        n = 0
        while n < BLOCK_R and y + dp <= y1 + 1e-6: rows.append(y + dp / 2); y += dp + GAP; n += 1
        if n < BLOCK_R or y + WALK + dp > y1: break
        y += WALK - GAP
    sx = (x1 - x0 - ((cols[-1] + MOD_L / 2) - x0)) / 2 if cols else 0   # centre the grid in the free width
    sy = 0 if from_top else (y1 - y0 - ((rows[-1] + dp / 2) - y0))
    return [(cx + sx, cy + sy) for cy in rows for cx in cols], dp

def hits(mx, my, dp, rects):
    return any(mx + MOD_L / 2 > r[0] and mx - MOD_L / 2 < r[1] and my + dp / 2 > r[2] and my - dp / 2 < r[3] for r in rects)

roofs = {r['id']: r for r in json.load(open(os.path.join(HERE, '..', 'src', 'roofs.json')))['roofs']}
ex = json.load(open(os.path.join(HERE, '..', 'src', 'roofs.json')))['existing_solar']
a1 = math.atan(0.1 * 22.8 / 22.8)                        # roof 1 slope 1:10 both sides (ridge centred)
out = []

# --- roof 1 south slope (south-facing): only the clear part west of the existing array, with a 1 m access gap to it
R1 = roofs[1]; ry = m(R1['ridge_y'])
pts, dp = grid(m(R1['x'][0]) + EDGE, m(ex['groups_x'][0][0]) - 1.0, ry + RIDGE_CLR, m(R1['y'][1]) - EDGE, a1)
r1s = pts
out.append({'roof': '1S', 'name': 'Roof 1 · south slope', 'faces': 'S', 'tilt_deg': round(math.degrees(a1), 1), 'mods': r1s, 'dp': dp,
            'note': 'West of the existing array only, 1 m access path kept beside it.'})

# --- new building south roof (south-facing, tallest, unshaded): FULL roof — owner: the ventilators will be removed
NB = roofs[7]; nx0, ny0 = m(NB['x'][0]), m(NB['y'][0])          # west edge, ridge/step line E (drawing R3 roof plan)
anb = math.atan(0.1)
pts, dpn = grid(nx0 + EDGE, m(NB['x'][1]) - EDGE, ny0 + EDGE, m(NB['y'][1]) - EDGE, anb)
# skylights (polycarbonate 1 m x 3 m, drawing R3 roof plan) stay — only the turbovents between them go (owner). Keep 0.3 m clear.
SKY = []
for c in (3.73, 9.15, 15.2, 22.7):                             # column centres from the west edge (m)
    for r0, r1 in ((0.5, 3.4), (9.66, 12.7)):                  # rows south of ridge line E (m)
        SKY.append((nx0 + c - 0.5, nx0 + c + 0.5, ny0 + r0, ny0 + r1))
skyk = [(r[0] - 0.3, r[1] + 0.3, r[2] - 0.3, r[3] + 0.3) for r in SKY]
nbs = [p for p in pts if not hits(p[0], p[1], dpn, skyk)]
out.append({'roof': '7S', 'name': 'New building · south roof', 'faces': 'S', 'tilt_deg': round(math.degrees(anb), 1), 'mods': nbs, 'dp': dpn,
            'note': 'Full roof except the polycarbonate skylights (kept free, owner); turbovents removed (owner). PEB under construction: ask the PEB vendor now to design purlins for the module load (~15 kg/m2).'})

# --- roofs 3 and 5: single slope falling south (owner) — full roofs, kept clear of their turbo ventilators (owner)
VENTS = [(208, 462), (272, 462), (340, 462), (203, 593), (273, 592), (342, 592), (230, 708), (273, 707), (340, 703)]   # px, from the screenshot
VCLR = 0.9                                                    # keep-out radius around each ventilator (m)
vrect = [(m(x) - VCLR, m(x) + VCLR, m(y) - VCLR, m(y) + VCLR) for x, y in VENTS]
R3N, R35 = roofs[3], roofs[5]                                  # v4: roof 3 north half (faces N) / roof 3 south half + roof 5 (one S slope)
a3n = math.atan((R3N['high'] - R3N['low']) / m(R3N['y'][1] - R3N['y'][0])); a35 = math.atan((R35['high'] - R35['low']) / m(R35['y'][1] - R35['y'][0]))
pts, dp35 = grid(m(R35['x'][0]) + EDGE, m(R35['x'][1]) - EDGE, m(R35['y'][0]) + EDGE, m(R35['y'][1]) - 0.6, a35)
out.append({'roof': '35S', 'name': 'Roof 3 south half + roof 5', 'faces': 'S', 'tilt_deg': round(math.degrees(a35), 1), 'dp': dp35,
            'mods': [p for p in pts if not hits(p[0], p[1], dp35, vrect)],
            'note': 'One slope from roof 3\'s ridge to roof 5\'s south edge (owner); 6 turbo ventilators kept clear. West part: late-afternoon shade from the new building.'})
pts3n, dp3n = grid(m(R3N['x'][0]) + EDGE, m(R3N['x'][1]) - EDGE, m(R3N['y'][0]) + EDGE, m(R3N['y'][1]) - EDGE, a3n, from_top=False)
roof3n_capacity = len([p for p in pts3n if not hits(p[0], p[1], dp3n, vrect)])     # north-facing: reserve only (owner order: roof 1 north for the balance)
vents_out = VENTS

# --- roof 1 north slope, only for the balance, filled from the east end (nearest the inverter)
need = TARGET - sum(len(o['mods']) for o in out)
pts, dpN = grid(m(R1['x'][0]) + EDGE, m(R1['x'][1]) - EDGE, m(R1['y'][0]) + EDGE, ry - RIDGE_CLR, a1, from_top=False)
pts.sort(key=lambda p: (-p[0], p[1]))                         # east first, then north->south within a column
r1n = sorted(pts[:max(0, need)], key=lambda p: (p[1], p[0]))
out.append({'roof': '1N', 'name': 'Roof 1 · north slope (balance)', 'faces': 'N', 'tilt_deg': round(math.degrees(a1), 1), 'mods': r1n, 'dp': dpN,
            'capacity_left': len(pts) - len(r1n)})

total = sum(len(o['mods']) for o in out)
summary = {'_note': 'Version v5 (2026-10-31). Generated by design/layout.py — do not edit by hand.',
           'module': {'wp': MOD_WP, 'L': MOD_L, 'W': MOD_W, 'orientation': 'landscape (long side E-W)', 'assumed': True},
           'rules': {'edge_m': EDGE, 'ridge_clear_m': RIDGE_CLR, 'block': [BLOCK_C, BLOCK_R], 'walkway_m': WALK},
           'target_modules': TARGET, 'total_modules': total, 'kwp': round(total * MOD_WP / 1000, 2),
           'skylights_px': [[round(v * S, 1) for v in r] for r in SKY], 'vents_px': vents_out, 'reserve_roof3_north_modules': roof3n_capacity,
           'inverter': {'px': [1236, 652], 'note': 'east wall of roof 1, south corner (owner)'},
           'transformer': {'px': [1262, 668], 'note': 'next to the inverter (owner)'},
           'arrays': [{'roof': o['roof'], 'name': o['name'], 'faces': o['faces'], 'tilt_deg': o['tilt_deg'], 'modules': len(o['mods']),
                       'kwp': round(len(o['mods']) * MOD_WP / 1000, 2), 'dp': o['dp'], 'note': o.get('note', ''),
                       **({'north_capacity_left': o['capacity_left']} if 'capacity_left' in o else {}),
                       'mods_px': [[round(x * S, 1), round(y * S, 1)] for x, y in o['mods']]} for o in out]}
json.dump(summary, open(os.path.join(HERE, 'layout.json'), 'w'), indent=1)
for a in summary['arrays']: print(f"{a['roof']:3} {a['name']:34} {a['modules']:4} modules  {a['kwp']:7.2f} kWp" + (f"   (north slope room left: {a['north_capacity_left']})" if 'north_capacity_left' in a else ''))
print('Roof 3 north half (faces N) — reserve, not used:', roof3n_capacity, 'modules')
print(f"TOTAL {total} modules = {summary['kwp']} kWp  (target {TARGET})")
