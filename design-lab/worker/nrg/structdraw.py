# Design Lab worker v1.4.0 (2026-10-31) — structure drawing sheets (A3, NRG title block).
#
# From the structure saved in the Design Lab (app: lib/structure — the
# automatic choice or the owner's override, pass or fail), one sheet per
# panel table: side elevation of a typical frame, plan, member schedule,
# BOM lines, design data with each member's check. Sheet roofs: the
# aluminium-piece layout of a row. Pillow only; saved as PNG + one PDF.
import math
import re

from PIL import Image, ImageDraw

from .render import font, INK, MUTED, TEAL

DPI = 150
A3 = (int(420 / 25.4 * DPI), int(297 / 25.4 * DPI))      # 2480 × 1754 px
RED, AMBER, GREEN, STEEL, PANEL, GREY = (185, 28, 28), (180, 83, 9), (31, 157, 99), (70, 80, 96), (30, 58, 110), (200, 205, 212)
SEC = lambda s: str(s).replace('x', '×')


def _util_col(u):
    return RED if u > 1 else AMBER if u > 0.9 else GREEN


def _frame(d: ImageDraw.ImageDraw, W, H, title_lines):
    m = 40
    d.rectangle([m, m, W - m, H - m], outline=INK, width=4)
    tb = (W - m - 760, H - m - 250, W - m, H - m)          # title block, bottom right
    d.rectangle(tb, outline=INK, width=3)
    d.text((tb[0] + 24, tb[1] + 18), 'NRG TECHNOLOGISTS PVT. LTD.', fill=(0, 0, 254), font=font(30, True))
    d.text((tb[0] + 24, tb[1] + 56), 'Solar EPC · 989/6, GIDC Makarpura, Vadodara', fill=MUTED, font=font(20))
    for i, (k, v) in enumerate(title_lines):
        y = tb[1] + 96 + i * 30
        d.text((tb[0] + 24, y), k, fill=MUTED, font=font(19))
        d.text((tb[0] + 230, y), v, fill=INK, font=font(21, True))
    return tb


def _table(d, x, y, cols, rows, widths, size=19, head_fill=(241, 245, 249)):
    rh = size + 14
    d.rectangle([x, y, x + sum(widths), y + rh], fill=head_fill)
    cx = x
    for c, w in zip(cols, widths):
        d.text((cx + 8, y + 6), c, fill=MUTED, font=font(size, True)); cx += w
    for r, row in enumerate(rows):
        yy = y + rh * (r + 1)
        cx = x
        for i, (v, w) in enumerate(zip(row, widths)):
            col = INK
            if isinstance(v, tuple):
                v, col = v
            d.text((cx + 8, yy + 6), str(v), fill=col, font=font(size)); cx += w
        d.line([x, yy + rh, x + sum(widths), yy + rh], fill=(226, 232, 240), width=1)
    d.rectangle([x, y, x + sum(widths), y + rh * (len(rows) + 1)], outline=GREY, width=2)
    return y + rh * (len(rows) + 1)


def _dim(d, a, b, text, off=(0, 0), size=18):
    (x1, y1), (x2, y2) = a, b
    ox, oy = off
    d.line([x1 + ox, y1 + oy, x2 + ox, y2 + oy], fill=TEAL, width=2)
    for x, y in ((x1, y1), (x2, y2)):
        d.line([x + ox - 6, y + oy - 6, x + ox + 6, y + oy + 6], fill=TEAL, width=2)
    d.text(((x1 + x2) / 2 + ox, (y1 + y2) / 2 + oy - 4), text, fill=TEAL, font=font(size, True), anchor='md')


