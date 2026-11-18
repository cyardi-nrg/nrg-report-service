# Version: v2 (2026-11-18) — owner: entry into the staircase cabin only from the NORTH, WEST or SOUTH side (not east).
#   One sleeve mid-way along each of those three walls; every cable takes the sleeve with the shortest wall run.
#   Wall runs now follow the walls round the corners (no short-cuts through a room).
# Was v1 (2026-11-18) — Sangani Skyz: DC cable routes the way NRG lays them (owner, 18-11-2026)
#   string end → under the panels along a RAFTER to the table edge → along the edge PURLIN until the
#   structure can cross over onto the staircase cabin / lift room wall → ALONG THE WALL to the entry
#   sleeve → inside, down to the inverter.
# B1 has no wall beside it: its cables cross over onto B2's structure and carry on from there.
# Everything is worked in the array frame (u = metres along the rows, east; v = metres across rows, north).
from geom import BLOCKS, CABIN, PPM, U, N, P, panel_centre

PANEL_PITCH = 1.154      # m along a row
ROW_PITCH = 2.26         # m across rows (on plan)
FRAME_EVERY = 2.5        # panels between frames (rafter + columns), owner's structure rule
SLEEVE_H = 2.5           # m, entry sleeve height on the cabin wall
INV_H = 1.5              # m, inverter height inside
CABIN_IN = 2.0           # m, inside the cabin, sleeve → inverter (average)
SLACK = 1.0              # m per conductor
LIFT = [P(470, 718), P(632, 712), P(637, 828), P(475, 834)]   # lift room (dashed box south of the cabin)


def uv(pt):
    x, y = pt
    return (x * U[0] + y * U[1]) / PPM, (x * N[0] + y * N[1]) / PPM


def box(poly):
    us, vs = zip(*(uv(p) for p in poly))
    return min(us), max(us), min(vs), max(vs)


CAB = box(CABIN)          # (u0, u1, v0, v1)
LFT = box(LIFT)
ENTRY = {'N': ((CAB[0] + CAB[1]) / 2, CAB[3]),                # owner: no entry from the east
         'W': (CAB[0], (CAB[2] + CAB[3]) / 2),
         'S': ((CAB[0] + CAB[1]) / 2, CAB[2])}


def blk(b):
    (x0, y0), nc, nr, h = BLOCKS[b]
    u0, v0 = uv((x0, y0))
    c0 = -1 if b == 'B3W' else 0
    return dict(u0=u0 + c0 * PANEL_PITCH, u1=u0 + nc * PANEL_PITCH, v0=v0, v1=v0 + nr * ROW_PITCH, h=h, ub=u0)


def rafters(b):
    k = blk(b)
    n = int((k['u1'] - k['u0']) / (FRAME_EVERY * PANEL_PITCH))
    xs = [k['u0'] + j * FRAME_EVERY * PANEL_PITCH for j in range(n + 1)]
    if k['u1'] - xs[-1] > 0.5:
        xs.append(k['u1'])
    return xs


def clamp(x, a, b):
    return min(max(x, a), b)


def nearest(xs, x):
    return min(xs, key=lambda r: abs(r - x))


# ---------------------------------------------------------------- walking round a room's walls
def _corners(bx):
    u0, u1, v0, v1 = bx
    return [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]          # SW, SE, NE, NW (anticlockwise)


def _t(bx, p):
    """position of a wall point along the perimeter, starting at the SW corner, anticlockwise"""
    u0, u1, v0, v1 = bx
    w, h = u1 - u0, v1 - v0
    u, v = p
    d = {abs(v - v0): ('S', u - u0), abs(u - u1): ('E', w + v - v0), abs(v - v1): ('N', w + h + u1 - u), abs(u - u0): ('W', 2 * w + h + v1 - v)}
    return d[min(d)][1], 2 * (w + h)


