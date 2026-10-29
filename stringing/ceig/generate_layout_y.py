# Version: v1 (2026-10-29) — Jain Granite & Marble layout set WITH Y-CONNECTORS (3 sheets)
#   L-01  PANEL LAYOUT + ELECTRICAL WIRING (strings, Y-connectors, wiring diagram)
#   L-02  WALKWAY LAYOUT
#   L-03  CABLE TRAY (DUCTING) + CABLE LENGTHS
# Reuses the roof / module / walkway / tray geometry of generate_ceig_drawings.py (v7), so both sets
# always agree. The CEIG set (sheets 01-06) and the BOM v2 are NOT changed by this script — they
# still show the no-Y design.
#   python3 generate_layout_y.py && node render_pdf.js
#
# Y design: the two mirrored partner strings of each MPPT are joined on the roof, in the gap
# between their blocks: + Y at their row-1 (row-5) terminals, − Y at their row-4 (row-8)
# terminals. One 6 sq mm +/− home run per MPPT runs in the tray to the inverter.

import generate_ceig_drawings as g
from generate_ceig_drawings import (T, TL, R, L, PL, C, table, compass, legend_block, system_block,
                                    sym_inverter, sym_la, equipment_group, corner_mark, label_corners,
                                    snake_cells, row_centre_y, Rm, draw_walkways, walkway_runs, walk_lengths,
                                    dim_h, BLOCK_X, BLOCK_Y, BW, MOD_W, MOD_L, MGAP, ROOF_W, INV, NAMES,
                                    SCOL, STRING_MAP, TRAY_GAP_X, TRAY_HY, TRAY_W, TRAY_GAP_END, WALL_DROP,
                                    TRAY_COL, WALK_FILL, WALK_STROKE, CON_Y0, WALK_W, SOUTH_Y0, LADDER, LA,
                                    BRAND, RIDGE_X)

VERSION = 'v1'
g.P['date'] = '29-10-26'

# ---------------------------------------------------------------- Y design data
TRAY_SIZE = '50 x 50 MM'
Y_SLACK = 0.5          # m per conductor: slack / drip loop at the Y end of the home run
TAIL_INV = 1.5         # m per conductor: dressing into the inverter
FAR_LEAD = 1.5         # m of 4 sq mm: far string's +/− lead across the gap (under the walkway) to the Y
JUMPER_LEN = 2.5       # m of 4 sq mm per row-turn jumper (same as BOM v2)
ROW_TURNS = 3          # per string
R6 = 3.39e-3           # ohm/m, 6 sq mm tinned Cu at 20 °C (EN 50618)
VMP = 20 * 41.6        # V, string Vmp at STC
IMP2 = 2 * 15.03       # A, two strings in parallel
PLUS_COL, MINUS_COL = '#d62828', '#111'
RATES = {'4': 58, '6': 84}   # owner's rates ₹/m


def mppt_pairs():
    """[(mppt, s_near, s_far, slope, gap, plus_row, minus_row)] — s_near is in the block on the tray side"""
    out = []
    for m in (1, 2, 3, 4):
        ss = [s for (mm, i, s, sl) in sorted(STRING_MAP) if mm == m]
        sl = [x for (mm, i, s, x) in STRING_MAP if mm == m][0]
        b = [k for k, p in enumerate(NAMES) if ss[0] in p][0]
        half = NAMES[b].index(ss[0])
        gap = b // 2
        rp, rm = (0, 3) if half == 0 else (4, 7)
        out.append((m, ss[0], ss[1], sl, gap, rp, rm))
    return out


def home_run(gap, row):
    """one conductor, Y in the gap at `row` → tray north → header east → east wall → inverter"""
    hy = TRAY_HY + TRAY_W / 2
    tx = TRAY_GAP_X[gap]
    return (row_centre_y(row) - hy) + (ROOF_W - tx) + WALL_DROP + (INV[1] - hy) + TAIL_INV + Y_SLACK


def y_schedule():
    out = []
    for m, sn, sf, sl, gap, rp, rm in mppt_pairs():
        p, n = home_run(gap, rp), home_run(gap, rm)
        vd = IMP2 * R6 * (p + n) / VMP * 100
        out.append((m, sn, sf, sl, gap, rp, rm, p, n, vd))
    return out


def quantities():
    sch = y_schedule()
    hr6 = sum(r[7] + r[8] for r in sch)
    n_str = 8
    far = n_str * FAR_LEAD                     # 4 far strings x (+ and −) = 8 leads
    jump = n_str * ROW_TURNS * JUMPER_LEN
    return dict(hr6=hr6, hr6_order=round(hr6 * 1.05 / 5 + 0.499) * 5, far=far, jump=jump,
                c4=far + jump, c4_order=round((far + jump) * 1.05 / 5 + 0.499) * 5,
                y_sets=4, mc4_hr=8, mc4_far=8, mc4_jump=n_str * ROW_TURNS)


def tray_segments_y():
    cab = {'T1': ('4 x 6 SQ MM + 16 SQ MM E', 'MPPT 3, 4'), 'T2': ('4 x 6 SQ MM + 16 SQ MM E', 'MPPT 1, 2'),
           'T3a': ('4 x 6 SQ MM + 16 SQ MM E', 'MPPT 3, 4'), 'T3b': ('8 x 6 SQ MM + 16 SQ MM E', 'ALL 4 MPPT'),
           'T4': ('8 x 6 SQ MM + 16 SQ MM E', 'ALL 4 MPPT')}
    return [(sid, desc, pts, cab[sid][0], cab[sid][1], ln) for sid, desc, pts, _, _, ln in g.tray_segments()]


