# Design Lab worker v1.4.0 (2026-10-31) — stage 'structure' (per quote / layout):
# drawing sheets for the structure saved in the Design Lab (the automatic best
# combination or the owner's own pipes / spacings — drawn even if it fails,
# clearly marked). One A3 sheet per panel table (PDF with all sheets + a PNG of
# each); sheet roofs get the aluminium-piece sheet. The saved structure is
# carried forward unchanged into the new version.
import os

from nrg import structdraw


def run(job) -> dict:
    lid = job.row.get('layout_id')
    v = job.latest_version('structure', lid, approved_only=True) or job.latest_version('structure', lid)
    data = (v or {}).get('data') or {}
    if not data.get('input'):
        raise RuntimeError('Save the structure first (Structure stage → “Save structure”), then run the drawings.')
    inp = data['input']
    label = (job.layout or {}).get('label') or ''
    sheets, names = [], []
    if data.get('kind') == 'aluminium':
        sheets.append(structdraw.alu_sheet(data, inp, job.customer, label, v['version']))
        names.append('S-01 aluminium')
    else:
        for i, b in enumerate((data.get('blocks') or [])[:12]):
            sheets.append(structdraw.gi_sheet(b, inp, data, job.customer, label, f'S-{i + 1:02d}', v['version']))
            names.append(f"S-{i + 1:02d} {b['block']['name']}")
    if not sheets:
        raise RuntimeError('The saved structure has no tables to draw.')
    pngs = [os.path.join(job.workdir, f'{n}.png') for n in names]
    pdf = os.path.join(job.workdir, 'Structure drawings.pdf')
    structdraw.save(sheets, pngs, pdf)
    job.file_output(pdf, 'structural_drawing', title=f'{len(sheets)} sheet{"s" if len(sheets) != 1 else ""} (PDF)')
    for n, p in zip(names, pngs):
        job.file_output(p, 'structural_drawing', title=n)
    fails = [b['block']['name'] for b in data.get('blocks', []) if not b.get('pass')]
    carry = {k: data[k] for k in data if k not in ('document_ids', 'job_id', 'worker', 'summary')}
    return {**carry, 'summary': f"{len(sheets)} structure sheet{'s' if len(sheets) != 1 else ''} drawn"
                                + (f" — {', '.join(fails)} FAIL the member checks (drawn as chosen)." if fails else '.')}
