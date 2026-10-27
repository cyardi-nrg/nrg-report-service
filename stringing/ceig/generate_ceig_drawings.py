# Version: v2 (2026-10-27) — adds 04 Walkway Layout, 05 Cable Tray Layout; block gaps re-read from photo
# CEIG drawing set for Jain Granite & Marble — 100 kWp rooftop (Adani 625 Wp TOPCon x 160,
# GoodWe GW80K-MT). Follows NRG's own CEIG submission format (Energy Pack SLD / Equipment
# Layout / Earthing Layout samples): A3 landscape, title block on the right.
#
# Produces three HTML pages (one inline SVG each); render_pdf.js prints them to PDF.
#   python3 generate_ceig_drawings.py && node render_pdf.js
#
# Every value that is an estimate (cable lengths, roof size, module electricals scaled from the
# 620 W datasheet, inverter max AC current) is marked with * on the sheet.

import html
import os

OUT = os.path.dirname(os.path.abspath(__file__))
VERSION = 'v2'
FONT = 'Liberation Sans, Arial, Helvetica, sans-serif'

# ---------------------------------------------------------------- project data
P = {
    'client': 'JAIN GRANITE & MARBLE',
    'epc': 'NRG TECHNOLOGISTS PVT LTD',
    'epc_addr': '989/6, GIDC Makarpura, Vadodara',
    'title': '100.00 kWp (DC)_ROOFTOP SOLAR PLANT',
    'date': '27-10-26',
    'paper': 'A3',
}
SYSTEM = [
    ('SITE LOCATION', '— (LAT, LONG TO BE ADDED)'),
    ('DC CAPACITY', '100.00 kWp'),
    ('TOTAL PLANT CAPACITY (AC)', '80 kW'),
    ('DC / AC RATIO', '1.25'),
    ('MODULE CAPACITY', '625 Wp (ADANI N-TOPCon)'),
    ('MODULE DIMENSION (L X W X H)', '2382 X 1134 X 30 mm *'),
    ('TOTAL PV MODULES', '160 Nos.'),
    ('INVERTER CAPACITY', '80 kW (GOODWE GW80K-MT) 1 No.'),
    ('AZIMUTH / TILT', 'EAST-WEST (90° / 270°), ROOF SLOPE'),
]
# strings in inverter-input order: (MPPT, input, string, slope)
STRING_MAP = [(1, 1, 'S5', 'E'), (1, 2, 'S7', 'E'), (2, 1, 'S6', 'E'), (2, 2, 'S8', 'E'),
              (3, 1, 'S1', 'W'), (3, 2, 'S3', 'W'), (4, 1, 'S2', 'W'), (4, 2, 'S4', 'W')]

# ---------------------------------------------------------------- svg helpers
W, H = 1680, 1188          # A3 landscape at 4 units per mm
TB_X0, TB_X1 = 1262, 1650   # right-hand title column
FR = (30, 30, 1650, 1158)   # inner frame


def esc(s):
    return html.escape(str(s), quote=True)


def T(x, y, s, size=9, anchor='start', weight='normal', fill='#000', italic=False, rot=None):
    tr = f' transform="rotate({rot} {x} {y})"' if rot is not None else ''
    st = ' font-style="italic"' if italic else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}"'
            f' fill="{fill}"{st}{tr}>{esc(s)}</text>')


def TL(x, y, lines, size=9, lh=None, **kw):
    lh = lh or size * 1.25
    return ''.join(T(x, y + i * lh, s, size, **kw) for i, s in enumerate(lines))


def R(x, y, w, h, stroke='#000', sw=1, fill='none', dash=None, rx=0):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}"{d}/>'