# ---------------------------------------------------------------- drawing helpers
def ysym(x, y, pol, r=6):
    col = PLUS_COL if pol == '+' else MINUS_COL
    return (C(x, y, r + 1.5, '#fff', 0, '#fff') + C(x, y, r, '#000', 0.8, col) +
            L(x - r * 0.45, y - r * 0.5, x, y, '#fff', 1.2) + L(x + r * 0.45, y - r * 0.5, x, y, '#fff', 1.2) +
            L(x, y, x, y + r * 0.55, '#fff', 1.2))


def title(dwg_no, name, scale, sheet):
    tb = g.title_block(dwg_no, name, scale)
    tb = tb.replace(f'NRG CEIG drawing set {g.VERSION} — generated 27-10-2026',
                    f'NRG layout set with Y-connectors {VERSION} — generated 29-10-2026')
    return tb.replace('01 OF 01', f'{sheet:02d} OF 03')


def page(body, name):
    g.page(body, name)


def strings_on_plan(P_, marks=True):
    """snake wiring, label corners, + / − terminals and the Y-connectors with their short leads"""
    o = []
    for b, bx in enumerate(BLOCK_X):
        for half in range(2):
            s = NAMES[b][half]
            cells = snake_cells(b, half)
            pts = [P_(bx + c * (MOD_W + MGAP) + MOD_W / 2, BLOCK_Y + r * (MOD_L + MGAP) + MOD_L / 2) for r, c in cells]
            o.append(PL(pts, '#fff', 3) + PL(pts, SCOL[s], 1.2))
            if marks:
                for (r, c), corner in label_corners(cells).items():
                    x1, y1 = P_(bx + c * (MOD_W + MGAP), BLOCK_Y + r * (MOD_L + MGAP))
                    x2, y2 = P_(bx + c * (MOD_W + MGAP) + MOD_W, BLOCK_Y + r * (MOD_L + MGAP) + MOD_L)
                    o.append(corner_mark(x1, y1, x2, y2, corner))
    for m, sn, sf, sl, gap, rp, rm in mppt_pairs():
        tx = TRAY_GAP_X[gap]
        for row, pol in ((rp, '+'), (rm, '−')):
            yy = row_centre_y(row)
            for s in (sn, sf):
                b = [k for k, p in enumerate(NAMES) if s in p][0]
                c = 4 if b % 2 == 0 else 0
                px, py = P_(BLOCK_X[b] + c * (MOD_W + MGAP) + MOD_W / 2, yy)
                yx, yy_ = P_(tx, yy)
                o.append(L(px, py, yx, yy_, PLUS_COL if pol == '+' else MINUS_COL, 1.6, None if s == sn else '3,2'))
                o.append(C(px, py, 6, '#000', 0.8, '#fff') + T(px, py + 3.5, pol, 9, 'middle', 'bold'))
            yx, yy_ = P_(tx, yy)
            o.append(ysym(yx, yy_, pol))
    return ''.join(o)


def inverter_on_plan(P_, label1, label2):
    o = []
    ex, ey = P_(ROOF_W, TRAY_HY + TRAY_W / 2)
    ix, iy = P_(*INV)
    gs = 0.7
    o.append(PL([(ex, ey), (ex + 10, ey), (ex + 10, iy), (ix - 66 * gs, iy)], TRAY_COL, 5))
    o.append(equipment_group(ix, iy, gs))
    o.append(T(ix, iy + 28, label1, 7, 'middle', 'bold'))
    o.append(T(ix, iy + 37, label2, 7, 'middle'))
    return ''.join(o), (ex, ey, ix, iy, gs)


