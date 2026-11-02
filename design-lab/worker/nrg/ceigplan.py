# Design Lab worker v1.8.1 (2026-10-31) — CEIG plan sheets 02–06, made general from the
# owner-approved Jain Granite set (equipment, earthing, walkway, cable tray, stringing layouts).
# Jain's sheets drew one known roof by hand; here each sheet is drawn from the design itself:
# the drawn roofs (site metres, north up), the chosen panel option, the Stringing result and the
# walkway / tray / earthing routes of handlers/layouts.compute(). Line drawings, no satellite
# picture — a CEIG submission wants clean sheets. Routes are square to the building and
# approximate; every sheet says "verify on site".
import math

from nrg.ceigkit import (T, TL, R, L, C, table, sym_module, sym_inverter, sym_la, sym_pit, sym_meter, compass,
                         legend_block, system_block, title_block, page, earth_pit_section, connection_detail,
                         module_ground_detail, TB_X0)

SCALES = [50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 600, 750, 1000, 1250, 1500, 2000]
WALK_FILL, WALK_STROKE, TRAY_COL, EARTH_COL, LA_COL = '#d6d3d1', '#57534e', '#ea580c', '#15803d', '#d62828'
STR_COLS = ['#e6194b', '#f58231', '#3cb44b', '#008080', '#4363d8', '#911eb4', '#f032e6', '#9a6324', '#800000', '#808000', '#000075',
            '#469990', '#c026d3', '#0e7490', '#b45309', '#4d7c0f']


class Plan:
    """Fits site metres into a box on the sheet at a standard scale (1:n on A3, 4 units per mm)."""

    def __init__(self, pts, box, margin=5.0):
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        self.x0, self.y0, x1, y1 = min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin
        bx0, by0, bx1, by1 = box
        k = min((bx1 - bx0) / (x1 - self.x0), (by1 - by0) / (y1 - self.y0))      # units per metre
        need = 4000 / k                                                           # 1:need
        self.scale = next((s for s in SCALES if s >= need), math.ceil(need / 100) * 100)
        self.k = 4000 / self.scale
        w, h = (x1 - self.x0) * self.k, (y1 - self.y0) * self.k
        self.ox, self.oy = bx0 + ((bx1 - bx0) - w) / 2, by0 + ((by1 - by0) - h) / 2
        self.box = box

    def clip(self, body: list) -> str:
        """Plan drawing clipped to its box (buildings beyond the work area are cut at the frame)."""
        bx0, by0, bx1, by1 = self.box
        return (f'<clipPath id="planclip"><rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}"/></clipPath>'
                f'<g clip-path="url(#planclip)">' + ''.join(body) + '</g>')

    def __call__(self, x, y):
        return self.ox + (x - self.x0) * self.k, self.oy + (y - self.y0) * self.k

    def poly(self, pts, stroke='#000', sw=1, fill='none', dash=None, close=True):
        d = f' stroke-dasharray="{dash}"' if dash else ''
        p = ' '.join(f'{a:.1f},{b:.1f}' for a, b in (self(*q) for q in pts))
        tag = 'polygon' if close else 'polyline'
        return f'<{tag} points="{p}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}"{d} stroke-linejoin="round"/>'


def _bounds(d):
    """The work area: the panels, the inverters, the pits, the arresters and the meter (not every drawn roof)."""
    site = d['site']
    pts = [c for a in d['arrays'] for m in a['_mods'] for c in m.corners]
    if site.inverter:
        pts.append(site.inverter)
    it = d.get('items') or {}
    pts += [p for _, p in it.get('pits', [])] + list(it.get('la', []))
    if it.get('meter'):
        pts.append(it['meter'])
    if not pts:
        pts = [q for r in site.roofs for q in r['poly'].exterior.coords]
    return pts


def _base(P: Plan, d, mod_fill='#eef2ff', mod_stroke='#94a3b8', strings=False):
    site, o = d['site'], []
    for r in site.roofs:
        o.append(P.poly(list(r['poly'].exterior.coords), '#000', 1.2, '#fafaf9'))
        for hole in r['poly'].interiors:
            o.append(P.poly(list(hole.coords), '#000', 0.8, '#fff'))
    for ob in getattr(site, 'obstacles', []) or []:
        poly = next((v for v in (ob if isinstance(ob, (tuple, list)) else [ob]) if hasattr(v, 'exterior')), None)
        if poly is not None:
            o.append(P.poly(list(poly.exterior.coords), '#78716c', 0.6, '#e7e5e4'))
    if not strings:
        for a in d['arrays']:
            for m in a['_mods']:
                o.append(P.poly(m.corners, mod_stroke, 0.4, mod_fill))
    return o


