# Version: v6 (2026-11-01) — 300 kWp panel layout, 3 options, for Pluga Pumps & Motors, Savli (site-google-01).
# Owner brief (cumulative):
#   300 kW · inverters at roof 1's south-east corner, transformer next to them · roofs 2, 4, 6 not used
#   roof 3 = gable: its south half + all of roof 5 = one south slope; roof 3 north half faces north
#   roofs 3 + 5: skylight strips and turbo ventilators kept clear (vents NOT in one line — owner, after close-up)
#   new building: turbovents removed, skylights kept free; upright (portrait) panels where they fit more
#   remove panels shaded by the new building (checked: 21 Dec, 9 am - 3 pm solar time, Vadodara 22.4 N)
#   Option 1: south-facing roofs -> new building north roof -> roof 1 north
#   Option 2: south-facing roofs -> roof 1 north (closer to the inverters)
#   Option 3: roof 1 south + roof 1 north first -> new building south -> roof 3 south half + roof 5
# Coordinates: px on src/google-satellite.webp (north up), 10.75 px/m. Output: design/layout.json
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
S = 10.75
MOD_WP, MOD_L, MOD_W, GAP = 625, 2.382, 1.134, 0.02        # ASSUMED module: 625 Wp TOPCon
TARGET = 480                                              # 300 kWp / 625 Wp = 24 strings x 20
EDGE, RIDGE_CLR = 1.0, 2.6
YIELD = {'S': 1500, 'N': 1435}                            # kWh/kWp/yr at a 1:10 roof slope, Vadodara (N about -4.5 %)
def m(px): return px / S

J = json.load(open(os.path.join(HERE, '..', 'src', 'roofs.json')))
roofs = {r['id']: r for r in J['roofs']}
EX = J['existing_solar']
INV = (1236, 652)                                          # inverters (px), roof 1 south-east corner (owner)

# ---------------------------------------------------------------- heights (heightfield of every roof, for the shade check)
def roof_h(r, x, y):
    x0, x1, y0, y1 = m(r['x'][0]), m(r['x'][1]), m(r['y'][0]), m(r['y'][1])
    if not (x0 <= x <= x1 and y0 <= y <= y1): return None
    if r['type'] == 'gable':
        yr = m(r['ridge_y']); ridge = r['eave'] + r.get('slope', 0.1) * ((yr - y0) + (y1 - yr)) / 2
        return ridge - abs(y - yr) * (ridge - r['eave']) / ((yr - y0) if y < yr else (y1 - yr))
    hi, lo = r['high'], r['low']
    f = {'S': (y - y0) / (y1 - y0), 'N': (y1 - y) / (y1 - y0), 'W': (x1 - x) / (x1 - x0), 'E': (x - x0) / (x1 - x0)}[r['down']]
    return hi - f * (hi - lo)
def H(x, y):
    hs = [h for h in (roof_h(r, x, y) for r in J['roofs']) if h is not None]
    return max(hs) if hs else 0.0

# ---------------------------------------------------------------- sun (21 Dec, 9:00-15:00 solar time)
LAT, DEC = math.radians(22.4), math.radians(-23.44)
SUN = []
for k in range(0, 13):
    h = math.radians(15 * (9 + 0.5 * k - 12))
    el = math.asin(math.sin(LAT) * math.sin(DEC) + math.cos(LAT) * math.cos(DEC) * math.cos(h))
    ca = (math.sin(DEC) - math.sin(el) * math.sin(LAT)) / (math.cos(el) * math.cos(LAT))
    az = math.acos(max(-1, min(1, ca))); az = az if h < 0 else 2 * math.pi - az
    SUN.append((math.sin(az), -math.cos(az), math.tan(el)))      # east, south (plan y), rise per metre
def shaded(x, y, z):
    for dx, dy, t in SUN:
        s = 0.3
        while s < 70:
            if H(x + dx * s, y + dy * s) > z + s * t + 0.02: return True
            s += 0.3
    return False

