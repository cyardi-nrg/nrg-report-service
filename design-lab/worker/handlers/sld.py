# Design Lab worker v1.9.0 (2026-11-01) — stage 'sld' (per quote / layout): the single line diagram
# on its own (A3 PDF + a picture for the Design Lab). The full CEIG set is the 'ceig' stage.
from handlers import ceig
from nrg import ceig_pdf, sld


def run(job) -> dict:
    d = ceig.build(job)
    d['sheet'] = '01 OF 01'
    name = f"{d['info']['file']}_01_SLD"
    out = ceig_pdf.render([(name, sld.sheet_sld(d))], job.workdir, preview=True)[0]
    job.file_output(out['pdf'], 'single_line_diagram', title='Single line diagram')
    job.file_output(out['png'], 'single_line_diagram', title='Single line diagram (picture)')
    z = sld.sizing(d)
    return {'summary': f"SLD for {d['option']}: {len(d['strings'])} strings on {z['n_inv']} × {d['inverter'].get('model')}; "
                       f"each inverter {z['br_inv']} A MCCB + {z['run_i']}R × {z['sq_i']} sq mm Al; ACDB → LT panel {z['br_main']} A {z['main_kind']}, "
                       f"{z['run_m']}R × {z['sq_m']} sq mm Al; AC drop ≈ {z['vd_ac']:.2f} %, DC drop {z['vd_dc'][0]:.2f}–{z['vd_dc'][1]:.2f} %. "
                       "Values marked * are estimates — verify.",
            'sizing': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in z.items() if not isinstance(v, tuple)}, 'option': d['option'],
            'lt': d.get('lt') or {}}   # the SLD form's LT panel / DG details, carried forward
