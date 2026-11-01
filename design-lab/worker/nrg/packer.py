# Design Lab worker v1.11.0 (2026-11-01) — fit panels on each roof face.
#
# v1.11.0 (owner: "allow diff structure to be at diff heights … roof 1 at 2 mtr … staircase cabin at 0.5"):
#   a roof's own structure height (Roof design) decides it — ELEV_MIN or more = raised walk-under tables (3 + 2
#   rows) with their low edge at that height; less = low tables with that front leg. Not given: Site questions
#   (Elevated → ELEV_CLEAR) as in v1.10.
#
# v1.10.0 (owner, Keystone Skymont): GI tables are ALWAYS PORTRAIT — landscape needs more purlin, already
#   settled; it is no longer tried on flat roofs at all. And the Site question "Mounting: Elevated structure"
#   is now read: an elevated roof gets raised portrait tables of 3 and 2 rows (the frames the Structure stage
#   designs) with only a walkway between them, as one block — e.g. 3 rows + walkway + 2 rows. The panels are
#   above the parapet, so its shadow no longer removes rows, and the frame may overhang the roof edge a little.
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
#  * FLAT roofs, low tables: at 10° facing the roof's side nearest south —
#    PORTRAIT only (1 / 2 / 3 rows; owner: landscape needs ~2.5× the 40×40
#    purlin pipe) — spaced so a table never shades the next one on 21 Dec
#    9:00–15:00, front leg at least as high as the parapet;
#  * FLAT roofs, ELEVATED (Site questions): portrait tables of 3 and 2 rows at
#    10°, a 0.6 m walkway between tables, low edge ELEV_CLEAR above the slab;
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
ELEV_CLEAR = 2.1     # elevated: low edge of the panels above the slab (walk-under), m — when the roof has no height of its own
ELEV_MIN = 1.8       # a roof's structure height from this up is laid out as raised walk-under tables, m
ELEV_WALK = 0.6      # elevated: walkway between tables, m
ELEV_OVERHANG = 0.3  # elevated: the panels may run past the roof edge / setback by this much (posts stay on the roof), m
ELEV_TABLES = (3, 2) # elevated: rows per table — the owner's 2- and 3-row frames


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


def _rows(area_local, w, d, gap_after_row, group, walk, flat_table=False, row_ok=None):
    """Pack rectangles w × d along x, rows going down +y. Returns [(x0, y0, row)].
    row_ok(cells) → False drops a whole row (e.g. every panel in it would be in shade) and slides down instead,
    so it doesn't count as one of a group's rows (owner, v1.8.6: real 5-row groups, mirrored about the walkway)."""
    if area_local.is_empty:
        return []
    P = prep(area_local)
    minx, miny, maxx, maxy = area_local.bounds
    out, y, r = [], miny, 0
    while y + d <= maxy + 1e-6:
        x, row = minx, []
        while x + w <= maxx + 1e-6:
            if P.contains(box(x + 1e-3, y + 1e-3, x + w - 1e-3, y + d - 1e-3)):   # 1 mm tolerance: an edge exactly on the boundary still fits
                row.append((x, y, r))
                x += w + GAP
            else:
                x += 0.1
        step = 0.1
        if row and row_ok is not None and not row_ok(row):
            row, step = [], 0.25          # all in shade: slide in bigger steps (the shade check is the slow part)
        if not row:
            # an empty row (roof edge, setback, all in shade) must not count as one of the 5 — otherwise the first
            # group has only 4 real rows and its strings can't mirror the group across the walkway. Slide down.
            y += step
            continue
        out += row
        r += 1
        y += d + gap_after_row
        if group and r % group == 0:
            y += walk - gap_after_row
    return out