# ---------------------------------------------------------------- packing
def pack(x0, x1, y0, y1, slope, orient, strips=(), obs=(), rows_grp=4, walk=0.8, cols_grp=7, walk_c=0.8, from_top=True):
    w = MOD_L if orient == 'L' else MOD_W                  # plan width (E-W)
    d = (MOD_W if orient == 'L' else MOD_L) * math.cos(slope)   # plan depth (N-S)
    ivs = [(x0, x1)]
    for a, b in sorted(strips):                            # full-height exclusions split the width
        nv = []
        for p, q in ivs:
            if b <= p or a >= q: nv.append((p, q)); continue
            if a > p: nv.append((p, a))
            if b < q: nv.append((b, q))
        ivs = nv
    cols = []
    for p, q in ivs:
        xs, x, n = [], p, 0
        while x + w <= q + 1e-6:
            xs.append(x + w / 2); x += w + GAP; n += 1
            if cols_grp and n % cols_grp == 0: x += walk_c - GAP
        if xs: off = (q - (xs[-1] + w / 2)) / 2; cols += [c + off for c in xs]
    rows, y, n = [], y0, 0
    while y + d <= y1 + 1e-6:
        rows.append(y + d / 2); y += d + GAP; n += 1
        if rows_grp and n % rows_grp == 0: y += walk - GAP
    if not from_top and rows: rows = [r + (y1 - (rows[-1] + d / 2)) for r in rows]
    out = [(c, r) for r in rows for c in cols
           if not any(c + w / 2 > o[0] and c - w / 2 < o[1] and r + d / 2 > o[2] and r - d / 2 < o[3] for o in obs)]
    return out, w, d

def wd(o, slope): return (MOD_L, MOD_W * math.cos(slope)) if o == 'L' else (MOD_W, MOD_L * math.cos(slope))

def unshaded(mods, slope, roof_id, lift=0.15):
    """mods: [(x, y, orient)]; keeps those with no corner shaded on 21 Dec 9-15 h."""
    r = roofs[roof_id]; keep = []
    cl = lambda v, a, b: min(max(v, a), b)
    for cx, cy, o in mods:
        w, d = wd(o, slope)
        pts = [(cx, cy)] + [(cx + sx * w / 2, cy + sy * d / 2) for sx in (-1, 1) for sy in (-1, 1)]
        if not any(shaded(x, y, roof_h(r, cl(x, m(r['x'][0]), m(r['x'][1])), cl(y, m(r['y'][0]), m(r['y'][1]))) + lift) for x, y in pts):
            keep.append((cx, cy, o))
    return keep

# ---------------------------------------------------------------- obstacles
# roofs 3 + 5: turbo ventilators at their measured positions on the satellite image (owner: not in one line)
VENTS = [(208, 462), (272, 462), (340, 462), (203, 593), (273, 592), (342, 592), (230, 708), (273, 707), (340, 703)]
SKYCOL = (191, 257, 328)                                  # skylight strip centres (px), 1.0 m wide — read off the satellite image
vrect = [(m(x) - 0.9, m(x) + 0.9, m(y) - 0.9, m(y) + 0.9) for x, y in VENTS]
strips35 = [(m(c) - 0.5 - 0.3, m(c) + 0.5 + 0.3) for c in SKYCOL]
# new building skylights (drawing 262711-AR-T-01-101 R3 roof plan), metres from its west edge / from ridge line E
NBX0, NBE = m(roofs[7]['x'][0]), m(roofs[7]['y'][0])
NBCOLS = (3.69, 9.10, 15.2, 22.7)
SKY7 = [(NBX0 + c - 0.5, NBX0 + c + 0.5, NBE + a, NBE + b) for c in NBCOLS for a, b in ((0.44, 3.45), (9.6, 12.6))]
SKY8 = [(NBX0 + c - 0.5, NBX0 + c + 0.5, NBE - b, NBE - a) for a, b in ((4.57, 7.44), (12.35, 15.4), (19.5, 22.3)) for c in NBCOLS] + \
       [(NBX0 + c - 0.5, NBX0 + c + 0.5, NBE - 27.7, NBE - 24.7) for c in (15.2, 22.7)]
def grow(rs, k=0.3): return [(a - k, b + k, c - k, e + k) for a, b, c, e in rs]

def pack_banded(x0, x1, y0, y1, slope, obs, rows_grp_p=2, rows_grp_l=4, walk=0.6):
    """Split the roof into N-S bands where the obstacle set is constant; in each band use whichever of landscape /
    portrait fits more, packing between the obstacles (as full-height strips within the band). Bands abut."""
    ys = sorted({y0, y1} | {v for o in obs for v in (o[2], o[3]) if y0 < v < y1})
    out = []
    for ya, yb in zip(ys, ys[1:]):
        inb = [(o[0], o[1]) for o in obs if o[2] < yb - 1e-6 and o[3] > ya + 1e-6]
        best_b = []
        for o in 'LP':
            mods, w, d = pack(x0, x1, ya, yb, slope, o, strips=inb, rows_grp=rows_grp_p if o == 'P' else rows_grp_l, walk=walk, cols_grp=0)
            if len(mods) > len(best_b): best_b = [(c, r, o) for c, r in mods]
        out += best_b
    return out

