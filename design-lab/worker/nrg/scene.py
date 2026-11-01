# Design Lab worker v1.11.0 (2026-11-01) — the 3D scene for viewer/viewer.template.html,
# built from the drawn roofs (nrg/site.py) and the chosen panel option.
# v1.11.0 (owner: "first show me the 3d views of the roof so i can approve that before panel placement"):
#   option=None builds the roofs alone (Roof design stage).
import base64
import io
import json
import os

from PIL import Image
from shapely.geometry import Point

VIEWER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'viewer')


def _roof_z(site, x, y) -> float:
    """Height of the roof surface (not of things on it) at a point; 0 off the roofs."""
    best = 0.0
    for r in site.roofs:
        for f in r.get('faces', []):
            if f.poly.buffer(0.05).contains(Point(x, y)):
                best = max(best, f.height_at(x, y))
    return best


def build_scene(site, option: dict | None, mods: list, spec: dict, customer: str, base_path: str | None, note: str) -> dict:
    roofs_only = option is None
    if roofs_only:
        option = {'name': 'Roofs as drawn', 'kwp': 0, 'modules': 0, 'arrays': [], 'annualKwh': 0}
    used = {f.key for f in site.faces}
    faces = []
    for r in site.roofs:
        for f in r.get('faces', []):
            pts = list(f.poly.exterior.coords)[:-1]
            faces.append({'key': f.key, 'kind': f.kind, 'used': f.key in used, 'parapet': f.parapet,
                          'poly': [[round(x, 3), round(y, 3), round(f.height_at(x, y), 3)] for x, y in pts]})
    obstacles = []
    for kind, poly, hgt, _ in site.obstacles:
        pts = list(poly.exterior.coords)[:-1]
        c = poly.centroid
        base = 0.0 if kind == 'tree' else _roof_z(site, c.x, c.y)
        obstacles.append({'kind': kind, 'poly': [[round(x, 3), round(y, 3)] for x, y in pts], 'base': round(base, 3), 'top': round(base + hgt, 3),
                          'zs': [round(_roof_z(site, x, y), 3) for x, y in pts], 'area': round(poly.area, 2)})
    face_kind = {f.key: f for f in site.faces}
    modules = []
    for m in mods:
        f = face_kind.get(m.face)
        modules.append({'c': [[round(x, 3), round(y, 3), round(z, 3)] for (x, y), z in zip(m.corners, m.z)], 'o': m.orient,
                        'base': round(f.height_at(0, 0), 3) if f is not None and f.kind == 'flat' else None})

    xs = [p[0] for F in faces for p in F['poly']] + [p[0] for o in obstacles for p in o['poly']]
    ys = [p[1] for F in faces for p in F['poly']] + [p[1] for o in obstacles for p in o['poly']]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    extent = max(15.0, ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5 / 2)
    focus = ([sum(m.x for m in mods) / len(mods), sum(m.y for m in mods) / len(mods), sum(sum(m.z) / 4 for m in mods) / len(mods)]
             if mods else [cx, cy, 0.0])
    roof_mid = sum(p[2] for F in faces for p in F['poly']) / max(1, sum(len(F['poly']) for F in faces)) / 2   # half the typical roof height

    ground = None
    if base_path and os.path.exists(base_path):
        img = Image.open(base_path).convert('RGB')
        img.thumbnail((2048, 2048))
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=82)
        corners = [site.to_m({'x': x, 'y': y}) for x, y in ((0, 0), (100, 0), (100, 100), (0, 100))]
        ground = {'img': 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode(), 'corners': [[round(a, 3), round(b, 3)] for a, b in corners]}

    labels, timeline = [], [{'at': 0, 't': customer, 's': 'Roofs as drawn — heights, parapets, cabins and marks' if roofs_only else f"{option['kwp']} kWp · {option['modules']} × {spec['wp']} Wp{' ' + spec['make'] if spec.get('make') else ''}"}]
    t = 6.0
    for a in option['arrays']:
        ms = a['_mods']
        mx, my = sum(m.x for m in ms) / len(ms), sum(m.y for m in ms) / len(ms)
        top = max(z for m in ms for z in m.z) + 1.2
        labels.append({'x': mx, 'y': my, 'z': top, 't': a['name'], 's': f"{a['modules']} panels · {a['kwp']} kWp"})
        timeline.append({'at': round(t, 1), 't': a['name'], 's': f"{a['modules']} panels ({'portrait' if a['orient'] == 'P' else 'landscape'}, {a['tilt']}°) · {a['kwp']} kWp · ≈ {a['kwh']:,} units a year"})
        t += min(8.0, 24.0 / max(1, len(option['arrays'])))
    if roofs_only:
        for r in site.roofs:
            c = r['poly'].centroid
            labels.append({'x': c.x, 'y': c.y, 'z': float(r.get('heightM') or 0) + 1.5, 't': r.get('name') or f"Roof {r.get('no')}",
                           's': f"{float(r.get('heightM') or 0):g} m{' · not for solar' if not r.get('use', True) else ''}"
                                + (f" · structure {float(r['structureM']):g} m" if r.get('structureM') not in (None, '') else '')})
        timeline.append({'at': 32, 't': 'Roofs as drawn', 's': 'Check the heights, the cabins and what is marked — then approve Roof design'})
    else:
        timeline.append({'at': 32, 't': f"{option['kwp']} kWp in all", 's': f"≈ {option['annualKwh']:,} units a year · panels kept clear of shade, vents and skylights"})
    if site.inverter:
        labels.append({'x': site.inverter[0], 'y': site.inverter[1], 'z': 2.2, 't': 'Inverter', 's': ''})

    return {
        'title': f'{customer} — roofs as drawn (3D)' if roofs_only else f'{customer} — {option["kwp"]} kWp solar (3D)',
        'spec': ([customer, 'Roofs as drawn', f"{len(site.roofs)} roofs · heights as entered", 'Approve Roof design before Panel placement'] if roofs_only else
                 [customer, f"NEW {option['kwp']} kWp · {option['modules']} × {spec['wp']} Wp{' ' + spec['make'] if spec.get('make') else ''}",
                  option['name'], f"≈ {option['annualKwh']:,} units a year"]),
        'note': note,
        'center': [round(cx, 3), round(cy, 3)], 'extent': round(extent, 2), 'focus': [round(v, 3) for v in focus], 'roofMid': round(roof_mid, 2),
        'ground': ground, 'faces': faces, 'obstacles': obstacles, 'modules': modules,
        'inverter': [round(v, 3) for v in site.inverter] if site.inverter else None,
        'labels': labels, 'timeline': timeline, 'duration': 40,
        'capAll': 'Roofs as drawn' if roofs_only else f"{option['kwp']} kWp on {len(option['arrays'])} roof face{'s' if len(option['arrays']) != 1 else ''}",
        'capClose': 'Roof heights and marks as entered' if roofs_only else 'Panels kept clear of edges, vents and skylights',
    }


def write_viewer(scene: dict, path: str) -> None:
    tpl = open(os.path.join(VIEWER, 'viewer.template.html'), encoding='utf-8').read()
    three = open(os.path.join(VIEWER, 'three-r158.min.js'), encoding='utf-8').read()
    if three.startswith('console.warn('):
        three = '0' + three[three.index(')') + 1:]          # silence the "build/three.min.js is deprecated" banner
    logo = 'data:image/png;base64,' + base64.b64encode(open(os.path.join(VIEWER, 'nrg-logo.png'), 'rb').read()).decode()
    for ph in ('/*__THREE__*/', '/*__LOGO__*/', '/*__SCENE__*/null', '/*__TITLE__*/'):
        if ph not in tpl:
            raise RuntimeError(f'{ph} missing from the viewer template')
    html = (tpl.replace('/*__TITLE__*/', scene['title'].replace('<', ''))
               .replace('/*__LOGO__*/', logo)
               .replace('/*__SCENE__*/null', json.dumps(scene, separators=(',', ':')).replace('</', '<\\/'))
               .replace('/*__THREE__*/', three))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
