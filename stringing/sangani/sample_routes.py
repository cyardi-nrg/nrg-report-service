# Version: v2 (2026-11-18) — draws NRG's routing (routes.py): rafter → edge purlin → across onto the cabin /
#   lift room wall → along the wall → sleeve → inverter. Was v1: straight L to the nearest cabin wall.
# Sangani Skyz: DC cable route for sample flats
#   python3 sample_routes.py F48 F12 F30 F21   ->  Sangani-Skyz_DC-Route-Samples_v2.png
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routes  # noqa: E402
import sangani_stringing as S  # noqa: E402
from geom import CABIN, PPM, U, N, panel_poly, panel_centre  # noqa: E402

VERSION = 'v2'
PICK = sys.argv[1:] or ['F48', 'F12', 'F30', 'F21']
COLS = ['#2563eb', '#059669', '#d97706', '#7c3aed']


def px(p):
    """array frame (u, v) metres -> picture pixels"""
    u, v = p
    return (u * U[0] + v * N[0]) * PPM, (u * U[1] + v * N[1]) * PPM


def main():
    flats = S.build_flats()
    order = sorted(flats, key=lambda f: -S.to_m(panel_centre(*f[1][0]))[1] * 1000 + S.to_m(panel_centre(*f[1][0]))[0])
    rows = {f'F{i+1:02d}': f for i, f in enumerate(order)}
    base = Image.open(os.path.join(S.HERE, 'Sangani-Skyz_2D-layout_v1.2.jpg')).convert('RGB').crop((40, 230, 1440, 1470))
    ox, oy = 40, 230
    im = Image.new('RGB', (base.width + 760, base.height + 120), 'white')
    g = base.convert('L').convert('RGB')
    im.paste(Image.blend(g, Image.new('RGB', g.size, 'white'), 0.6), (0, 90))
    d = ImageDraw.Draw(im)

    def T(pt):
        return pt[0] - ox, pt[1] - oy + 90
    d.text((20, 15), f'Sangani Skyz — DC cable routes, NRG routing — sample flats {", ".join(PICK)} ({VERSION})',
           fill='#1e3a8a', font=S.font(26, True))
    d.text((20, 52), 'Red = +, black = −. Under the panels along a RAFTER (dashed) → along the edge PURLIN → across onto the cabin / '
           'lift room WALL (dots) → along the wall → sleeve → inverter.', fill='#333', font=S.font(15))
    d.polygon([T(p) for p in CABIN], fill='#fde68a', outline='#92400e')
    d.polygon([T(p) for p in routes.LIFT], fill='#fef3c7', outline='#92400e')
    cab = [T(p) for p in CABIN]
    d.text((sum(p[0] for p in cab) / 4, sum(p[1] for p in cab) / 4), 'STAIRCASE\nCABIN', fill='#92400e', font=S.font(14, True), anchor='mm', align='center')
    lf = [T(p) for p in routes.LIFT]
    d.text((sum(p[0] for p in lf) / 4, sum(p[1] for p in lf) / 4), 'LIFT ROOM', fill='#92400e', font=S.font(13, True), anchor='mm')
    for _, cells in flats:
        for c in cells:
            d.polygon([T(p) for p in panel_poly(*c)], outline='#9ca3af')
    for b in routes.BLOCKS:                              # frames (rafters)
        k = routes.blk(b)
        for ur in routes.rafters(b):
            d.line([T(px((ur, k['v0']))), T(px((ur, k['v1'])))], fill='#9ca3af', width=1)
    x0, y = base.width + 20, 110
    for n, sid in enumerate(PICK):
        blk, cells = rows[sid]
        col = COLS[n % len(COLS)]
        for c in cells:
            d.polygon([T(p) for p in panel_poly(*c)], fill=col, outline='#111')
        pts = [T(panel_centre(*c)) for c in cells]
        d.line(pts, fill='white', width=3)
        res = {}
        for end, cable, off in ((cells[0], '#dc2626', -3), (cells[-1], '#111111', 3)):
            L = routes.length(end)
            res[cable] = L
            pp = [T(px(p)) for p in L['pts']]
            pp = [(x + off, yy + off) for x, yy in pp]
            land = L['land']
            d.line(pp[:land], fill=cable, width=4)                      # on the structure
            d.line(pp[land - 1:land + 1], fill=cable, width=2)          # crossing over
            for a, z in zip(pp[land:], pp[land + 1:]):                  # along the wall: dotted
                steps = max(1, int(((z[0] - a[0]) ** 2 + (z[1] - a[1]) ** 2) ** 0.5 / 9))
                for i in range(0, steps, 2):
                    t0, t1 = i / steps, min(1, (i + 1) / steps)
                    d.line([(a[0] + (z[0] - a[0]) * t0, a[1] + (z[1] - a[1]) * t0), (a[0] + (z[0] - a[0]) * t1, a[1] + (z[1] - a[1]) * t1)],
                           fill=cable, width=4)
        for (x, yy), sym in ((pts[0], '+'), (pts[-1], '−')):
            d.ellipse([x - 9, yy - 9, x + 9, yy + 9], fill='white', outline='black')
            d.text((x, yy), sym, fill='black', font=S.font(13, True), anchor='mm')
        mx, my = sum(p[0] for p in pts) / 4, sum(p[1] for p in pts) / 4
        d.rounded_rectangle([mx - 24, my - 12, mx + 24, my + 12], 4, fill='white', outline='black')
        d.text((mx, my), sid, fill='black', font=S.font(14, True), anchor='mm')
        P_, M_ = res['#dc2626'], res['#111111']
        d.text((x0, y), f'{sid}  ({blk}, structure {S.BLOCKS[cells[0][0]][3]:.1f} m) → {P_["side"]} sleeve', fill=col, font=S.font(17, True))
        y += 27
        lines = [('', '+ (red)', '− (black)'),
                 ('Rafter + purlin' + (' (+ B2)' if cells[0][0] == 'B1' else ''), f'{P_["structure"]:.1f}', f'{M_["structure"]:.1f}'),
                 ('Crossing to the wall', f'{P_["cross"]:.1f}', f'{M_["cross"]:.1f}'),
                 ('Along the wall', f'{P_["wall"]:.1f}', f'{M_["wall"]:.1f}'),
                 ('Up / down to sleeve + inverter', f'{P_["vert"]:.1f}', f'{M_["vert"]:.1f}'),
                 ('Inside cabin + slack', f'{P_["inside"]:.1f}', f'{M_["inside"]:.1f}'),
                 ('TOTAL (m)', f'{P_["total"]:.1f}', f'{M_["total"]:.1f}')]
        for a, b, c in lines:
            bold = a in ('', 'TOTAL (m)')
            d.text((x0, y), a, fill='#111', font=S.font(13, bold))
            d.text((x0 + 270, y), b, fill='#111', font=S.font(13, bold))
            d.text((x0 + 370, y), c, fill='#111', font=S.font(13, bold))
            y += 19
        vd = S.IMP * S.R_DC * (P_['total'] + M_['total']) / (4 * S.VMP) * 100
        d.text((x0, y), f'Loop {P_["total"] + M_["total"]:.1f} m · ΔV {vd:.2f} % on 2.5 sq mm', fill='#111', font=S.font(13))
        y += 34
    for side, (eu, ev) in routes.ENTRY.items():           # sleeves last, so no panel hides them
        x, y = T(px((eu, ev)))
        d.rectangle([x - 9, y - 9, x + 9, y + 9], fill='white', outline='#92400e', width=2)
        d.text((x + (14 if side == 'W' else -14), y + 22), f'{side} SLEEVE', fill='#92400e', font=S.font(12, True), anchor='lm' if side == 'W' else 'rm')
    notes = ['ASSUMED — please confirm:',
             '• Two entry sleeves, mid-way along the cabin\'s west and east',
             '  walls; inverters on those two walls inside.',
             '• Cables cross onto the wall at structure height and run',
             '  along it (clamped) down to the sleeve at 2.5 m.',
             '• B1 has no wall nearby: its cables hop onto B2 and run',
             '  along a B2 rafter to the lift room wall.']
    for t in notes:
        d.text((x0, y), t, fill='#92400e' if t.startswith('ASSUMED') else '#333', font=S.font(13, t.startswith('ASSUMED')))
        y += 19
    out = os.path.join(S.HERE, f'Sangani-Skyz_DC-Route-Samples_{VERSION}.png')
    im.save(out)
    print(out)


if __name__ == '__main__':
    main()
