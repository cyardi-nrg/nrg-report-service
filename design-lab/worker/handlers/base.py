# Design Lab worker v1.14.0 (2026-11-02) — stage 'base': start a design from a BASE DESIGN instead of from scratch.
#
# Owner (Nov 2026): "give an option of start from scratch or upload basic 3D design … it could be a 3D design that
# I made for Gen Granite and Marble [SolarEdge Designer], or an AutoCAD file which was done for Sejal Shah. This
# gives you the layout as well as the panel placement." And: "north is always at the top".
#
# The owner uploads the base design (a SolarEdge screenshot, or the AutoCAD drawing as a PDF / picture) and runs
# this stage on it. The Mac:
#   1. turns a PDF into a picture (first page) and turns the picture so north is up (the owner says where north is);
#   2. finds every panel and table on it (nrg/basedesign.py);
#   3. works out the scale from the panel size (the quote's panel, else 625 Wp = 2.382 m long) — north is up;
#   4. sketches a flat roof round each group of tables (a NEW draft of Roof design — the owner sets the real roof
#      kind, heights, cabins and obstacles there and approves it);
#   5. files a check picture: every panel it read, table by table, with rows × panels.
# Panel placement then uses THESE panels instead of placing its own (handlers/panels.py plan()).
# Saved version: {pictureDocumentId, pxPerM, imageW, imageH, panelWp, tiltDeg, tables: [{name, rows, cols, orient,
#   panels: [{x, y, corners}] in % of the picture}], panels}.
import logging
import math
import os

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

from nrg import basedesign
from nrg.inputs import answers, floors_below, panel_spec, _num, STOREY_M
from nrg.render import font

log = logging.getLogger('designlab')

PICTURE_TYPES = {'google_maps_screenshot', 'site_sketch', 'cad_plan'}      # the Design Lab offers these as base pictures
MAX_SIDE = 4000          # a PDF page is drawn at most this many pixels across
GROUP_M = 1.5            # tables closer than this (m) are on the same roof
ROOF_MARGIN = 0.6        # the sketched roof runs this far past the outer panels, m
TILT_DEFAULT = 10.0      # table tilt when the owner gives none, degrees


def _picture(job, doc) -> tuple[str, bool]:
    """The base design as a picture file. Returns (path, is_new_picture) — a PDF page is drawn to a new PNG."""
    src = job.fetch(doc)
    ext = os.path.splitext(src)[1].lower()
    if ext in ('.dwg', '.dxf'):
        raise RuntimeError('Reading panels straight from a DWG / DXF comes later — for now save the AutoCAD drawing as a PDF '
                           '(or take a screenshot of it, north up) and upload that.')
    if ext == '.pdf' or open(src, 'rb').read(5) == b'%PDF-':
        import pymupdf
        pdf = pymupdf.open(src)
        page = pdf[int(job.input.get('page') or 0)]
        zoom = min(4.0, MAX_SIDE / max(page.rect.width, page.rect.height))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        out = os.path.join(job.workdir, 'base-design.png')
        pix.save(out)
        return out, True
    try:
        Image.open(src).verify()
    except Exception:
        raise RuntimeError('That file is not a picture or a PDF — upload a screenshot (PNG / JPG) or a PDF of the base design.')
    return src, False


def _panel_wp(job) -> int:
    if job.input.get('panelWp'):
        return int(job.input['panelWp'])
    rows = job.db.select('design_layouts', {'design_id': f"eq.{job.design['design_id']}", 'select': 'panel_wp'})
    wps = [int(r['panel_wp']) for r in rows if r.get('panel_wp')]
    return max(set(wps), key=wps.count) if wps else 625


def _height(a: dict) -> tuple[float, bool]:
    """Terrace height from Site questions (floors × floor height). Returns (m, assumed)."""
    n = floors_below(a)
    storey = _num(a.get('storeyM')) or STOREY_M
    if n:
        return round(n * storey, 2), False
    return STOREY_M, True


def _parapet(a: dict) -> float:
    t = str(a.get('parapetHeight') or '')
    v = _num(t)
    if v is None:
        return 0.0
    return round(v * 0.3048, 2) if ('ft' in t.lower() or 'feet' in t.lower() or "'" in t) else (v if v < 3 else v / 100)


