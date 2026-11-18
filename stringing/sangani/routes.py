# Version: v1 (2026-11-18) — Sangani Skyz: DC cable routes the way NRG lays them (owner, 18-11-2026)
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


CAB = box(CABIN)
LFT = box(LIFT)
ENTRY = {'W': (CAB[0], (CAB[2] + CAB[3]) / 2), 'E': (CAB[1], (CAB[2] + CAB[3]) / 2)}   # assumed: one sleeve mid-wall each side


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


def route(cell):
    """waypoints (u, v) from a string end to the entry sleeve, the wall landing index, and the structure height"""
    b = cell[0]
    k = blk(b)
    uc, vc = uv(panel_centre(*cell))
    ur = nearest(rafters(b), uc)
    pts = [(uc, vc), (ur, vc)]
    if b == 'B5':                                   # south edge purlin → over the cabin → cabin north wall
        tu = clamp(ur, CAB[0] + 0.3, CAB[1] - 0.3)
        pts += [(ur, k['v0']), (tu, k['v0']), (tu, CAB[3])]
    elif b in ('B4W', 'B4E'):                       # nearer edge purlin → table end beside the cabin → cabin side wall
        ve = k['v0'] if abs(vc - k['v0']) < abs(vc - k['v1']) else k['v1']
        end = k['u1'] if b == 'B4W' else k['u0']
        wall = CAB[0] if b == 'B4W' else CAB[1]
        pts += [(ur, ve), (end, ve), (wall, clamp(ve, CAB[2] + 0.3, CAB[3] - 0.3))]
    elif b in ('B3W', 'B3E'):                       # north edge purlin → table end beside the lift room → lift room side wall
        end = k['u1'] if b == 'B3W' else k['u0']
        wall = LFT[0] if b == 'B3W' else LFT[1]
        pts += [(ur, k['v1']), (end, k['v1']), (wall, clamp(k['v1'], LFT[2] + 0.3, LFT[3] - 0.3))]
    else:                                           # B2, and B1 via B2: north edge purlin → under the lift room → its south wall
        if b == 'B1':
            k2 = blk('B2')
            ur2 = nearest(rafters('B2'), ur)
            pts += [(ur, k['v1']), (ur, k2['v0']), (ur2, k2['v0'])]
            ur, k = ur2, k2
        tu = clamp(ur, LFT[0] + 0.3, LFT[1] - 0.3)
        pts += [(ur, k['v1']), (tu, k['v1']), (tu, LFT[2])]
    land = len(pts) - 1
    side = 'W' if pts[-1][0] < (CAB[0] + CAB[1]) / 2 else 'E'
    eu, ev = ENTRY[side]
    lu, lv = pts[-1]
    pts += [(eu, lv), (eu, ev)]                     # along the walls (lift room → cabin) to the sleeve on that side
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