def L(x1, y1, x2, y2, stroke='#000', sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def PL(pts, stroke='#000', sw=1, dash=None, fill='none'):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    return f'<polyline points="{p}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}"{d} stroke-linejoin="round"/>'


def C(x, y, r, stroke='#000', sw=1, fill='none', dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ''
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" stroke="{stroke}" stroke-width="{sw}" fill="{fill}"{d}/>'


def table(x, y, col_w, rows, rh=16, size=8, head=None, head_size=10, bold_first=False, wrap_rows=None):
    """Simple bordered table. rows: list of tuples; a cell may be a list of lines."""
    out = []
    cy = y
    tw = sum(col_w)
    if head:
        out.append(R(x, cy, tw, rh + 4, sw=1))
        out.append(T(x + tw / 2, cy + rh - 1, head, head_size, 'middle', 'bold'))
        cy += rh + 4
    for row in rows:
        lines_n = max(len(c) if isinstance(c, list) else 1 for c in row)
        h = max(rh, lines_n * (size + 2) + 6)
        cx = x
        for i, (cell, w) in enumerate(zip(row, col_w)):
            out.append(R(cx, cy, w, h, sw=0.8))
            lines = cell if isinstance(cell, list) else [cell]
            ty = cy + (h - len(lines) * (size + 2)) / 2 + size
            for k, s in enumerate(lines):
                out.append(T(cx + 4, ty + k * (size + 2), s, size,
                             weight='bold' if (bold_first and i == 0) else 'normal'))
            cx += w
        cy += h
    return ''.join(out), cy


# ---------------------------------------------------------------- symbols
def sym_module(x, y, w=22, h=13):
    return R(x - w / 2, y - h / 2, w, h, stroke='#1f3bb8', sw=1.2) + L(x - w / 2, y + h / 2, x + w / 2, y - h / 2, '#1f3bb8', 0.8)


def sym_inverter(x, y, w=26, h=16):
    return (R(x - w / 2, y - h / 2, w, h, fill='#22c55e', sw=1) + L(x - w / 2, y + h / 2, x + w / 2, y - h / 2, '#000', 0.8))


def sym_earth(x, y, s=1.0):
    return (L(x, y, x, y + 8 * s) + L(x - 9 * s, y + 8 * s, x + 9 * s, y + 8 * s, sw=1.4) +
            L(x - 6 * s, y + 11 * s, x + 6 * s, y + 11 * s, sw=1.2) + L(x - 3 * s, y + 14 * s, x + 3 * s, y + 14 * s))


def sym_breaker(x, y, box=False):
    """vertical circuit breaker centred on (x, y), 28 tall"""
    s = (R(x - 2, y - 7, 4, 14, stroke='none', fill='#fff') +   # break the feeder line at the contacts
         L(x, y - 14, x, y - 7) + L(x, y + 7, x, y + 14) + L(x, y + 7, x - 8, y - 6) +
         L(x - 3, y - 10, x + 3, y - 4) + L(x - 3, y - 4, x + 3, y - 10))
    if box:
        s += R(x - 12, y - 12, 18, 24, sw=0.7, dash='3,2')
    return s


def sym_contactor(x, y):
    return (R(x - 2, y - 7, 4, 14, stroke='none', fill='#fff') +
            L(x, y - 14, x, y - 7) + L(x, y + 7, x, y + 14) + L(x, y + 7, x - 8, y - 6) +
            f'<path d="M {x-4} {y-7} A 4 4 0 0 1 {x+4} {y-7}" stroke="#000" fill="none"/>')


def sym_spd(x, y):  # horizontal, centred
    return (R(x - 9, y - 6, 18, 12, sw=1) + L(x - 5, y + 3, x + 5, y - 3) +
            f'<path d="M {x+5} {y-3} l -4 0 m 4 0 l 0 4" stroke="#000" fill="none"/>')


def sym_meter(x, y, s=30):
    return R(x - s / 2, y - s / 2, s, s, sw=1.2) + C(x, y, s * 0.36, sw=1.2)


def sym_lamp(x, y, col):
    return C(x, y, 6, fill=col, sw=0.8) + L(x - 4, y - 4, x + 4, y + 4, sw=0.6) + L(x - 4, y + 4, x + 4, y - 4, sw=0.6)


def sym_cable(x1, x2, y, col='#000'):
    cx, rx = (x1 + x2) / 2, (x2 - x1) / 2
    return f'<ellipse cx="{cx:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="6" stroke="{col}" fill="none" stroke-width="1"/>'


def sym_la(x, y, s=1.0, col='#d62828'):
    return (L(x, y, x, y - 14 * s, col, 1.6) + L(x, y, x - 12 * s, y + 7 * s, col, 1.6) +
            L(x, y, x + 12 * s, y + 7 * s, col, 1.6) + C(x, y, 3 * s, col, 1, '#fff'))


def sym_pit(x, y):
    return R(x - 8, y - 8, 16, 16, stroke='#0a6a20', sw=1.2, fill='#e8f5e9') + C(x, y, 4, '#0a6a20', 1, '#0a6a20')


def sym_fire(x, y):
    return C(x, y, 6, sw=1) + L(x - 11, y, x + 11, y) + L(x, y - 9, x, y - 6) + f'<path d="M {x+11} {y} l -4 -3 m 4 3 l -4 3" stroke="#000" fill="none"/>'


def compass(x, y, r=26):
    return (C(x, y, r, sw=1) + f'<polygon points="{x},{y-r+2} {x-6},{y} {x+6},{y}" fill="#000"/>' +
            f'<polygon points="{x},{y+r-2} {x-6},{y} {x+6},{y}" fill="#fff" stroke="#000"/>' +
            L(x - r + 2, y, x + r - 2, y, sw=0.8) +
            T(x, y - r - 3, 'N', 10, 'middle', 'bold') + T(x, y + r + 11, 'S', 9, 'middle') +
            T(x + r + 4, y + 3, 'E', 9) + T(x - r - 10, y + 3, 'W', 9))


# ---------------------------------------------------------------- title block
def title_block(dwg_no, dwg_name, scale):
    x0, x1 = TB_X0, TB_X1
    w = x1 - x0
    o = [L(x0, FR[1], x0, FR[3], sw=1.4)]
    y = 790
    o.append(L(x0, y, x1, y))
    o.append(T(x0 + 4, y + 13, 'CUSTOMER SIGN AND STAMP:', 8))
    y = 860
    # revision table
    cols = [26, 52, 150, 54, 54, 52]
    hdr = ['REV.', 'DATE', 'DESCRIPTION', 'DRAWN BY', 'CHECKED BY', 'APPROVED BY']
    r0 = ['R0', P['date'], 'FIRST ISSUE', '', '', '']
    for rowi, row in enumerate([r0, hdr]):
        cx = x0
        for c, s in zip(cols, row):
            o.append(R(cx, y, c, 14, sw=0.6))
            o.append(T(cx + c / 2, y + 10, s, 6.5 if rowi else 7, 'middle'))
            cx += c
        y += 14
    rows = [('CLIENT:', [P['client']], 40, 11), ('EPC CONTRACTOR:', [P['epc'], P['epc_addr']], 40, 10),
            ('DESIGN BY:', [P['epc'], P['epc_addr']], 40, 10)]
    for lab, val, h, fs in rows:
        o.append(R(x0, y, w, h, sw=0.8))
        o.append(L(x0 + 78, y, x0 + 78, y + h, sw=0.8))
        o.append(T(x0 + 39, y + h / 2 + 3, lab, 7.5, 'middle'))
        o.append(T(x0 + 78 + (w - 78) / 2, y + h / 2 + (0 if len(val) > 1 else 4), val[0], fs, 'middle', 'bold'))
        if len(val) > 1:
            o.append(T(x0 + 78 + (w - 78) / 2, y + h / 2 + 12, val[1], 7, 'middle'))
        y += h
    for lab, val in (('DRAWING NO.:', dwg_no), ('DRAWING NAME:', dwg_name), ('PROJECT TITLE:', P['title'])):
        o.append(R(x0, y, w, 24, sw=0.8))
        o.append(T(x0 + 3, y + 8, lab, 6.5))
        o.append(T(x0 + 4, y + 20, val, 10, weight='bold' if lab == 'DRAWING NAME:' else 'normal'))
        y += 24
    # released for + scale
    o.append(R(x0, y, w, 26, sw=0.8))
    o.append(L(x1 - 48, y, x1 - 48, y + 26, sw=0.8))
    o.append(T(x0 + 3, y + 8, 'RELEASED FOR:', 6.5))
    cx = x0 + 4
    for s in ('PRELIMINARY', 'TENDER', 'REVISION', 'FABRICATION', 'CONSTRUCTION', 'APPROVAL'):
        o.append(R(cx, y + 14, 6, 6, sw=0.7, fill='#000' if s == 'APPROVAL' else 'none'))
        o.append(T(cx + 8, y + 20, s, 5.5))
        cx += 8 + len(s) * 3.2 + 6
    o.append(T(x1 - 24, y + 9, 'SCALE', 6.5, 'middle'))
    o.append(T(x1 - 24, y + 21, scale, 8, 'middle', 'bold'))
    y += 26
    cols = [62, 62, 62, 66, 66, 70]
    hdr = ['DESIGN BY', 'DRAWN BY', 'CHECKED BY', 'APPROVED BY', 'PAPER SIZE', 'SHEET NO.']
    val = ['', '', '', '', P['paper'], '01 OF 01']
    cx = x0
    for c, a, b in zip(cols, hdr, val):
        o.append(R(cx, y, c, FR[3] - y, sw=0.8))
        o.append(T(cx + c / 2, y + 9, a, 6.5, 'middle'))
        o.append(T(cx + c / 2, y + 21, b or '________', 7.5, 'middle', 'bold' if b else 'normal', '#000' if b else '#999'))
        o.append(T(cx + c / 2, y + 30, P['date'] if not b else '', 6.5, 'middle'))
        cx += c
    o.append(T(x1 - 4, FR[3] + 12, f'NRG CEIG drawing set {VERSION} — generated 27-10-2026', 7, 'end', fill='#777'))
    return ''.join(o)


def legend_block(y, title, rows, rh=18):
    x0, x1 = TB_X0, TB_X1
    o = [T((x0 + x1) / 2, y + 12, title, 10, 'middle', 'bold'), L((x0 + x1) / 2 - 40, y + 14, (x0 + x1) / 2 + 40, y + 14, sw=0.8)]
    y += 20
    for sym, txt in rows:
        o.append(R(x0 + 4, y, 90, rh, sw=0.6) + R(x0 + 94, y, x1 - x0 - 98, rh, sw=0.6))
        o.append(sym(x0 + 49, y + rh / 2))
        o.append(T(x0 + 100, y + rh / 2 + 3, txt, 7.5))
        y += rh
    return ''.join(o), y


def system_block(y):
    x0, x1 = TB_X0, TB_X1
    o = [T((x0 + x1) / 2, y + 12, 'SYSTEM DESCRIPTION', 10, 'middle', 'bold'), L((x0 + x1) / 2 - 58, y + 14, (x0 + x1) / 2 + 58, y + 14, sw=0.8)]
    y += 20
    for a, b in SYSTEM:
        o.append(R(x0 + 4, y, 150, 14, sw=0.5) + R(x0 + 154, y, x1 - x0 - 158, 14, sw=0.5))
        o.append(T(x0 + 8, y + 10, a, 7))
        o.append(T(x0 + 158, y + 10, b, 7))
        y += 14
    return ''.join(o), y


def page(svg_body, name):
    frame = (R(15, 15, W - 30, H - 30, sw=1.2) + R(FR[0], FR[1], FR[2] - FR[0], FR[3] - FR[1], sw=1.6))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="420mm" height="297mm" '
           f'font-family="{FONT}">' + R(0, 0, W, H, stroke='none', fill='#fff') + frame + svg_body + '</svg>')
    doc = ('<!doctype html><html><head><meta charset="utf-8"><title>' + esc(name) + '</title>'
           '<style>@page{size:420mm 297mm;margin:0}html,body{margin:0;padding:0;background:#fff}svg{display:block}</style>'
           '</head><body>' + svg + '</body></html>')
    with open(os.path.join(OUT, name + '.html'), 'w', encoding='utf-8') as f:
        f.write(doc)


# ================================================================= 01  SLD
def sheet_sld():
    o = []
    cx = 720            # solar chain centre line
    gx = 920            # grid incomer line
    RED = '#d62828'

    # ---- grid / net meter / LT panel
    o.append(L(gx, 62, gx, 200, RED, 1.6))
    o.append(f'<polygon points="{gx},52 {gx-6},64 {gx+6},64" fill="{RED}"/>')
    o.append(T(gx, 46, 'TO GRID (DISCOM, 415 V, 3Ø, 50 Hz)', 9, 'middle', 'bold'))
    o.append(R(gx - 16, 88, 32, 32, fill='#fff', sw=1.2) + C(gx, 104, 11, sw=1.2))
    o.append(TL(gx - 22, 100, ['NET METER', '(BI-DIRECTIONAL, BY DISCOM)'], 7.5, anchor='end'))
    o.append(R(470, 140, 520, 190, dash='6,4', sw=1))
    o.append(T(476, 153, 'CLIENT LT PANEL (EXISTING)', 8.5, 'start', 'bold'))
    o.append(sym_breaker(gx, 170, box=True))
    o.append(TL(gx + 16, 166, ['EXISTING MAIN', 'BREAKER'], 7))
    o.append(L(510, 200, 960, 200, '#000', 4))
    o.append(T(512, 194, '415 V, TPN BUS BAR (EXISTING)', 7.5))
    for lx in (540, 600):
        o.append(L(lx, 200, lx, 296, RED, 1.2) + sym_breaker(lx, 240) + f'<polygon points="{lx},306 {lx-5},296 {lx+5},296" fill="#000"/>')
        o.append(T(lx, 320, 'LOAD', 7.5, 'middle'))
    o.append(T(570, 275, 'EXISTING', 6.5, 'middle') + T(570, 284, 'LOADS', 6.5, 'middle'))
    o.append(L(cx, 200, cx, 380, RED, 1.6))
    o.append(sym_breaker(cx, 252, box=True))
    o.append(TL(cx + 18, 242, ['160 A, 415 V, 4P MCCB', 'O/C, S/C  (SOLAR FEEDER – NEW)', 'Icu ≥ FAULT LEVEL AT LT PANEL *'], 7.5))

    # ---- solar generation meter
    o.append(R(cx - 80, 352, 160, 56, sw=1, stroke='#1f3bb8'))
    o.append(sym_meter(cx, 380, 30))
    o.append(T(cx + 78, 362, 'SOLAR METER', 7.5, 'end', 'bold'))
    o.append(T(cx - 76, 404, 'GENERATION METER (AS PER DISCOM/GEDA)', 6, 'start'))
    o.append(L(cx, 408, cx, 500, RED, 1.6))
    o.append(sym_cable(cx - 28, cx + 28, 450))
    o.append(TL(cx + 36, 438, ['1.1 KV, 1R X 3.5C x 95 SQ.MM', 'AL. XLPE INSULATED, ARMOURED CABLE', '(CABLE LENGTH : ≈ 20 M *)  (MAX. CABLE LENGTH : 25 M)'], 7.5))

    # ---- ACDB
    o.append(R(560, 500, 380, 200, dash='6,4', sw=1, stroke='#c026d3'))
    o.append(R(820, 500, 120, 26, sw=1, stroke='#c026d3'))
    o.append(T(880, 512, 'ACDB', 9, 'middle', 'bold'))
    o.append(T(880, 522, 'OUTDOOR TYPE 1 IN / 1 OUT', 6, 'middle'))
    o.append(L(cx, 500, cx, 700, RED, 1.6))
    # SPD branch
    o.append(L(cx, 540, cx - 52, 540) + sym_spd(cx - 62, 540) + L(cx - 71, 540, cx - 90, 540) + sym_earth(cx - 90, 540, 0.7))
    o.append(TL(cx - 146, 562, ['AC SPD, 3Ø + N', 'Uc 320 V, 40 kA', 'TYPE : 2'], 7))
    # lamps
    for i, (c, lab) in enumerate((('#22c55e', 'ON'), ('#ef4444', 'OFF'))):
        o.append(sym_lamp(cx + 30 + i * 22, 548, c) + T(cx + 30 + i * 22, 566, lab, 6.5, 'middle'))
    for i, (c, lab) in enumerate((('#ef4444', 'R'), ('#facc15', 'Y'), ('#2563eb', 'B'))):
        o.append(sym_lamp(cx + 92 + i * 22, 548, c) + T(cx + 92 + i * 22, 566, lab, 6.5, 'middle'))
    o.append(sym_contactor(cx, 598) + TL(cx + 14, 596, ['CONTACTOR', '160 A, 4P'], 7))
    o.append(R(cx + 40, 616, 34, 16, sw=1) + T(cx + 57, 628, 'NVR', 7.5, 'middle', 'bold') + L(cx + 6, 624, cx + 40, 624, dash='2,2'))
    o.append(sym_breaker(cx, 664, box=True) + TL(cx + 18, 658, ['160 A, 415 V', '4P MCCB', 'O/C, S/C'], 7))
    o.append(L(940, 640, 960, 640) + sym_earth(960, 640, 0.8) + T(948, 672, 'EARTHING (EP-2)', 6.5))

    # ---- inverter -> ACDB cable
    o.append(L(cx, 700, cx, 762, RED, 1.6))
    o.append(sym_cable(cx - 28, cx + 28, 726))
    o.append(TL(cx + 36, 716, ['1.1 KV, 1R X 3.5C x 95 SQ.MM AL. XLPE INSULATED,', 'ARMOURED CABLE (CABLE LENGTH : ≈ 3 M *)'], 7.5))

    # ---- inverter
    ix0, ix1, iy0, iy1 = 450, 1010, 762, 880
    o.append(T(ix0, iy0 - 6, 'INV. – 80 kW GOODWE GW80K-MT', 10, weight='bold'))
    o.append(R(ix0, iy0, ix1 - ix0, iy1 - iy0, sw=1.4))
    o.append(L(ix0, iy1, ix1, iy0, sw=1))
    o.append(f'<path d="M {ix1-120} {iy0+34} q 14 -22 28 0 t 28 0" stroke="#000" fill="none" stroke-width="1.4"/>')
    o.append(L(ix0 + 50, iy1 - 52, ix0 + 110, iy1 - 52, sw=1.4) + L(ix0 + 50, iy1 - 40, ix0 + 110, iy1 - 40, sw=1.4, dash='8,5'))
    o.append(L(ix0, 820, ix0 - 20, 820) + sym_earth(ix0 - 20, 820, 0.8) + T(ix0 - 34, 850, 'EP-2', 6.5))
    sec = (ix1 - ix0) / 4
    col_x = {}
    for m in range(4):
        sx = ix0 + m * sec
        o.append(R(sx, iy1, sec, 18, sw=0.8) + T(sx + sec / 2, iy1 + 13, f'MPPT {m+1}', 8, 'middle', 'bold'))
        for i in range(4):
            px = sx + sec / 8 + i * sec / 4
            o.append(R(sx + i * sec / 4, iy1 + 18, sec / 4, 14, sw=0.5) + T(px, iy1 + 28, str(i + 1), 7, 'middle',
                                                                             'bold' if i < 2 else 'normal', '#000' if i < 2 else '#999'))
            if i < 2:
                col_x[(m + 1, i + 1)] = px
    o.append(T(ix1 + 4, iy1 + 28, 'INPUTS 3, 4: SPARE', 6.5, fill='#555'))

    # ---- DCDB
    dy0, dy1 = 940, 1010
    o.append(R(ix0, dy0, ix1 - ix0, dy1 - dy0, stroke='#ea580c', sw=1))
    o.append(L(ix0, dy0 + 16, ix1, dy0 + 16, '#ea580c', 0.8))
    o.append(T(ix0 + 6, dy0 + 11, 'DCDB (8 IN / 8 OUT), IP65, 1500 V DC RATED  —  PER STRING: DC SPD 1200 V, 40 kA, TYPE 2  +  DC MCB 25 A, 1200 V DC (2P)', 7.5, weight='bold'))
    o.append(L(ix1, 985, ix1 + 16, 985) + sym_earth(ix1 + 16, 985, 0.8) + T(ix1 + 4, 1014, 'EP-1', 6.5))

    # ---- strings
    for (m, i, s, slope) in STRING_MAP:
        x = col_x[(m, i)]
        o.append(L(x, iy1 + 32, x, dy0, '#000', 1) + L(x, dy0 + 16, x, 1112, '#000', 1))
        o.append(f'<g transform="translate({x-7},{964})">' + R(0, 0, 14, 10, sw=0.8) + L(3, 8, 11, 2, sw=0.7) + '</g>')   # SPD
        o.append(f'<path d="M {x} {986} l -5 6 m 5 -6 l 0 14" stroke="#000" fill="none"/>' + L(x - 3, 988, x + 3, 982, sw=0.8))  # MCB
        o.append(sym_module(x, 1046, 16, 10) + T(x - 10, 1049, '20', 6.5, 'end'))
        o.append(sym_module(x, 1060, 16, 10) + T(x - 10, 1063, '19', 6.5, 'end'))
        o.append(L(x - 6, 1072, x + 6, 1072) + L(x - 6, 1076, x + 6, 1076))
        o.append(sym_module(x, 1088, 16, 10) + T(x - 10, 1091, '2', 6.5, 'end'))
        o.append(sym_module(x, 1102, 16, 10) + T(x - 10, 1105, '1', 6.5, 'end'))
        o.append(T(x, 1124, s, 10, 'middle', 'bold') + T(x, 1135, f'({slope})', 6.5, 'middle'))
    o.append(sym_cable(ix0 + 8, ix1 - 8, 1026, '#16a34a'))
    o.append(TL(ix1 + 6, 1022, ['1R X 1C X 4 SQ.MM XLPO UV Cu.', 'CABLE (EN 50618) FOR +VE & –VE', '(EACH STRING ITS OWN PAIR)'], 7))
    o.append(T(ix0 - 6, 1148, 'E = EAST SLOPE, W = WEST SLOPE.  20 MODULES PER STRING, 8 STRINGS = 160 MODULES', 7, 'start', fill='#333'))

    # ---- left column: note, cable details, string table, design check
    o.append(R(44, 46, 380, 64, sw=1))
    o.append(TL(50, 60, ['* NOTE:', '1. VALUES MARKED * ARE ESTIMATES — VERIFY WITH DATASHEET / ON SITE.',
                         '2. DG SET / CHANGEOVER: NONE CONSIDERED. CONFIRM ON SITE; IF A DG',
                         '    EXISTS, ADD CHANGEOVER + INTERLOCK (SOLAR OFF ON DG).'], 7.5))
    tb, y = table(44, 124, [118, 58, 100, 104], [
        (['CABLE SIZE'], ['CURRENT', 'RATING'], ['CABLE', 'CONNECTION'], ['CABLE TYPE']),
        (['1.1 KV, 1R X 3.5C', 'X 95 SQ MM'], ['216 A **'], ['INVERTER TO', 'ACDB'], ['AL. XLPE INSULATED', 'ARMOURED CABLE']),
        (['1.1 KV, 1R X 3.5C', 'X 95 SQ MM'], ['216 A **'], ['ACDB TO CLIENT', 'LT PANEL'], ['AL. XLPE INSULATED', 'ARMOURED CABLE']),
        (['1R X 1C X 4 SQ MM'], ['55 A **'], ['MODULE TO', 'DCDB / INVERTER'], ['XLPO UV Cu. CABLE', 'FOR +VE & –VE']),
        (['1R X 1C X 16 SQ MM'], ['—'], ['PV STRUCTURE', 'TO EP-1'], ['Cu EARTH CABLE']),
        (['1R X 1C X 25 SQ MM'], ['—'], ['INVERTER / ACDB', 'TO EP-2'], ['Cu EARTH CABLE']),
        (['1R X 1C X 50 SQ MM'], ['—'], ['LA TO EP-3'], ['Cu EARTH CABLE']),
    ], rh=18, size=7.5, head='CABLE DETAILS', bold_first=False)
    o.append(tb)
    o.append(TL(46, y + 10, ['** CATALOGUE RATING IN AIR. DESIGN CURRENT: AC 1.25 x 127 A = 159 A;',
                             '    DC 1.25 x 15.96 A = 20 A PER STRING. CHECK WITH CABLE MAKER\'S TABLE.'], 6.8))
    rows = [('MPPT', 'INPUT', 'STRING', 'MODULES', 'SLOPE')] + [(str(m), str(i), s, '20', 'EAST' if sl == 'E' else 'WEST') for m, i, s, sl in STRING_MAP]
    tb, y2 = table(44, y + 34, [60, 60, 70, 80, 110], rows, rh=15, size=7.5, head='STRING / MPPT SCHEDULE')
    o.append(tb)
    tb, y3 = table(44, y2 + 14, [190, 190], [
        ('Voc @ 5 °C (20 x 52.3 V)', '1,046 V  <  1,100 V  ✓'),
        ('Vmp @ 70 °C / STC / 5 °C', '723 / 832 / 880 V  (200–1000 V) ✓'),
        ('CURRENT PER MPPT (Imp / Isc)', '30.1 A ≤ 44 A  /  31.9 A ≤ 55 A ✓'),
        ('DC VOLTAGE DROP (4 SQ MM)', '0.52 % – 1.03 % *'),
        ('AC VOLTAGE DROP (95 SQ MM AL)', '≈ 0.45 % *'),
        ('STRING FUSE', 'NOT REQUIRED (≤ 2 STRINGS / MPPT)'),
    ], rh=15, size=7.3, head='DESIGN CHECK')
    o.append(tb)

    # ---- inverter + module legends
    lx = 1030
    tb, y = table(lx, 46, [118, 106], [
        ('TOTAL PLANT SIZE', '100.00 kWp'), ('NO. OF INVERTER', '1'), ('INVERTER MODEL', 'GW80K-MT'),
        ('AC POWER', '80 kW'), ('MAX. DC VOLTAGE', '1100 V'), (['MPPT VOLTAGE', 'RANGE'], '200 – 1000 V'),
        ('NO. OF MPPT / INPUTS', '4 / 16'), (['DC I/P CURRENT', 'PER MPPT'], '44 A'), (['MAX. DC SHORT CKT', 'CURRENT PER MPPT'], '55 A'),
        (['MAX. AC O/P', 'CURRENT'], '127 A *'),
    ], rh=17, size=7.5, head='INVERTER LEGEND')
    o.append(tb)
    tb, y = table(lx, y + 14, [118, 106], [
        ('MODULE POWER', '625 Wp'), ('NO. OF MODULE', '160'), ('MODULE MODEL', ['ADANI', 'AB-G12R-132-625', '(N-TYPE TOPCon)']),
        ('Voc', '49.8 V *'), ('Vmp', '41.6 V *'), ('Isc', '15.96 A *'), ('Imp', '15.03 A *'),
        ('TEMP. COEFF. Voc', '–0.25 %/°C *'),
    ], rh=17, size=7.5, head='MODULE LEGEND (STC)')
    o.append(tb)

    # ---- right column: symbols, system description, protection
    sy_rows = [
        (lambda x, y: sym_module(x, y), 'PV MODULE'),
        (lambda x, y: sym_inverter(x, y), 'STRING INVERTER'),
        (lambda x, y: sym_earth(x, y - 7, 0.6), 'EARTHING'),
        (lambda x, y: sym_spd(x, y), 'SURGE PROTECTION DEVICE (SPD)'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_breaker(x, y) + '</g>', 'MINIATURE CIRCUIT BREAKER (MCB)'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_breaker(x, y, True) + '</g>', 'MOULDED CASE CIRCUIT BREAKER (MCCB)'),
        (lambda x, y: R(x - 8, y - 7, 16, 14, sw=0.8, stroke='#1f3bb8') + C(x, y, 5, sw=0.8), 'SOLAR ENERGY GENERATION METER'),
        (lambda x, y: R(x - 8, y - 7, 16, 14, sw=0.8) + C(x, y, 5, sw=0.8), 'NET METER (DISCOM)'),
        (lambda x, y: sym_lamp(x - 16, y, '#ef4444') + sym_lamp(x, y, '#facc15') + sym_lamp(x + 16, y, '#2563eb'), 'R, Y, B LIVE INDICATING LAMPS'),
        (lambda x, y: sym_lamp(x, y, '#22c55e'), 'CIRCUIT BREAKER ON'),
        (lambda x, y: sym_lamp(x, y, '#ef4444'), 'CIRCUIT BREAKER OFF'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_contactor(x, y) + '</g>', 'CONTACTOR'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, sw=0.8) + T(x, y + 3, 'NVR', 6.5, 'middle', 'bold'), 'NO VOLT RELAY'),
        (lambda x, y: sym_cable(x - 14, x + 14, y), 'CABLE'),
    ]
    tb, y = legend_block(70, 'SYMBOLS NOMENCLATURE', sy_rows, rh=17)
    o.append(tb)
    tb, y = system_block(y + 8)
    o.append(tb)
    prot = ['INVERTER PROTECTION :- 80 kW (GOODWE GW80K-MT)', '1. DC REVERSE POLARITY PROTECTION', '2. AC SHORT CIRCUIT PROTECTION',
            '3. INSULATION RESISTANCE DETECTION', '4. RESIDUAL-CURRENT MONITORING UNIT (RCMU)', '5. ANTI-ISLANDING PROTECTION',
            '6. AC / DC SURGE PROTECTION TYPE II', '7. DC SWITCH (INTEGRATED)', '8. STRING CURRENT MONITORING',
            '9. AC OVER / UNDER VOLTAGE & FREQUENCY PROTECTION', '10. ANTI-PID / AFCI : OPTIONAL',
            '11. SAFETY STANDARDS : AS PER GOODWE DATASHEET', '     (IEC 62109-1/-2, IEC 61727, IEC 62116)']
    o.append(TL(TB_X0 + 6, y + 18, prot, 7.4, lh=11.5))
    o.append(title_block('01', 'SINGLE LINE DIAGRAM', 'NTS'))
    page(''.join(o), 'Jain-Granite_01_SLD_' + VERSION)