def gi_sheet(block: dict, inp: dict, saved: dict, customer: str, layout_label: str, sheet_no: str, version: int) -> Image.Image:
    W, H = A3
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    b = block['block']
    ladder = block.get('frameType') == 'ladder'
    tilt = float(inp.get('tiltDeg') or 10)
    t = math.radians(tilt)
    portrait = inp.get('orientation') == 'portrait'
    pL, pW = float(inp['panel']['lengthM']), float(inp['panel']['widthM'])
    up, ew = (pL, pW) if portrait else (pW, pL)
    pieces = block.get('pieces') or []
    raf = next((p for p in pieces if p['descr'].startswith('Rafter') or ' Rafter chord' in p['descr'] or p['descr'].startswith('R1')), None)
    Ls = float(raf['lenM']) if raf and not ladder else b['rows'] * up + (b['rows'] - 1) * 0.02
    legs = [p for p in pieces if p['descr'].startswith('Leg ')]
    n_legs = max(1, block.get('legsPerFrame') or len(legs) or 1)
    ovs = 0.4
    leg_s = [ovs + i * ((Ls - 2 * ovs) / max(1, n_legs - 1)) for i in range(n_legs)] if n_legs > 1 else [ovs]
    if legs and not ladder:   # simple frame: the saved cut list has each leg's height
        leg_h = [float(re.search(r'\(([\d.]+) m\)', p['descr']).group(1)) for p in legs]
    else:                     # ladder frame: legs rise with the slope from the front leg
        f0 = float(inp.get('frontLegM') or 0.6)
        leg_h = [f0 + (s - ovs) * math.sin(t) for s in leg_s]
    Wt = b['cols'] * ew + (b['cols'] - 1) * 0.02
    nr = int(block.get('frames') or 2)
    gap = float(block.get('frameGapM') or 2.0)

    tb = _frame(d, W, H, [('Client', customer), ('Project', layout_label), ('Drawing', f"Structure — {b['name']}"),
                          ('Sheet / rev', f'{sheet_no} · R{version}'), ('Scale', 'not to scale — dimensions in metres')])
    d.text((70, 60), f"{b['name']} — {b['rows']} × {b['cols']} panels ({'portrait' if portrait else 'landscape'}) · "
                     f"{'ladder-rafter frame' if ladder else 'simple GI frame'}", fill=INK, font=font(34, True))
    ok = block.get('pass')
    d.text((70, 108), '✓ PASSES the member checks' if ok else '✗ FAILS the member checks — quantities worked out as chosen, check before ordering',
           fill=GREEN if ok else RED, font=font(24, True))

    # ---------- side elevation (left top)
    ex, ey, ew_box, eh_box = 90, 200, 1050, 620
    d.text((ex, ey - 40), 'SIDE ELEVATION — typical frame (looking east)', fill=INK, font=font(24, True))
    top = max(leg_h) + Ls * math.sin(t) + 0.3
    sc = min((ew_box - 120) / (Ls * math.cos(t) + 1.0), (eh_box - 140) / max(1.0, top + 0.6))
    gx, gy = ex + 60, ey + eh_box - 60                             # ground line origin (front = left = south)
    P = lambda s, z: (gx + s * sc, gy - z * sc)                    # s along the plan (m from the front end), z height
    d.line([ex, gy, ex + ew_box, gy], fill=INK, width=3)
    d.text((ex, gy + 10), 'ROOF SLAB', fill=MUTED, font=font(18))
    front_z = leg_h[0]
    # rafter (slope: the front end is lowest)
    r0 = (0.0, front_z - ovs * math.tan(t)), (Ls * math.cos(t), front_z + (Ls - ovs) * math.sin(t))
    d.line([P(*r0[0]), P(*r0[1])], fill=STEEL, width=10 if not ladder else 6)
    if ladder:
        d.line([P(r0[0][0], r0[0][1] - 0.25), P(r0[1][0], r0[1][1] - 0.25)], fill=STEEL, width=6)
    # panels on top
    for k in range(b['rows']):
        s0, s1 = k * (up + 0.02), k * (up + 0.02) + up
        d.line([P(s0 * math.cos(t), front_z - ovs * math.tan(t) + s0 * math.sin(t) + 0.12), P(s1 * math.cos(t), front_z - ovs * math.tan(t) + s1 * math.sin(t) + 0.12)], fill=PANEL, width=14)
        for q in (0.25, 0.75):                                     # purlins under each panel row
            s = s0 + q * up
            x, z = P(s * math.cos(t), front_z - ovs * math.tan(t) + s * math.sin(t) + 0.04)
            d.rectangle([x - 7, z - 7, x + 7, z + 7], fill=(14, 116, 144))
    # legs
    for i, s in enumerate(leg_s):
        h = leg_h[min(i, len(leg_h) - 1)]
        d.line([P(s * math.cos(t), 0), P(s * math.cos(t), h)], fill=STEEL, width=8)
        d.rectangle([P(s * math.cos(t) - 0.15, 0.06)[0], P(0, 0.06)[1], P(s * math.cos(t) + 0.15, 0)[0], P(0, 0)[1]], fill=(120, 120, 120))
        d.text((P(s * math.cos(t), h / 2)[0] + 12, P(0, h / 2)[1]), f'{h:.2f} m', fill=TEAL, font=font(18, True), anchor='lm')
    if len(leg_s) > 1 and not ladder:
        d.line([P(leg_s[0] * math.cos(t), 0.15), P(leg_s[1] * math.cos(t), leg_h[1] - 0.1)], fill=(120, 130, 145), width=4)
    _dim(d, P(0, 0), P(Ls * math.cos(t), 0), f'{Ls * math.cos(t):.2f} m on plan · rafter {Ls:.2f} m', off=(0, 40))
    if len(leg_s) > 1:
        _dim(d, P(leg_s[0] * math.cos(t), 0), P(leg_s[1] * math.cos(t), 0), f'legs {block.get("legSpacingM") or (leg_s[1] - leg_s[0]):.2f} m', off=(0, 80), size=16)
    d.text((P(Ls * math.cos(t), top)[0] - 10, P(0, top)[1]), f'tilt {tilt:.0f}°', fill=INK, font=font(22, True), anchor='rm')
    d.text((ex + ew_box - 290, gy + 12), '◄ south is to the left (front, lowest)', fill=MUTED, font=font(18))

    # ---------- plan (right top)
    px0, py0, pw, ph = 1220, 200, 1160, 620
    d.text((px0, py0 - 40), 'PLAN — rafters, legs, purlins, panels', fill=INK, font=font(24, True))
    Dp = Ls * math.cos(t)
    sp = min((pw - 80) / (Wt + 0.6), (ph - 120) / (Dp + 0.6))
    ox, oy = px0 + 40, py0 + 40
    Q = lambda x, y: (ox + x * sp, oy + y * sp)                   # x east, y south (plan); north up
    for k in range(b['rows']):
        for c in range(b['cols']):
            x0, y0 = c * (ew + 0.02), (b['rows'] - 1 - k) * (up + 0.02) * math.cos(t)
            d.rectangle([Q(x0, y0), Q(x0 + ew, y0 + up * math.cos(t))], outline=PANEL, width=2, fill=(214, 224, 240))
        for q in (0.25, 0.75):
            yy = (b['rows'] - 1 - k) * (up + 0.02) * math.cos(t) + (1 - q) * up * math.cos(t)
            d.line([Q(-0.02, yy), Q(Wt + 0.02, yy)], fill=(14, 116, 144), width=3)
    xs = [0.3 + i * gap for i in range(nr)] if nr > 1 else [Wt / 2]
    if nr > 1:
        xs = [0.3 + i * (Wt - 0.6) / (nr - 1) for i in range(nr)]
    for x in xs:
        d.line([Q(x, -0.2), Q(x, Dp + 0.2)], fill=STEEL, width=6)
        for s in leg_s:
            cx, cy = Q(x, Dp - s * math.cos(t))
            d.rectangle([cx - 8, cy - 8, cx + 8, cy + 8], fill=(234, 88, 12))
    if nr > 1:
        _dim(d, Q(xs[0], Dp), Q(xs[1], Dp), f"{block.get('frameGapM', gap):.2f} m", off=(0, 50), size=17)
    _dim(d, Q(0, Dp), Q(Wt, Dp), f'{Wt:.2f} m · {nr} rafters', off=(0, 95))
    d.text((px0 + pw - 40, py0 - 36), 'N ▲', fill=INK, font=font(24, True))
    d.text((px0, py0 + ph + 4), '■ leg + base plate (4 anchors)   — rafter   — purlin (2 per panel row)', fill=MUTED, font=font(17))

    # ---------- member schedule (bottom left)
    y = 900
    d.text((90, y), 'MEMBER SCHEDULE — cut pieces for this table', fill=INK, font=font(24, True))
    cut = lambda t_, n_: t_ if len(t_) <= n_ else t_[:n_ - 1] + '…'
    rows = [(SEC(p['section']), cut(p['descr'], 46), p['qty'], f"{float(p['lenM']):.3f}", f"{p['qty'] * float(p['lenM']):.1f}") for p in pieces[:16]]
    end = _table(d, 90, y + 40, ['Pipe', 'Piece', 'Qty', 'Length m', 'Total m'], rows, [150, 520, 80, 130, 130])
    if len(pieces) > 16:
        d.text((90, end + 6), f'+ {len(pieces) - 16} more pieces — see the BOM', fill=MUTED, font=font(17))

    # ---------- checks + design data (bottom middle)
    x2, y2 = 1150, 900
    d.text((x2, y2), 'MEMBER CHECKS', fill=INK, font=font(24, True))
    mrows = [(m['member'], SEC(m['section'])[:44], (f"{round(100 * m['util'])} %", _util_col(m['util']))) for m in (block.get('members') or [])]
    end = _table(d, x2, y2 + 40, ['Member', 'Section', 'Uses'], mrows, [250, 520, 110])
    site = inp.get('site') or {}
    data = [f"Wind {site.get('windKmh')} km/h · surroundings cat. {site.get('terrain')} · {site.get('floors')} floor(s) × {site.get('storeyH')} m",
            f"Pipe grade fy {inp.get('fy')} N/mm² · panel {pL} × {pW} m, {inp['panel'].get('kg')} kg",
            f"Uplift up to {block.get('upliftKn')} kN per leg · {block.get('legs')} legs on this table",
            'IS 875-3 wind, IS 800 checks without safety factors ("gives way at"); sag limit span/180.',
            "Uses over 100 % = fails; over 90 % = close."]
    for i, line in enumerate(data):
        d.text((x2, end + 18 + i * 28), line, fill=MUTED, font=font(18))
    return img


