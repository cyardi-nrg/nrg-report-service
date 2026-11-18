# Version: v2 (2026-11-18) — DC lengths now follow NRG's routing (routes.py): rafter → edge purlin → across onto the
#   cabin / lift room wall → along the wall → entry sleeve → inverter. Stringing and AC unchanged from v1.
# Was v1 (2026-11-18) — Sangani Skyz (G+12, 48 flats) — per-flat stringing, DC and AC cable schedule
# 192 x 545 Wp, 4 panels per flat = one string of 4 into one Solaryaan 2 kW single-phase inverter per flat.
# Inverters inside the staircase cabin (terrace); AC down the staircase shaft to the meters beside the
# staircase on the ground floor. Geometry from the approved 2D layout v1.2 (geom.py).
#   python3 sangani_stringing.py   ->  Sangani-Skyz_Stringing-Plan_v2.png + Sangani-Skyz_Cable-Schedule_v2.xlsx
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geom import BLOCKS, CABIN, PPM, PU, PV, U, N, panel_poly, panel_centre  # noqa: E402
import routes  # noqa: E402

VERSION = 'v2'
HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'Sangani-Skyz_2D-layout_v1.2.jpg')

# ---------------------------------------------------------------- design inputs (owner)
TERRACE_H = 42.0        # m, ground floor to terrace (owner: ~42 m, parking + 12 floors)
INV_H = 1.5             # m, inverter height on the cabin wall
CABIN_IN = 2.0          # m, routing inside the cabin to the inverter (average)
SLACK = 1.0             # m per conductor, loops / terminations
AC_CABIN = 3.0          # m, inverter -> shaft inside the cabin
AC_GROUND = 5.0         # m, foot of the shaft -> meter (meter room right next to the staircase)
AC_TAIL = 2.0           # m, terminations
DC_MM2, AC_MM2 = 2.5, 2.5
R_DC = 7.98e-3          # ohm/m, 2.5 sq mm tinned Cu solar cable at 20 C
R_AC = 7.41e-3          # ohm/m, 2.5 sq mm Cu at 20 C
# 545 Wp mono PERC 144 half-cell, typical datasheet (make to be confirmed)
VOC, VMP, ISC, IMP, BETA_VOC = 49.65, 41.80, 13.93, 13.04, -0.0027
P_INV, V_GRID = 2000, 230


def m(px):
    return px / PPM


def to_m(pt):
    """picture px -> metres east / north of the picture origin"""
    return pt[0] / PPM, -pt[1] / PPM


CAB_M = [to_m(p) for p in CABIN]
CAB_E0, CAB_E1 = min(p[0] for p in CAB_M), max(p[0] for p in CAB_M)
CAB_N0, CAB_N1 = min(p[1] for p in CAB_M), max(p[1] for p in CAB_M)


def to_cabin(pt):
    """terrace route (east/north legs) from a point to the nearest cabin wall"""
    e, n = to_m(pt)
    de = 0 if CAB_E0 <= e <= CAB_E1 else min(abs(e - CAB_E0), abs(e - CAB_E1))
    dn = 0 if CAB_N0 <= n <= CAB_N1 else min(abs(n - CAB_N0), abs(n - CAB_N1))
    return de + dn


# ---------------------------------------------------------------- flats (strings)
def square(b, k, r=0, terminal='W'):
    """2 x 2 string: + and − at the same column (the one facing the cabin)"""
    a, z = (k, k + 1) if terminal == 'W' else (k + 1, k)
    return [(b, a, r + 1), (b, z, r + 1), (b, z, r), (b, a, r)]


def row4(b, k, r):
    return [(b, k + i, r) for i in range(4)]