def along_walls(bx, a, b):
    """shortest way round the room's walls from wall point a to wall point b: waypoints"""
    ta, per = _t(bx, a)
    tb, _ = _t(bx, b)
    cs = _corners(bx)
    tc = [_t(bx, c)[0] for c in cs]
    fwd = (tb - ta) % per
    if fwd <= per - fwd:
        mids = sorted((((t - ta) % per), c) for t, c in zip(tc, cs) if 0 < (t - ta) % per < fwd)
    else:
        mids = sorted((((ta - t) % per), c) for t, c in zip(tc, cs) if 0 < (ta - t) % per < per - fwd)
    return [a] + [c for _, c in mids] + [b]


def plen(pts):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def to_sleeve(land, on):
    """from the wall landing to the best sleeve: round the lift room (if landed there), across the gap, round the cabin"""
    best = None
    for side, e in ENTRY.items():
        if on == 'CAB':
            path = along_walls(CAB, land, e)
        else:
            top = (clamp(land[0], CAB[0] + 0.3, CAB[1] - 0.3), LFT[3])   # lift room north wall, under the cabin
            path = along_walls(LFT, land, top) + along_walls(CAB, (top[0], CAB[2]), e)
        if best is None or plen(path) < plen(best[1]):
            best = (side, path)
    return best


def route(cell):
    """waypoints (u, v) from a string end to the entry sleeve, the wall landing index, structure height, sleeve"""
    b = cell[0]
    k = blk(b)
    uc, vc = uv(panel_centre(*cell))
    ur = nearest(rafters(b), uc)
    pts = [(uc, vc), (ur, vc)]
    if b == 'B5':                                   # south edge purlin → over the cabin → cabin north wall
        tu = clamp(ur, CAB[0] + 0.3, CAB[1] - 0.3)
        pts += [(ur, k['v0']), (tu, k['v0']), (tu, CAB[3])]
        on = 'CAB'
    elif b in ('B4W', 'B4E'):                       # nearer edge purlin → table end beside the cabin → cabin side wall
        ve = k['v0'] if abs(vc - k['v0']) < abs(vc - k['v1']) else k['v1']
        end = k['u1'] if b == 'B4W' else k['u0']
        wall = CAB[0] if b == 'B4W' else CAB[1]
        pts += [(ur, ve), (end, ve), (wall, clamp(ve, CAB[2] + 0.3, CAB[3] - 0.3))]
        on = 'CAB'
    elif b in ('B3W', 'B3E'):                       # north edge purlin → table end beside the lift room → lift room side wall
        end = k['u1'] if b == 'B3W' else k['u0']
        wall = LFT[0] if b == 'B3W' else LFT[1]
        pts += [(ur, k['v1']), (end, k['v1']), (wall, clamp(k['v1'], LFT[2] + 0.3, LFT[3] - 0.3))]
        on = 'LFT'
    else:                                           # B2, and B1 via B2: north edge purlin → under the lift room → its south wall
        if b == 'B1':
            k2 = blk('B2')
            ur2 = nearest(rafters('B2'), ur)
            pts += [(ur, k['v1']), (ur, k2['v0']), (ur2, k2['v0'])]
            ur, k = ur2, k2
        tu = clamp(ur, LFT[0] + 0.3, LFT[1] - 0.3)
        pts += [(ur, k['v1']), (tu, k['v1']), (tu, LFT[2])]
        on = 'LFT'
    land = len(pts) - 1
    side, wall_path = to_sleeve(pts[-1], on)
    pts += wall_path[1:]
    return pts, land, BLOCKS[b][3], side


def length(cell):
    """per-conductor metres, broken down: structure (rafter + purlin + hop), crossing, wall, vertical, inside"""
    pts, land, h, side = route(cell)
    seg = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
    structure = sum(seg[:land - 1])
    cross = seg[land - 1]
    wall = sum(seg[land:])
    vert = abs(h - SLEEVE_H) + (SLEEVE_H - INV_H)
    inside = CABIN_IN + SLACK
    return dict(structure=structure, cross=cross, wall=wall, vert=vert, inside=inside,
                total=structure + cross + wall + vert + inside, side=side, pts=pts, land=land)
