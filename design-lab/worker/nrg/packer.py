# Design Lab worker v1.2.0 (2026-10-31) — fit panels on each roof face.
#
# Rules carried over from the owner-approved Pluga layout, made general:
#  * rows run along the building's own lines, across the slope (a rotated
#    building is handled — rows follow its longest wall);
#  * usable area = the face less its edge setback, less every marked
#    obstacle plus clearance (vents / skylights 0.3 m, cabins / tanks /
#    lift rooms 0.6 m, existing solar 0.5 m, trees 1 m);
#  * SHEET roofs: panels flush on the sheet, landscape in groups of 4 rows
#    or portrait in groups of 2, a 0.6 m walkway between groups; whichever
#    of landscape / portrait fits more ("portrait panels where they fit more");
#  * FLAT roofs: tables at 10° facing the roof's side nearest south —
#    portrait 1 / 2 / 3 rows or landscape 2 / 3 rows, whichever fits most —
#    spaced so a table never shades the next one on 21 Dec 9:00–15:00,
#    front leg at least as high as the parapet;
#  * then the shade check (nrg/sun.py) drops any panel with a shaded corner.
import math
from dataclasses import dataclass

import numpy as np
from shapely import affinity
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from .site import Site, Face
from .sun import shaded

GAP = 0.02           # between panels, m
WALK = 0.6           # walkway between row groups on sheet roofs, m
TILT_FLAT = 10.0     # table tilt on flat roofs, degrees
FRONT_LEG = 0.6      # minimum front leg on flat roofs, m
LIFT = 0.15          # panel above the sheet, m


@dataclass
class Module:
    face: str
    x: float                 # centre, site metres (x east, y south)
    y: float
    corners: list            # 4 (x, y) in site metres
    z: list                  # height of each corner, m
    orient: str              # 'L' / 'P'
    row: int
    u: float = 0.0           # position along the rows (local), for filling whole columns


def kwh_per_kwp(tilt_deg: float, facing: tuple) -> float:
    """Vadodara, kWh per kWp per year. Pinned to the Pluga figures the owner accepted (1:10 sheet:
    south 1500, north 1435) and a 10° south table ~1525; east / west in between. ESTIMATE."""
    cos_az = facing[1]                      # +1 facing south, -1 north
    return 1468 + 5.6 * tilt_deg * cos_az


def _frame(face: Face) -> float:
    """Angle (deg) to turn the face so its rows run along x and the slope runs down +y."""
    mrr = face.poly.minimum_rotated_rectangle
    c = list(mrr.exterior.coords)
    e1, e2 = (c[1][0] - c[0][0], c[1][1] - c[0][1]), (c[2][0] - c[1][0], c[2][1] - c[1][1])
    best, best_score = 0.0, -1.0
    for ex, ey in (e1, e2):
        n = math.hypot(ex, ey) or 1
        ux, uy = ex / n, ey / n
        score = abs(-uy * face.down[0] + ux * face.down[1])   # u perpendicular to the slope ⇔ normal along it
        if score > best_score:
            best, best_score = math.degrees(math.atan2(uy, ux)), score
    # make local +y point down the slope / to the front of the tables
    ang = -best
    a = math.radians(ang)
    dy_local = face.down[0] * math.sin(a) + face.down[1] * math.cos(a)
    return ang if dy_local >= 0 else ang + 180


def usable_area(site: Site, face: Face):
    keep_out = [o[1].buffer(o[3]) for o in site.obstacles if o[1].intersects(face.poly.buffer(1))]
    area = face.poly.buffer(-face.setback, join_style=2)
    if keep_out:
        area = area.difference(unary_union(keep_out))
    return area


def _rows(area_local, w, d, gap_after_row, group, walk, flat_table=False):
    """Pack rectangles w × d along x, rows going down +y. Returns [(x0, y0, row)]."""
    if area_local.is_empty:
        return []
    P = prep(area_local)
    minx, miny, maxx, maxy = area_local.bounds
    out, y, r = [], miny, 0
    while y + d <= maxy + 1e-6:
        x, placed = minx, False
        while x + w <= maxx + 1e-6:
            if P.contains(box(x + 1e-3, y + 1e-3, x + w - 1e-3, y + d - 1e-3)):   # 1 mm tolerance: an edge exactly on the boundary still fits
                out.append((x, y, r))
                x += w + GAP
                placed = True
            else:
                x += 0.1
        r += 1
        y += d + gap_after_row
        if group and r % group == 0:
            y += walk - gap_after_row
    return out