def alu_sheet(saved: dict, inp: dict, customer: str, layout_label: str, version: int) -> Image.Image:
    W, H = A3
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    portrait = inp.get('orientation') == 'portrait'
    _frame(d, W, H, [('Client', customer), ('Project', layout_label), ('Drawing', 'Structure — sheet roof, aluminium'),
                     ('Sheet / rev', f'S-01 · R{version}'), ('Scale', 'not to scale')])
    d.text((70, 60), f"Sheet roof — aluminium {'100 × 300 (portrait)' if portrait else '80 × 100 trapezoidal (landscape)'} pieces", fill=INK, font=font(34, True))
    d.text((70, 108), 'Short pieces shared between neighbouring panels: 2 × (panels in a row + 1) per row, screwed to the sheet crests', fill=MUTED, font=font(22))
    # one typical row of 6 panels
    pL, pW = float(inp['panel']['lengthM']), float(inp['panel']['widthM'])
    up, ew = (pL, pW) if portrait else (pW, pL)
    n = 6
    sc = 1500 / (n * (ew + 0.02))
    x0, y0 = 160, 260
    for c in range(n):
        x = x0 + c * (ew + 0.02) * sc
        d.rectangle([x, y0, x + ew * sc, y0 + up * sc], fill=(214, 224, 240), outline=PANEL, width=3)
    for c in range(n + 1):
        x = x0 + c * (ew + 0.02) * sc - 0.01 * sc
        for yy in (y0 + 0.2 * up * sc, y0 + 0.8 * up * sc):
            d.rectangle([x - 14, yy - 30, x + 14, yy + 30], fill=STEEL)
            d.text((x, yy + 36), 'mid' if 0 < c < n else 'end', fill=MUTED, font=font(16), anchor='mt')
    d.text((x0, y0 + up * sc + 70), f'Typical row of {n} panels: {2 * (n + 1)} aluminium pieces, {2 * (n - 1)} mid clamps, 4 end clamps', fill=INK, font=font(22, True))
    y = y0 + up * sc + 140
    rows = [(l['description'], l['quantity'], l['unit']) for l in saved.get('lines', [])]
    _table(d, 90, y, ['Item (whole job)', 'Qty', 'Unit'], rows, [900, 160, 120], size=21)
    return img


def save(sheets: list, png_paths: list, pdf_path: str) -> None:
    for im, p in zip(sheets, png_paths):
        im.save(p, optimize=True)
    rgb = [im.convert('RGB') for im in sheets]
    rgb[0].save(pdf_path, save_all=True, append_images=rgb[1:], resolution=DPI)
