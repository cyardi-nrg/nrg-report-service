# Design Lab worker v1.14.3 (2026-11-02) — read a BASE DESIGN picture: where every panel is.
#
# Owner (Nov 2026): "give an option of start from scratch or upload basic 3D design" — a SolarEdge Designer
# screenshot (solid blue panels split by thin light lines, on a satellite picture) or an AutoCAD drawing as a PDF /
# picture (panels drawn as blue outlined rectangles, like Sejal Parikh's). The layout and panel placement are already
# done there; the Design Lab reads them instead of placing panels itself.
#
# read_panels(rgb) → {'style', 'tables': [{panels: [...], rows, cols, orient, angle}], 'panel_px': (long, short)}
# Each panel: centre (x, y) and its 4 corners in picture pixels. Scale (px per m) comes later from the panel size.
import math

import numpy as np
from scipy import ndimage

MIN_PANEL_PX = 40          # a panel smaller than this many pixels is noise / text
ASPECT = 2.1               # panel long / short side (2.382 × 1.134 m for 600–630 Wp)


def _blue(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    return (b > r + 45) & (b > g + 32) & (g < 125)                 # panel navy / CAD blue — not sky-blue icons, not a blue-tinted satellite picture (v1.14.3)


def _axes(ys, xs):
    """Angle (rad) of the blob's minimum-area rectangle edge nearest the picture's x axis."""
    from scipy.spatial import ConvexHull
    pts = np.stack([xs, ys], 1).astype(float)
    hull = pts[ConvexHull(pts).vertices]
    best = (float('inf'), 0.0)
    for i in range(len(hull)):
        dx, dy = hull[(i + 1) % len(hull)] - hull[i]
        a = math.atan2(dy, dx)
        c, s = math.cos(-a), math.sin(-a)
        u = hull[:, 0] * c - hull[:, 1] * s; v = hull[:, 0] * s + hull[:, 1] * c
        area = (u.max() - u.min()) * (v.max() - v.min())
        if area < best[0]:
            best = (area, a)
    ang = best[1]
    while ang > math.pi / 4:
        ang -= math.pi / 2
    while ang < -math.pi / 4:
        ang += math.pi / 2
    return ang


def _runs(profile, thr):
    """Segments where profile >= thr: [(start, end)] (end exclusive)."""
    on = profile >= thr
    out, s = [], None
    for i, v in enumerate(on):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i)); s = None
    if s is not None:
        out.append((s, len(on)))
    return out