# ---------------------------------------------------------------- candidate arrays (capacity of each, shade-checked)
R1 = roofs[1]; ry = m(R1['ridge_y']); a1 = math.atan(0.1)
def tag(mods, o): return [(c, r, o) for c, r in mods]
def best(*cands): return max(cands, key=len)
CAND = {}
def cand(key, name, faces, roof, slope, mods): CAND[key] = dict(name=name, faces=faces, roof=roof, slope=slope, mods=unshaded(mods, slope, roof))
# roof 1 south: west of the existing array only (1 m access path beside it), landscape blocks of 7 x 4
mods, _, _ = pack(m(R1['x'][0]) + EDGE, m(EX['groups_x'][0][0]) - 1.0, ry + RIDGE_CLR, m(R1['y'][1]) - EDGE, a1, 'L')
cand('1S', 'Roof 1 · south slope', 'S', 1, a1, tag(mods, 'L'))
# roof 1 north: full capacity, landscape blocks, filled from the east end (nearest the inverters)
mods, _, _ = pack(m(R1['x'][0]) + EDGE, m(R1['x'][1]) - EDGE, m(R1['y'][0]) + EDGE, ry - RIDGE_CLR, a1, 'L', from_top=False)
cand('1N', 'Roof 1 · north slope', 'N', 1, a1, tag(mods, 'L'))
# new building: banded packing around the skylights (landscape / portrait per band), no N-S walkways needed
R7, R8, R35 = roofs[7], roofs[8], roofs[5]
a7 = math.atan(0.1); a8 = math.atan((R8['high'] - R8['low']) / m(R8['y'][1] - R8['y'][0])); a35 = math.atan((R35['high'] - R35['low']) / m(R35['y'][1] - R35['y'][0]))
cand('7S', 'New building · south roof', 'S', 7, a7,
     pack_banded(m(R7['x'][0]) + EDGE, m(R7['x'][1]) - EDGE, m(R7['y'][0]) + EDGE, m(R7['y'][1]) - EDGE, a7, grow(SKY7)))
cand('7N', 'New building · north roof', 'N', 8, a8,
     pack_banded(m(R8['x'][0]) + EDGE, m(R8['x'][1]) - EDGE, m(R8['y'][0]) + EDGE, m(R8['y'][1]) - 0.3, a8, grow(SKY8)))
# roof 3 south half + roof 5: skylight strips run the full slope; vents as point obstacles; best of portrait / landscape / banded
x0, x1, y0, y1 = m(R35['x'][0]) + EDGE, m(R35['x'][1]) - EDGE, m(R35['y'][0]) + EDGE, m(R35['y'][1]) - 0.6
full = [(a, b, y0 - 1, y1 + 1) for a, b in strips35]
c35 = [tag(pack(x0, x1, y0, y1, a35, o, strips=strips35, obs=vrect, rows_grp=2 if o == 'P' else 4, walk=0.6, cols_grp=0)[0], o) for o in 'LP']
c35.append(pack_banded(x0, x1, y0, y1, a35, full + vrect))
cand('35S', 'Roof 3 south half + roof 5', 'S', 5, a35, best(*[unshaded(c, a35, 5) for c in c35]))

# ---------------------------------------------------------------- options
ORDERS = {1: ['1S', '7S', '35S', '7N', '1N'], 2: ['1S', '7S', '35S', '1N'], 3: ['1S', '1N', '7S', '35S']}
TITLES = {1: 'Option 1 · south-facing → new building north → roof 1 north',
          2: 'Option 2 · south-facing → roof 1 north (closer to the inverters)',
          3: 'Option 3 · roof 1 south + north first → new building → roof 3/5'}