def pack_face(site: Site, face: Face, L: float, W: float, sun: list) -> dict:
    ang = _frame(face)
    a = math.radians(ang)
    origin = face.poly.centroid
    area = usable_area(site, face)
    loc = affinity.rotate(area, ang, origin=origin, use_radians=False)
    inv = lambda x, y: (origin.x + (x - origin.x) * math.cos(-a) - (y - origin.y) * math.sin(-a),
                        origin.y + (x - origin.x) * math.sin(-a) + (y - origin.y) * math.cos(-a))
    candidates = []
    if face.kind == 'sheet':
        alpha = math.atan(face.pitch)
        for o in 'LP':
            w, d = (L, W * math.cos(alpha)) if o == 'L' else (W, L * math.cos(alpha))
            cells = _rows(loc, w, d, GAP, 4 if o == 'L' else 2, WALK)
            mods = []
            for x0, y0, r in cells:
                cs = [inv(x0, y0), inv(x0 + w, y0), inv(x0 + w, y0 + d), inv(x0, y0 + d)]
                mods.append(Module(face.key, *inv(x0 + w / 2, y0 + d / 2), cs, [face.height_at(*c) + LIFT for c in cs], o, r, x0 + w / 2))
            candidates.append((o, mods, 0))
        tilt = math.degrees(alpha)
    else:
        # flat roof: try several table shapes and keep whichever fits most after the shade check —
        # portrait tables of 1, 2 or 3 rows, landscape tables of 2 or 3 rows
        t = math.radians(TILT_FLAT)
        slab = face.height_at(0, 0)
        front = max(FRONT_LEG, face.parapet)
        for o, n_rows in (('P', 2), ('P', 1), ('P', 3), ('L', 2), ('L', 3)):
            up, across = (L, W) if o == 'P' else (W, L)          # panel side up the tilt / along the table
            d1 = up * math.cos(t)
            dT = n_rows * d1 + (n_rows - 1) * GAP
            rise = n_rows * up * math.sin(t)
            gap = 0.6                                             # at least a walkway between tables
            for sx, sy, tn in sun:                                # …and no table shades the one behind, 21 Dec 9–15 h
                v_comp = sx * math.sin(a) + sy * math.cos(a)
                if v_comp > 0 and tn > 0:
                    gap = max(gap, rise / tn * v_comp)
            mods = []
            for x0, y0, r in _rows(loc, across, dT, gap, 0, 0):
                zf = lambda v, y0=y0: slab + front + (y0 + dT - v) * math.tan(t)   # front of the table is lowest
                for k in range(n_rows):
                    yy = y0 + k * (d1 + GAP)
                    cs = [inv(x0, yy), inv(x0 + across, yy), inv(x0 + across, yy + d1), inv(x0, yy + d1)]
                    mods.append(Module(face.key, *inv(x0 + across / 2, yy + d1 / 2), cs, [zf(yy), zf(yy), zf(yy + d1), zf(yy + d1)], o, n_rows * r + k, x0 + across / 2))
            candidates.append((o, mods, n_rows))
        tilt = TILT_FLAT

    # shade check on every candidate set, keep the one with most panels
    best_o, best, best_raw, best_rows = 'L', [], 0, 0
    for o, mods, n_rows in candidates:
        if not mods:
            continue
        xs = np.array([c[0] for m in mods for c in m.corners])
        ys = np.array([c[1] for m in mods for c in m.corners])
        zs = np.array([z for m in mods for z in m.z])
        hit = shaded(site, xs, ys, zs, sun).reshape(len(mods), 4).any(axis=1)
        kept = [m for m, h in zip(mods, hit) if not h]
        if len(kept) > len(best):
            best_o, best, best_raw, best_rows = o, kept, len(mods), n_rows
    return {
        'key': face.key, 'roof_no': face.roof_no, 'name': face.name, 'kind': face.kind, 'facing': face.facing,
        'tilt_deg': round(tilt, 1), 'orient': best_o, 'table_rows': best_rows, 'modules': best, 'shaded_out': best_raw - len(best),
        'yield': kwh_per_kwp(tilt, face.down), 'usable_m2': round(area.area, 1),
    }