def _split_even(segs, step_hint):
    """A segment much longer than the usual one is two or more panels whose line was too faint — split it evenly."""
    if not segs:
        return segs
    lens = sorted(e - s for s, e in segs)
    ref = step_hint or lens[len(lens) // 2]
    out = []
    for s, e in segs:
        k = max(1, round((e - s) / ref)) if ref else 1
        for i in range(k):
            out.append((s + (e - s) * i / k, s + (e - s) * (i + 1) / k))
    return out


def _filled_tables(blue):
    """SolarEdge style: each solid blue blob is a table; the thin light lines inside split it into panels."""
    lab, n = ndimage.label(ndimage.binary_closing(blue, iterations=1))
    tables = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        if len(xs) < MIN_PANEL_PX * 2:
            continue
        ang = _axes(ys, xs)
        c, s = math.cos(-ang), math.sin(-ang)
        cx, cy = xs.mean(), ys.mean()
        u = (xs - cx) * c - (ys - cy) * s                  # table frame: u along the rows, v across
        v = (xs - cx) * s + (ys - cy) * c
        u0, v0 = u.min(), v.min()
        W, H = int(math.ceil(u.max() - u0)) + 1, int(math.ceil(v.max() - v0)) + 1
        grid_all = np.zeros((H, W), bool)
        grid_all[(v - v0).astype(int), (u - u0).astype(int)] = True       # the filled table
        # blue (not line) pixels in the table frame: sample the original mask
        uu, vv = np.meshgrid(np.arange(W) + u0, np.arange(H) + v0)
        X = cx + uu * math.cos(ang) - vv * math.sin(ang)
        Y = cy + uu * math.sin(ang) + vv * math.cos(ang)
        Xi, Yi = np.clip(X.round().astype(int), 0, blue.shape[1] - 1), np.clip(Y.round().astype(int), 0, blue.shape[0] - 1)
        inside = ndimage.binary_fill_holes(ndimage.binary_closing(grid_all, iterations=2))
        bl = blue[Yi, Xi] & inside
        colp = bl.sum(0) / np.maximum(1, inside.sum(0))
        rowp = bl.sum(1) / np.maximum(1, inside.sum(1))
        cu = np.nonzero(inside.any(0))[0]; cv = np.nonzero(inside.any(1))[0]
        if len(cu) < 4 or len(cv) < 4:
            continue
        tables.append(dict(ang=ang, cx=cx, cy=cy, u0=u0, v0=v0, colp=colp[cu[0]:cu[-1] + 1], rowp=rowp[cv[0]:cv[-1] + 1],
                           ua=cu[0], ub=cu[-1] + 1, va=cv[0], vb=cv[-1] + 1))
    if not tables:
        return []
    pu, _ = _pitch([t['colp'] for t in tables])
    rsc = _scores([t['rowp'] for t in tables])
    def near(target):                                    # best row score within ±15 % of a target pitch
        ks = [k for k in rsc if 0.85 * target <= k <= 1.15 * target]
        return max(ks, key=lambda k: rsc[k]) if ks else None
    pv = 0.0
    if pu:
        kp, kl = near(pu * ASPECT), near(pu / ASPECT)
        cand = [k for k in (kp, kl) if k]
        if cand:
            k = max(cand, key=lambda k: rsc[k])
            pv = _peak(rsc, k) if rsc[k] > 0.03 else (pu * ASPECT)
        else:
            pv = pu * ASPECT
    # v1.14.3: the pitch read off thin lines is ± half a pixel on a small screenshot — fine-tune it (± 8 %) so every
    # table's length is closest to a whole number of panels (Express Cranes: 161 px tables read as 12, not 13, panels)
    def tune(p, key_a, key_b):
        if not p:
            return p
        Ls = [t[key_b] - t[key_a] for t in tables]
        cands = np.linspace(0.92 * p, 1.08 * p, 161)
        cost = [sum((L / c - round(L / c)) ** 2 for L in Ls) + 0.5 * ((c - p) / p) ** 2 for c in cands]
        return float(cands[int(np.argmin(cost))])
    pu = tune(pu, 'ua', 'ub')          # along the rows only: rows are foreshortened differently on each roof's slope
    out = []
    for t in tables:
        L, Hh = t['ub'] - t['ua'], t['vb'] - t['va']
        nc = max(1, round(L / pu)) if pu else 1
        nr = max(1, round(Hh / pv)) if pv else 1
        cols = [(t['ua'] + L * k / nc, t['ua'] + L * (k + 1) / nc) for k in range(nc)]
        rows = [(t['va'] + Hh * k / nr, t['va'] + Hh * (k + 1) / nr) for k in range(nr)]
        out.append(_table_from_grid(t, cols, rows))
    return out


def _scores(profiles, lo=4, hi=90):
    acs = []
    for pr in profiles:
        x = np.asarray(pr, float)
        if len(x) >= max(2 * lo, 12):          # a tiny blob (noise) has no pattern to read
            acs.append(x - np.convolve(x, np.ones(9) / 9, mode='same'))      # keep only the thin dips
    sc = {}
    for lag in range(lo, hi):
        num = sum(float((x[:-lag] * x[lag:]).sum()) for x in acs if len(x) > lag + 2)
        den = sum(float((x * x).sum()) for x in acs)
        sc[lag] = num / den if den else -1.0
    return sc


def _peak(sc, lag):
    """Sub-pixel peak position around an integer lag (parabola through 3 points)."""
    a, b, c = sc.get(lag - 1, 0), sc[lag], sc.get(lag + 1, 0)
    d = a - 2 * b + c
    return lag + (0.5 * (a - c) / d if d < 0 else 0.0)


def _pitch(profiles, lo=4, hi=90):
    """The panel pitch (px): the FIRST strong repeat of the dips (later peaks are its multiples)."""
    sc = _scores(profiles, lo, hi)
    if not sc:
        return 0.0, {}
    top = max(sc.values())
    if top <= 0.03:
        return 0.0, sc
    for lag in range(lo + 1, hi - 1):
        if sc[lag] >= 0.8 * top and sc[lag] >= sc[lag - 1] and sc[lag] >= sc[lag + 1]:
            return _peak(sc, lag), sc
    return 0.0, sc


def _table_from_grid(t, cols, rows):
    ang, cx, cy, u0, v0 = t['ang'], t['cx'], t['cy'], t['u0'], t['v0']
    to_xy = lambda uu, vv: (cx + (uu + u0) * math.cos(ang) - (vv + v0) * math.sin(ang), cy + (uu + u0) * math.sin(ang) + (vv + v0) * math.cos(ang))
    panels = []
    for ri, (va, vb) in enumerate(rows):
        for ci, (ua, ub) in enumerate(cols):
            cs = [to_xy(ua, va), to_xy(ub, va), to_xy(ub, vb), to_xy(ua, vb)]
            panels.append({'row': ri, 'col': ci, 'x': sum(p[0] for p in cs) / 4, 'y': sum(p[1] for p in cs) / 4, 'corners': cs,
                           'w': ub - ua, 'h': vb - va})
    w = np.median([p['w'] for p in panels]); h = np.median([p['h'] for p in panels])
    return {'panels': panels, 'rows': len(rows), 'cols': len(cols), 'angle_deg': math.degrees(ang),
            'orient': 'P' if h > w else 'L', 'panel_px': (max(w, h), min(w, h))}


def _outlined_tables(blue):
    """AutoCAD style: panels are blue outlined rectangles — each panel is a hole inside the blue lines."""
    lines = ndimage.binary_dilation(blue, iterations=1)
    filled = ndimage.binary_fill_holes(lines)
    holes = filled & ~lines
    lab, n = ndimage.label(holes)
    if not n:
        return []
    objs = ndimage.find_objects(lab)
    cells = []
    for i, sl in enumerate(objs):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = int((lab[sl] == i + 1).sum())
        if area < MIN_PANEL_PX or area < 0.75 * w * h:            # not a clean rectangle (text, symbols)
            continue
        cells.append(dict(i=i + 1, x=(sl[1].start + sl[1].stop) / 2, y=(sl[0].start + sl[0].stop) / 2, w=w, h=h, area=area))
    if not cells:
        return []
    # panels are the most common rectangle size (± 25 %), long side about 1.6–2.4 × the short side
    areas = np.array([c['area'] for c in cells])
    med = np.median(areas[(areas > np.percentile(areas, 25))])
    cells = [c for c in cells if 0.7 * med <= c['area'] <= 1.35 * med and 1.4 <= max(c['w'], c['h']) / max(1, min(c['w'], c['h'])) <= 2.6]
    cells = _fill_strips(cells, blue)
    # tables: cells that touch (share an outline) form one table
    occ = np.zeros(blue.shape, np.int32)
    for k, c in enumerate(cells):
        y0, y1 = int(c['y'] - c['h'] / 2 - 2), int(c['y'] + c['h'] / 2 + 3)
        x0, x1 = int(c['x'] - c['w'] / 2 - 2), int(c['x'] + c['w'] / 2 + 3)
        occ[max(0, y0):y1, max(0, x0):x1] = 1
    tl, tn = ndimage.label(occ)
    out = []
    for k in range(1, tn + 1):
        mine = [c for c in cells if tl[min(int(c['y']), tl.shape[0] - 1), min(int(c['x']), tl.shape[1] - 1)] == k]
        if not mine:
            continue
        w = float(np.median([m['w'] for m in mine])); h = float(np.median([m['h'] for m in mine]))
        cols = len(_clusters([m['x'] for m in mine], w * 0.5)); rows = len(_clusters([m['y'] for m in mine], h * 0.5))
        panels = [{'x': c['x'], 'y': c['y'], 'w': c['w'], 'h': c['h'],
                   'corners': [(c['x'] - c['w'] / 2, c['y'] - c['h'] / 2), (c['x'] + c['w'] / 2, c['y'] - c['h'] / 2),
                               (c['x'] + c['w'] / 2, c['y'] + c['h'] / 2), (c['x'] - c['w'] / 2, c['y'] + c['h'] / 2)]} for c in mine]
        out.append({'panels': panels, 'rows': rows, 'cols': cols, 'angle_deg': 0.0, 'orient': 'P' if h > w else 'L', 'panel_px': (max(w, h), min(w, h))})
    return out


def _clusters(vals, tol):
    vals = sorted(vals); out = []
    for v in vals:
        if out and v - out[-1][-1] <= tol:
            out[-1].append(v)
        else:
            out.append([v])
    return out


def _fill_strips(cells, blue):
    """Cells hidden under text: walk each line of cells one pitch at a time and add a cell wherever the strip's two
    side borders carry on and a cross line closes it (CAD panels are drawn as a ladder of equal boxes)."""
    if not cells:
        return cells
    H, W = blue.shape
    lines = ndimage.binary_dilation(blue, iterations=1)
    w = float(np.median([c['w'] for c in cells])); h = float(np.median([c['h'] for c in cells]))
    have = list(cells)

    def spacing(key, other, size):                       # neighbour-to-neighbour pitch along one axis
        ds = []
        for c in cells:
            d = [abs(o[key] - c[key]) for o in cells if o is not c and abs(o[other] - c[other]) < size * 0.3 and abs(o[key] - c[key]) > 0]
            if d:
                ds.append(min(d))
        return float(np.median(ds)) if ds else 0.0
    px = spacing('x', 'y', h) or (w + 3); py = spacing('y', 'x', w) or (h + 3)

    def taken(x, y):
        return any(abs(c['x'] - x) < w * 0.5 and abs(c['y'] - y) < h * 0.5 for c in have)

    def frac(ys, xs):
        ys = np.clip(np.asarray(ys, int), 0, H - 1); xs = np.clip(np.asarray(xs, int), 0, W - 1)
        return float(lines[ys, xs].mean()) if len(ys) else 0.0

    def closed(x, y):
        x0, x1, y0, y1 = x - w / 2, x + w / 2, y - h / 2, y + h / 2
        if x0 < 1 or y0 < 1 or x1 > W - 2 or y1 > H - 2:
            return False
        yy = np.arange(int(y0) + 2, int(y1) - 1); xx = np.arange(int(x0) + 2, int(x1) - 1)
        sides = min(frac(yy, np.full(len(yy), x0 - 0.5)), frac(yy, np.full(len(yy), x1 + 0.5)))
        ends = min(max(frac(np.full(len(xx), y0 + d), xx) for d in (-2, -1, 0, 1)), max(frac(np.full(len(xx), y1 + d), xx) for d in (-2, -1, 0, 1)))
        return sides > 0.8 and ends > 0.7

    for axis in ('y', 'x'):
        changed = True
        while changed:
            changed = False
            for c in list(have):
                for sgn in (-1, 1):
                    nx = c['x'] + (sgn * px if axis == 'x' else 0)
                    ny = c['y'] + (sgn * py if axis == 'y' else 0)
                    # the pitch between neighbours: cell size + the shared line
                    if not taken(nx, ny) and closed(nx, ny):
                        have.append({'i': -1, 'x': nx, 'y': ny, 'w': w, 'h': h, 'area': w * h}); changed = True
    return have


def read_panels(rgb: np.ndarray) -> dict:
    blue = _blue(rgb)
    filled = ndimage.binary_fill_holes(ndimage.binary_closing(blue, iterations=2))
    solid = blue.sum() / max(1, filled.sum())               # SolarEdge ≈ 0.8, outlines ≈ 0.1–0.3
    style = 'filled' if solid > 0.55 else 'outlined'
    tables = _filled_tables(blue) if style == 'filled' else _outlined_tables(blue)
    tables = [t for t in tables if t['panels']]
    tables.sort(key=lambda t: (np.mean([p['y'] for p in t['panels']]), np.mean([p['x'] for p in t['panels']])))
    long_px = float(np.median([t['panel_px'][0] for t in tables])) if tables else 0.0
    return {'style': style, 'tables': tables, 'panel_long_px': long_px, 'panels': sum(len(t['panels']) for t in tables)}
