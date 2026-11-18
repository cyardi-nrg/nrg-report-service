# Version: v1 (2026-11-18) — Sangani Skyz: draw the DC cable route used in the v1 schedule for sample flats
#   python3 sample_routes.py F48 F12   ->  Sangani-Skyz_DC-Route-Samples_v1.png
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sangani_stringing as S  # noqa: E402
from geom import BLOCKS, CABIN, PPM, panel_poly, panel_centre  # noqa: E402

VERSION = 'v1'
PICK = sys.argv[1:] or ['F48', 'F12']


def route(pt):
    """the L-shaped terrace route of to_cabin(): east/west leg first, then north/south, to the nearest cabin wall"""
    e, n = S.to_m(pt)
    e1 = min(max(e, S.CAB_E0), S.CAB_E1)
    n1 = min(max(n, S.CAB_N0), S.CAB_N1)
    return [(e, n), (e1, n), (e1, n1)]


def main():
    flats = S.build_flats()
    order = sorted(flats, key=lambda f: -S.to_m(panel_centre(*f[1][0]))[1] * 1000 + S.to_m(panel_centre(*f[1][0]))[0])
    rows = {f'F{i+1:02d}': f for i, f in enumerate(order)}
    base = Image.open(os.path.join(S.HERE, 'Sangani-Skyz_2D-layout_v1.2.jpg')).convert('RGB').crop((40, 230, 1440, 1470))
    ox, oy = 40, 230
    im = Image.new('RGB', (base.width + 720, base.height + 120), 'white')
    g = base.convert('L').convert('RGB')
    im.paste(Image.blend(g, Image.new('RGB', g.size, 'white'), 0.6), (0, 90))
    d = ImageDraw.Draw(im)

    def T(pt):
        return pt[0] - ox, pt[1] - oy + 90

    def TM(em):
        return T((em[0] * PPM, -em[1] * PPM))
    d.text((20, 15), f'Sangani Skyz — DC cable route used in the v1 schedule — sample flats {", ".join(PICK)} ({VERSION})',
           fill='#1e3a8a', font=S.font(26, True))
    d.text((20, 52), 'Red = + cable, black = − cable. Route = straight down the structure column at the string end, then an L along the '
           'terrace (E–W leg, then N–S leg) to the nearest cabin wall, through the wall, up to the inverter.', fill='#333', font=S.font(15))
    d.polygon([T(p) for p in CABIN], fill='#fde68a', outline='#92400e')
    for _, cells in flats:
        for c in cells:
            d.polygon([T(p) for p in panel_poly(*c)], outline='#9ca3af')
    x0, y = base.width + 20, 110
    cols = {'F48': '#2563eb', 'F12': '#059669'}
    for sid in PICK:
        blk, cells = rows[sid]
        col = cols.get(sid, '#7c3aed')
        for c in cells:
            d.polygon([T(p) for p in panel_poly(*c)], fill=col, outline='#111')
        pts = [T(panel_centre(*c)) for c in cells]
        d.line(pts, fill='white', width=3)
        lp, lm, jump = S.flat_dc(cells)
        h = max(BLOCKS[b][3] for b, _, _ in cells)
        for end, cable, off in ((cells[0], '#dc2626', -4), (cells[-1], '#111111', 4)):
            r = route(panel_centre(*end))
            pr = [TM(p) for p in r]
            pr = [(x + off, yy + off) for x, yy in pr]
            d.line(pr, fill=cable, width=4)
            d.ellipse([pr[-1][0] - 7, pr[-1][1] - 7, pr[-1][0] + 7, pr[-1][1] + 7], fill=cable)
        for (x, yy), sym in ((pts[0], '+'), (pts[-1], '−')):
            d.ellipse([x - 9, yy - 9, x + 9, yy + 9], fill='white', outline='black')
            d.text((x, yy), sym, fill='black', font=S.font(13, True), anchor='mm')
        mx, my = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
        d.rounded_rectangle([mx - 24, my - 12, mx + 24, my + 12], 4, fill='white', outline='black')
        d.text((mx, my), sid, fill='black', font=S.font(14, True), anchor='mm')
        # breakdown
        rp, rm = route(panel_centre(*cells[0])), route(panel_centre(*cells[-1]))
        ew_p, ns_p = abs(rp[1][0] - rp[0][0]), abs(rp[2][1] - rp[1][1])
        ew_m, ns_m = abs(rm[1][0] - rm[0][0]), abs(rm[2][1] - rm[1][1])
        d.text((x0, y), f'{sid}  ({blk}, structure {h:.1f} m high)', fill=col, font=S.font(18, True))
        y += 30
        lines = [('', '+ (red)', '− (black)'),
                 ('Down the column', f'{h:.1f}', f'{h:.1f}'),
                 ('Terrace, E–W leg', f'{ew_p:.1f}', f'{ew_m:.1f}'),
                 ('Terrace, N–S leg', f'{ns_p:.1f}', f'{ns_m:.1f}'),
                 ('Up the cabin wall', f'{S.INV_H:.1f}', f'{S.INV_H:.1f}'),
                 ('Inside the cabin', f'{S.CABIN_IN:.1f}', f'{S.CABIN_IN:.1f}'),
                 ('Slack', f'{S.SLACK:.1f}', f'{S.SLACK:.1f}'),
                 ('TOTAL (m)', f'{lp:.1f}', f'{lm:.1f}')]
        for a, b, c in lines:
            bold = a in ('', 'TOTAL (m)')
            d.text((x0, y), a, fill='#111', font=S.font(14, bold))
            d.text((x0 + 230, y), b, fill='#111', font=S.font(14, bold))
            d.text((x0 + 340, y), c, fill='#111', font=S.font(14, bold))
            y += 21
        vd = S.IMP * S.R_DC * (lp + lm) / (4 * S.VMP) * 100
        d.text((x0, y), f'Loop {lp + lm:.1f} m · ΔV {vd:.2f} % on 2.5 sq mm', fill='#111', font=S.font(14))
        y += 45
    notes = ['WHAT THIS ROUTE ASSUMES (v1) — to be agreed:',
             '• Each cable drops down the column at its string end.',
             '• It runs on the terrace floor in an L to the nearest',
             '  point of the cabin wall, passing under other blocks.',
             '• It enters the cabin through the wall at that point.',
             'In practice the cables of many flats should share a few',
             'trays and enter the cabin at one or two wall sleeves,',
             'which adds a few metres to some runs.']
    for t in notes:
        d.text((x0, y), t, fill='#92400e' if t.startswith('WHAT') else '#333', font=S.font(14, t.startswith('WHAT')))
        y += 21
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'Sangani-Skyz_DC-Route-Samples_{VERSION}.png')
    im.save(out)
    print(out)


if __name__ == '__main__':
    main()