def pack_face(site: Site, face: Face, L: float, W: float, sun: list, elevated: bool = False) -> dict:
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
        # landscape in groups of 5 rows (owner: a 20-panel string = 4 columns × 5 rows, so + and − both land
        # on the walkway side), groups of 4 as the fallback; portrait in groups of 2; walkways between the groups
        for o, group in (('L', 5), ('L', 4), ('P', 2)):
            w, d = (L, W * math.cos(alpha)) if o == 'L' else (W, L * math.cos(alpha))

            def row_ok(row, w=w, d=d):
                # keep a row unless EVERY panel in it would be shaded (21 Dec, 9–15 h)
                xs, ys, zs = [], [], []
                for x0, y0, _ in row:
                    for cx, cy in ((x0, y0), (x0 + w, y0), (x0 + w, y0 + d), (x0, y0 + d)):
                        X, Y = inv(cx, cy)
                        xs.append(X); ys.append(Y); zs.append(face.height_at(X, Y) + LIFT)
                hit = shaded(site, np.array(xs), np.array(ys), np.array(zs), sun).reshape(len(row), 4).any(axis=1)
                return not hit.all()
            cells = _rows(loc, w, d, GAP, group, WALK, row_ok=row_ok)
            mods = []
            for x0, y0, r in cells:
                cs = [inv(x0, y0), inv(x0 + w, y0), inv(x0 + w, y0 + d), inv(x0, y0 + d)]
                mods.append(Module(face.key, *inv(x0 + w / 2, y0 + d / 2), cs, [face.height_at(*c) + LIFT for c in cs], o, r, x0 + w / 2))
            candidates.append((o, mods, group))
        tilt = math.degrees(alpha)
    elif (face.structure is not None and face.structure >= ELEV_MIN) or (face.structure is None and elevated):
        clear = face.structure if face.structure is not None else ELEV_CLEAR
        mods, tables = _elevated(site, face, area, ang, origin, inv, L, W, clear)
        candidates.append(('P', mods, max(tables) if tables else 3))
        tilt = TILT_FLAT
    else:
        # flat roof: try several table shapes and keep whichever fits most after the shade check —
        # PORTRAIT tables of 1, 2 or 3 rows only (owner, v1.10.0: GI structures are always portrait)
        t = math.radians(TILT_FLAT)
        slab = face.height_at(0, 0)
        front = face.structure if face.structure is not None else max(FRONT_LEG, face.parapet)   # owner's height, else above the parapet
        for o, n_rows in (('P', 2), ('P', 1), ('P', 3)):
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

    # shade check on every candidate set, then pick
    results = []
    for o, mods, n_rows in candidates:
        if not mods:
            continue
        xs = np.array([c[0] for m in mods for c in m.corners])
        ys = np.array([c[1] for m in mods for c in m.corners])
        zs = np.array([z for m in mods for z in m.z])
        hit = shaded(site, xs, ys, zs, sun).reshape(len(mods), 4).any(axis=1)
        results.append((o, [m for m, h in zip(mods, hit) if not h], len(mods), n_rows))
    best_o, best, best_raw, best_rows = 'L', [], 0, 0
    if results:
        top = lambda o: max((r for r in results if r[0] == o), key=lambda r: len(r[1]), default=None)
        p_best, l_best = top('P'), top('L')
        if face.kind == 'flat':
            # GI tables: portrait only (owner) — only portrait candidates are built for flat roofs
            pick = p_best
        else:
            # sheet roofs: landscape groups of 5 preferred over 4 unless 4 fits 5 %+ more; then whichever of
            # landscape / portrait fits more (owner)
            l5 = next((r for r in results if r[0] == 'L' and r[3] == 5), None)
            l4 = next((r for r in results if r[0] == 'L' and r[3] == 4), None)
            # owner (v1.8.6): 5 landscape rows is THE preference — 4 only when 5 rows fit far fewer panels (< 80 %)
            land = l5 if l5 and (not l4 or len(l5[1]) >= 0.8 * len(l4[1])) else l4
            pool = [r for r in results if r[0] == 'P'] + ([land] if land else [])
            pick = max(pool, key=lambda r: len(r[1]))
        best_o, best, best_raw, best_rows = pick
    is_elev = face.kind == 'flat' and ((face.structure is not None and face.structure >= ELEV_MIN) or (face.structure is None and elevated))
    front_leg = (face.structure if face.structure is not None else ELEV_CLEAR) if is_elev else \
        (face.structure if face.structure is not None else max(FRONT_LEG, face.parapet))
    return {
        'key': face.key, 'roof_no': face.roof_no, 'name': face.name, 'kind': face.kind, 'facing': face.facing,
        'tilt_deg': round(tilt, 1), 'orient': best_o, 'table_rows': best_rows if face.kind == 'flat' else 0,
        'group_rows': best_rows,   # rows per group (sheet) / per table (flat)
        'modules': best, 'shaded_out': best_raw - len(best),
        'yield': kwh_per_kwp(tilt, face.down), 'usable_m2': round(area.area, 1),
        'mounting': ('flush' if face.kind == 'sheet' else 'elevated' if is_elev else 'tables'),
        'front_leg': (None if face.kind == 'sheet' else round(front_leg, 2)),   # front leg / low edge above the roof, m (Structure)
    }


