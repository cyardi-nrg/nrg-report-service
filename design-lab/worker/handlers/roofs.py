# Design Lab worker v1.2.0 (2026-10-31) — stage 'roofs' on the Mac: the roof &
# shade report for the roofs the owner drew. Usable area of each roof
# after setbacks and obstacles, how much of it the winter sun shades
# (21 Dec, 9 am – 3 pm), and how many 625 Wp panels it could take. The
# drawn roof model is carried forward unchanged into the new version.
import os

import numpy as np

from nrg import site as sitemod
from nrg import sun as sunmod
from nrg import packer, render
from nrg.inputs import roof_model, base_picture


def run(job) -> dict:
    model, v = roof_model(job)
    site = sitemod.build(model, job.design.get('marks'))
    sun = sunmod.winter_sun()
    rows, cells = [], []
    for f in site.faces:
        area = packer.usable_area(site, f)
        if area.is_empty:
            rows.append({'face': f.key, 'name': f.name, 'usable_m2': 0, 'shaded_pct': 0, 'panels625': 0})
            continue
        minx, miny, maxx, maxy = area.bounds
        xs, ys = np.meshgrid(np.arange(minx + 0.35, maxx, 0.7), np.arange(miny + 0.35, maxy, 0.7))
        from shapely.prepared import prep
        from shapely.geometry import Point
        P = prep(area)
        pts = [(x, y) for x, y in zip(xs.ravel(), ys.ravel()) if P.contains(Point(x, y))]
        if pts:
            px, py = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
            zs = np.array([f.height_at(x, y) for x, y in pts]) + 0.15
            hit = sunmod.shaded(site, px, py, zs, sun)
            cells += [(x, y, 0.7) for (x, y), h in zip(pts, hit) if h]
            pct = round(100 * hit.mean())
        else:
            pct = 0
        cap = len(packer.pack_face(site, f, 2.382, 1.134, sun)['modules'])
        rows.append({'face': f.key, 'name': f.name, 'usable_m2': round(area.area), 'shaded_pct': pct, 'panels625': cap})
    base = base_picture(job, model)
    lines = [f"{r['face']}|{r['name']} — {r['usable_m2']:,} m² usable, {r['shaded_pct']} % shaded in winter, room for ~{r['panels625']} × 625 Wp" for r in rows]
    total = sum(r['panels625'] for r in rows)
    lines.append(f"In all: room for about {total} panels of 625 Wp ≈ {round(total * 0.625, 1)} kWp. Red = shaded on 21 Dec between 9 am and 3 pm.")
    out = os.path.join(job.workdir, 'Roof-and-shade.png')
    render.draw_layout(site, base, [], [], 'Roof & shade report', lines, out, shade_cells=cells)
    job.file_output(out, 'design_report', title='Roof and shade report')
    return {'summary': f"{len(rows)} roof face(s) checked: room for about {total} × 625 Wp ({round(total * 0.625, 1)} kWp).",
            'model': model, 'faces': rows, 'capacity625': total}
