# Design Lab worker v1.11.0 (2026-11-01) — the drawn roof model in metres.
#
# v1.11.0 (owner): a roof may stand on another roof — its height is then given ABOVE that roof (onRoofId +
#   heightAboveM; e.g. the staircase cabin 3 m above Roof 1); each roof may carry its own structure height
#   (structureM: the panels' low edge above that roof — e.g. Roof 1 at 2 m elevated, the cabin at 0.5 m);
#   the inverter's and the meter's floor give inverter_z / meter_z for the cable drops (nrg/inputs.placement).
#
# Reads the RoofModel the owner draws in the Design Lab (lib/design-lab.ts:
# points in % of the base picture, pxPerM, imageW / imageH) and turns it
# into a site frame in metres: x → east, y → south (north up). If north
# is not up on the picture (a hand sketch, a rotated AutoCAD plan), the
# north arrow from Site & marks turns everything so it is.
#
# Each roof becomes one or two FACES (the planes panels go on):
#   flat RCC      one face, panels on tilted tables facing south
#   sheet, mono   one face sloping down to N / S / E / W
#   sheet, gable  two faces either side of a ridge in the middle
# and a height map (0.25 m cells) of everything that can cast shade:
# roofs, parapets, cabins, tanks, lift rooms, ventilators, trees.
import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity

CELL = 0.25          # height map resolution, m
DIRS = {'S': (0.0, 1.0), 'N': (0.0, -1.0), 'E': (1.0, 0.0), 'W': (-1.0, 0.0)}
OBSTACLE_CLEAR = {'turbo_vent': 0.3, 'skylight': 0.3, 'cabin': 0.6, 'lift_room': 0.6, 'tank': 0.6, 'existing_solar': 0.5, 'tree': 1.0, 'other': 0.3}


@dataclass
class Face:
    key: str               # "3S" — roof number + facing
    roof_no: int
    name: str
    kind: str              # 'flat' (tables) | 'sheet' (flush)
    poly: Polygon          # plan outline, m
    down: tuple            # unit vector the surface slopes down to (sheet) / tables face (flat)
    pitch: float           # rise per metre of run (sheet); 0 for flat
    height_at: callable    # (x, y) -> surface height, m
    setback: float
    facing: str            # N / S / E / W (nearest)
    parapet: float = 0.0
    structure: float | None = None   # owner's structure height above this roof (panels' low edge), m — None = by the rules


@dataclass
class Site:
    ppm: float
    W: int
    H: int
    rot_deg: float                          # picture turned by this much so north is up
    faces: list = field(default_factory=list)
    obstacles: list = field(default_factory=list)   # (kind, Polygon, clearance)
    roofs: list = field(default_factory=list)       # raw roof dicts with 'poly'
    inverter: tuple | None = None
    inverter_z: float | None = None   # height of the inverter (same datum as the roof heights), m — from Site questions
    meter_z: float | None = None      # height of the meter (normally the ground floor), m
    grid: np.ndarray | None = None
    gx0: float = 0.0
    gy0: float = 0.0

    # picture px <-> site metres ------------------------------------------------
    def to_m(self, pt: dict) -> tuple:
        px, py = pt['x'] / 100 * self.W, pt['y'] / 100 * self.H
        cx, cy = self.W / 2, self.H / 2
        a = math.radians(self.rot_deg)
        rx = cx + (px - cx) * math.cos(a) - (py - cy) * math.sin(a)
        ry = cy + (px - cx) * math.sin(a) + (py - cy) * math.cos(a)
        return rx / self.ppm, ry / self.ppm

    def to_px(self, x: float, y: float) -> tuple:
        rx, ry = x * self.ppm, y * self.ppm
        cx, cy = self.W / 2, self.H / 2
        a = -math.radians(self.rot_deg)
        return cx + (rx - cx) * math.cos(a) - (ry - cy) * math.sin(a), cy + (rx - cx) * math.sin(a) + (ry - cy) * math.cos(a)

    def h(self, xs, ys):
        """Height map lookup (vectorised); outside the map = ground (0)."""
        ix = np.floor((np.asarray(xs) - self.gx0) / CELL).astype(int)
        iy = np.floor((np.asarray(ys) - self.gy0) / CELL).astype(int)
        ok = (ix >= 0) & (iy >= 0) & (ix < self.grid.shape[1]) & (iy < self.grid.shape[0])
        out = np.zeros(np.shape(ix))
        out[ok] = self.grid[iy[ok], ix[ok]]
        return out


def _nearest_dir(v) -> str:
    return max(DIRS, key=lambda k: DIRS[k][0] * v[0] + DIRS[k][1] * v[1])