# ================================================================= layout geometry (metres)
MOD_W, MOD_L, MGAP = 1.134, 2.382, 0.02
BW = 5 * MOD_W + 4 * MGAP
BL = 8 * MOD_L + 7 * MGAP
BLOCK_X = [0.65, 7.0, 16.85, 23.2]     # from the layout photo (both inter-block gaps ≈ 0.6 m)
BLOCK_Y = 1.5
ROOF_W, ROOF_L, RIDGE_X = 29.8, 36.0, 14.8
INV = (33.8, 4.2)                      # inverter group centre (east wall, ground)
PITS = [('EP-1 (DC)', 34.8, 8.0), ('EP-2 (AC)', 35.8, 10.5), ('EP-3 (LA)', 34.8, 14.5)]
LA = (RIDGE_X, 1.0)
NAMES = [['S1', 'S2'], ['S3', 'S4'], ['S5', 'S6'], ['S7', 'S8']]
SCOL = {'S1': '#e6194b', 'S2': '#f58231', 'S3': '#3cb44b', 'S4': '#008080', 'S5': '#4363d8', 'S6': '#911eb4', 'S7': '#f032e6', 'S8': '#9a6324'}


def plan(ox, oy, k, labels=True, string_colours=False):
    """roof + modules in plan. returns (svg, to_px)"""
    def P_(x, y):
        return ox + x * k, oy + y * k
    o = []
    x0, y0 = P_(0, 0)
    o.append(R(x0, y0, ROOF_W * k, ROOF_L * k, sw=1.4) + R(x0 + 3, y0 + 3, ROOF_W * k - 6, ROOF_L * k - 6, sw=0.5))
    rx, _ = P_(RIDGE_X, 0)
    o.append(L(rx, y0, rx, y0 + ROOF_L * k, '#555', 1.2, '10,4,2,4'))
    if labels:
        o.append(T(rx, y0 + ROOF_L * k - 6, 'RIDGE', 8, 'middle', 'bold', '#555'))
        o.append(T(P_(RIDGE_X / 2, 0)[0], y0 + ROOF_L * k - 22, '← WEST SLOPE', 9, 'middle', 'bold', '#555'))
        o.append(T(P_((RIDGE_X + ROOF_W) / 2, 0)[0], y0 + ROOF_L * k - 22, 'EAST SLOPE →', 9, 'middle', 'bold', '#555'))
    for b, bx in enumerate(BLOCK_X):
        for r in range(8):
            for c in range(5):
                mx, my = P_(bx + c * (MOD_W + MGAP), BLOCK_Y + r * (MOD_L + MGAP))
                fill = '#fff'
                if string_colours:
                    fill = SCOL[NAMES[b][r // 4]] + '33'
                o.append(R(mx, my, MOD_W * k, MOD_L * k, stroke='#1f3bb8', sw=0.9, fill=fill))
        for h in range(2):
            sx, sy = P_(bx + BW / 2, BLOCK_Y + (h * 4 + 2) * (MOD_L + MGAP))
            if labels:
                o.append(R(sx - 30, sy - 9, 60, 14, fill='#fff', stroke='none', sw=0) +
                         T(sx, sy + 2, f'{NAMES[b][h]} – 20 MOD.', 7.5, 'middle', 'bold', '#d62828'))
            hy = P_(0, BLOCK_Y + 4 * (MOD_L + MGAP) - MGAP / 2)[1]
        bx0, _ = P_(bx, 0)
        o.append(L(bx0 - 2, hy, bx0 + BW * k + 2, hy, '#d62828', 1.2, '4,2'))
    return ''.join(o), P_


def dim_h(x1, x2, y, txt):
    return (L(x1, y, x2, y, '#d62828', 0.8) + L(x1, y - 5, x1, y + 5, '#d62828', 0.8) + L(x2, y - 5, x2, y + 5, '#d62828', 0.8) +
            T((x1 + x2) / 2, y - 4, txt, 8, 'middle', fill='#d62828'))


def dim_v(x, y1, y2, txt):
    return (L(x, y1, x, y2, '#d62828', 0.8) + L(x - 5, y1, x + 5, y1, '#d62828', 0.8) + L(x - 5, y2, x + 5, y2, '#d62828', 0.8) +
            T(x - 5, (y1 + y2) / 2, txt, 8, 'middle', fill='#d62828', rot=-90))


def equipment_group(cx, cy, s=1.0):
    o = [f'<ellipse cx="{cx}" cy="{cy}" rx="{78*s}" ry="{26*s}" stroke="#000" stroke-dasharray="4,3" fill="none"/>']
    o.append(R(cx - 66 * s, cy - 8 * s, 34 * s, 16 * s, stroke='#0891b2', sw=1.4, fill='#fff') + T(cx - 49 * s, cy + 3 * s, 'DCDB', 7 * s, 'middle'))
    o.append(R(cx - 22 * s, cy - 10 * s, 44 * s, 20 * s, fill='#22c55e', sw=1) + L(cx - 22 * s, cy + 10 * s, cx + 22 * s, cy - 10 * s, sw=0.8))
    o.append(R(cx + 32 * s, cy - 8 * s, 34 * s, 16 * s, stroke='#d62828', sw=1.4, fill='#fff') + T(cx + 49 * s, cy + 3 * s, 'ACDB', 7 * s, 'middle'))
    o.append(sym_fire(cx, cy - 34 * s))
    return ''.join(o)


# ================================================================= 02  EQUIPMENT LAYOUT
def sheet_equipment():
    o = [compass(80, 90)]
    ox, oy, k = 160, 120, 25.0
    pl, P_ = plan(ox, oy, k)
    o.append(pl)
    x0, y0 = P_(0, 0)
    o.append(dim_h(x0, x0 + ROOF_W * k, y0 - 22, f'≈ {ROOF_W:.1f} m (ROOF WIDTH, TO BE MEASURED) *'))
    o.append(dim_v(x0 - 22, y0, y0 + ROOF_L * k, f'≈ {ROOF_L:.0f} m (ROOF LENGTH, TO BE MEASURED) *'))
    bx0, by0 = P_(BLOCK_X[0], BLOCK_Y)
    o.append(dim_h(bx0, P_(BLOCK_X[3] + BW, 0)[0], by0 + BL * k + 20, f'ARRAY ≈ {BLOCK_X[3] + BW - BLOCK_X[0]:.1f} m'))
    o.append(dim_v(P_(BLOCK_X[3] + BW, 0)[0] + 18, by0, by0 + BL * k, f'{BL:.2f} m (8 MODULES)'))
    # DC cable route
    route = []
    for pair in (0, 1):
        gx = P_(BLOCK_X[pair * 2] + BW + (BLOCK_X[pair * 2 + 1] - BLOCK_X[pair * 2] - BW) / 2, 0)[0]
        _, gy = P_(0, BLOCK_Y + BL)
        o.append(PL([(gx, gy - 4), (gx, P_(0, 0.3)[1])], "#ea580c", 2.4, '7,4'))
    ry = P_(0, 0.3)[1]
    ix, iy = P_(*INV)
    o.append(PL([(P_(BLOCK_X[0] + BW + 0.3, 0)[0], ry), (P_(ROOF_W, 0)[0], ry), (P_(ROOF_W + 0.6, 0)[0], ry), (P_(ROOF_W + 0.6, 0)[0], iy)], '#ea580c', 2.4, '7,4'))
    o.append(T(P_(23.6, 0)[0], ry - 5, 'DC CABLE ROUTE – 8 STRINGS, 4 SQ MM (16 CORES)', 7.5, 'middle', 'bold', '#ea580c'))
    # LA
    lx, ly = P_(*LA)
    o.append(sym_la(lx, ly, 1.2))
    o.append(TL(lx + 8, ly + 34, ['LA (ESE)', 'ON 5 m MAST'], 8.5, weight='bold', fill='#d62828'))
    # equipment + pits
    o.append(equipment_group(ix, iy, 0.95))
    o.append(TL(ix - 70, iy + 40, ['INV. – 80 kW GOODWE GW80K-MT', 'WITH DCDB & ACDB, EAST WALL,', 'GROUND LEVEL (≈ 10 m BELOW EAVE)'], 7.5))
    for name, px_, py_ in PITS:
        px, py = P_(px_, py_)
        o.append(sym_pit(px, py) + T(px + 14, py + 4, name, 8.5, weight='bold'))
    o.append(T(ix + 4, P_(0, 18.5)[1], 'TO CLIENT LT PANEL (≈ 20 m) *', 8, 'middle', 'bold'))
    o.append(PL([(ix + 66, iy), (ix + 90, iy), (ix + 90, P_(0, 17.6)[1])], '#d62828', 1.6))
    o.append(f'<polygon points="{ix+90},{P_(0, 17.6)[1]+8} {ix+85},{P_(0, 17.6)[1]} {ix+95},{P_(0, 17.6)[1]}" fill="#d62828"/>')
    o.append(TL(60, 1080, ['NOTE: ROOF SIZE, BLOCK POSITIONS AND EQUIPMENT LOCATIONS ARE SCALED FROM THE CLIENT LAYOUT IMAGE (*) — VERIFY ON SITE.',
                           'BLOCKS 1 & 2 ON WEST SLOPE, BLOCKS 3 & 4 ON EAST SLOPE. EACH BLOCK = 5 x 8 MODULES (PORTRAIT) = 2 STRINGS OF 20.'], 8))
    # right column
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: sym_inverter(x, y, 22, 12), 'STRING INVERTER'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, stroke='#d62828', sw=1.2) + T(x, y + 3, 'ACDB', 6, 'middle'), 'AC DISTRIBUTION BOX'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, stroke='#0891b2', sw=1.2) + T(x, y + 3, 'DCDB', 6, 'middle'), 'DC DISTRIBUTION BOX'),
        (lambda x, y: sym_la(x, y + 2, 0.6), 'LIGHTNING ARRESTER'),
        (lambda x, y: sym_fire(x, y), 'FIRE-EXTINGUISHER'),
        (lambda x, y: sym_pit(x, y), 'EARTHING PIT'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#ea580c', 2.4, '7,4'), 'DC CABLE ROUTE'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#555', 1.2, '10,4,2,4'), 'ROOF RIDGE'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#d62828', 1.2, '4,2'), 'STRING BOUNDARY'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title_block('02', 'EQUIPMENT LAYOUT', '1:160 (A3)'))
    page(''.join(o), 'Jain-Granite_02_Equipment-Layout_' + VERSION)


# ================================================================= 03  EARTHING LAYOUT
def earth_pit_section(x, y):
    o = [T(x + 10, y + 18, 'EARTHING AS PER IS 3043:2018', 13, weight='bold')]
    gy = y + 70
    o.append(L(x + 10, gy, x + 300, gy, sw=1) + T(x + 14, gy - 6, 'GROUND LEVEL', 7, fill='#1f3bb8'))
    # chamber
    o.append(R(x + 70, gy - 10, 70, 60, stroke='#b45309', sw=3, fill='#fde68a55'))
    o.append(R(x + 62, gy - 14, 86, 6, fill='#999', stroke='#555'))
    o.append(T(x + 152, gy - 10, 'PIT COVER', 7, fill='#1f3bb8'))
    rod_top, rod_bot = gy + 10, gy + 300
    o.append(R(x + 90, gy + 50, 30, rod_bot - gy - 50, stroke='#b45309', fill='#fed7aa', dash='3,2'))
    o.append(R(x + 101, rod_top, 8, rod_bot - rod_top, fill='#b45309', stroke='#7c2d12'))
    o.append(R(x + 94, rod_top + 6, 22, 10, fill='#facc15', stroke='#000', sw=0.6))
    o.append(L(x + 50, rod_top, x + 50, rod_bot, '#d62828') + L(x + 44, rod_top, x + 56, rod_top, '#d62828') + L(x + 44, rod_bot, x + 56, rod_bot, '#d62828'))
    o.append(T(x + 44, (rod_top + rod_bot) / 2, '3000 MM', 11, 'middle', fill='#d62828', rot=-90))
    labs = [(gy + 30, 'CEMENT CONCRETE / BRICK CHAMBER', '(WITH PIT COVER) 300 X 300 X 300'),
            (gy + 22, 'TEST LINK / CLAMP', ''),
            (gy + 160, '17.2 MM DIA COPPER BONDED', 'ELECTRODE, 3 M LONG'),
            (gy + 220, 'CHEMICAL BACKFILL', '(EARTHING COMPOUND)'),
            (gy + 292, 'NATURAL SOIL', '')]
    for i, (ly, a, b) in enumerate(labs):
        ty = gy + 24 + i * 52
        o.append(L(x + 120, ly, x + 170, ty - 3, '#1f3bb8', 0.7) + T(x + 172, ty, a, 7.5, fill='#1f3bb8'))
        if b:
            o.append(T(x + 172, ty + 10, b, 7.5, fill='#1f3bb8'))
    # plan view
    px, py = x + 330, y + 70
    o.append(R(px, py, 90, 90, stroke='#b45309', sw=4) + R(px + 14, py + 14, 62, 62, sw=0.8) + C(px + 45, py + 45, 6, fill='#b45309'))
    o.append(T(px + 45, py + 112, 'PLAN VIEW', 11, 'middle', 'bold') + T(px + 45, py - 6, '300 MM', 7, 'middle', fill='#d62828'))
    o.append(R(x + 20, y + 395, 230, 22, rx=8) + T(x + 135, y + 410, 'SECTION VIEW OF EARTH PIT', 11, 'middle'))
    return ''.join(o)


def connection_detail(x, y):
    o = []
    gy = y + 30
    o.append(L(x + 10, gy, x + 90, gy) + L(x + 250, gy, x + 330, gy) + T(x + 12, gy - 4, 'GROUND LEVEL', 6.5, fill='#1f3bb8') + T(x + 252, gy - 4, 'GROUND LEVEL', 6.5, fill='#1f3bb8'))
    o.append(R(x + 90, gy - 6, 160, 130, stroke='#b45309', sw=4, fill='none'))
    o.append(R(x + 125, gy + 50, 90, 10, fill='#e5e7eb', sw=0.8) + T(x + 170, gy + 46, 'LINK PLATE 50 X 6 Cu', 6.5, 'middle', fill='#1f3bb8'))
    o.append(R(x + 165, gy + 60, 10, 66, fill='#b45309', stroke='#7c2d12'))
    o.append(PL([(x + 40, gy + 70), (x + 120, gy + 70), (x + 130, gy + 56)], '#16a34a', 4))
    o.append(PL([(x + 300, gy + 70), (x + 220, gy + 70), (x + 210, gy + 56)], '#16a34a', 2))
    o.append(T(x + 30, gy + 86, 'Cu. EARTH CABLE', 7, fill='#1f3bb8') + T(x + 240, gy + 86, 'Cu. EARTH CABLE', 7, fill='#1f3bb8'))
    o.append(R(x + 50, gy + 150, 240, 34, rx=6) + TL(x + 170, gy + 163, ['EQUIPMENT EARTHING CONNECTION', 'DETAIL FOR DC, AC & LA EARTH PITS'], 8, anchor='middle'))
    return ''.join(o)


def module_ground_detail(x, y):
    o = []
    # module frame section and rail
    o.append(PL([(x + 40, y + 30), (x + 40, y + 90), (x + 70, y + 90), (x + 70, y + 84), (x + 46, y + 84), (x + 46, y + 30)], '#000', 1.4, fill='#e5e7eb'))
    o.append(PL([(x + 120, y + 30), (x + 120, y + 90), (x + 150, y + 90), (x + 150, y + 84), (x + 126, y + 84), (x + 126, y + 30)], '#000', 1.4, fill='#e5e7eb'))
    o.append(R(x + 20, y + 92, 160, 10, fill='#cbd5e1'))
    for bx in (x + 58, x + 138):
        o.append(R(bx - 3, y + 74, 6, 34, fill='#475569', stroke='none') + R(bx - 9, y + 74, 18, 4, fill='#000', stroke='none') + R(bx - 7, y + 106, 14, 5, fill='#000', stroke='none'))
    o.append(f'<path d="M {x+66} {y+80} C {x+90} {y+60}, {x+110} {y+60}, {x+132} {y+80}" stroke="#16a34a" stroke-width="3" fill="none"/>')
    labels = [('MODULE FRAME', x + 140, y + 30), ('BOLT', x + 150, y + 76), ('WASHER / STAR WASHER', x + 154, y + 88),
              ('AL GROUNDING LUG (BIMETALLIC)', x + 150, y + 104), ('NUT', x + 150, y + 116)]
    for s, lx, ly in labels:
        o.append(L(lx - 6, ly - 3, lx + 40, ly + 12 - 10, '#1f3bb8', 0.6) + T(lx + 44, ly + 4, s, 7, fill='#1f3bb8'))
    o.append(L(x + 98, y + 66, x + 40, y + 140, '#1f3bb8', 0.6) + T(x + 6, y + 150, '6 SQ.MM COPPER EARTHING CABLE', 7, fill='#1f3bb8'))
    o.append(R(x + 40, y + 168, 210, 22, rx=6) + T(x + 145, y + 183, 'MODULE GROUNDING DETAIL', 11, 'middle'))
    return ''.join(o)


def sheet_earthing():
    o = [compass(80, 90)]
    ox, oy, k = 380, 110, 13.5
    # LA range circle clipped to the upper panel
    o.append('<defs><clipPath id="up"><rect x="30" y="30" width="1232" height="620"/></clipPath></defs>')
    lx, ly = ox + LA[0] * k, oy + LA[1] * k
    o.append(f'<g clip-path="url(#up)">' + C(lx, ly, 470, '#d62828', 1.2) + '</g>')
    pl, P_ = plan(ox, oy, k, labels=False)
    o.append(pl)
    for b, bx in enumerate(BLOCK_X):
        cx_, cy_ = P_(bx + BW / 2, BLOCK_Y + BL + 1.2)
        o.append(T(cx_, cy_ + 3, f'BLOCK {b+1}', 8, 'middle', 'bold', '#1f3bb8'))
        # MMS to MMS earthing (along the block)
        for c in (0.25, 0.75):
            xx = P_(bx + BW * c, 0)[0]
            o.append(L(xx, P_(0, BLOCK_Y)[1], xx, P_(0, BLOCK_Y + BL)[1], '#86efac', 1.6))
    o.append(T(P_(RIDGE_X, 0)[0], P_(0, ROOF_L)[1] - 6, 'RIDGE', 7, 'middle', 'bold', '#555'))
    # DC earth bus (16 sq mm) along north edge -> EP-1
    ey = P_(0, 1.1)[1]
    for bx in BLOCK_X:
        xx = P_(bx + BW / 2, 0)[0]
        o.append(L(xx, ey, xx, P_(0, BLOCK_Y)[1], '#0a6a20', 2))
    ix, iy = P_(*INV)
    p1 = P_(PITS[0][1], PITS[0][2])
    o.append(PL([(P_(BLOCK_X[0] + BW / 2, 0)[0], ey), (P_(ROOF_W + 0.9, 0)[0], ey), (P_(ROOF_W + 0.9, 0)[0], p1[1]), p1], '#0a6a20', 2.2))
    # AC earth -> EP-2
    p2 = P_(PITS[1][1], PITS[1][2])
    o.append(PL([(ix, iy + 10), (ix, p2[1]), p2], '#0a6a20', 2.2))
    # LA down conductor -> EP-3 (own route, >= 1 m from DC/AC)
    p3 = P_(PITS[2][1], PITS[2][2])
    o.append(PL([(lx, ly), (lx, P_(0, -0.8)[1]), (P_(39.7, 0)[0], P_(0, -0.8)[1]), (P_(39.7, 0)[0], p3[1]), p3], '#a3e635', 2.6))
    o.append(sym_la(lx, ly, 0.9))
    o.append(T(lx + 12, ly - 12, 'LA', 9, weight='bold', fill='#d62828'))
    o.append(equipment_group(ix, iy, 0.55))
    o.append(T(ix - 50, iy + 4, 'INV. 80 kW', 7, 'end'))
    for name, px_, py_ in PITS:
        px, py = P_(px_, py_)
        o.append(sym_pit(px, py) + T(px + 12, py + 4, name, 7.5, 'start', 'bold'))
    o.append(T(1010, 560, 'LA RANGE : 65 M *', 15, 'middle', fill='#000') + L(960, 540, lx + 342, ly + 322, '#d62828', 1))
    o.append(T(1010, 576, '(REQUIRED ≥ 25 M TO COVER FARTHEST MODULE)', 7.5, 'middle'))
    o.append(L(30, 650, TB_X0, 650, sw=1.4))
    o.append(L(560, 650, 560, FR[3], sw=1.2) + L(900, 650, 900, FR[3], sw=1.2) + L(560, 900, 900, 900, sw=1.2))
    o.append(earth_pit_section(40, 660))
    o.append(connection_detail(570, 670))
    o.append(module_ground_detail(910, 680))
    o.append(R(570, 910, 320, 230, sw=0) )
    o.append(TL(580, 930, ['EARTH PIT SCHEDULE', 'EP-1 (DC) : PV STRUCTURE / MODULE FRAMES, DCDB, 16 SQ MM Cu',
                           'EP-2 (AC) : INVERTER PE & BODY, ACDB, AC SPD, CABLE', '                  ARMOUR, 25 SQ MM Cu',
                           'EP-3 (LA) : ESE LIGHTNING ARRESTER, 50 SQ MM Cu,', '                  INSULATED SPACERS, TEST LINK 1 m ABOVE GL',
                           '', 'PIT SPACING (FROM LAYOUT IMAGE) ≈ 2.5 – 4 m *',
                           'PREFERRED ≥ 6 m (2 x ELECTRODE LENGTH) — MOVE EP-3', 'AWAY FROM EP-1 / EP-2 WHERE SITE ALLOWS.'], 8, lh=12))
    # right column
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: sym_inverter(x, y, 22, 12), 'STRING INVERTER'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, stroke='#d62828', sw=1.2) + T(x, y + 3, 'ACDB', 6, 'middle'), 'AC DISTRIBUTION BOX'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, stroke='#0891b2', sw=1.2) + T(x, y + 3, 'DCDB', 6, 'middle'), 'DC DISTRIBUTION BOX'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#0a6a20', 2.2), 'EARTH CABLE (FOR DC & AC)'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#a3e635', 2.6), 'EARTH CABLE (FOR LA)'),
        (lambda x, y: sym_pit(x, y), 'EARTHING PIT'),
        (lambda x, y: sym_la(x, y + 2, 0.6), 'LIGHTNING ARRESTER'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#16a34a', 3), 'MODULE TO MODULE EARTHING CABLE'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#86efac', 1.6), 'MMS TO MMS EARTHING CABLE'),
        (lambda x, y: sym_fire(x, y), 'FIRE-EXTINGUISHER'),
    ]
    tb, y = legend_block(50, 'LEGENDS', leg, rh=17)
    o.append(tb)
    tb, y = system_block(y + 8)
    o.append(tb)
    notes = ['GENERAL NOTES', '1. PV YARD EARTHING GRID WITH 16 SQ MM Cu EARTHING CABLE.',
             '2. INVERTER & ACDB EARTHING WITH 25 SQ MM Cu EARTHING CABLE.',
             '3. LA EARTHING WITH 50 SQ MM Cu CABLE, KEPT ≥ 1 m FROM DC / AC CABLES.',
             '4. TOTAL EARTH RESISTANCE OF EARTHING SYSTEM SHOULD BE LESS THAN 1 Ω.',
             '5. TOTAL 3 NOS. EARTH ELECTRODES: EP-1 DC, EP-2 AC, EP-3 LA.',
             '6. MIN. DISTANCE BETWEEN EARTH PITS 3 m; 6 m PREFERRED.',
             '7. 17.2 MM DIA x 3 m COPPER BONDED ELECTRODE WITH CHEMICAL BACKFILL.',
             '8. MODULE TO MODULE EARTHING WITH 1C x 6 SQ MM Cu CABLE.',
             '9. EARTH PIT LOCATION IS INDICATIVE; MAY VARY PER SITE CONDITIONS.',
             '10. AFTER JOINT, CABLE SLEEVE SHOULD BE APPLIED.',
             '11. ALL EQUIPMENT SHALL BE CONNECTED TO THE NEAREST EARTH PIT,',
             '      WHETHER SHOWN IN THE DRAWING OR NOT.',
             '12. PIT INTERCONNECTION AS PER CEIG APPROVAL.',
             '* VALUES MARKED * TO BE CONFIRMED ON SITE / LA DATASHEET.']
    o.append(T((TB_X0 + TB_X1) / 2, y + 22, notes[0], 9.5, 'middle', 'bold', '#d62828'))
    o.append(TL(TB_X0 + 6, y + 40, notes[1:], 7.2, lh=11.5))
    o.append(title_block('03', 'EARTHING LAYOUT', 'NTS'))
    page(''.join(o), 'Jain-Granite_03_Earthing-Layout_' + VERSION)