def _dims(P: Plan, d):
    o = []
    for i, r in enumerate(d['site'].roofs):
        x0, y0, x1, y1 = r['poly'].bounds
        (a, b), (c, e) = P(x0, y0), P(x1, y1)
        if c - a > 60:
            o.append(L(a, b - 10, c, b - 10, '#1f3bb8', 0.6) + L(a, b - 14, a, b - 6, '#1f3bb8', 0.6) + L(c, b - 14, c, b - 6, '#1f3bb8', 0.6))
            o.append(T((a + c) / 2, b - 13, f'{x1 - x0:.1f} M *', 6.5, 'middle', fill='#1f3bb8'))
        if e - b > 60:
            o.append(L(a - 10, b, a - 10, e, '#1f3bb8', 0.6))
            o.append(T(a - 13, (b + e) / 2, f'{y1 - y0:.1f} M *', 6.5, 'middle', fill='#1f3bb8', rot=-90))
    return o


def _equipment(P: Plan, d):
    site, o = d['site'], []
    if not site.inverter:
        return o
    n = int(d['inverter'].get('count') or 1)
    ix, iy = P(*site.inverter)
    for k in range(n):
        o.append(sym_inverter(ix + (k - (n - 1) / 2) * 30, iy, 24, 15))
    o.append(R(ix - n * 15 - 4, iy - 12, n * 30 + 8, 24, '#16a34a', 0.6, dash='3,2'))
    o.append(T(ix, iy - 16, f"INVERTERS ({n} × {d['inverter'].get('model', '')})", 7, 'middle', 'bold'))
    o.append(R(ix + n * 15 + 10, iy - 9, 26, 18, '#c026d3', 1, '#fae8ff') + T(ix + n * 15 + 23, iy + 3, 'ACDB', 6, 'middle', 'bold'))
    meter = (d.get('items') or {}).get('meter')
    if meter:
        mx, my = P(*meter)
        o.append(sym_meter(mx, my, 18) + T(mx + 14, my + 3, 'LT PANEL / METER', 7, weight='bold'))
        o.append(L(ix + n * 15 + 36, iy, mx, iy, '#d62828', 1.2, '6,3') + L(mx, iy, mx, my, '#d62828', 1.2, '6,3'))
    return o


def _right(d, legend_title, rows, dwg_no, name, scale_txt, sheet):
    tb, y = legend_block(52, legend_title, rows, rh=17)
    tb2, y = system_block(d['system'], y + 10)
    return tb + tb2 + title_block(d['info'], dwg_no, name, scale_txt, sheet)


def _frame_note(P, extra=''):
    return T(48, 1150, f'ROUTES ARE SQUARE TO THE BUILDING AND APPROXIMATE — VERIFY ON SITE. DIMENSIONS MARKED * FROM THE DRAWN ROOFS.{extra}', 7, fill='#555')


# ---------------------------------------------------------------- 02 equipment layout
def sheet_equipment(d) -> str:
    P = Plan(_bounds(d), (60, 80, 1240, 1110))
    it = d['items']
    o = _base(P, d) + _dims(P, d)
    for p0, p1 in it.get('walkways', []):
        o.append(L(*P(*p0), *P(*p1), WALK_STROKE, max(2, 0.6 * P.k)))
    for t in it.get('trays', []):
        o.append(P.poly(t, TRAY_COL, 1.6, close=False))
    o += _equipment(P, d)
    for name, (x, y) in it.get('pits', []):
        px, py = P(x, y)
        o.append(sym_pit(px, py) + T(px, py + 17, name.split(' ')[0], 6, 'middle', 'bold', EARTH_COL))
    for x, y in it.get('la', []):
        px, py = P(x, y)
        o.append(sym_la(px, py, 0.7))
    o = [P.clip(o)]
    o.append(compass(1200, 110))
    o.append(_frame_note(P))
    rows = [(lambda x, y: sym_module(x, y), 'PV MODULE'),
            (lambda x, y: sym_inverter(x, y), 'STRING INVERTER'),
            (lambda x, y: R(x - 13, y - 7, 26, 14, '#c026d3', 1, '#fae8ff'), 'ACDB'),
            (lambda x, y: sym_meter(x, y, 14), 'LT PANEL / NET METER'),
            (lambda x, y: L(x - 20, y, x + 20, y, WALK_STROKE, 5), 'WALKWAY'),
            (lambda x, y: L(x - 20, y, x + 20, y, TRAY_COL, 2), 'CABLE TRAY'),
            (lambda x, y: L(x - 20, y, x + 20, y, '#d62828', 1.2, '6,3'), 'AC CABLE ROUTE'),
            (lambda x, y: sym_pit(x, y), 'EARTH PIT'),
            (lambda x, y: sym_la(x, y + 4, 0.6), 'LIGHTNING ARRESTER')]
    o.append(_right(d, 'LEGEND', rows, '02', 'EQUIPMENT LAYOUT', f'1:{P.scale}', d.get('sheet02', '02')))
    return page(''.join(o), f"{d['info']['file']}_02_Equipment-Layout")