def build(model: dict, marks: dict | None) -> Site:
    marks = marks or {}
    rot = 0.0
    same_pic = not marks.get('screenshotDocumentId') or marks.get('screenshotDocumentId') == model.get('baseDocumentId')
    if same_pic and marks.get('northUp') is False and marks.get('northTail') and marks.get('north'):
        t, n = marks['northTail'], marks['north']
        vx, vy = (n['x'] - t['x']) / 100 * model['imageW'], (n['y'] - t['y']) / 100 * model['imageH']
        rot = -math.degrees(math.atan2(vx, -vy))       # turn the picture so the arrow points up
    s = Site(ppm=float(model['pxPerM']), W=int(model['imageW']), H=int(model['imageH']), rot_deg=rot)
    if same_pic and marks.get('inverter'):
        s.inverter = s.to_m(marks['inverter'])

    for o in model.get('obstacles', []):
        pts = [s.to_m(p) for p in o['points']]
        if len(pts) >= 3:
            s.obstacles.append((o['kind'], Polygon(pts).buffer(0), float(o.get('heightM') or 0), OBSTACLE_CLEAR.get(o['kind'], 0.3)))

    # a roof standing on another roof: height = that roof's height + the height above it (resolved in order)
    by_id = {r.get('id'): r for r in model.get('roofs', [])}

    def abs_h(r, depth=0):
        base = by_id.get(r.get('onRoofId')) if r.get('onRoofId') else None
        if base is not None and base is not r and depth < 8 and r.get('heightAboveM') is not None:
            return abs_h(base, depth + 1) + float(r.get('heightAboveM') or 0)
        return float(r.get('heightM') or 0)

    for r in model.get('roofs', []):
        r = {**r, 'heightM': abs_h(r)}
        pts = [s.to_m(p) for p in r['points']]
        if len(pts) < 3:
            continue
        poly = Polygon(pts).buffer(0)
        r = {**r, 'poly': poly}
        s.roofs.append(r)
        hgt, pitch, setback = float(r.get('heightM') or 0), float(r.get('pitch') or 0.1), float(r.get('setbackM') if r.get('setbackM') is not None else 0.5)
        name = r.get('name') or f"Roof {r['no']}"
        if r['kind'] in ('flat_rcc', 'other'):
            st = r.get('structureM')
            f = Face(f"{r['no']}", r['no'], name, 'flat', poly, DIRS['S'], 0.0, (lambda x, y, hh=hgt: hh), setback, 'S', float(r.get('parapetM') or 0),
                     float(st) if st not in (None, '') else None)
            r['faces'] = [f]
        elif r['kind'] == 'sheet_mono':
            d = DIRS.get(r.get('downhill') or 'S')
            lo = max(px * d[0] + py * d[1] for px, py in poly.exterior.coords)       # projection of the eave (lowest edge)
            f = Face(f"{r['no']}{r.get('downhill') or 'S'}", r['no'], name, 'sheet', poly, d, pitch,
                     (lambda x, y, d=d, lo=lo, hh=hgt, p=pitch: hh + p * (lo - (x * d[0] + y * d[1]))), setback, r.get('downhill') or 'S')
            r['faces'] = [f]
        else:  # gable: ridge through the middle
            minx, miny, maxx, maxy = poly.bounds
            ew = (r.get('ridge') or 'EW') == 'EW'
            mid = (miny + maxy) / 2 if ew else (minx + maxx) / 2
            half = (maxy - miny) / 2 if ew else (maxx - minx) / 2
            sides = (('N', box(minx - 1, miny - 1, maxx + 1, mid)), ('S', box(minx - 1, mid, maxx + 1, maxy + 1))) if ew else \
                    (('W', box(minx - 1, miny - 1, mid, maxy + 1)), ('E', box(mid, miny - 1, maxx + 1, maxy + 1)))
            r['faces'] = []
            for side, half_box in sides:
                part = poly.intersection(half_box)
                if part.is_empty or part.area < 1:
                    continue
                if part.geom_type != 'Polygon':
                    part = max(part.geoms, key=lambda g: g.area)
                fn = (lambda x, y, hh=hgt, p=pitch, mid=mid, half=half: hh + p * (half - abs(y - mid))) if ew else \
                     (lambda x, y, hh=hgt, p=pitch, mid=mid, half=half: hh + p * (half - abs(x - mid)))
                r['faces'].append(Face(f"{r['no']}{side}", r['no'], f'{name} · {side} slope', 'sheet', part, DIRS[side], pitch, fn, setback, side))
        if r.get('use', True):
            s.faces += r['faces']

    _height_map(s)
    return s


def _height_map(s: Site) -> None:
    geoms = [r['poly'] for r in s.roofs] + [o[1] for o in s.obstacles]
    if not geoms:
        s.grid = np.zeros((1, 1))
        return
    minx, miny, maxx, maxy = unary_union(geoms).bounds
    s.gx0, s.gy0 = minx - 8, miny - 8
    nx, ny = int((maxx - minx + 16) / CELL) + 1, int((maxy - miny + 16) / CELL) + 1
    grid = np.zeros((ny, nx))
    xs = s.gx0 + (np.arange(nx) + 0.5) * CELL
    ys = s.gy0 + (np.arange(ny) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys)

    def mask(poly: Polygon) -> np.ndarray:
        img = Image.new('1', (nx, ny), 0)
        for g in (poly.geoms if hasattr(poly, 'geoms') else [poly]):
            ImageDraw.Draw(img).polygon([((x - s.gx0) / CELL, (y - s.gy0) / CELL) for x, y in g.exterior.coords], fill=1)
        return np.array(img, dtype=bool)

    for r in s.roofs:
        for f in r['faces']:
            m = mask(f.poly)
            hv = np.vectorize(f.height_at)(X[m], Y[m]) if f.kind == 'sheet' else np.full(m.sum(), f.height_at(0, 0))
            grid[m] = np.maximum(grid[m], hv)
            if f.parapet > 0:  # parapet wall: a 0.25 m ring at the edge of a flat roof
                ring = mask(f.poly) & ~mask(f.poly.buffer(-0.25))
                grid[ring] = np.maximum(grid[ring], f.height_at(0, 0) + f.parapet)
    roof_only = grid.copy()
    for kind, poly, hgt, _ in s.obstacles:
        m = mask(poly)
        if m.any():
            # on top of the roof surface cell by cell (a skylight on a sloping sheet stays on the slope;
            # a cabin's top follows the roof under it); a tree stands on the ground
            base = 0.0 if kind == 'tree' else roof_only[m]
            grid[m] = np.maximum(grid[m], base + hgt)
    s.grid = grid
