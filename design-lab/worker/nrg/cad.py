# Design Lab worker v1.1.0 (2026-10-31) — AutoCAD (DWG / DXF) → a plan picture
# with a known scale + suggested roof outlines.
#
# Owner's choice for the roof model: "drawing plus AutoCAD". The worker
# turns the client's / architect's drawing into a picture the Design Lab
# can use as the base for drawing roofs (exactly like a Google Maps
# screenshot or a hand sketch), but with the scale already known — no
# scale bar to click — and outlines every closed shape big enough to be a
# roof, for the owner to accept or adjust.
#
# DWG is first converted to DXF: ODA File Converter (free, opendesign.com)
# if installed, else LibreDWG's dwg2dxf (brew install libredwg). DXF is
# read with ezdxf. The drawing's units come from $INSUNITS; when the
# drawing does not say, they are guessed from its size and the guess is
# reported (never silently assumed).
import math
import os
import shutil
import subprocess

import ezdxf
from ezdxf import recover
from PIL import Image, ImageDraw

UNIT_M = {1: 0.0254, 2: 0.3048, 4: 0.001, 5: 0.01, 6: 1.0, 14: 0.1}  # inch, foot, mm, cm, m, dm
UNIT_NAME = {1: 'inches', 2: 'feet', 4: 'mm', 5: 'cm', 6: 'm', 14: 'dm'}
MAX_PX = 2400


def to_dxf(path: str, workdir: str) -> str:
    if path.lower().endswith('.dxf'):
        return path
    oda = shutil.which('ODAFileConverter') or next((p for p in ['/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter'] if os.path.exists(p)), None)
    out = os.path.join(workdir, 'dxf')
    os.makedirs(out, exist_ok=True)
    if oda:
        src = os.path.join(workdir, 'dwg')
        os.makedirs(src, exist_ok=True)
        shutil.copy(path, src)
        subprocess.run([oda, src, out, 'ACAD2018', 'DXF', '0', '1', '*.DWG'], check=True, timeout=600, capture_output=True)
    elif shutil.which('dwg2dxf'):
        subprocess.run(['dwg2dxf', '-y', '-o', os.path.join(out, 'drawing.dxf'), path], check=True, timeout=600, capture_output=True)
    else:
        raise RuntimeError('This is a DWG file and no converter is installed on the Mac. Install the free “ODA File Converter” '
                           '(opendesign.com/guestfiles/oda_file_converter) or run:  brew install libredwg   — then press Run again. '
                           '(Or ask the architect for a DXF.)')
    found = [os.path.join(out, f) for f in os.listdir(out) if f.lower().endswith('.dxf')]
    if not found:
        raise RuntimeError('The DWG could not be converted (the converter produced no DXF).')
    return found[0]


def _flatten(entity, depth=0):
    """Model-space entities, with block references (INSERT) opened up to 3 levels deep."""
    if entity.dxftype() == 'INSERT' and depth < 3:
        try:
            for e in entity.virtual_entities():
                yield from _flatten(e, depth + 1)
        except Exception:
            return
    else:
        yield entity