# ---------------------------------------------------------------- 03 earthing layout
def sheet_earthing(d) -> str:
    P = Plan(_bounds(d), (60, 70, 1240, 690))
    it = d['items']
    o = _base(P, d, '#f8fafc', '#cbd5e1')
    for e in it.get('earth', []):
        o.append(P.poly(e, EARTH_COL, 1.6, close=False))
    for r in it.get('la_runs', []):
        o.append(P.poly(r, LA_COL, 1.6, close=False, dash='8,4'))
    for x, y in it.get('la', []):
        px, py = P(x, y)
        o.append(sym_la(px, py, 0.8) + T(px + 12, py - 6, 'LA', 7, fill=LA_COL, weight='bold'))
    for name, (x, y) in it.get('pits', []):
        px, py = P(x, y)
        o.append(sym_pit(px, py) + T(px, py + 17, name.split(' ')[0], 6.5, 'middle', 'bold', EARTH_COL))
    o += _equipment(P, d)
    o = [P.clip(o)]
    o.append(compass(1200, 100))
    o.append(L(44, 705, 1250, 705, '#000', 0.8))
    o.append(earth_pit_section(50, 712))
    o.append(connection_detail(520, 760))
    o.append(module_ground_detail(880, 740))
    tb, y = table(520, 980, [190, 150], [
        ('EARTH PITS', '3 Nos. — DC (EP-1), AC (EP-2), LA (EP-3)'),
        ('PIT SPACING', '3 M (MIN. 2 M)'),
        ('LIGHTNING ARRESTERS', f"{it.get('la_n', 0)} Nos. (FOR {it.get('total_kw', 0):g} kW)"),
        ('STRUCTURE EARTHING TO EP-1', f"≈ {it.get('earth_m', 0):,.0f} M *"),
        ('LA DOWN-CONDUCTOR TO EP-3', f"≈ {it.get('la_m', 0):,.0f} M *"),
    ], rh=15, size=7, head='EARTHING SUMMARY')
    o.append(tb)
    o.append(_frame_note(P))
    rows = [(lambda x, y: sym_pit(x, y), 'EARTH PIT (IS 3043)'),
            (lambda x, y: sym_la(x, y + 4, 0.6), 'LIGHTNING ARRESTER (ESE / CONVENTIONAL)'),
            (lambda x, y: L(x - 20, y, x + 20, y, EARTH_COL, 2), 'STRUCTURE EARTHING (16 SQ MM Cu) TO EP-1'),
            (lambda x, y: L(x - 20, y, x + 20, y, LA_COL, 2, '8,4'), 'LA DOWN-CONDUCTOR (50 SQ MM Cu) TO EP-3'),
            (lambda x, y: sym_inverter(x, y), 'INVERTER / ACDB — 25 SQ MM Cu TO EP-2'),
            (lambda x, y: sym_module(x, y), 'PV MODULE')]
    o.append(_right(d, 'LEGEND', rows, '03', 'EARTHING LAYOUT', f'1:{P.scale}', d.get('sheet03', '03')))
    return page(''.join(o), f"{d['info']['file']}_03_Earthing-Layout")