# ================================================================= L-01  PANEL LAYOUT + ELECTRICAL WIRING
def sheet_l01():
    o = [compass(80, 90)]
    ox, oy, k = 150, 110, 20.0
    pl, P_ = g.plan(ox, oy, k, labels=False, string_colours=True)
    o.append(pl)
    o.append(g.draw_trays(P_))
    o.append(strings_on_plan(P_))
    for b, bx in enumerate(BLOCK_X):
        for half in range(2):
            s = NAMES[b][half]
            m = [mm for (mm, i, ss, sl) in STRING_MAP if ss == s][0]
            lx_, ly_ = P_(bx + BW / 2, BLOCK_Y + (half * 4 + 1.5) * (MOD_L + MGAP) + MOD_L / 2)
            o.append(R(lx_ - 34, ly_ - 10, 68, 16, fill='#fff', stroke=SCOL[s], sw=1.2, rx=3) +
                     T(lx_, ly_ + 2, f'{s} · MPPT {m}', 8, 'middle', 'bold', '#111'))
        cx_, cy_ = P_(bx + BW / 2, BLOCK_Y - 0.5)
        o.append(T(cx_, cy_, f'BLOCK {b+1}', 8, 'middle', 'bold', '#1f3bb8'))
    x0, y0 = P_(0, 0)
    rx, _ = P_(RIDGE_X, 0)
    o.append(T(rx, y0 + 36 * k - 6, 'RIDGE', 8, 'middle', 'bold', '#555'))
    o.append(T(P_(RIDGE_X / 2 + 1.5, 0)[0], P_(0, 31)[1], '← WEST SLOPE', 9, 'middle', 'bold', '#555'))
    o.append(T(P_((RIDGE_X + ROOF_W) / 2, 0)[0], P_(0, 31)[1], 'EAST SLOPE →', 9, 'middle', 'bold', '#555'))
    for gap, txt in ((0, 'T1: MPPT 3 + 4 HOME RUNS'), (1, 'T2: MPPT 1 + 2 HOME RUNS')):
        tx_, ty_ = P_(TRAY_GAP_X[gap], 21.4)
        o.append(TL(tx_, ty_, [txt, '(4 x 6 SQ MM)'], 7, weight='bold', fill='#7c2d12', anchor='middle'))
    s_, _ = inverter_on_plan(P_, 'INV. GW80K-MT', '(EAST WALL, GROUND)')
    o.append(s_)

    # ---- Y-connection detail (gap 1/2; gap 3/4 identical) — stretched across the slope for clarity
    sx, sy, kx, ky = 985, 168, 55.0, 13.0
    o.append(T(sx + 95, sy - 40, 'DETAIL A — Y-CONNECTION IN GAP 1/2', 8.5, 'middle', 'bold'))
    o.append(T(sx + 95, sy - 29, '(GAP 3/4 IDENTICAL: S5/S7 = MPPT 1, S6/S8 = MPPT 2)', 6.8, 'middle'))
    b1e = BLOCK_X[0] + BW
    xl = b1e - MOD_W - 0.15

    def D(x, y):
        return sx + (x - xl) * kx, sy + (y - BLOCK_Y) * ky
    for r in range(8):
        for bx, c in ((BLOCK_X[0], 4), (BLOCK_X[1], 0)):
            x1, y1 = D(bx + c * (MOD_W + MGAP), BLOCK_Y + r * (MOD_L + MGAP))
            s = NAMES[0 if bx == BLOCK_X[0] else 1][r // 4]
            o.append(R(x1, y1, MOD_W * kx, MOD_L * ky, stroke='#1f3bb8', sw=0.8, fill=SCOL[s] + '22'))
    w1 = walkway_runs()[0]
    a, b_ = D(w1[1], BLOCK_Y)
    c_, d_ = D(w1[2], BLOCK_Y + 8 * (MOD_L + MGAP))
    o.append(R(a, b_, c_ - a, d_ - b_, stroke=WALK_STROKE, sw=0.6, fill=WALK_FILL))
    a, b_ = D(TRAY_GAP_X[0] - TRAY_W / 2, BLOCK_Y - 0.9)
    c_, d_ = D(TRAY_GAP_X[0] + TRAY_W / 2, TRAY_GAP_END)
    o.append(R(a, b_, c_ - a, d_ - b_, stroke='#7c2d12', sw=0.6, fill=TRAY_COL))
    tx0, _ = D(TRAY_GAP_X[0], 0)
    o.append(T(tx0, b_ - 4, '↑ TO NORTH TRAY', 6.5, 'middle', 'bold', '#7c2d12'))
    o.append(T((D(w1[1], 0)[0] + D(w1[2], 0)[0]) / 2, d_ + 10, 'W1', 7, 'middle', 'bold', WALK_STROKE))
    for m, sn, sf, sl, gap, rp, rm in mppt_pairs():
        if gap != 0:
            continue
        for row, pol in ((rp, '+'), (rm, '−')):
            yy = row_centre_y(row)
            col = PLUS_COL if pol == '+' else MINUS_COL
            nx, ny = D(BLOCK_X[0] + 4 * (MOD_W + MGAP) + MOD_W * 0.8, yy)
            fx, _ = D(BLOCK_X[1] + MOD_W * 0.2, yy)
            yx, _ = D(TRAY_GAP_X[0], yy)
            o.append(L(nx, ny, yx, ny, col, 1.6) + L(fx, ny, yx, ny, col, 1.6, '3,2'))
            o.append(C(nx, ny, 5, '#000', 0.8, '#fff') + T(nx, ny + 3, pol, 8, 'middle', 'bold'))
            o.append(C(fx, ny, 5, '#000', 0.8, '#fff') + T(fx, ny + 3, pol, 8, 'middle', 'bold'))
            o.append(ysym(yx, ny, pol, 5))
            o.append(T(nx - 9, ny + 3, f'{sn}{pol}', 7, 'end', 'bold', SCOL[sn]))
            o.append(T(fx + 9, ny + 3, f'{sf}{pol}', 7, 'start', 'bold', SCOL[sf]))
            wx_ = (D(w1[1], 0)[0] + D(w1[2], 0)[0]) / 2
            o.append(R(wx_ - 15, ny + 5, 30, 9, fill='#fff', stroke='none') + T(wx_, ny + 12, f'Y{pol} · M{m}', 6.2, 'middle', 'bold', col))
    lx, ly = D(BLOCK_X[0] + 2.5 * (MOD_W + MGAP), BLOCK_Y + 8 * (MOD_L + MGAP))
    o.append(T(sx - 6, ly + 20, 'BLOCK 1 (COL 5)', 6.5, 'start', 'bold', '#1f3bb8'))
    o.append(T(D(BLOCK_X[1] + MOD_W, 0)[0] + 6, ly + 20, 'BLOCK 2 (COL 1)', 6.5, 'end', 'bold', '#1f3bb8'))
    dy = ly + 34
    o.append(TL(sx - 30, dy, ['NEAR STRING (S1 / S2): MODULE LEAD PLUGS STRAIGHT INTO THE Y.',
                              f'FAR STRING (S3 / S4): {FAR_LEAD:.1f} m 4 SQ MM LEAD (DASHED), CLIPPED UNDER',
                              'THE W1 GRATING, TO THE Y. ROWS STRETCHED ACROSS THE SLOPE.'], 6.6))

    # ---- string design check
    tb, y = table(925, dy + 40, [100, 194], [
        ('MODULES / STRING', '20 (ADANI 625 Wp N-TOPCon)'),
        ('Voc @ 5 °C', '20 x 52.3 = 1,046 V  < 1,100 V  ✓'),
        ('Vmp RANGE', '723 – 880 V  (MPPT 200 – 1,000 V)  ✓'),
        ('CURRENT / MPPT', 'Y = 2 STRINGS: Imp 30.1 A ≤ 44 A ; Isc 31.9 ≤ 55 A ✓'),
        ('Y-CONNECTOR', '≥ 40 A, 1500 V DC (1.25 x 31.9 A = 39.9 A)'),
        ('HOME RUN', '6 SQ MM, ONE +/− PAIR PER MPPT'),
        ('V-DROP (6 SQ MM)', f'{min(r[9] for r in y_schedule()):.2f} – {max(r[9] for r in y_schedule()):.2f} %  (≤ 1.5 %) ✓'),
        ('STRING FUSE', 'NOT REQUIRED (2 STRINGS / MPPT)'),
    ], rh=14, size=6.8, head='STRING DESIGN CHECK')
    o.append(tb)
    o.append(TL(928, y + 12, ['⚠ MANY STANDARD MC4 Y-BRANCHES ARE RATED ONLY 30 A — BELOW THE',
                              '30.1 A THEY WILL CARRY HERE. BUY ≥ 40 A, SAME MAKE AS THE MODULE',
                              'CONNECTORS (MIXED MAKES = HOT JOINTS).'], 6.8, weight='bold', fill='#b91c1c'))

    # ---- wiring diagram (electrical) under the plan
    wx, wy = 150, 862
    o.append(T(wx, wy, 'ELECTRICAL WIRING DIAGRAM — STRINGS → Y-CONNECTORS → 6 SQ MM HOME RUN → GW80K-MT', 9, weight='bold'))
    ivx, ivy, ivw, ivh = 760, wy + 10, 140, 190
    o.append(R(ivx, ivy, ivw, ivh, sw=1.4, fill='#f0fdf4') + R(ivx + 70, ivy, 70, ivh, stroke='none', fill='#dcfce7') +
             T(ivx + 105, ivy + ivh / 2 - 6, 'GOODWE', 9, 'middle', 'bold') +
             T(ivx + 105, ivy + ivh / 2 + 7, 'GW80K-MT', 9, 'middle', 'bold') + T(ivx + 105, ivy + ivh / 2 + 19, '(EAST WALL)', 7, 'middle'))
    sch = {r[0]: r for r in y_schedule()}
    for i, (m, sn, sf, sl, gap, rp, rm) in enumerate(mppt_pairs()):
        ry = wy + 22 + i * 46
        for j, s in enumerate((sn, sf)):
            by = ry + j * 18
            o.append(R(wx, by - 7, 128, 14, stroke=SCOL[s], sw=1.2, fill=SCOL[s] + '22') +
                     T(wx + 4, by + 3, f'{s}: 20 x 625 Wp ({"EAST" if sl == "E" else "WEST"})', 6.8, weight='bold'))
            o.append(L(wx + 128, by - 3, 330, ry + 4, PLUS_COL, 1.1) + L(wx + 128, by + 3, 330, ry + 14, MINUS_COL, 1.1))
        o.append(ysym(336, ry + 4, '+', 5) + ysym(336, ry + 14, '−', 5))
        o.append(T(348, ry, 'Y+', 6.5, weight='bold', fill=PLUS_COL) + T(348, ry + 23, 'Y−', 6.5, weight='bold'))
        o.append(L(342, ry + 4, ivx, ry + 4, PLUS_COL, 2) + L(342, ry + 14, ivx, ry + 14, MINUS_COL, 2))
        p, n, vd = sch[m][7], sch[m][8], sch[m][9]
        o.append(T(575, ry + 0.5, f'6 SQ MM:  + {p:.1f} m   /   − {n:.1f} m   ·   ΔV {vd:.2f} %', 7, 'middle', 'bold'))
        o.append(T(575, ry + 24, f'IN TRAY T{gap + 1} → NORTH EDGE → EAST WALL', 6.3, 'middle', fill='#7c2d12'))
        o.append(T(ivx + 4, ry + 12, f'MPPT {m}  IN 1', 7, weight='bold'))
        o.append(T(ivx + 4, ry + 22, '(IN 2: SEAL CAP)', 5.8, fill='#555'))
    o.append(TL(60, 1080, ['NOTE: OWNER\'S MIRRORED SNAKE — + BESIDE + AND − BESIDE − ACROSS EACH GAP, SO THE TWO PARTNER STRINGS OF AN MPPT ARE JOINED RIGHT THERE BY ONE + Y AND ONE − Y. ONE 6 SQ MM',
                           '+/− PAIR PER MPPT RUNS IN THE TRAY TO THE INVERTER. EAST AND WEST NEVER SHARE AN MPPT / Y. UNUSED INVERTER INPUTS (IN 2 OF EACH MPPT) GET THE SUPPLIED SEALING CAPS.',
                           'INVERTER NOW MONITORS PER MPPT, NOT PER STRING. LENGTHS SCALED FROM THE LAYOUT IMAGE (*) — VERIFY ON SITE.'], 7.6))
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2, fill=SCOL['S1'] + '33'), 'MODULE (TINT = STRING)'),
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1) + corner_mark(x - 9, y - 6, x + 9, y + 6, 'NE', 6), f'{BRAND} LABEL CORNER (NE / SW = ROTATED 180°)'),
        (lambda x, y: L(x - 20, y, x + 20, y, SCOL['S5'], 1.6), 'STRING WIRING ORDER'),
        (lambda x, y: C(x - 10, y, 6, '#000', 0.8, '#fff') + T(x - 10, y + 3, '+', 8, 'middle', 'bold') + C(x + 10, y, 6, '#000', 0.8, '#fff') + T(x + 10, y + 3, '−', 8, 'middle', 'bold'), 'STRING + / − TERMINAL'),
        (lambda x, y: ysym(x - 10, y, '+') + ysym(x + 10, y, '−'), 'Y-CONNECTOR + / − (≥ 40 A)'),
        (lambda x, y: L(x - 20, y, x + 20, y, PLUS_COL, 1.6, '3,2'), 'FAR-STRING LEAD 4 SQ MM'),
        (lambda x, y: R(x - 20, y - 3, 40, 6, stroke='#7c2d12', fill=TRAY_COL, sw=0.8), f'DC CABLE TRAY {TRAY_SIZE}'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#555', 1.2, '10,4,2,4'), 'ROOF RIDGE'),
        (lambda x, y: sym_inverter(x, y, 22, 12), 'STRING INVERTER'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title('L-01', 'PANEL LAYOUT + ELECTRICAL WIRING (Y)', '1:200 (A3)', 1))
    page(''.join(o), 'Jain-Granite_L01_Panel-Layout-Wiring-Y_' + VERSION)


# ================================================================= L-02  WALKWAY LAYOUT
def sheet_l02():
    o = [compass(80, 90)]
    ox, oy, k = 150, 110, 20.0
    pl, P_ = g.plan(ox, oy, k)
    o.append(pl)
    o.append(draw_walkways(P_))
    x0, y0 = P_(0, 0)
    o.append(dim_h(x0, x0 + ROOF_W * k, y0 - 20, f'≈ {ROOF_W:.1f} m (ROOF WIDTH, TO BE MEASURED) *'))
    hx, hy = P_(RIDGE_X, CON_Y0 + WALK_W)
    o.append(T(hx, hy + 14, 'WC – CONNECTING WALKWAY 300 MM (STRAIGHT, JUST SOUTH OF THE ARRAYS)', 7.5, 'middle', 'bold', WALK_STROKE))
    w1 = walkway_runs()[0]
    a1x, a1y = P_(w1[2], CON_Y0 + 4.0)
    o.append(TL(a1x + 6, a1y, ['WA1 – ACCESS', '(W1 CONTINUED', ' SOUTH)'], 7.5, weight='bold', fill=WALK_STROKE))
    a2x, a2y = P_(3.4, SOUTH_Y0)
    o.append(T(a2x, a2y - 5, 'WA2 – ACCESS FROM LADDER', 7.5, 'middle', 'bold', WALK_STROKE))
    ax, ay = P_(*LADDER)
    o.append(R(ax - 26, ay - 12, 22, 24, stroke='#000', sw=1, fill='#fff') + ''.join(L(ax - 24, ay - 9 + i * 6, ax - 6, ay - 9 + i * 6, sw=0.8) for i in range(4)))
    o.append(TL(ax - 30, ay + 26, ['ROOF ACCESS', 'LADDER (SW)'], 7.5, weight='bold'))
    # Y-connector positions (for reference: leads pass under the grating there)
    for m, sn, sf, sl, gap, rp, rm in mppt_pairs():
        for row, pol in ((rp, '+'), (rm, '−')):
            yx, yy = P_(TRAY_GAP_X[gap], row_centre_y(row))
            o.append(ysym(yx, yy, pol, 4.5))
    # cleaning reach: each gap walkway serves the full width of the block on either side
    runs = walkway_runs()
    ry = BLOCK_Y + 1.2 * (MOD_L + MGAP)
    for (n, x1, x2, *_), (bl, br) in zip(runs, ((0, 1), (2, 3))):
        a1, yy = P_(x1, ry)
        a2, _ = P_(x2, ry)
        f1, _ = P_(BLOCK_X[bl], ry)
        f2, _ = P_(BLOCK_X[br] + BW, ry)
        for xa, xf in ((a1, f1), (a2, f2)):
            dx = 5 if xa > xf else -5
            o.append(L(xa, yy, xf, yy, '#16a34a', 1.6) + f'<polygon points="{xf},{yy} {xf+dx},{yy-4} {xf+dx},{yy+4}" fill="#16a34a"/>')
            mx = (xa + xf) / 2
            o.append(R(mx - 34, yy + 5, 68, 12, fill='#fff', stroke='none') + T(mx, yy + 14, 'REACH ≈ 5.8 m', 7, 'middle', 'bold', '#16a34a'))
    o.append(TL(60, 1080, ['NOTE: ONE WALKWAY PER SLOPE (IN THE GAP BETWEEN ITS TWO BLOCKS) + ONE STRAIGHT CONNECTOR JUST SOUTH OF THE ARRAYS, REACHED FROM THE SW LADDER. FARTHEST MODULE ≈ 5.8 m',
                           'FROM THE WALKWAY — CLEAN WITH A 6–7 m WATER-FED TELESCOPIC POLE. W1 / W2 RUN PARALLEL TO THE RIDGE, SO THEY ARE LEVEL. THE Y-CONNECTORS SIT IN THE SAME GAPS (ROWS 1, 4, 5, 8):',
                           'THEIR LEADS PASS UNDER THE GRATING, CLIPPED — NEVER LOOSE ON THE WALKING SURFACE. ROOF SIZE / GAPS SCALED FROM THE LAYOUT IMAGE (*) — VERIFY ON SITE.'], 7.8))
    ns, con, wa1, wa2 = walk_lengths()
    rows = [('ID', 'LOCATION', 'WIDTH', 'LENGTH')]
    for n, ln, d in ns:
        rows.append((n, d, '300 MM', f'{ln:.1f} m'))
    rows.append(('WC', 'CONNECTOR, SOUTH OF ARRAYS, W1 → W2', '300 MM', f'{con:.1f} m'))
    rows.append(('WA1', 'ACCESS: W1 CONTINUED SOUTH *', '300 MM', f'{wa1:.1f} m'))
    rows.append(('WA2', 'ACCESS: SOUTH EDGE, LADDER → WA1 *', '300 MM', f'{wa2:.1f} m'))
    tot = sum(ln for _, ln, _ in ns) + con + wa1 + wa2
    rows.append(('', 'TOTAL 300 MM WALKWAY', '', f'{tot:.1f} m'))
    rows.append(('', 'ORDER (+5 %)', '', f'{tot*1.05:.0f} m'))
    tb, y = table(940, 120, [26, 148, 42, 80], rows, rh=15, size=6.8, head='WALKWAY SCHEDULE')
    o.append(tb)
    sx, sy = 950, y + 40
    o.append(T(sx + 140, sy - 12, 'SECTION A-A (BLOCK 1 | W1 | BLOCK 2)', 9, 'middle', 'bold'))
    o.append(L(sx, sy + 70, sx + 280, sy + 70, sw=1.2))
    o.append(R(sx + 129, sy + 62, 22, 6, fill=WALK_FILL, stroke=WALK_STROKE))
    for i in range(5):
        o.append(R(sx + 2 + i * 25, sy + 54, 24, 6, stroke='#1f3bb8', fill='#dbeafe'))
        o.append(R(sx + 154 + i * 25, sy + 54, 24, 6, stroke='#1f3bb8', fill='#dbeafe'))
    px_ = sx + 140
    o.append(C(px_, sy + 14, 5) + L(px_, sy + 19, px_, sy + 44) + L(px_, sy + 44, px_ - 5, sy + 62) + L(px_, sy + 44, px_ + 5, sy + 62))
    for d in (1, -1):
        o.append(L(px_, sy + 26, px_ + d * 136, sy + 50, '#16a34a', 1.4))
    o.append(T(sx + 60, sy + 30, '≈ 5.8 m', 7.5, 'middle', 'bold', '#16a34a') + T(sx + 220, sy + 30, '≈ 5.8 m', 7.5, 'middle', 'bold', '#16a34a'))
    o.append(T(sx + 140, sy + 86, '5 MODULES | W1 | 5 MODULES', 7.5, 'middle'))
    notes = ['WALKWAY NOTES', '1. FRP / HDG STEEL ANTI-SKID GRATING, UV STABILISED,', '    MIN. 150 KG/M² RATED.',
             '2. FIX TO PURLINS WITH CLAMPS — NO SHEET PUNCTURE,', '    OR SEAL WITH EPDM WASHERS.',
             '3. ≥ 50 MM CLEAR OF MODULE FRAMES; NO SHADING.',
             '4. WA2 RUNS ALONG THE SOUTH EAVE AND THE LADDER', '    LANDING — LIFELINE / HANDRAIL THERE ONLY.',
             '5. NO TRAY CROSSINGS: TRAYS RUN NORTH, WALKWAY', '    CONNECTOR AND ACCESS RUN SOUTH (SHEET L-03).',
             '6. IF GAP 1/2 OR 3/4 MEASURES < 0.5 m, MOUNT THE', '    TRAY BENEATH THE WALKWAY.',
             '7. OUTER MODULE COLUMNS (≈ 5.8 m AWAY): INSPECTION /', '    REPLACEMENT FROM A CRAWL BOARD ON PURLIN LINES.',
             '8. Y-CONNECTORS (◉) SIT BESIDE THE TRAY IN THE GAPS:', '    FAR-STRING LEADS RUN UNDER THE GRATING IN UV',
             '    CLIPS — CHECK THEM AT EVERY CLEANING ROUND.']
    o.append(T(sx, sy + 116, notes[0], 8.5, weight='bold'))
    o.append(TL(sx, sy + 132, notes[1:], 7, lh=10.5))
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: R(x - 20, y - 4, 40, 8, stroke=WALK_STROKE, fill=WALK_FILL, sw=0.8), 'WALKWAY 300 MM (W1, W2)'),
        (lambda x, y: R(x - 20, y - 4, 40, 8, stroke=WALK_STROKE, fill=WALK_FILL, sw=0.8), 'CONNECTOR / ACCESS 300 MM (WC, WA1, WA2)'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#16a34a', 1.6), 'CLEANING REACH'),
        (lambda x, y: ysym(x - 8, y, '+', 4.5) + ysym(x + 8, y, '−', 4.5), 'Y-CONNECTOR POSITION (SEE L-01)'),
        (lambda x, y: R(x - 8, y - 8, 16, 16, sw=1) + L(x - 6, y - 3, x + 6, y - 3, sw=0.7) + L(x - 6, y + 3, x + 6, y + 3, sw=0.7), 'ROOF ACCESS LADDER'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#555', 1.2, '10,4,2,4'), 'ROOF RIDGE'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title('L-02', 'WALKWAY LAYOUT (MODULE CLEANING)', '1:200 (A3)', 2))
    page(''.join(o), 'Jain-Granite_L02_Walkway-Layout_' + VERSION)


# ================================================================= L-03  CABLE TRAY (DUCTING) + CABLE LENGTHS
def sheet_l03():
    o = [compass(80, 90)]
    ox, oy, k = 150, 110, 20.0
    pl, P_ = g.plan(ox, oy, k)
    o.append(pl)
    o.append(draw_walkways(P_, labels=False, fill='#f1f0ef', stroke='#a8a29e'))
    o.append(g.draw_trays(P_))
    segs = tray_segments_y()
    lens = {sid: ln for sid, _, _, _, _, ln in segs}
    t1x, t2x = TRAY_GAP_X
    tags = {'T1': P_(t1x - 1.3, 12.5), 'T2': P_(t2x - 1.3, 12.5), 'T3a': P_((t1x + t2x) / 2 + 3.5, TRAY_HY - 1.0),
            'T3b': P_((t2x + ROOF_W) / 2, TRAY_HY - 1.0)}
    for sid, (tx, ty) in tags.items():
        o.append(R(tx - 30, ty - 9, 60, 13, fill='#fff7ed', stroke=TRAY_COL, sw=0.8) + T(tx, ty + 1, f'{sid}  {lens[sid]:.1f} m', 7.5, 'middle', 'bold', '#7c2d12'))
    for m, sn, sf, sl, gap, rp, rm in mppt_pairs():
        for row, pol in ((rp, '+'), (rm, '−')):
            yx, yy = P_(TRAY_GAP_X[gap], row_centre_y(row))
            o.append(ysym(yx, yy, pol, 5))
            o.append(R(yx + 8, yy - 6, 30, 11, fill='#fff', stroke='none') + T(yx + 10, yy + 3, f'M{m}{pol}', 7, weight='bold', fill=PLUS_COL if pol == '+' else MINUS_COL))
    s_, (ex, ey, ix, iy, gs) = inverter_on_plan(P_, 'INV. 80 kW + DCDB + ACDB', '(EAST WALL, GROUND LEVEL)')
    o.append(s_)
    o.append(TL(ex + 16, iy + 58, [f'T4  {lens["T4"]:.1f} m', f'DOWN WALL ≈ {WALL_DROP:.0f} m', '+ ALONG WALL'], 7.5, weight='bold', fill='#7c2d12'))
    acx = ix + 66 * gs + 12
    o.append(PL([(ix + 66 * gs, iy), (acx, iy), (acx, P_(0, 19.5)[1])], '#2563eb', 3, '8,4'))
    o.append(TL(acx + 6, P_(0, 13.0)[1], ['AC: 95 SQ MM', 'AL ARMOURED', 'TO LT PANEL', '≈ 20 m *', '150 x 50 MM', 'TRAY / TRENCH'], 7.5, weight='bold', fill='#2563eb'))
    lx, ly = P_(*LA)
    o.append(sym_la(lx, ly, 0.9))

    # ---- tray schedule (right column)
    rows = [('ID', 'ROUTE', 'LENGTH', 'CABLES IN TRAY')]
    total = 0
    for sid, desc, _, cab, st, ln in segs:
        rows.append((sid, [desc[:desc.index(':') + 1], desc[desc.index(':') + 2:]], f'{ln:.1f} m', [cab, f'({st})']))
        total += ln
    rows.append(('', f'TOTAL DC TRAY {TRAY_SIZE}', f'{total:.1f} m', ''))
    rows.append(('', 'ORDER (+10 %), 2.5 m LENGTHS', f'{total*1.1:.0f} m', f'{int(-(-total*1.1 // 2.5))} LENGTHS + COVERS'))
    tb, y = table(940, 120, [26, 132, 40, 98], rows, rh=15, size=6.5, head='CABLE TRAY SCHEDULE (DC)')
    o.append(tb)

    # ---- tray section
    sx, sy = 1030, y + 48
    o.append(T(sx + 50, sy - 22, 'TRAY SECTION (T3b / T4, FULL LOAD)', 9, 'middle', 'bold'))
    s2 = 2.0
    tw, th = 50 * s2, 50 * s2
    o.append(PL([(sx, sy), (sx, sy + th), (sx + tw, sy + th), (sx + tw, sy)], '#000', 2.2))
    o.append(R(sx - 4, sy - 8, tw + 8, 5, fill='#9ca3af', stroke='#000', sw=0.8) + T(sx + tw + 8, sy - 3, 'COVER', 7))
    d6 = 6.8 * s2
    for i in range(8):
        cx_ = sx + 3 + d6 / 2 + (i % 6) * (d6 + 1)
        cy_ = sy + th - 2 - d6 / 2 - (i // 6) * (d6 + 1)
        o.append(C(cx_, cy_, d6 / 2, '#000', 0.6, PLUS_COL if i % 2 == 0 else '#111'))
    o.append(C(sx + tw - 13, sy + th - 30, 4.3 * s2, '#000', 0.6, '#16a34a'))
    o.append(L(sx, sy + th + 14, sx + tw, sy + th + 14, '#d62828', 0.8) + T(sx + tw / 2, sy + th + 26, '50 MM', 8, 'middle', fill='#d62828'))
    o.append(L(sx - 14, sy, sx - 14, sy + th, '#d62828', 0.8) + T(sx - 18, sy + th / 2, '50 MM', 8, 'middle', fill='#d62828', rot=-90))
    fill_mm2 = 8 * 3.1416 / 4 * 6.8 ** 2 + 3.1416 / 4 * 8.6 ** 2
    o.append(TL(sx - 90, sy + th + 44, ['8 x 6 SQ MM DC (Ø ≈ 6.8 MM; RED +VE, BLACK –VE)', '+ 1 x 16 SQ MM Cu EARTH (GREEN, Ø ≈ 8.6 MM)',
                                        f'FILL ≈ {fill_mm2:.0f} / 2,500 MM² ≈ {fill_mm2/25:.0f} % (LIMIT 40 %)',
                                        'WITH Y-CONNECTORS THE TRAY CARRIES HALF THE CORES', 'OF THE NO-Y DESIGN — 50 x 50 IS ENOUGH.'], 7.0))
    notes = ['CABLE TRAY NOTES', f'1. {TRAY_SIZE} PERFORATED HDG TRAY, 1.6 MM, WITH',
             '    BOLTED COVER (UV & BIRD / MONKEY PROTECTION).',
             '2. ONE SIZE THROUGHOUT, FITTINGS COMMON.',
             '3. RAISE TRAY 75–100 MM ABOVE SHEET ON PURLIN', '    CLAMPS EVERY 1.5 m; WALL BRACKETS EVERY 1.2 m.',
             '4. FITTINGS: 1 FLAT BEND, 1 TEE, 2 VERTICAL BENDS,', '    COUPLERS AT EVERY JOINT, 2 END CAPS.',
             '5. Y-CONNECTORS STAY OUTSIDE THE TRAY, CLIPPED TO', '    THE RAIL BESIDE IT, NEVER LYING IN WATER.',
             '6. BOND TRAY SECTIONS TOGETHER AND TO EP-1.',
             '7. AC CABLE IN ITS OWN TRAY / TRENCH, ≥ 300 MM FROM DC.',
             '8. LA DOWN CONDUCTOR NEVER IN OR ON THE TRAY.']
    ny = sy + th + 118
    o.append(T(sx - 90, ny, notes[0], 8.5, weight='bold'))
    o.append(TL(sx - 90, ny + 16, notes[1:], 7, lh=10.5))

    # ---- cable lengths (under the plan)
    sch = y_schedule()
    q = quantities()
    rows = [('MPPT', 'STRINGS (Y)', 'SLOPE', 'Y POSITION', '+VE 6 SQ MM', '–VE 6 SQ MM', 'LOOP', 'ΔV @ 30.1 A')]
    for m, sn, sf, sl, gap, rp, rm, p, n, vd in sch:
        rows.append((f'MPPT {m}', f'{sn} + {sf}', 'EAST' if sl == 'E' else 'WEST', f'GAP {2*gap+1}/{2*gap+2}, ROW {rp+1} / {rm+1}',
                     f'{p:.1f} m', f'{n:.1f} m', f'{p+n:.1f} m', f'{vd:.2f} %'))
    rows.append(('TOTAL', '', '', '', f'{sum(r[7] for r in sch):.1f} m', f'{sum(r[8] for r in sch):.1f} m', f'{q["hr6"]:.1f} m', ''))
    tb, y = table(150, 858, [46, 64, 38, 112, 66, 66, 52, 56], rows, rh=14, size=6.8, head='DC HOME-RUN CABLE LENGTHS (ONE +/− PAIR PER MPPT, 6 SQ MM)')
    o.append(tb)
    o.append(TL(152, y + 11, [f'EACH RUN = Y → TRAY NORTH → NORTH EDGE → DOWN EAST WALL ({WALL_DROP:.0f} m) → INVERTER, + {Y_SLACK:.1f} m SLACK AT THE Y + {TAIL_INV:.1f} m AT THE INVERTER.',
                              f'ΔV = 30.1 A x {R6*1000:.2f} mΩ/m x LOOP ÷ {VMP:.0f} V (STC). 4 SQ MM STRING-LEVEL LEADS ADD < 0.02 %.'], 6.6))
    rows = [('ITEM', 'SPEC', 'QTY', 'ORDER'),
            ('HOME RUNS', '6 SQ MM SOLAR DC (RED + / BLACK −)', f'{q["hr6"]:.0f} m', f'{q["hr6_order"]} m'),
            ('FAR-STRING LEADS', f'4 SQ MM, 8 x {FAR_LEAD:.1f} m (S3, S4, S7, S8 ±)', f'{q["far"]:.0f} m', ''),
            ('ROW-TURN JUMPERS', f'4 SQ MM, {8*ROW_TURNS} x {JUMPER_LEN} m (3 / STRING)', f'{q["jump"]:.0f} m', ''),
            ('4 SQ MM TOTAL', 'LEADS + JUMPERS', f'{q["c4"]:.0f} m', f'{q["c4_order"]} m'),
            ('Y-CONNECTOR SET', '1 x + (M-M-F) & 1 x − (F-F-M), ≥ 40 A', '4 SETS', '4 + 1 SPARE'),
            ('MC4 PAIRS', f'HOME RUNS {q["mc4_hr"]} + LEADS {q["mc4_far"]} + JUMPERS {q["mc4_jump"]}',
             f'{q["mc4_hr"] + q["mc4_far"] + q["mc4_jump"]}', f'{round((q["mc4_hr"] + q["mc4_far"] + q["mc4_jump"]) * 1.1 + 0.499)}')]
    tb, y2 = table(668, 858, [82, 156, 34, 50], rows, rh=14, size=6.3, head='DC CABLE & CONNECTOR QUANTITIES')
    o.append(tb)
    cost = q['hr6_order'] * RATES['6'] + q['c4_order'] * RATES['4']
    o.append(T(670, y2 + 11, f'CABLE ≈ ₹{cost:,.0f} ({q["hr6_order"]} m x ₹84 + {q["c4_order"]} m x ₹58).', 6.6, weight='bold'))
    o.append(TL(60, 1080, ['NOTE: TRAYS T1 / T2 SIT IN THE ≈ 0.6 m GAPS BESIDE WALKWAYS W1 / W2; THE Y-CONNECTORS (◉, SEE L-01) SIT BESIDE THEM AT ROWS 1, 4, 5 AND 8. TRAYS RUN NORTH, WALKWAY',
                           'CONNECTOR RUNS SOUTH — NO CROSSINGS. GAPS AND ROOF SIZE SCALED FROM THE LAYOUT IMAGE (*) — VERIFY ON SITE AND RE-CUT THE HOME RUNS TO THE MEASURED ROUTE.',
                           'LA DOWN CONDUCTOR CROSSES T3a ONCE, AT 90°, RAISED ≥ 0.5 m ON AN INSULATED STAND-OFF, THEN RUNS ≥ 1 m NORTH OF THE TRAY (SEE CEIG SHEET 03).'], 7.6))
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: R(x - 20, y - 3, 40, 6, stroke='#7c2d12', fill=TRAY_COL, sw=0.8), f'DC CABLE TRAY {TRAY_SIZE}'),
        (lambda x, y: ysym(x - 10, y, '+', 5) + ysym(x + 10, y, '−', 5), 'Y-CONNECTOR + / − (M = MPPT)'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#2563eb', 3, '8,4'), 'AC CABLE ROUTE (95 SQ MM AL)'),
        (lambda x, y: R(x - 20, y - 4, 40, 8, stroke='#a8a29e', fill='#f1f0ef', sw=0.8), 'WALKWAY (SEE L-02)'),
        (lambda x, y: sym_la(x, y + 2, 0.6), 'LIGHTNING ARRESTER'),
        (lambda x, y: sym_inverter(x, y, 22, 12), 'STRING INVERTER'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title('L-03', 'CABLE TRAY + DC CABLE LENGTHS (Y)', '1:200 (A3)', 3))
    page(''.join(o), 'Jain-Granite_L03_Cable-Tray-Lengths-Y_' + VERSION)


if __name__ == '__main__':
    sheet_l01()
    sheet_l02()
    sheet_l03()
    for r in y_schedule():
        print(f'MPPT {r[0]} {r[1]}+{r[2]}  +{r[7]:.1f}  -{r[8]:.1f}  loop {r[7]+r[8]:.1f}  dV {r[9]:.2f}%')
    print(quantities())