# ================================================================= walkway / tray geometry (metres)
WALK_W, HEAD_W = 0.30, 0.45
ARRAY_END = BLOCK_Y + BL
HEAD_Y0 = 0.50                       # header walkway along the north edge: y 0.50 – 0.95
TRAY_W = 0.10
TRAY_HY = 0.25                       # header tray along the very north edge: y 0.25 – 0.35
TRAY_GAP_X = [BLOCK_X[0] + BW + 0.05, BLOCK_X[2] + BW + 0.05]   # trays hug the west side of gaps 1-2 and 3-4
TRAY_GAP_END = 19.6                  # just past the row-8 terminals
WALL_DROP = 10.0                     # roof height 8-10 m


def walkway_runs():
    e = [x + BW for x in BLOCK_X]
    xs = [('W1', 0.175, 'WEST EAVE, WEST OF BLOCK 1'), ('W2', e[0] + 0.22, 'GAP BLOCK 1 / 2 (BESIDE T1)'),
          ('W3', e[1] + 0.10, 'EAST OF BLOCK 2 (RIDGE SIDE)'), ('W4', BLOCK_X[2] - 0.40, 'WEST OF BLOCK 3 (RIDGE SIDE)'),
          ('W5', e[2] + 0.22, 'GAP BLOCK 3 / 4 (BESIDE T2)'), ('W6', e[3] + 0.10, 'EAST EAVE, EAST OF BLOCK 4')]
    return [(n, x, x + WALK_W, HEAD_Y0 + HEAD_W, ARRAY_END, d) for n, x, d in xs]


