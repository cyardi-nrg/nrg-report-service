# Version: v1 (2026-11-20) — Express Cranes 75 kWp: string layout for the LANDSCAPE layout (south shed)
# 120 x Adani 625 Wp, landscape (long side along the E–W ridge), 4 groups L1–L4 of 5 rows x 6, 6 strings x 20.
# Geometry from the 3D model (3d-design/express-cranes/src/viewer.template.html v1): south shed 16.6 x 28.1 m,
# ridge E–W at mid-length, 10° slopes; L1, L2 on the north face, L3, L4 on the south face; walkways (300 mm)
# in the L1|L2 and L3|L4 gaps, along the ridge and down the west side. Drawn square to the shed (the shed
# itself sits ~6° clockwise of true north).
# Owner's stringing rules: 5 panels up the slope per column, so a string of 4 columns (20) starts and ends on
# the same (walkway) edge; panels joined side by side (long edges), turns only at the column ends; string
# ends on the walkway side; mirrored partner strings so + meets + and − meets − (Y possible); never red next
# to black where two strings meet; label (ADANI) corner on each panel's + side.
#   python3 express_stringing.py   ->  Express-Cranes_Stringing-Landscape_v1.png
import math
import os

from PIL import Image, ImageDraw, ImageFont

VERSION = 'v1'
HERE = os.path.dirname(os.path.abspath(__file__))
BRAND = 'ADANI'

# ---------------------------------------------------------------- geometry (metres, shed frame: x east, y south)
W, L = 16.61, 28.13
MOD_L, MOD_W, MGAP = 2.382, 1.134, 0.02
COS = math.cos(math.radians(10))
PD = MOD_W * COS                      # module depth on plan (10° slope)
WALK_GAP = 0.6 * COS
GW = 6 * MOD_L + 5 * MGAP             # group width (E–W)
GD = 5 * PD + 4 * MGAP                # group depth (N–S)
RIDGE = L / 2
HALF = 2 * GD + WALK_GAP
U0 = (W - GW) / 2
_s = []
for h0 in (0, RIDGE):
    s0 = h0 + (RIDGE - HALF) / 2
    _s += [s0, s0 + GD + WALK_GAP]
GROUPS = {'L1': _s[0], 'L2': _s[1], 'L3': _s[2], 'L4': _s[3]}     # y of each group's north edge
FACE = {'L1': 'N', 'L2': 'N', 'L3': 'S', 'L4': 'S'}
WALK_W = 0.30


def cell_box(g, c, r):
    """module (column c = 0..5 from the west, row r = 0..4 from the north) -> (x0, y0, x1, y1) metres"""
    x0 = U0 + c * (MOD_L + MGAP)
    y0 = GROUPS[g] + r * (PD + MGAP)
    return x0, y0, x0 + MOD_L, y0 + PD


def column(g, c, down):
    """the 5 panels of one column, walked north→south (down) or south→north"""
    rows = list(range(5)) if down else list(range(4, -1, -1))
    return [(g, c, r) for r in rows]


def snake(g, cols, start_down):
    seq, d = [], start_down
    for c in cols:
        seq += column(g, c, d)
        d = not d
    return seq


# ---------------------------------------------------------------- strings (owner's rules)
# L1 / L2 face each other across the L1|L2 walkway, L3 / L4 across the L3|L4 walkway.
# Full strings use columns 1–4 from the west; columns 5–6 of the two facing groups make one string that
# crosses its walkway once (at column 5) — 30-panel groups cannot be cut into 20s otherwise.
STRINGS = [
    ('S1', 'L1 cols 1–4', snake('L1', [0, 1, 2, 3], start_down=False)),                       # + / − on L1 south edge
    ('S2', 'L1 + L2 cols 5–6', snake('L1', [5, 4], False) + snake('L2', [4, 5], True)),       # crosses the walkway at col 5
    ('S3', 'L2 cols 1–4', snake('L2', [0, 1, 2, 3], start_down=True)),                        # + / − on L2 north edge (mirror of S1)
    ('S4', 'L3 cols 1–4', snake('L3', [0, 1, 2, 3], start_down=False)),                       # + / − on L3 south edge
    ('S5', 'L3 + L4 cols 5–6', snake('L3', [5, 4], False) + snake('L4', [4, 5], True)),
    ('S6', 'L4 cols 1–4', snake('L4', [0, 1, 2, 3], start_down=True)),                        # + / − on L4 north edge (mirror of S4)
]
SCOL = {'S1': '#e6194b', 'S2': '#f58231', 'S3': '#4363d8', 'S4': '#3cb44b', 'S5': '#911eb4', 'S6': '#0f9b8e'}
JUMPER = 2.5            # m of 4 sq mm for a column turn (next column's end panel is one module length away)
CROSS = 1.5             # m of 4 sq mm across a walkway (0.6 m gap + slack), clipped under the grating


