# Design Lab worker v1.1.0 (2026-10-31) — job stage 'cad': turn an uploaded
# AutoCAD drawing (Documents → Design → AutoCAD drawing) into a plan
# picture with a known scale + suggested roof outlines. The picture is
# filed as an "AutoCAD plan" design document; the Design Lab offers it as
# a base picture for site marking and the roof editor, with its scale
# (px per metre) and the suggestions already attached.
import os

from nrg import cad
from nrg.jobs import Job


def run(job: Job) -> dict:
    doc_id = job.input.get('document_id')
    docs = job.input_documents(['autocad_drawing'])
    doc = next((d for d in docs if d['document_id'] == doc_id), None) if doc_id else (docs[0] if docs else None)
    if not doc:
        raise RuntimeError('No AutoCAD drawing found on this project (Documents → Design → AutoCAD drawing).')
    src = job.fetch(doc)
    name = os.path.splitext(os.path.basename(src))[0]
    png = os.path.join(job.workdir, f'{name} — plan.png')
    meta = cad.read(src, job.workdir, png)
    job.file_output(png, 'cad_plan', title=name, extra={**meta, 'source_document_id': doc['document_id']})
    n = len(meta['candidates'])
    return {
        'summary': f"AutoCAD plan ready: {meta['size_m'][0]} × {meta['size_m'][1]} m, {meta['units_note']}. "
                   f"{n} closed shape{'' if n == 1 else 's'} found that could be roofs — pick them in Roof design.",
        'no_version': True,
    }
