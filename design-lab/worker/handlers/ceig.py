# Design Lab worker v1.9.0 (2026-11-01) — stage 'ceig' (per quote / layout): the CEIG drawing set,
# made general from the owner-approved Jain Granite set (NRG's own CEIG submission format):
#   01 Single line diagram   02 Equipment layout   03 Earthing layout
#   04 Walkway layout        05 Cable tray layout  06 Stringing layout
# A3 landscape PDFs with NRG's title block, filed into the project's CEIG / Design folders, plus
# the whole set as one PDF. build() is shared with the 'sld' stage (handlers/sld.py).
import datetime as dt
import os
import re

from handlers import layouts, panels, stringing as hstr, views
from nrg import ceig_pdf, ceigplan, sld
from nrg import stringing as S
from nrg.config import VERSION
from nrg.generation import site_location

EPC = ('NRG TECHNOLOGISTS PVT LTD', '989/6, GIDC Makarpura, Vadodara')


def build(job) -> dict:
    """Everything the sheets need, from the design: plan, chosen option, strings, routes."""
    ins = hstr.inputs(job)          # the inverter picked in the Design Lab (Stringing) — fails plainly if not saved yet
    P = panels.plan(job)
    opt, _ = views.chosen_option(job, P)
    site, arrays = P['site'], opt['arrays']
    res = S.design(site, arrays, ins['inverter'], ins['module'], ins['rates'])
    if not res['strings']:
        raise RuntimeError('No strings could be made: ' + '; '.join(res['warnings']))
    for i, s in enumerate(res['strings']):
        s['_i'] = i
    items = layouts.compute(job, P, opt)
    inv, mod = ins['inverter'], ins['module']
    kwp, n_mod, wp = float(opt['kwp']), int(opt['modules']), int(P['spec']['wp'])
    n_inv = int(inv.get('count') or 1)
    ac_kw = n_inv * float(inv.get('acKw') or 0)
    lat, lon, _src = site_location(job.project, job.design.get('marks'))
    faces = sorted({(a['facing'], round(float(a.get('tilt') or 0))) for a in arrays})
    today = dt.date.today()
    client = (job.customer or 'CLIENT').upper()
    info = {'client': client, 'epc': EPC[0], 'epc_addr': EPC[1], 'title': f'{kwp:.2f} kWp (DC)_ROOFTOP SOLAR PLANT',
            'date': today.strftime('%d-%m-%y'), 'paper': 'A3', 'version': VERSION, 'generated': today.strftime('%d-%m-%Y'),
            'file': re.sub(r'[^A-Za-z0-9]+', '-', job.customer or 'Design').strip('-')[:40] or 'Design'}
    system = [('SITE LOCATION', f'{lat:.5f}, {lon:.5f}'), ('DC CAPACITY', f'{kwp:.2f} kWp'),
              ('TOTAL PLANT CAPACITY (AC)', f'{ac_kw:g} kW'), ('DC / AC RATIO', f'{kwp / ac_kw:.2f}' if ac_kw else '—'),
              ('MODULE CAPACITY', f"{wp} Wp ({(P['spec'].get('make') or mod.get('name') or '').upper()[:22]})"),
              ('MODULE DIMENSION (L X W)', f"{P['spec']['L'] * 1000:.0f} X {P['spec']['W'] * 1000:.0f} mm *"),
              ('TOTAL PV MODULES', f'{n_mod} Nos.'),
              ('INVERTER CAPACITY', f"{inv.get('acKw', 0):g} kW ({inv.get('model', '')}) {n_inv} No."),
              ('AZIMUTH / TILT', ', '.join(f'{f} {t}°' for f, t in faces)[:38] or '—')]
    # LT panel / DG details saved in the Design Lab's SLD form (carried forward in every SLD version)
    sv = job.latest_version('sld', job.row.get('layout_id'))
    lt = ((sv or {}).get('data') or {}).get('lt') or {}
    if lt.get('dg'):
        system.append(('DG SET', f"{lt.get('dgKva') or '—'} kVA, {'ATS' if lt.get('changeover') == 'ats' else 'manual'} changeover"))
    return {'lt': lt, 'info': info, 'system': system, 'site': site, 'arrays': arrays, 'items': items, 'stringing': res,
            'inverter': inv, 'module': mod, 'rates': ins['rates'], 'strings': res['strings'], 'pairs': res.get('pairs', []), 'limits': res['limits'],
            'kwp': kwp, 'modules': n_mod, 'wp': wp, 'acCableM': items.get('ac_m'), 'option': opt['name'],
            'dc': ((res['compare']['y']['m4'] + res['compare']['y']['m6']) if res['useY'] else res['compare']['single']['m4']) / 2}


SHEETS = [('01', 'single_line_diagram', 'SLD', sld.sheet_sld), ('02', 'equipment_layout_drawing', 'Equipment layout', ceigplan.sheet_equipment),
          ('03', 'earthing_layout_drawing', 'Earthing layout', ceigplan.sheet_earthing), ('04', 'walkway_layout_drawing', 'Walkway layout', ceigplan.sheet_walkway),
          ('05', 'cable_tray_layout_drawing', 'Cable tray layout', ceigplan.sheet_tray), ('06', 'wiring_layout_drawing', 'Stringing layout', ceigplan.sheet_stringing)]


def run(job) -> dict:
    d = build(job)
    n = len(SHEETS)
    d['sheet'] = f'01 OF {n:02d}'
    for no, *_ in SHEETS:
        d[f'sheet{no}'] = f'{no} OF {n:02d}'
    docs = [(f"{d['info']['file']}_{no}_{title.replace(' ', '-')}", fn(d)) for no, _, title, fn in SHEETS]
    out = ceig_pdf.render(docs, job.workdir, preview=False)
    for (no, dtype, title, _), o in zip(SHEETS, out):
        job.file_output(o['pdf'], dtype, title=f'CEIG {no} {title}', extra={'ceig_sheet': no})
    whole = ceig_pdf.join([o['pdf'] for o in out], os.path.join(job.workdir, f"{d['info']['file']}_CEIG-set.pdf"))
    if whole:
        job.file_output(whole, 'design_report', title='CEIG drawing set (all sheets)', extra={'ceig_set': True})
    z = sld.sizing(d)
    return {'summary': f"CEIG set: {n} A3 sheets (SLD, equipment, earthing, walkway, cable tray, stringing)"
                       + (' + the whole set as one PDF' if whole else '') + f" for {d['option']}. "
                       f"{z['n_inv']} × {d['inverter'].get('model')}: {z['br_inv']} A MCCB + {z['run_i']}R × {z['sq_i']} sq mm Al each; "
                       f"feeder {z['br_main']} A {z['main_kind']}, {z['run_m']}R × {z['sq_m']} sq mm Al. Values marked * are estimates — verify.",
            'sheets': [no for no, *_ in SHEETS], 'sizing': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in z.items() if not isinstance(v, tuple)},
            'option': d['option']}