def build_flats():
    cab_e = (CAB_E0 + CAB_E1) / 2

    def term(b, k):
        e, _ = to_m(panel_centre(b, k, 0))
        return 'E' if e < cab_e else 'W'          # terminal column on the side facing the cabin
    F = []
    for b, n in (('B1', 10), ('B2', 9)):
        off = 0 if b == 'B1' else 1               # B2 col 0 goes to flat W2
        for i in range(n):
            k = off + 2 * i
            F.append((b, square(b, k, 0, term(b, k))))
    for i in range(3):
        F.append(('B3W', square('B3W', 2 * i, 0, 'E')))
    for i in range(2):
        F.append(('B3E', square('B3E', 2 * i, 0, 'W')))
    for i in range(3):
        F.append(('B4W', square('B4W', 1 + 2 * i, 0, 'E')))
    for i in range(3):
        F.append(('B4E', square('B4E', 2 * i, 0, 'W')))
    for g in range(5):                            # B5 cols 1..20 in groups of 4 columns x 3 rows
        k = 1 + 4 * g
        t = term('B5', k + 1)
        F.append(('B5', square('B5', k, 0, t)))
        F.append(('B5', square('B5', k + 2, 0, t)))
        F.append(('B5', row4('B5', k, 2)))
    # three flats across neighbouring blocks (owner approved)
    F.append(('W1', [('B5', 0, 2), ('B5', 0, 1), ('B5', 0, 0), ('B4W', 0, 1)]))
    F.append(('W2', [('B4W', 0, 0), ('B3W', -1, 1), ('B2', 0, 1), ('B2', 0, 0)]))
    F.append(('E1', [('B4E', 6, 1), ('B4E', 6, 0), ('B3E', 4, 1), ('B3E', 4, 0)]))
    return F


def ends(cells):
    """(+ end point, − end point) in picture px: outer edge of first / last panel"""
    return panel_centre(*cells[0]), panel_centre(*cells[-1])


def flat_dc(cells):
    lp = routes.length(cells[0])['total']        # + leaves the first panel, − the last (NRG routing, routes.py)
    lm = routes.length(cells[-1])['total']
    # jumpers between panels that are not side by side (row turns inside a square are module leads)
    jump = 0.0
    for a, z in zip(cells, cells[1:]):
        if a[0] != z[0]:
            pa, pz = panel_centre(*a), panel_centre(*z)
            jump += m(abs(pa[0] - pz[0]) + abs(pa[1] - pz[1])) + abs(BLOCKS[a[0]][3] - BLOCKS[z[0]][3]) + 0.5
    return lp, lm, jump


def ac_len():
    return AC_CABIN + TERRACE_H + AC_GROUND + AC_TAIL


def main():
    flats = build_flats()
    assert len(flats) == 48, len(flats)
    used = [c for _, cells in flats for c in cells]
    assert len(used) == 192 and len(set(used)) == 192
    rows = []
    for i, (blk, cells) in enumerate(sorted(flats, key=lambda f: -to_m(panel_centre(*f[1][0]))[1] * 1000 + to_m(panel_centre(*f[1][0]))[0])):
        lp, lm, jump = flat_dc(cells)
        dc_loop = lp + lm
        vd_dc = IMP * R_DC * dc_loop / (4 * VMP) * 100
        ac = ac_len()
        i_ac = P_INV / V_GRID
        vd_ac = 2 * ac * i_ac * R_AC / V_GRID * 100
        rows.append(dict(sid=f'F{i+1:02d}', blk=blk, cells=cells, lp=lp, lm=lm, jump=jump, vd_dc=vd_dc, ac=ac, vd_ac=vd_ac))
    draw(rows)
    excel(rows)
    tot = lambda k: sum(r[k] for r in rows)
    print(f"DC +{tot('lp'):.0f} m  -{tot('lm'):.0f} m  jumpers {tot('jump'):.0f} m  AC {tot('ac'):.0f} m (2-core)")
    print(f"DC dV {min(r['vd_dc'] for r in rows):.2f}-{max(r['vd_dc'] for r in rows):.2f} %   AC dV {rows[0]['vd_ac']:.2f} %")
    return rows


# ---------------------------------------------------------------- drawing
PAL = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#42d4f4', '#f032e6', '#9a6324', '#469990', '#800000', '#808000', '#000075']


def font(sz, bold=False):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else '')
    return ImageFont.truetype(p, sz)