def walk_lengths():
    runs = walkway_runs()
    ns = [(n, y2 - y1, d) for n, x1, x2, y1, y2, d in runs]
    head = runs[-1][2] - runs[0][1]
    return ns, head


def tray_segments():
    t1x, t2x = TRAY_GAP_X
    hy = TRAY_HY + TRAY_W / 2
    segs = [('T1', 'GAP BLOCK 1/2: ROW 8 → NORTH EDGE', [(t1x, TRAY_GAP_END), (t1x, hy)], '8 x 4 SQ MM + 16 SQ MM E', 'S1–S4'),
            ('T2', 'GAP BLOCK 3/4: ROW 8 → NORTH EDGE', [(t2x, TRAY_GAP_END), (t2x, hy)], '8 x 4 SQ MM + 16 SQ MM E', 'S5–S8'),
            ('T3a', 'NORTH EDGE: T1 → T2 (OVER RIDGE)', [(t1x, hy), (t2x, hy)], '8 x 4 SQ MM + 16 SQ MM E', 'S1–S4'),
            ('T3b', 'NORTH EDGE: T2 → EAST EAVE', [(t2x, hy), (ROOF_W, hy)], '16 x 4 SQ MM + 16 SQ MM E', 'ALL 8 STRINGS'),
            ('T4', f'EAST WALL: DOWN {WALL_DROP:.0f} m + ALONG TO INVERTER', None, '16 x 4 SQ MM + 16 SQ MM E', 'ALL 8 STRINGS')]
    out = []
    for sid, desc, pts, cab, st in segs:
        ln = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])) if pts else WALL_DROP + (INV[1] - hy)
        out.append((sid, desc, pts, cab, st, ln))
    return out


