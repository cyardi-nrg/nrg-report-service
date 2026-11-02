# Design Lab worker v1.15.0 (2026-11-02) — stage 'views' (per quote / layout): 3D of the
# v1.15.0: building style from Site questions + walkways on sheet roofs, for the realistic viewer.
# (v1.3.0) 3D of the
# chosen panel layout option — one interactive 3D file (opens offline in any browser,
# to send to the client) + still pictures from five views.
import os

from handlers import panels
from nrg import scene as scenemod, shots
from nrg.inputs import answers

VIEW_TITLE = {'aerial_se': 'Aerial from the south-east', 'aerial_sw': 'Aerial from the south-west', 'top': 'Top view',
              'south': 'From the south', 'close': 'Close-up'}


def chosen_option(job, P: dict) -> tuple[dict, list]:
    """The option the owner picked in Panel placement (else the recommended one), rebuilt exactly."""
    v = job.latest_version('panels', job.row.get('layout_id'), approved_only=True) or job.latest_version('panels', job.row.get('layout_id'))
    want = ((v or {}).get('data') or {}).get('recommended') if v else None
    built = []
    for k, (title, order) in panels.orders(P['packs']).items():
        arrays, mods = panels.option_arrays(P, order)
        opt = {'name': f'Option {k} · {title}', 'arrays': arrays, 'modules': len(mods), 'kwp': round(len(mods) * P['spec']['wp'] / 1000, 2),
               'annualKwh': sum(a['kwh'] for a in arrays)}
        built.append((opt, mods))
    if not v:
        raise RuntimeError('Run Panel placement first — the 3D shows the panel layout option you choose there.')
    for opt, mods in built:
        if opt['name'] == want:
            return opt, mods
    return max(built, key=lambda b: b[0]['annualKwh'])


def walkways_3d(site, opt: dict) -> list:
    """Walkway centre lines between row groups on sheet roofs, at the roof surface (x, y, z)."""
    from handlers.layouts import _walkways
    faces = {f.key: f for f in site.faces}
    out = []
    for a in opt.get('arrays', []):
        f = faces.get(a.get('face'))
        if f is None or '_pack' not in a:
            continue
        for (x0, y0), (x1, y1) in _walkways(a):
            out.append(((x0, y0, f.height_at(x0, y0)), (x1, y1, f.height_at(x1, y1))))
    return out


def run(job) -> dict:
    P = panels.plan(job)
    opt, mods = chosen_option(job, P)
    base = panels.base_picture(job, P['model'])
    note = (f"Concept visualisation from the NRG Design Lab · roofs as drawn (Roof design v{P['roof_v']['version']}); "
            'heights as entered — verify on site')
    sc = scenemod.build_scene(P['site'], opt, mods, P['spec'], job.customer, base, note,
                              style=answers(job).get('buildingType'), walkways=walkways_3d(P['site'], opt))
    html = os.path.join(job.workdir, '3D-viewer.html')
    scenemod.write_viewer(sc, html)
    job.file_output(html, 'design_3d_view', title=f"{opt['name'].split(' · ')[0]} — interactive 3D (open in a browser)")
    pics = shots.stills(html, job.workdir)
    for v, path in pics:
        job.file_output(path, 'design_3d_view', title=VIEW_TITLE.get(v, v))
    return {'summary': f"3D of {opt['name']} ({opt['kwp']} kWp): interactive file + {len(pics)} pictures.",
            'option': opt['name'], 'views': [v for v, _ in pics]}