ix, iy = m(INV[0]), m(INV[1])
def dist(c, r): return abs(c - ix) + abs(r - iy) + 8.0          # Manhattan along eaves + ~8 m down the wall
options = []
for k, order in ORDERS.items():
    left, arrs = TARGET, []
    for key in order:
        if left <= 0: break
        C = CAND[key]; mods = list(C['mods'])
        if len(mods) > left: mods = sorted(mods, key=lambda p: (-round(p[0], 1), p[1]))[:left]   # partial: whole columns from the east end (nearest the inverters)
        left -= len(mods)
        orients = sorted({o for _, _, o in mods})
        arrs.append({**{kk: C[kk] for kk in ('name', 'faces', 'roof')}, 'slope_deg': round(math.degrees(C['slope']), 2), 'orient': '+'.join(orients),
                     'key': key, 'modules': len(mods),
                     'kwp': round(len(mods) * MOD_WP / 1000, 2), 'capacity': len(C['mods']),
                     'avg_dist_m': round(sum(dist(p[0], p[1]) for p in mods) / max(1, len(mods)), 1),
                     'mods_px': [[round(x * S, 1), round(y * S, 1), o] for x, y, o in mods]})
    n = sum(a['modules'] for a in arrs); kS = sum(a['kwp'] for a in arrs if a['faces'] == 'S'); kN = sum(a['kwp'] for a in arrs if a['faces'] == 'N')
    dc = sum(a['modules'] / 20 * 2 * a['avg_dist_m'] for a in arrs)        # string cable (+ and -), metres
    options.append({'id': k, 'title': TITLES[k], 'modules': n, 'kwp': round(n * MOD_WP / 1000, 2), 'kwp_south': round(kS, 2), 'kwp_north': round(kN, 2),
                    'kwh_year': round(kS * YIELD['S'] + kN * YIELD['N']), 'dc_cable_m': round(dc, -1), 'arrays': arrs,
                    'short': left > 0})

# winter (21 Dec 9-15 h) shadow zone on the roofs next to the new building, sampled every 0.7 m — for the drawing
SHADE = []
for rid in (3, 5, 8):
    r = roofs[rid]; yy = m(r['y'][0]) + 0.35
    while yy < m(r['y'][1]):
        xx = m(r['x'][0]) + 0.35
        while xx < m(r['x'][1]):
            if shaded(xx, yy, roof_h(r, xx, yy) + 0.15): SHADE.append([round(xx * S, 1), round(yy * S, 1)])
            xx += 0.7
        yy += 0.7

out = {'_note': 'Version v6 (2026-11-01). Generated by design/layout.py — do not edit by hand.',
       'shade_px': SHADE, 'shade_cell_px': round(0.7 * S, 2),
       'module': {'wp': MOD_WP, 'L': MOD_L, 'W': MOD_W, 'assumed': True},
       'target_modules': TARGET, 'yield_kwh_per_kwp': YIELD,
       'shade_check': '21 Dec, 9:00-15:00 solar time, every 30 min, Vadodara 22.4 N; module removed if any corner is shaded',
       'inverter': {'px': list(INV), 'note': 'east wall of roof 1, south corner (owner)'},
       'transformer': {'px': [1262, 668], 'note': 'next to the inverters (owner)'},
       'vents_px': VENTS,
       'skylights': [{'roof': '7S', 'px': [round(v * S, 1) for v in r]} for r in SKY7] + [{'roof': '7N', 'px': [round(v * S, 1) for v in r]} for r in SKY8] +
                    [{'roof': '3N', 'px': [c - 5.4, c + 5.4, 400, 545]} for c in SKYCOL] + [{'roof': '35S', 'px': [c - 5.4, c + 5.4, 545, 775]} for c in SKYCOL],
       'capacity': {k: len(v['mods']) for k, v in CAND.items()},
       'options': options}
json.dump(out, open(os.path.join(HERE, 'layout.json'), 'w'), indent=1)
print('capacity (shade-checked):', {k: len(v['mods']) for k, v in CAND.items()})
for o in options:
    print(f"\n{o['title']}\n  " + '\n  '.join(f"{a['key']:3} {a['name']:30} {a['modules']:4} / {a['capacity']:4}  {a['kwp']:7.2f} kWp  {a['orient']}  avg {a['avg_dist_m']} m" for a in o['arrays']))
    print(f"  TOTAL {o['modules']} = {o['kwp']} kWp · S {o['kwp_south']} / N {o['kwp_north']} · {o['kwh_year']:,} kWh/yr · DC string cable ≈ {o['dc_cable_m']:.0f} m" + ('  SHORT!' if o['short'] else ''))