# ---------------------------------------------------------------- 04 walkway layout
def sheet_walkway(d) -> str:
    P = Plan(_bounds(d), (60, 80, 1240, 1000))
    it = d['items']
    o = _base(P, d) + _dims(P, d)
    for i, (p0, p1) in enumerate(it.get('walkways', [])):
        a, b = P(*p0), P(*p1)
        o.append(L(*a, *b, WALK_STROKE, max(3, 0.6 * P.k)) + L(*a, *b, WALK_FILL, max(1.5, 0.6 * P.k - 2)))
        o.append(T((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 5, f'W{i + 1} · {math.dist(p0, p1):.1f} M', 6.5, 'middle', 'bold', WALK_STROKE))
    o = [P.clip(o)]
    o.append(compass(1200, 110))
    tb, _ = table(60, 1020, [300, 200], [('FRP WALKWAY BETWEEN THE ROW GROUPS (0.6 M WIDE)', f"{it.get('walk_m', 0):,.1f} M *"),
                                          ('WALKWAY RUNS', str(len(it.get('walkways', []))))], rh=16, size=7.5, head='WALKWAY')
    o.append(tb)
    o.append(_frame_note(P))
    rows = [(lambda x, y: L(x - 20, y, x + 20, y, WALK_STROKE, 6) + L(x - 20, y, x + 20, y, WALK_FILL, 3), 'FRP WALKWAY (0.6 M)'),
            (lambda x, y: sym_module(x, y), 'PV MODULE')]
    o.append(_right(d, 'LEGEND', rows, '04', 'WALKWAY LAYOUT', f'1:{P.scale}', d.get('sheet04', '04')))
    return page(''.join(o), f"{d['info']['file']}_04_Walkway-Layout")


# ---------------------------------------------------------------- 05 cable tray layout
def sheet_tray(d) -> str:
    P = Plan(_bounds(d), (60, 80, 1240, 1000))
    it = d['items']
    o = _base(P, d)
    for t in it.get('trays', []):
        o.append(P.poly(t, TRAY_COL, 2.4, close=False))
    o += _equipment(P, d)
    o = [P.clip(o)]
    o.append(compass(1200, 110))
    rows_t = [('CABLE TRAY (INCL. DROP DOWN THE WALL)', f"{it.get('tray_m', 0):,.1f} M *")]
    if it.get('ac_m'):
        rows_t.append(('AC CABLE, INVERTERS TO LT PANEL / METER', f"{it['ac_m']:,.1f} M *"))
    if d.get('dc'):
        rows_t.append(('DC CABLE PER COLOUR (STRINGING)', f"{d['dc']:,.0f} M *"))
    tb, _ = table(60, 1020, [300, 200], rows_t, rh=16, size=7.5, head='CABLE TRAY & CABLES')
    o.append(tb)
    o.append(_frame_note(P))
    rows = [(lambda x, y: L(x - 20, y, x + 20, y, TRAY_COL, 3), 'CABLE TRAY (PERFORATED, GI)'),
            (lambda x, y: L(x - 20, y, x + 20, y, '#d62828', 1.2, '6,3'), 'AC CABLE ROUTE'),
            (lambda x, y: sym_inverter(x, y), 'STRING INVERTER'),
            (lambda x, y: R(x - 13, y - 7, 26, 14, '#c026d3', 1, '#fae8ff'), 'ACDB'),
            (lambda x, y: sym_meter(x, y, 14), 'LT PANEL / NET METER'),
            (lambda x, y: sym_module(x, y), 'PV MODULE')]
    o.append(_right(d, 'LEGEND', rows, '05', 'CABLE TRAY LAYOUT', f'1:{P.scale}', d.get('sheet05', '05')))
    return page(''.join(o), f"{d['info']['file']}_05_Cable-Tray-Layout")


def _snake(P: Plan, s: dict) -> str:
    """The wiring path of one string, panel to panel in connection order, numbered from the + end, so the
    electricians see where each string turns at the end of a column (owner: "create the snake in the strings").
    Each number is the panel's place in the string; + and − are at the two ends."""
    chain = list(s['mods'])
    if s.get('plus') is chain[-1]:
        chain = chain[::-1]
    pts = [P(m.x, m.y) for m in chain]
    line = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    o = [f'<polyline points="{line}" stroke="#ffffff" stroke-width="2.6" fill="none" stroke-linejoin="round" opacity="0.9"/>',
         f'<polyline points="{line}" stroke="#111" stroke-width="0.9" fill="none" stroke-linejoin="round"/>']
    w = abs(P(chain[0].corners[1][0], chain[0].corners[1][1])[0] - P(chain[0].corners[0][0], chain[0].corners[0][1])[0]) + \
        abs(P(chain[0].corners[1][0], chain[0].corners[1][1])[1] - P(chain[0].corners[0][0], chain[0].corners[0][1])[1])
    if w >= 10:                                          # big enough on the sheet to print the panel numbers
        fs = 5.2 if w < 22 else 6.2
        for k, (x, y) in enumerate(pts):
            o.append(T(x + 2.5, y - 2, str(k + 1), fs, 'start', 'bold', '#111'))
    return ''.join(o)


# ---------------------------------------------------------------- 06 stringing layout
def sheet_stringing(d) -> str:
    P = Plan(_bounds(d), (60, 80, 1240, 985))
    res = d['stringing']
    o = _base(P, d, strings=True)
    for i, s in enumerate(res['strings']):
        col = STR_COLS[i % len(STR_COLS)]
        for m in s['mods']:
            o.append(P.poly(m.corners, '#fff', 0.4, col))
        o.append(_snake(P, s))
        mid = s['mods'][len(s['mods']) // 2]
        mx, my = P(mid.x, mid.y)
        lab = s['id'] + (f" · {s['inverter']}-M{s['mppt']}" if s.get('mppt') else '')
        o.append(R(mx - len(lab) * 2.4 - 3, my - 6, len(lab) * 4.8 + 6, 12, 'none', 0, '#ffffffdd', rx=3) + T(mx, my + 3, lab, 6.5, 'middle', 'bold'))
        for pole, c in (('plus', '#dc2626'), ('minus', '#111')):
            px, py = P(s[pole].x, s[pole].y)
            o.append(C(px, py, 3.2, '#fff', 0.6, c))
    for q in res.get('pairs', []):
        A, B = res['strings'][q['a']], res['strings'][q['b']]
        for pole, c in (('plus', '#dc2626'), ('minus', '#111')):
            a, b = P(A[pole].x, A[pole].y), P(B[pole].x, B[pole].y)
            j = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            # legs follow the rows (along, then across) rather than cutting over the panels
            o.append(f'<polyline points="{a[0]:.1f},{a[1]:.1f} {j[0]:.1f},{a[1]:.1f} {j[0]:.1f},{j[1]:.1f}" stroke="{c}" stroke-width="1.4" fill="none"/>'
                     f'<polyline points="{b[0]:.1f},{b[1]:.1f} {j[0]:.1f},{b[1]:.1f} {j[0]:.1f},{j[1]:.1f}" stroke="{c}" stroke-width="1.4" fill="none"/>')
            if pole == 'plus':
                o.append(T(j[0], j[1] - 5, q['id'], 6.5, 'middle', 'bold', '#7c3aed'))
    o += _equipment(P, d)
    o = [P.clip(o)]
    o.append(compass(1200, 110))
    srows = []
    for s in res['strings']:
        srows.append((s['id'], f"Y-PAIR {s['pair']}" if s.get('pair') else 'SINGLE', f"{s.get('inverter', '—')}/{s.get('mppt', '—')}/{s.get('input', '—')}", str(s['n']), s['faceName'][:22]))
    per_col, cols = 8, 3
    hdr = ('STRING', 'Y PAIR', 'INV/MPPT/IN', 'MODS', 'ROOF')
    for c in range(cols):
        part = srows[c * per_col:(c + 1) * per_col]
        if part:
            tb, _ = table(60 + c * 396, 1000, [50, 56, 76, 40, 168], [hdr] + part, rh=13, size=6.3)
            o.append(tb)
    if len(srows) > per_col * cols:
        o.append(T(60, 996, f"STRINGS {per_col * cols + 1}–{len(srows)}: SEE THE STRING SCHEDULE / SLD", 6.5, fill='#b45309'))
    o.append(T(48, 1150, f"S = SINGLE STRING, Y1-A / Y1-B = THE TWO STRINGS OF Y PAIR Y1.  BLACK LINE = WIRING PATH, NUMBERS = PANEL ORDER FROM THE +VE END.  ● RED = +VE END, ● BLACK = –VE END.  Y PAIRS (PURPLE): SAME POLES JOINED AT A Y-CONNECTOR, ONE HOME RUN TO THE INVERTER (6 SQ.MM, BIGGER WHERE THE DROP NEEDS IT).  "
                         f"{res['compare']['choice'].upper()}.  VERIFY ON SITE.", 7, fill='#555'))
    rows = [(lambda x, y: R(x - 11, y - 6, 22, 12, '#fff', 0.5, STR_COLS[0]), 'STRING (ONE COLOUR EACH)'),
            (lambda x, y: C(x - 8, y, 3.2, '#fff', 0.6, '#dc2626') + C(x + 8, y, 3.2, '#fff', 0.6, '#111'), '+VE / –VE STRING END'),
            (lambda x, y: L(x - 12, y + 5, x, y - 3, '#dc2626', 1.4) + L(x + 12, y + 5, x, y - 3, '#dc2626', 1.4), 'Y-CONNECTOR JOINT'),
            (lambda x, y: sym_inverter(x, y), 'STRING INVERTER')]
    o.append(_right(d, 'LEGEND', rows, '06', 'STRINGING LAYOUT', f'1:{P.scale}', d.get('sheet06', '06')))
    return page(''.join(o), f"{d['info']['file']}_06_Stringing-Layout")