def _shapes(msp):
    """(segments, closed polygons, layer per polygon) in drawing units."""
    segs, polys = [], []
    for e in (x for ent in msp for x in _flatten(ent)):
        t = e.dxftype()
        try:
            if t == 'LINE':
                segs.append([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
            elif t in ('LWPOLYLINE', 'POLYLINE'):
                pts = [(p[0], p[1]) for p in (e.get_points('xy') if t == 'LWPOLYLINE' else [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices])]
                if len(pts) < 2:
                    continue
                closed = e.closed or (len(pts) > 3 and math.dist(pts[0], pts[-1]) < 1e-6)
                segs.append(pts + ([pts[0]] if closed else []))
                if closed and len(pts) >= 3:
                    polys.append((pts if pts[0] != pts[-1] else pts[:-1], e.dxf.layer))
            elif t in ('ARC', 'CIRCLE', 'ELLIPSE', 'SPLINE'):
                pts = [(v.x, v.y) for v in e.flattening(0.01 if t != 'SPLINE' else 0.05)] if t != 'CIRCLE' else \
                      [(e.dxf.center.x + e.dxf.radius * math.cos(a / 24 * 2 * math.pi), e.dxf.center.y + e.dxf.radius * math.sin(a / 24 * 2 * math.pi)) for a in range(25)]
                if len(pts) >= 2:
                    segs.append(pts)
        except Exception:
            continue
    return segs, polys


def _area(pts):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def read(path: str, workdir: str, png_path: str) -> dict:
    dxf = to_dxf(path, workdir)
    try:
        doc = ezdxf.readfile(dxf)
    except Exception:
        doc, _ = recover.readfile(dxf)  # damaged / older files
    segs, polys = _shapes(doc.modelspace())
    if not segs:
        raise RuntimeError('No lines were found in the drawing’s model space (is the plan only on a layout / paper sheet?).')

    # extents: ignore the outer 1 % of points either side, so a stray point far away doesn't shrink the plan
    xs = sorted(p[0] for s in segs for p in s)
    ys = sorted(p[1] for s in segs for p in s)
    k = len(xs) // 100
    x0, x1, y0, y1 = xs[k], xs[-1 - k], ys[k], ys[-1 - k]
    span = max(x1 - x0, y1 - y0) or 1.0

    code = int(doc.header.get('$INSUNITS', 0) or 0)
    if code in UNIT_M:
        unit, units_note = UNIT_M[code], f'drawing units: {UNIT_NAME[code]}'
    else:  # not stated — guess from the size of a building site (20 m – 1 km across)
        unit = 0.001 if span > 2000 else (0.01 if span > 1000 else 1.0)
        units_note = f'drawing does not state its units — taken as {"mm" if unit == 0.001 else "cm" if unit == 0.01 else "m"} from its size; check a known length'

    x0, x1, y0, y1 = float(x0), float(x1), float(y0), float(y1)   # plain numbers (ezdxf gives numpy ones) so the result can be stored as JSON
    w_m, h_m = (x1 - x0) * unit, (y1 - y0) * unit
    pad = 0.04 * max(w_m, h_m)
    px_per_m = MAX_PX / (max(w_m, h_m) + 2 * pad)
    W, H = int((w_m + 2 * pad) * px_per_m), int((h_m + 2 * pad) * px_per_m)

    def P(x, y):  # drawing units → picture pixels (north / +y up)
        return ((x - x0) * unit + pad) * px_per_m, H - ((y - y0) * unit + pad) * px_per_m

    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    for s in segs:
        d.line([P(x, y) for x, y in s], fill=(40, 40, 40), width=2)

    # roof candidates: closed shapes from 15 m² to 90 % of the whole plan, biggest first, duplicates dropped
    total = w_m * h_m
    cands, seen = [], []
    skip_layer = ('TITLE', 'BORDER', 'FRAME', 'SHEET', 'VIEWPORT', 'VPORT', 'DEFPOINTS', 'TEXT', 'DIM', 'HATCH', 'GRID')
    for pts, layer in sorted(polys, key=lambda pl: -_area(pl[0])):
        if any(k in (layer or '').upper() for k in skip_layer):
            continue  # title blocks, sheet frames, dimensions — never a roof
        a = float(_area(pts) * unit * unit)
        if not (15 <= a <= 0.9 * total):
            continue
        cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        if any(abs(a - a2) / a < 0.02 and math.dist((cx, cy), c2) * unit < 0.5 for a2, c2 in seen):
            continue
        seen.append((a, (cx, cy)))
        pix = [P(x, y) for x, y in pts]
        cands.append({'points': [{'x': round(float(px) / W * 100, 3), 'y': round(float(py) / H * 100, 3)} for px, py in pix],
                      'areaM2': round(a, 1), 'layer': layer})
        if len(cands) >= 40:
            break
    for c in cands:
        d.polygon([(p['x'] / 100 * W, p['y'] / 100 * H) for p in c['points']], outline=(14, 116, 144), width=3)

    # scale bar (10 m or 50 m) so the picture explains itself
    bar = 10 if w_m < 120 else 50
    bx, by = 0.04 * W, H - 0.03 * H
    d.line([(bx, by), (bx + bar * px_per_m, by)], fill=(14, 116, 144), width=6)
    d.text((bx, by - 22), f'{bar} m', fill=(14, 116, 144))
    img.save(png_path, optimize=True)

    return {'px_per_m': round(px_per_m, 4), 'image_w': W, 'image_h': H, 'north_up': True, 'units_note': units_note,
            'size_m': [round(w_m, 1), round(h_m, 1)], 'candidates': cands, 'entities': len(segs)}