def Rm(P_, x1, y1, x2, y2, **kw):
    a, b = P_(x1, y1)
    c, d = P_(x2, y2)
    return R(a, b, c - a, d - b, **kw)


WALK_FILL = '#d6d3d1'
WALK_STROKE = '#57534e'
TRAY_COL = '#ea580c'


def draw_walkways(P_, labels=True, fill=WALK_FILL, stroke=WALK_STROKE):
    o = []
    runs = walkway_runs()
    o.append(Rm(P_, runs[0][1], HEAD_Y0, runs[-1][2], HEAD_Y0 + HEAD_W, stroke=stroke, sw=0.8, fill=fill))
    for n, x1, x2, y1, y2, d in runs:
        o.append(Rm(P_, x1, y1, x2, y2, stroke=stroke, sw=0.8, fill=fill))
        if labels:
            cx_, cy_ = P_((x1 + x2) / 2, ARRAY_END + 0.9)
            o.append(T(cx_, cy_, n, 9, 'middle', 'bold', stroke))
    return ''.join(o)


def draw_trays(P_):
    o = []
    for tx in TRAY_GAP_X:
        o.append(Rm(P_, tx - TRAY_W / 2, TRAY_HY, tx + TRAY_W / 2, TRAY_GAP_END, stroke='#7c2d12', sw=0.8, fill=TRAY_COL))
    o.append(Rm(P_, TRAY_GAP_X[0] - TRAY_W / 2, TRAY_HY, ROOF_W, TRAY_HY + TRAY_W, stroke='#7c2d12', sw=0.8, fill=TRAY_COL))
    return ''.join(o)