def draw(rows):
    base = Image.open(LAYOUT).convert('RGB').crop((40, 230, 1440, 1470))
    ox, oy = 40, 230
    W = base.width + 760
    im = Image.new('RGB', (W, base.height + 170), 'white')
    g = base.convert('L').convert('RGB')
    im.paste(Image.blend(g, Image.new('RGB', g.size, 'white'), 0.55), (0, 110))
    d = ImageDraw.Draw(im)

    def T(pt):
        return pt[0] - ox, pt[1] - oy + 110
    d.text((20, 18), f'Sangani Skyz — G+12, 48 flats — stringing per flat ({VERSION})', fill='#1e3a8a', font=font(30, True))
    d.text((20, 60), '192 x 545 Wp · one string of 4 per flat → one Solaryaan 2 kW inverter per flat, inside the staircase cabin · north up',
           fill='#333', font=font(17))
    cab = [T(p) for p in CABIN]
    d.polygon(cab, fill='#fde68a', outline='#92400e')
    cx = sum(p[0] for p in cab) / 4
    cy = sum(p[1] for p in cab) / 4
    d.text((cx, cy - 22), 'STAIRCASE', fill='#92400e', font=font(15, True), anchor='mm')
    d.text((cx, cy), 'CABIN', fill='#92400e', font=font(15, True), anchor='mm')
    d.text((cx, cy + 22), '48 INVERTERS', fill='#92400e', font=font(13, True), anchor='mm')
    for i, r in enumerate(rows):
        col = PAL[i % len(PAL)]
        for b, k, rr in r['cells']:
            d.polygon([T(p) for p in panel_poly(b, k, rr)], fill=col, outline='#111')
    for r in rows:                                   # second pass: wiring and labels on top of every panel
        pts = [T(panel_centre(*c)) for c in r['cells']]
        d.line(pts, fill='white', width=3)
        p, q = pts[0], pts[-1]
        for (x, y), sym in ((p, '+'), (q, '−')):
            d.ellipse([x - 8, y - 8, x + 8, y + 8], fill='white', outline='black')
            d.text((x, y), sym, fill='black', font=font(13, True), anchor='mm')
        mx = sum(x for x, _ in pts) / 4
        my = sum(y for _, y in pts) / 4
        d.rounded_rectangle([mx - 22, my - 11, mx + 22, my + 11], 4, fill='white', outline='black')
        d.text((mx, my), r['sid'], fill='black', font=font(13, True), anchor='mm')
    # side table
    x0 = base.width + 20
    d.text((x0, 120), 'DC / AC CABLE PER FLAT', fill='#111', font=font(18, True))
    hdr = ['FLAT', 'BLOCK', 'DC +', 'DC −', 'JUMP', 'AC']
    xs = [x0, x0 + 70, x0 + 160, x0 + 250, x0 + 340, x0 + 430]
    y = 150
    for xx, h in zip(xs, hdr):
        d.text((xx, y), h, fill='#111', font=font(13, True))
    y += 22
    for r in rows:
        vals = [r['sid'], r['blk'], f"{r['lp']:.1f}", f"{r['lm']:.1f}", f"{r['jump']:.1f}" if r['jump'] else '–', f"{r['ac']:.0f}"]
        for xx, v in zip(xs, vals):
            d.text((xx, y), v, fill='#111', font=font(12))
        y += 19
    tot = lambda k: sum(r[k] for r in rows)
    y += 6
    d.line([(x0, y), (x0 + 500, y)], fill='#111', width=1)
    y += 6
    for xx, v in zip(xs, ['TOTAL', '', f"{tot('lp'):.0f}", f"{tot('lm'):.0f}", f"{tot('jump'):.0f}", f"{tot('ac'):.0f}"]):
        d.text((xx, y), v, fill='#111', font=font(13, True))
    y += 30
    notes = ['Lengths in metres, per conductor (DC) / per run (AC).',
             'DC 2.5 sq mm Cu solar cable: along a rafter → edge purlin',
             '→ across onto the cabin / lift room wall → along the wall',
             '→ sleeve (W or E side) → inverter. B1 goes via B2.',
             f'AC 2.5 sq mm Cu 2-core: cabin {AC_CABIN:.0f} m + shaft {TERRACE_H:.0f} m',
             f'+ ground {AC_GROUND:.0f} m + terminations {AC_TAIL:.0f} m.',
             'F-numbers are string numbers: the flat number of each',
             'is to be fixed on site (one inverter / meter per flat).',
             'W1, W2, E1 strings span two blocks (jumpers).']
    for t in notes:
        d.text((x0, y), t, fill='#333', font=font(13))
        y += 19
    d.text((20, im.height - 34), f'NRG Technologists · Sangani Skyz stringing {VERSION} · 18-11-2026 · from 2D layout v1.2 — verify on site',
           fill='#777', font=font(14))
    im.save(os.path.join(HERE, f'Sangani-Skyz_Stringing-Plan_{VERSION}.png'))