def _roofs(tables_m: list, a: dict) -> list:
    """One flat roof round each group of tables (metres, picture frame). The owner corrects them in Roof design."""
    shapes = [Polygon(t).convex_hull for t in tables_m]
    groups = unary_union([s.buffer(GROUP_M / 2) for s in shapes])
    parts = list(groups.geoms) if isinstance(groups, MultiPolygon) else [groups]
    parts.sort(key=lambda g: (g.centroid.y, g.centroid.x))
    h, assumed = _height(a)
    par = _parapet(a)
    st = _num(a.get('structureM'))
    out = []
    for i, g in enumerate(parts):
        inside = unary_union([s for s in shapes if s.intersects(g)])
        rect = inside.minimum_rotated_rectangle.buffer(ROOF_MARGIN, join_style=2)
        out.append({'poly': rect, 'no': i + 1, 'heightM': h, 'parapetM': par, 'structureM': st, 'assumed': assumed})
    return out


def run(job) -> dict:
    if not job.input.get('document_id'):         # "request changes" re-runs the stage: same file and settings as last time
        last = ((job.latest_version('base', None) or {}).get('data') or {})
        if last.get('documentId'):
            job.row['input'] = {**job.input, 'document_id': last['documentId'], 'north': last.get('north') or 'up',
                                'tiltDeg': last.get('tiltDeg'), 'panelWp': last.get('panelWp')}
    doc_id = job.input.get('document_id')
    if not doc_id:
        raise RuntimeError('Pick the base design picture / PDF in the Base design stage first.')
    rows = job.db.select('documents', {'document_id': f'eq.{doc_id}', 'select': 'document_id,document_type,google_drive_file_id,extracted_data'})
    if not rows:
        raise RuntimeError('The base design file is no longer in the project documents.')
    doc = rows[0]
    path, new_pic = _picture(job, doc)
    rgb = np.array(Image.open(path).convert('RGB'))
    # north must be up: an AutoCAD sheet is often drawn turned — the owner says where north is on the picture
    turn = {'up': 0, 'right': 1, 'down': 2, 'left': 3}.get(str(job.input.get('north') or 'up'), 0)
    if turn:
        rgb = np.ascontiguousarray(np.rot90(rgb, turn))           # counter-clockwise quarter turns: north ends up at the top
        path = os.path.join(job.workdir, 'base-design-north-up.png')
        Image.fromarray(rgb).save(path)
        new_pic = True
    H, W = rgb.shape[:2]
    read = basedesign.read_panels(rgb)
    if not read['panels']:
        raise RuntimeError('No panels found on this picture. The panels must be drawn in blue (SolarEdge Designer, or the '
                           'AutoCAD panel layer in blue), north up, and not too small — zoom in so each panel is at least '
                           '15 pixels long.')

    wp = _panel_wp(job)
    spec = panel_spec({'panel_wp': wp})
    tilt = float(job.input.get('tiltDeg') or TILT_DEFAULT)
    # SolarEdge draws tilted panels as seen from above: a portrait panel's long side is shortened by cos(tilt)
    orients = [t['orient'] for t in read['tables']]
    seen_L = spec['L'] * (math.cos(math.radians(tilt)) if read['style'] == 'filled' and orients.count('P') * 2 >= len(orients) else 1.0)
    ppm = float(job.input.get('pxPerM') or 0) or read['panel_long_px'] / seen_L      # the owner may correct the scale
    a = answers(job)

    # the picture the roofs are drawn on: the upload itself if the Design Lab can show it, else a filed copy
    pic_id = doc['document_id']
    if new_pic or doc['document_type'] not in PICTURE_TYPES:
        if not new_pic:                                  # a JPG / screenshot under another document type: file it as a PNG
            out = os.path.join(job.workdir, 'base-design.png')
            Image.fromarray(rgb).save(out)
            path = out
        name = os.path.splitext((doc.get('extracted_data') or {}).get('original_name') or 'Base design')[0]
        pic_id = job.file_output(path, 'cad_plan', title=f'{name} — base design picture',
                                 extra={'px_per_m': round(ppm, 3), 'size_m': [round(W / ppm, 1), round(H / ppm, 1)], 'candidates': [],
                                        'units_note': f'scale from the panel size ({wp} Wp, {spec["L"]} m long)',
                                        'source_document_id': doc['document_id'], 'base_design': True})

    pct = lambda x, y: {'x': round(x / W * 100, 4), 'y': round(y / H * 100, 4)}
    tables, tables_m = [], []
    for i, t in enumerate(read['tables']):
        name = f'T{i + 1}'
        tables.append({'name': name, 'rows': t['rows'], 'cols': t['cols'], 'orient': t['orient'], 'angleDeg': round(t['angle_deg'], 2),
                       'panels': [{**pct(p['x'], p['y']), 'corners': [pct(cx, cy) for cx, cy in p['corners']]} for p in t['panels']]})
        tables_m.append([(cx / ppm, cy / ppm) for p in t['panels'] for cx, cy in p['corners']])
    n = read['panels']

    # a new draft of Roof design: flat roofs round the tables, on the base picture
    roofs = _roofs(tables_m, a)
    model = {'version': 1, 'baseDocumentId': pic_id, 'pxPerM': round(ppm, 4), 'imageW': W, 'imageH': H, 'obstacles': [],
             'roofs': [{'id': f'base-{r["no"]}', 'no': r['no'], 'name': f'Roof {r["no"]}', 'kind': 'flat_rcc', 'use': True,
                        'points': [pct(x * ppm, y * ppm) for x, y in list(r['poly'].exterior.coords)[:-1]],
                        'heightM': r['heightM'], 'parapetM': r['parapetM'], 'setbackM': 0.3,
                        **({'structureM': r['structureM']} if r['structureM'] is not None else {}),
                        'note': 'Sketched round the base design tables — set the real roof outline, kind and heights'} for r in roofs]}
    if not job.input.get('keepRoofs'):
        last = job.latest_version('roofs', None)
        job.db.insert('design_stage_versions', {
            'design_id': job.design['design_id'], 'layout_id': None, 'stage': 'roofs', 'version': (last['version'] if last else 0) + 1,
            'status': 'draft', 'data': {'model': model, 'fromBase': True, 'job_id': job.job_id, 'worker': job.worker},
            'note': f'From the base design — {len(roofs)} roof(s) sketched round {len(tables)} tables', 'created_by': None,
        }, returning=False)

    # the check picture: every panel read, table by table
    img = Image.fromarray(rgb).convert('RGB')
    k = min(1.0, 2400 / max(W, H))
    if k < 1:
        img = img.resize((int(W * k), int(H * k)))
    d = ImageDraw.Draw(img, 'RGBA')
    for r in roofs:
        d.polygon([(x * ppm * k, y * ppm * k) for x, y in r['poly'].exterior.coords], outline=(217, 119, 6), width=3)
    for t, src in zip(tables, read['tables']):
        for p in src['panels']:
            d.polygon([(cx * k, cy * k) for cx, cy in p['corners']], fill=(20, 184, 166, 110), outline=(250, 204, 21), width=1)
        xs = [p['x'] for p in src['panels']]; ys = [p['y'] for p in src['panels']]
        label = f"{t['name']}  {t['rows']}×{t['cols']}" + ('' if t['rows'] * t['cols'] == len(src['panels']) else f" ({len(src['panels'])})")
        cx, cy = sum(xs) / len(xs) * k, sum(ys) / len(ys) * k
        f = font(max(14, int(22 * max(k, 0.6))), True)
        bb = d.textbbox((cx, cy), label, font=f, anchor='mm')
        d.rectangle([bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3], fill=(17, 24, 39, 210))
        d.text((cx, cy), label, fill='white', font=f, anchor='mm')
    head = (f"Read from the base design: {n} panels in {len(tables)} tables · {round(n * wp / 1000, 2)} kWp at {wp} Wp · "
            f"scale {ppm:.1f} px/m from the panel size · north up")
    f = font(20, True)
    d.rectangle([0, 0, img.size[0], 34], fill=(30, 58, 138, 230))
    d.text((10, 17), head, fill='white', font=f, anchor='lm')
    out = os.path.join(job.workdir, 'Base-design-read.jpg')
    img.save(out, quality=88)
    job.file_output(out, 'design_report', title='Base design — panels read')

    short = [t for t, src in zip(tables, read['tables']) if t['rows'] * t['cols'] != len(src['panels'])]
    size_m = f"{W / ppm:.0f} × {H / ppm:.0f} m"
    return {
        'summary': f"{n} panels in {len(tables)} tables read ({round(n * wp / 1000, 2)} kWp at {wp} Wp); picture {size_m}. "
                   + (f"Roof design: {len(roofs)} roof(s) sketched round the tables — set their kind and heights, then approve. "
                      if not job.input.get('keepRoofs') else '')
                   + (f"Check {', '.join(t['name'] for t in short)}: not a full rectangle." if short else 'Check the picture: every panel should be shaded teal.'),
        'documentId': doc['document_id'], 'pictureDocumentId': pic_id, 'style': read['style'], 'pxPerM': round(ppm, 4),
        'imageW': W, 'imageH': H, 'panelWp': wp, 'tiltDeg': tilt, 'north': ['up', 'right', 'down', 'left'][turn], 'tables': tables, 'panels': n,
        'roofsSketched': 0 if job.input.get('keepRoofs') else len(roofs),
    }