# ================================================================= 04  WALKWAY LAYOUT
def sheet_walkway():
    o = [compass(80, 90)]
    ox, oy, k = 150, 110, 20.0
    pl, P_ = plan(ox, oy, k)
    o.append(pl)
    o.append(draw_walkways(P_))
    x0, y0 = P_(0, 0)
    o.append(dim_h(x0, x0 + ROOF_W * k, y0 - 20, f'≈ {ROOF_W:.1f} m (ROOF WIDTH, TO BE MEASURED) *'))
    hx, hy = P_(ROOF_W / 2 + 5.5, HEAD_Y0 + HEAD_W / 2)
    o.append(R(hx - 96, hy - 6, 192, 12, fill='#fff', stroke='none') + T(hx, hy + 3, 'WH – HEADER WALKWAY 450 MM (NORTH EDGE)', 7.5, 'middle', 'bold', WALK_STROKE))
    ax, ay = P_(ROOF_W, HEAD_Y0 + HEAD_W / 2)
    o.append(R(ax + 2, ay - 12, 22, 24, stroke='#000', sw=1, fill='#fff') + ''.join(L(ax + 4, ay - 9 + i * 6, ax + 22, ay - 9 + i * 6, sw=0.8) for i in range(4)))
    o.append(TL(ax + 30, ay - 2, ['ROOF ACCESS LADDER', '(NE CORNER, NEAR INVERTER –', ' CONFIRM ON SITE) *'], 7.5, weight='bold'))
    # cleaning reach on block 1 from W1 and W2
    runs = walkway_runs()
    ry = BLOCK_Y + 1.2 * (MOD_L + MGAP)
    a1, _ = P_(runs[0][2], ry)
    mid, yy = P_(BLOCK_X[0] + BW / 2, ry)
    a2, _ = P_(runs[1][1], ry)
    for xa in (a1, a2):
        dx = 5 if xa > mid else -5
        o.append(L(xa, yy, mid, yy, '#16a34a', 1.6) + f'<polygon points="{mid},{yy} {mid+dx},{yy-4} {mid+dx},{yy+4}" fill="#16a34a"/>')
    o.append(R(mid - 48, yy + 5, 96, 12, fill='#fff', stroke='none') + T(mid, yy + 14, 'REACH ≈ 2.9 m EACH SIDE', 7, 'middle', 'bold', '#16a34a'))
    o.append(TL(60, 1080, ['NOTE: EVERY MODULE IS WITHIN ≈ 2.9 m (2½ MODULES) OF A WALKWAY – CLEAN WITH A 3.5 m TELESCOPIC BRUSH FROM THE WALKWAY. N–S WALKWAYS RUN',
                           'PARALLEL TO THE RIDGE (ALONG THE ROOF CONTOUR), SO THEY ARE LEVEL TO WALK ON. ROOF SIZE / GAPS SCALED FROM THE LAYOUT IMAGE (*) — VERIFY ON SITE.'], 7.8))
    ns, head = walk_lengths()
    rows = [('ID', 'LOCATION', 'WIDTH', 'LENGTH')]
    for n, ln, d in ns:
        rows.append((n, d, '300 MM', f'{ln:.1f} m'))
    rows.append(('WH', 'HEADER, NORTH EDGE, W1 → W6', '450 MM', f'{head:.1f} m'))
    tot300 = sum(ln for _, ln, _ in ns)
    rows.append(('', 'TOTAL 300 MM WALKWAY', '', f'{tot300:.1f} m'))
    rows.append(('', 'TOTAL 450 MM WALKWAY', '', f'{head:.1f} m'))
    rows.append(('', 'ORDER (+5 %): 300 MM / 450 MM', '', f'{tot300*1.05:.0f} / {head*1.05:.0f} m'))
    tb, y = table(940, 120, [26, 148, 42, 80], rows, rh=15, size=6.8, head='WALKWAY SCHEDULE')
    o.append(tb)
    sx, sy = 950, y + 40
    o.append(T(sx + 140, sy - 12, 'SECTION A-A (ACROSS BLOCK 1)', 9, 'middle', 'bold'))
    o.append(L(sx, sy + 70, sx + 280, sy + 70, sw=1.2))
    o.append(R(sx + 4, sy + 62, 22, 6, fill=WALK_FILL, stroke=WALK_STROKE) + R(sx + 254, sy + 62, 22, 6, fill=WALK_FILL, stroke=WALK_STROKE))
    for i in range(5):
        o.append(R(sx + 34 + i * 43.5, sy + 54, 41, 6, stroke='#1f3bb8', fill='#dbeafe'))
    for px_, d in ((sx + 15, 1), (sx + 265, -1)):
        o.append(C(px_, sy + 18, 5) + L(px_, sy + 23, px_, sy + 44) + L(px_, sy + 44, px_ - 5, sy + 62) + L(px_, sy + 44, px_ + 5, sy + 62))
        o.append(L(px_, sy + 30, px_ + d * 125, sy + 50, '#16a34a', 1.4))
    o.append(T(sx + 140, sy + 40, '2.9 m      2.9 m', 7, 'middle', fill='#16a34a'))
    o.append(T(sx + 140, sy + 86, 'W1 | 5 MODULES ≈ 5.75 m | W2', 7.5, 'middle'))
    notes = ['WALKWAY NOTES', '1. FRP / HDG STEEL ANTI-SKID GRATING, UV STABILISED,', '    MIN. 150 KG/M² RATED.',
             '2. FIX TO PURLINS WITH CLAMPS — NO SHEET PUNCTURE,', '    OR SEAL WITH EPDM WASHERS.',
             '3. ≥ 50 MM CLEAR OF MODULE FRAMES; NO SHADING.',
             '4. W1 & W6 ARE NEAR THE EAVE — PROVIDE LIFELINE /', '    HANDRAIL AT ROOF EDGE.',
             '5. HEADER WALKWAY LIFTED ON 100 MM SUPPORTS WHERE', '    TRAYS T1 / T2 PASS UNDER IT (SEE SHEET 05).',
             '6. IF GAP 1/2 OR 3/4 MEASURES < 0.5 m, MOUNT THE', '    TRAY BENEATH THE WALKWAY.']
    o.append(T(sx, sy + 116, notes[0], 8.5, weight='bold'))
    o.append(TL(sx, sy + 132, notes[1:], 7, lh=10.5))
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: R(x - 20, y - 4, 40, 8, stroke=WALK_STROKE, fill=WALK_FILL, sw=0.8), 'WALKWAY 300 MM (N–S)'),
        (lambda x, y: R(x - 20, y - 6, 40, 12, stroke=WALK_STROKE, fill=WALK_FILL, sw=0.8), 'HEADER WALKWAY 450 MM'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#16a34a', 1.6), 'CLEANING REACH'),
        (lambda x, y: R(x - 8, y - 8, 16, 16, sw=1) + L(x - 6, y - 3, x + 6, y - 3, sw=0.7) + L(x - 6, y + 3, x + 6, y + 3, sw=0.7), 'ROOF ACCESS LADDER'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#555', 1.2, '10,4,2,4'), 'ROOF RIDGE'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title_block('04', 'WALKWAY LAYOUT (MODULE CLEANING)', '1:200 (A3)'))
    page(''.join(o), 'Jain-Granite_04_Walkway-Layout_' + VERSION)


# ================================================================= 05  CABLE TRAY LAYOUT
def sheet_tray():
    o = [compass(80, 90)]
    ox, oy, k = 150, 110, 20.0
    pl, P_ = plan(ox, oy, k)
    o.append(pl)
    o.append(draw_walkways(P_, labels=False, fill='#f1f0ef', stroke='#a8a29e'))
    o.append(draw_trays(P_))
    segs = tray_segments()
    lens = {sid: ln for sid, _, _, _, _, ln in segs}
    t1x, t2x = TRAY_GAP_X
    tags = {'T1': P_(t1x - 1.3, 12.5), 'T2': P_(t2x - 1.3, 12.5), 'T3a': P_((t1x + t2x) / 2 + 3.5, TRAY_HY - 1.0),
            'T3b': P_((t2x + ROOF_W) / 2, TRAY_HY - 1.0)}
    for sid, (tx, ty) in tags.items():
        o.append(R(tx - 30, ty - 9, 60, 13, fill='#fff7ed', stroke=TRAY_COL, sw=0.8) + T(tx, ty + 1, f'{sid}  {lens[sid]:.1f} m', 7.5, 'middle', 'bold', '#7c2d12'))
    ex, ey = P_(ROOF_W, TRAY_HY + TRAY_W / 2)
    ix, iy = P_(*INV)
    gs = 0.7
    o.append(PL([(ex, ey), (ex + 10, ey), (ex + 10, iy), (ix - 66 * gs, iy)], TRAY_COL, 5))
    o.append(equipment_group(ix, iy, gs))
    o.append(T(ix, iy + 28, 'INV. 80 kW + DCDB + ACDB', 7, 'middle'))
    o.append(T(ix, iy + 37, '(EAST WALL, GROUND LEVEL)', 7, 'middle'))
    o.append(TL(ex + 16, iy + 58, [f'T4  {lens["T4"]:.1f} m', f'DOWN WALL ≈ {WALL_DROP:.0f} m', '+ ALONG WALL'], 7.5, weight='bold', fill='#7c2d12'))
    acx = ix + 66 * gs + 12
    o.append(PL([(ix + 66 * gs, iy), (acx, iy), (acx, P_(0, 19.5)[1])], '#2563eb', 3, '8,4'))
    o.append(TL(acx + 6, P_(0, 13.0)[1], ['AC: 95 SQ MM', 'AL ARMOURED', 'TO LT PANEL', '≈ 20 m *', '150 x 50 MM', 'TRAY / TRENCH'], 7.5, weight='bold', fill='#2563eb'))
    lx, ly = P_(*LA)
    o.append(sym_la(lx, ly, 0.9))
    for tx in (t1x, t2x):
        cx_, cy_ = P_(tx, HEAD_Y0 + HEAD_W / 2)
        o.append(C(cx_, cy_, 8, '#000', 1, 'none', '2,2'))
    o.append(TL(60, 1080, ['NOTE: TRAYS T1 / T2 SIT IN THE ≈ 0.6 m GAPS BESIDE WALKWAYS W2 / W5 AND PASS UNDER THE HEADER WALKWAY (CIRCLED). STRING LEADS DROP INTO THE',
                           'TRAY AT ROWS 1, 4, 5 AND 8 (SEE STRINGING PLAN v11). GAPS AND ROOF SIZE SCALED FROM THE LAYOUT IMAGE (*) — VERIFY ON SITE.',
                           'LA DOWN CONDUCTOR CROSSES T3a ONCE, AT 90°, RAISED ≥ 0.5 m ON AN INSULATED STAND-OFF, THEN RUNS ≥ 1 m NORTH OF THE TRAY (SEE SHEET 03).'], 7.8))
    rows = [('ID', 'ROUTE', 'LENGTH', 'CABLES IN TRAY')]
    total = 0
    for sid, desc, _, cab, st, ln in segs:
        rows.append((sid, [desc[:desc.index(':') + 1], desc[desc.index(':') + 2:]], f'{ln:.1f} m', [cab, f'({st})']))
        total += ln
    rows.append(('', 'TOTAL DC TRAY 100 x 50 MM', f'{total:.1f} m', ''))
    rows.append(('', 'ORDER (+10 %), 2.5 m LENGTHS', f'{total*1.1:.0f} m', f'{int(-(-total*1.1 // 2.5))} LENGTHS + COVERS'))
    tb, y = table(940, 120, [26, 132, 40, 98], rows, rh=15, size=6.5, head='CABLE TRAY SCHEDULE (DC)')
    o.append(tb)
    sx, sy = 990, y + 50
    o.append(T(sx + 100, sy - 22, 'TRAY SECTION (T3b / T4, FULL LOAD)', 9, 'middle', 'bold'))
    s2 = 2.0
    tw, th = 100 * s2, 50 * s2
    o.append(PL([(sx, sy), (sx, sy + th), (sx + tw, sy + th), (sx + tw, sy)], '#000', 2.2))
    o.append(R(sx - 4, sy - 8, tw + 8, 5, fill='#9ca3af', stroke='#000', sw=0.8) + T(sx + tw + 8, sy - 3, 'COVER', 7))
    for i in range(16):
        cx_ = sx + 2 + 3 * s2 + i * 6.0 * s2
        o.append(C(cx_, sy + th - 3 * s2 - 1.5, 3 * s2, '#000', 0.6, '#ef4444' if i % 2 == 0 else '#111'))
    o.append(C(sx + tw - 16, sy + th - 22, 4.5 * s2, '#000', 0.6, '#16a34a'))
    o.append(L(sx, sy + th + 14, sx + tw, sy + th + 14, '#d62828', 0.8) + T(sx + tw / 2, sy + th + 26, '100 MM', 8, 'middle', fill='#d62828'))
    o.append(L(sx - 14, sy, sx - 14, sy + th, '#d62828', 0.8) + T(sx - 18, sy + th / 2, '50 MM', 8, 'middle', fill='#d62828', rot=-90))
    o.append(TL(sx - 30, sy + th + 44, ['16 x 4 SQ MM DC (Ø ≈ 6 MM; RED +VE, BLACK –VE)', '+ 1 x 16 SQ MM Cu EARTH (GREEN)',
                                        'FILL ≈ 520 / 5,000 MM² ≈ 10 % (LIMIT 40 %)', 'SINGLE LAYER, ROOM FOR EXPANSION'], 7.2))
    notes = ['CABLE TRAY NOTES', '1. 100 x 50 MM PERFORATED HDG TRAY, 1.6 MM, WITH', '    BOLTED COVER (UV & BIRD / MONKEY PROTECTION).',
             '2. ONE SIZE THROUGHOUT — T1 / T2 / T3a CARRY 8 CORES,', '    BUT ONE SIZE KEEPS FITTINGS COMMON.',
             '3. RAISE TRAY 75–100 MM ABOVE SHEET ON PURLIN', '    CLAMPS EVERY 1.5 m; WALL BRACKETS EVERY 1.2 m.',
             '4. FITTINGS: 1 FLAT BEND, 1 TEE, 2 VERTICAL BENDS,', '    COUPLERS AT EVERY JOINT, 2 END CAPS.',
             '5. BOND TRAY SECTIONS TOGETHER AND TO EP-1.',
             '6. AC CABLE IN ITS OWN TRAY / TRENCH, ≥ 300 MM FROM DC.',
             '7. LA DOWN CONDUCTOR NEVER IN OR ON THE TRAY.']
    o.append(T(sx - 30, sy + th + 102, notes[0], 8.5, weight='bold'))
    o.append(TL(sx - 30, sy + th + 118, notes[1:], 7, lh=10.5))
    leg = [
        (lambda x, y: R(x - 9, y - 6, 18, 12, stroke='#1f3bb8', sw=1.2), 'SOLAR MODULES'),
        (lambda x, y: R(x - 20, y - 3, 40, 6, stroke='#7c2d12', fill=TRAY_COL, sw=0.8), 'DC CABLE TRAY 100 x 50 MM'),
        (lambda x, y: L(x - 20, y, x + 20, y, '#2563eb', 3, '8,4'), 'AC CABLE ROUTE (95 SQ MM AL)'),
        (lambda x, y: R(x - 20, y - 4, 40, 8, stroke='#a8a29e', fill='#f1f0ef', sw=0.8), 'WALKWAY (SEE SHEET 04)'),
        (lambda x, y: C(x, y, 7, '#000', 1, 'none', '2,2'), 'TRAY PASSES UNDER WALKWAY'),
        (lambda x, y: sym_la(x, y + 2, 0.6), 'LIGHTNING ARRESTER'),
        (lambda x, y: sym_inverter(x, y, 22, 12), 'STRING INVERTER'),
    ]
    tb, y = legend_block(70, 'LEGENDS', leg, rh=18)
    o.append(tb)
    tb, y = system_block(y + 12)
    o.append(tb)
    o.append(title_block('05', 'CABLE TRAY LAYOUT', '1:200 (A3)'))
    page(''.join(o), 'Jain-Granite_05_Cable-Tray-Layout_' + VERSION)


if __name__ == '__main__':
    sheet_sld()
    sheet_equipment()
    sheet_earthing()
    sheet_walkway()
    sheet_tray()
    print('html written to', OUT)