# ---------------------------------------------------------------- Excel
def excel(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = 'Per flat'
    thin = Side(style='thin', color='999999')
    bd = Border(left=thin, right=thin, top=thin, bottom=thin)
    hd = PatternFill('solid', fgColor='1E3A8A')
    ws['A1'] = f'SANGANI SKYZ — G+12, 48 FLATS — STRINGING & CABLE SCHEDULE ({VERSION}, 18-11-2026)'
    ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = ('192 x 545 Wp, 4 per flat (2.18 kWp) · 1 string of 4 → 1 Solaryaan 2 kW per flat in the staircase cabin · '
                f'DC {DC_MM2} sq mm Cu, AC {AC_MM2} sq mm Cu 2-core · terrace {TERRACE_H:.0f} m above ground, meters beside the staircase')
    head = ['String / flat', 'Block', 'Panels (block col,row)', 'DC + (m)', 'DC − (m)', 'Jumper (m)', 'DC total (m)',
            'DC ΔV %', 'AC run (m)', 'AC ΔV % (2 kW)', 'Flat no. (site)', 'Cabin sleeve']
    ws.append([])
    ws.append(head)
    for c in ws[4]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = hd
        c.alignment = Alignment(wrap_text=True, vertical='center')
        c.border = bd
    for r in rows:
        ws.append([r['sid'], r['blk'], ' '.join(f'{b}:{k+1},{rr+1}' for b, k, rr in r['cells']),
                   round(r['lp'], 1), round(r['lm'], 1), round(r['jump'], 1), None,
                   round(r['vd_dc'], 2), round(r['ac'], 1), round(r['vd_ac'], 2), '', routes.length(r['cells'][0])['side']])
        n = ws.max_row
        ws.cell(n, 7).value = f'=D{n}+E{n}+F{n}'
    first, last = 5, ws.max_row
    ws.append(['TOTAL', '', '', f'=SUM(D{first}:D{last})', f'=SUM(E{first}:E{last})', f'=SUM(F{first}:F{last})',
               f'=SUM(G{first}:G{last})', '', f'=SUM(I{first}:I{last})', '', '', ''])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
        for c in row:
            c.border = bd
    for col, w in zip('ABCDEFGHIJKL', [12, 8, 46, 10, 10, 10, 12, 9, 11, 13, 14, 10]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A5'

    s = wb.create_sheet('Summary & order')
    tr = ws.max_row
    s.append(['ITEM', 'SPEC', 'NET (m / nos)', 'ORDER', 'BASIS'])
    for c in s[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = hd
    s.append(['DC cable, red (+)', '2.5 sq mm Cu solar DC cable (EN 50618 / IS 17293), 1.1 kV', f"='Per flat'!D{tr}+'Per flat'!F{tr}/2",
              '=CEILING(C2*1.05,10)', '+ runs of all 48 strings, half the jumpers; +5 %'])
    s.append(['DC cable, black (−)', 'same', f"='Per flat'!E{tr}+'Per flat'!F{tr}/2", '=CEILING(C3*1.05,10)', '− runs, half the jumpers; +5 %'])
    s.append(['AC cable', '2.5 sq mm Cu 2-core (PVC / armoured as per site), 1.1 kV', f"='Per flat'!I{tr}", '=CEILING(C4*1.05,10)',
              f'48 runs x {ac_len():.0f} m; +5 %'])
    s.append(['MC4 connector pairs', '1500 V, same make as the panel connectors', 48 + 6, '=CEILING(C5*1.1,1)', '1 pair per string at the inverter + 6 for jumpers; +10 %'])
    s.append(['Inverters', 'Solaryaan 2 kW single-phase on-grid', 48, 48, 'one per flat, inside the staircase cabin'])
    s.append([])
    s.append(['CHECKS'])
    voc5 = 4 * VOC * (1 + BETA_VOC * (5 - 25))
    s.append(['String Voc @ 5 °C', f'4 x {VOC} x (1 + 0.27 % x 20) = {voc5:.0f} V', '', '', 'must be below the inverter max DC input — check Solaryaan datasheet'])
    s.append(['String Vmp', f'≈ {4*VMP*0.85:.0f} V (hot) – {4*VMP:.0f} V (STC)', '', '', 'must sit inside the inverter MPPT range — check datasheet'])
    s.append(['String Isc', f'{ISC} A', '', '', 'inverter max input / short-circuit current must be ≥ this'])
    s.append(['AC current', f'{P_INV/V_GRID:.1f} A at 230 V', '', '', f'2.5 sq mm Cu over {ac_len():.0f} m → ΔV {rows[0]["vd_ac"]:.1f} % (4 sq mm ≈ {rows[0]["vd_ac"]*2.5/4:.1f} %)'])
    for col, w in zip('ABCDE', [22, 52, 16, 14, 70]):
        s.column_dimensions[col].width = w
    wb.save(os.path.join(HERE, f'Sangani-Skyz_Cable-Schedule_{VERSION}.xlsx'))


if __name__ == '__main__':
    main()