def label_corners(seq):
    """label corner on the panel's + side: + north -> 'NE' (as delivered), + south -> 'SW' (rotated 180°)"""
    out = {}
    for i, cell in enumerate(seq):
        nxt = seq[i + 1] if i + 1 < len(seq) else None
        prv = seq[i - 1] if i > 0 else None
        same = lambda a: a is not None and a[0] == cell[0] and a[1] == cell[1]
        if same(nxt):
            plus_north = nxt[2] > cell[2]          # − faces the next panel; + faces away from it
        elif same(prv):
            plus_north = prv[2] < cell[2]          # + faces the previous panel
        else:
            plus_north = True
        out[cell] = 'NE' if plus_north else 'SW'
    return out


def joints(seq):
    """(column turns, walkway crossings) along a string"""
    turns = cross = 0
    for a, b in zip(seq, seq[1:]):
        if a[0] != b[0]:
            cross += 1
        elif a[1] != b[1]:
            turns += 1
    return turns, cross


# ---------------------------------------------------------------- drawing
K = 30.0
OX, OY = 80, 150


def P(x, y):
    return OX + x * K, OY + y * K


def font(sz, bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else ''), sz)


def main():
    used = [c for _, _, s in STRINGS for c in s]
    assert len(used) == 120 and len(set(used)) == 120 and all(len(s) == 20 for _, _, s in STRINGS)
    im = Image.new('RGB', (1820, 1080), 'white')
    d = ImageDraw.Draw(im)
    d.text((30, 22), f'Express Cranes — 75 kWp — string layout, LANDSCAPE ({VERSION})', fill='#1e3a8a', font=font(30, True))
    d.text((30, 64), '120 × Adani 625 Wp · 4 groups of 5 rows × 6 on the south shed · 6 strings × 20 · north up (shed ~6° off true north) · '
           'landscape = long side along the ridge', fill='#333', font=font(16))
    # shed, ridge, walkways
    d.rectangle([P(0, 0), P(W, L)], outline='#111', width=3)
    d.line([P(0, RIDGE), P(W, RIDGE)], fill='#666', width=2)
    xW = U0 - 0.15 - WALK_W
    walks = [(xW, GROUPS['L1'] + GD + (WALK_GAP - WALK_W) / 2, U0 + GW, GROUPS['L1'] + GD + (WALK_GAP + WALK_W) / 2),
             (xW, RIDGE - WALK_W / 2, U0 + GW, RIDGE + WALK_W / 2),
             (xW, GROUPS['L3'] + GD + (WALK_GAP - WALK_W) / 2, U0 + GW, GROUPS['L3'] + GD + (WALK_GAP + WALK_W) / 2),
             (xW, 0.4, xW + WALK_W, L - 0.4)]
    for x0, y0, x1, y1 in walks:
        d.rectangle([P(x0, y0), P(x1, y1)], fill='#fcd34d', outline='#92400e')
    d.text(P(W - 0.2, RIDGE - 0.25), 'RIDGE', fill='#555', font=font(13, True), anchor='rb')
    d.text(P(W / 2, 0.15), 'NORTH FACE ↑ (slopes north)', fill='#555', font=font(13, True), anchor='mt')
    d.text(P(W / 2, L - 0.15), 'SOUTH FACE ↓ (slopes south)', fill='#555', font=font(13, True), anchor='mb')
    lx, ly = P(-0.6, L - 0.9)
    d.rectangle([lx - 9, ly - 12, lx + 9, ly + 12], fill='#facc15', outline='black')
    d.text((lx, ly + 16), 'LADDER', fill='#111', font=font(12, True), anchor='mt')
    for g, y0 in GROUPS.items():
        d.text(P(U0 + GW + 0.3, y0 + GD / 2), g, fill='#1f3bb8', font=font(18, True), anchor='lm')
    # modules, strings
    for sid, _, seq in STRINGS:
        corners = label_corners(seq)
        for cell in seq:
            x0, y0, x1, y1 = cell_box(*cell)
            a, b = P(x0, y0)
            c, e = P(x1, y1)
            d.rectangle([a, b, c, e], fill=SCOL[sid] + '', outline='#1f2937')
            s = 9
            if corners[cell] == 'NE':
                d.polygon([(c, b), (c - s, b), (c, b + s)], fill='#fde047', outline='#111')
                d.text((c - 3, b + s + 1), BRAND, fill='#111', font=font(8, True), anchor='rt')
            else:
                d.polygon([(a, e), (a + s, e), (a, e - s)], fill='#fde047', outline='#111')
                d.text((a + 3, e - s - 1), BRAND, fill='#111', font=font(8, True), anchor='lb')
    for sid, _, seq in STRINGS:
        pts = [P((cell_box(*c)[0] + cell_box(*c)[2]) / 2, (cell_box(*c)[1] + cell_box(*c)[3]) / 2) for c in seq]
        d.line(pts, fill='white', width=3)
        for (x, y), sym in ((pts[0], '+'), (pts[-1], '−')):
            d.ellipse([x - 10, y - 10, x + 10, y + 10], fill='white', outline='black', width=2)
            d.text((x, y), sym, fill='black', font=font(15, True), anchor='mm')
        for a, b in zip(seq, seq[1:]):                       # J marks: column turns and walkway crossings
            if a[1] != b[1] or a[0] != b[0]:
                pa = P((cell_box(*a)[0] + cell_box(*a)[2]) / 2, (cell_box(*a)[1] + cell_box(*a)[3]) / 2)
                pb = P((cell_box(*b)[0] + cell_box(*b)[2]) / 2, (cell_box(*b)[1] + cell_box(*b)[3]) / 2)
                mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                d.rectangle([mx - 7, my - 6, mx + 7, my + 6], fill='#ffd400' if a[0] == b[0] else '#fb923c', outline='black')
                d.text((mx, my), 'J' if a[0] == b[0] else 'X', fill='black', font=font(9, True), anchor='mm')
        mid = pts[len(pts) // 2 - 3]
        d.rounded_rectangle([mid[0] - 24, mid[1] - 12, mid[0] + 24, mid[1] + 12], 4, fill='white', outline='black')
        d.text(mid, sid, fill='black', font=font(15, True), anchor='mm')
    # side table
    x0, y = 700, 150
    d.text((x0, y), 'STRING SCHEDULE', fill='#111', font=font(18, True))
    y += 32
    cols = [x0, x0 + 70, x0 + 220, x0 + 290, x0 + 450, x0 + 555, x0 + 660]
    for xx, h in zip(cols, ['STRING', 'PANELS', 'FACE', '+ / − AT', 'TURNS (J)', 'CROSS (X)', 'MIRROR OF']):
        d.text((xx, y), h, fill='#111', font=font(13, True))
    y += 24
    edge = {'S1': 'L1 S edge', 'S2': 'L1 S + L2 N, col 6', 'S3': 'L2 N edge', 'S4': 'L3 S edge', 'S5': 'L3 S + L4 N, col 6', 'S6': 'L4 N edge'}
    partner = {'S1': 'S3', 'S3': 'S1', 'S4': 'S6', 'S6': 'S4', 'S2': '—', 'S5': '—'}
    tj = tx = 0
    for sid, where, seq in STRINGS:
        t, x = joints(seq)
        tj += t
        tx += x
        vals = [sid, where, 'NORTH' if FACE[seq[0][0]] == 'N' else 'SOUTH', edge[sid], str(t), str(x) if x else '–', partner[sid]]
        for xx, v in zip(cols, vals):
            d.text((xx, y), v, fill=SCOL[sid] if xx == x0 else '#111', font=font(13, sid == v))
        y += 22
    y += 10
    d.text((x0, y), f'Column-turn jumpers: {tj} × ≈{JUMPER} m · walkway crossings: {tx} × ≈{CROSS} m (4 sq mm, under the grating)',
           fill='#111', font=font(13))
    y += 40
    d.text((x0, y), 'HOW EACH STRING RUNS', fill='#111', font=font(16, True))
    y += 26
    notes = ['• 5 panels up the slope per column, joined side by side (long edges); a string of',
             '  4 columns snakes up-down-up-down, so + and − both land on the WALKWAY edge.',
             '• S1 / S3 face each other across the L1|L2 walkway as mirror images: + opposite +,',
             '  − opposite − (column 1 and column 4). Same for S4 / S6 across the L3|L4 walkway.',
             '  → each mirror pair can share one MPPT through a + Y and a − Y at the walkway.',
             '• Each group has 30 panels, so columns 5–6 of L1 and L2 make S2, crossing the',
             '  walkway once at column 5 (X); likewise S5 from L3 + L4. Their ends are at',
             '  column 6, away from the other strings\' ends, so red never meets black.',
             '• North-face strings (S1–S3) and south-face strings (S4–S6) never share an MPPT.',
             f'• ◥ / ◣ = {BRAND} label corner, on each panel\'s + side: top-right as delivered,',
             '  bottom-left = panel turned 180°. It alternates column by column.',
             '• J = column-turn jumper, X = walkway crossing.']
    for t in notes:
        d.text((x0, y), t, fill='#333', font=font(13))
        y += 21
    y += 14
    d.text((x0, y), 'CHECK (Adani 625 Wp, values scaled from the 620 W datasheet)', fill='#111', font=font(16, True))
    y += 26
    for t in ['• 20 × Voc at 5 °C ≈ 20 × 52.3 = 1,046 V < 1,100 V inverter max',
              '• Vmp 723–880 V; Imp ≈ 15.0 A per string (30.1 A per Y pair)',
              '• Inverter make / model and where it sits: to be confirmed (needed for MPPTs, home runs, tray)']:
        d.text((x0, y), t, fill='#333', font=font(13))
        y += 21
    d.text((30, im.height - 30), f'NRG Technologists · Express Cranes string layout {VERSION} · 20-11-2026 · geometry from 3D v1 '
           '(SolarEdge screenshot) — verify on site', fill='#777', font=font(13))
    out = os.path.join(HERE, f'Express-Cranes_Stringing-Landscape_{VERSION}.png')
    im.save(out)
    print(out, 'turns', tj, 'crossings', tx)


if __name__ == '__main__':
    main()