def _elevated(site: Site, face: Face, area, ang, origin, inv, L: float, W: float, clear: float = ELEV_CLEAR) -> tuple[list, list]:
    """Elevated GI on a flat roof (owner, Keystone Skymont): portrait tables of 3 and 2 rows at 10°, one after
    another down the roof with only a walkway between them, low edge ELEV_CLEAR above the slab. Which mix of
    3- and 2-row tables (and where they start) is chosen to fit the most panels; ties go to 3-row tables first.
    Returns (modules, table sizes north to south). Rows are numbered table × 3 + k so each table is one group."""
    t = math.radians(TILT_FLAT)
    d1 = L * math.cos(t)
    across = W
    slab = face.height_at(face.poly.centroid.x, face.poly.centroid.y)
    # the frame may overhang the edge a little, but never into a taller roof / cabin next to it
    zone = area.buffer(ELEV_OVERHANG, join_style=2)
    for f in site.faces:
        if f is not face and f.poly.intersects(zone) and f.height_at(f.poly.centroid.x, f.poly.centroid.y) + f.parapet > slab + clear - 0.3:
            zone = zone.difference(f.poly)
    loc = affinity.rotate(zone, ang, origin=origin, use_radians=False)
    if loc.is_empty:
        return [], []
    P = prep(loc)
    minx, miny, maxx, maxy = loc.bounds
    STEP = 0.1
    memo = {}

    def band(y, n):
        dT = n * d1 + (n - 1) * GAP
        if y + dT > maxy + 1e-6:
            return None
        xs, x = [], minx
        while x + across <= maxx + 1e-6:
            if P.contains(box(x + 1e-3, y + 1e-3, x + across - 1e-3, y + dT - 1e-3)):
                xs.append(x)
                x += across + GAP
            else:
                x += 0.05
        return xs, dT

    def best(i):
        # most panels from y = miny + i·STEP downwards: skip a step, or put a 3- or 2-row table here
        if i in memo:
            return memo[i]
        y = miny + i * STEP
        res = (0, ())
        if y < maxy:
            res = best(i + 1)
            for n in ELEV_TABLES:
                b = band(y, n)
                if not b or not b[0]:
                    continue
                xs, dT = b
                nxt = best(i + max(1, math.ceil((dT + ELEV_WALK - 1e-6) / STEP)))
                cand = (len(xs) * n + nxt[0], ((y, n, tuple(xs)),) + nxt[1])
                if cand[0] > res[0]:
                    res = cand
        memo[i] = res
        return res

    import sys
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 10000))
    _, plan = best(0)
    # columns line up from table to table (one frame grid, purlins and legs in line — as in the owner's
    # drawing): put every table on one column grid, at the offset that keeps the most panels
    pitch = across + GAP
    best_o, best_cols = None, None
    for o in np.arange(0.0, pitch, 0.05):
        cols = []
        for y0, n, _ in plan:
            dT = n * d1 + (n - 1) * GAP
            j0 = math.ceil((minx - (minx + o)) / pitch)
            xs, x = [], minx + o + j0 * pitch
            while x + across <= maxx + 1e-6:
                if P.contains(box(x + 1e-3, y0 + 1e-3, x + across - 1e-3, y0 + dT - 1e-3)):
                    xs.append(x)
                x += pitch
            cols.append(tuple(xs))
        score = sum(len(xs) * n for xs, (_, n, _) in zip(cols, plan))
        if best_cols is None or score > best_o:
            best_o, best_cols = score, cols
    if best_cols is not None and best_o >= sum(len(xs) * n for _, n, xs in plan) - max((n for _, n, _ in plan), default=0):
        plan = tuple((y0, n, xs) for (y0, n, _), xs in zip(plan, best_cols))   # aligned, at most one column's panels lost
    mods, tables = [], []
    for ti, (y0, n, xs) in enumerate(plan):
        tables.append(n)
        dT = n * d1 + (n - 1) * GAP
        zf = lambda v, y0=y0, dT=dT: slab + clear + (y0 + dT - v) * math.tan(t)   # south (front) edge lowest
        for x0 in xs:
            for k in range(n):
                yy = y0 + k * (d1 + GAP)
                cs = [inv(x0, yy), inv(x0 + across, yy), inv(x0 + across, yy + d1), inv(x0, yy + d1)]
                mods.append(Module(face.key, *inv(x0 + across / 2, yy + d1 / 2), cs, [zf(yy), zf(yy), zf(yy + d1), zf(yy + d1)], 'P', 3 * ti + k, x0 + across / 2))
    return mods, tables
