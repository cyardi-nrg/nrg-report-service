# Design Lab worker v1.8.0 (2026-10-31) — CEIG drawing kit: A3 frame, title block, symbols,
# tables and the standard earthing details. Carried over from the owner-approved Jain Granite
# CEIG set (stringing/ceig/generate_ceig_drawings.py v7 — NRG's own submission format: A3
# landscape, title column on the right) and made general: every project value is passed in.
# Sheets are SVG inside HTML; nrg/ceig_pdf.py prints them to A3 PDF with the worker's Chromium.
import html

FONT = 'Liberation Sans, Arial, Helvetica, sans-serif'
W, H = 1680, 1188           # A3 landscape at 4 units per mm
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


# ---------------------------------------------------------------- title column
def title_block(info: dict, dwg_no: str, dwg_name: str, scale: str, sheet: str) -> str:
    """info: client, epc, epc_addr, title, date, paper, version, generated"""
    x0, x1 = TB_X0, TB_X1
    w = x1 - x0
    o = [L(x0, FR[1], x0, FR[3], sw=1.4)]
    y = 790
    o.append(L(x0, y, x1, y))
    o.append(T(x0 + 4, y + 13, 'CUSTOMER SIGN AND STAMP:', 8))
    y = 860
    cols = [26, 52, 150, 54, 54, 52]
    hdr = ['REV.', 'DATE', 'DESCRIPTION', 'DRAWN BY', 'CHECKED BY', 'APPROVED BY']
    r0 = ['R0', info['date'], 'FIRST ISSUE', '', '', '']
    for rowi, row in enumerate([r0, hdr]):
        cx = x0
        for c, s in zip(cols, row):
            o.append(R(cx, y, c, 14, sw=0.6))
            o.append(T(cx + c / 2, y + 10, s, 6.5 if rowi else 7, 'middle'))
            cx += c
        y += 14
    rows = [('CLIENT:', [info['client']], 40, 11 if len(info['client']) < 34 else 8.5),
            ('EPC CONTRACTOR:', [info['epc'], info['epc_addr']], 40, 10),
            ('DESIGN BY:', [info['epc'], info['epc_addr']], 40, 10)]
    for lab, val, h, fs in rows:
        o.append(R(x0, y, w, h, sw=0.8))
        o.append(L(x0 + 78, y, x0 + 78, y + h, sw=0.8))
        o.append(T(x0 + 39, y + h / 2 + 3, lab, 7.5, 'middle'))
        o.append(T(x0 + 78 + (w - 78) / 2, y + h / 2 + (0 if len(val) > 1 else 4), val[0], fs, 'middle', 'bold'))
        if len(val) > 1:
            o.append(T(x0 + 78 + (w - 78) / 2, y + h / 2 + 12, val[1], 7, 'middle'))
        y += h
    for lab, val in (('DRAWING NO.:', dwg_no), ('DRAWING NAME:', dwg_name), ('PROJECT TITLE:', info['title'])):
        o.append(R(x0, y, w, 24, sw=0.8))
        o.append(T(x0 + 3, y + 8, lab, 6.5))
        o.append(T(x0 + 4, y + 20, val, 10 if len(val) < 52 else 8, weight='bold' if lab == 'DRAWING NAME:' else 'normal'))
        y += 24
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
    val = ['', '', '', '', info.get('paper', 'A3'), sheet]
    cx = x0
    for c, a, b in zip(cols, hdr, val):
        o.append(R(cx, y, c, FR[3] - y, sw=0.8))
        o.append(T(cx + c / 2, y + 9, a, 6.5, 'middle'))
        o.append(T(cx + c / 2, y + 21, b or '________', 7.5, 'middle', 'bold' if b else 'normal', '#000' if b else '#999'))
        o.append(T(cx + c / 2, y + 30, info['date'] if not b else '', 6.5, 'middle'))
        cx += c
    o.append(T(x1 - 4, FR[3] + 12, f"NRG CEIG drawing set — Design Lab worker {info.get('version', '')} — generated {info.get('generated', '')}", 7, 'end', fill='#777'))
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


def system_block(rows, y):
    x0, x1 = TB_X0, TB_X1
    o = [T((x0 + x1) / 2, y + 12, 'SYSTEM DESCRIPTION', 10, 'middle', 'bold'), L((x0 + x1) / 2 - 58, y + 14, (x0 + x1) / 2 + 58, y + 14, sw=0.8)]
    y += 20
    for a, b in rows:
        o.append(R(x0 + 4, y, 150, 14, sw=0.5) + R(x0 + 154, y, x1 - x0 - 158, 14, sw=0.5))
        o.append(T(x0 + 8, y + 10, a, 7))
        o.append(T(x0 + 158, y + 10, b if len(str(b)) < 40 else str(b)[:39] + '…', 7))
        y += 14
    return ''.join(o), y


def page(svg_body: str, name: str) -> str:
    """One A3 sheet as a self-contained HTML document."""
    frame = (R(15, 15, W - 30, H - 30, sw=1.2) + R(FR[0], FR[1], FR[2] - FR[0], FR[3] - FR[1], sw=1.6))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="420mm" height="297mm" '
           f'font-family="{FONT}">' + R(0, 0, W, H, stroke='none', fill='#fff') + frame + svg_body + '</svg>')
    return ('<!doctype html><html><head><meta charset="utf-8"><title>' + esc(name) + '</title>'
            '<style>@page{size:420mm 297mm;margin:0}html,body{margin:0;padding:0;background:#fff}svg{display:block}</style>'
            '</head><body>' + svg + '</body></html>')
