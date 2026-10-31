# Design Lab worker v1.7.0 (2026-10-31) — stage 'layouts': walkway, cable tray and
# earthing layouts for the chosen panel option, with their lengths written into the
# BOM's "as per design" column.
#   Walkways (owner): between the rows — in the gap the layout leaves after each row group,
#     running along the rows (FRP on sheet roofs; tables on flat roofs have their own gaps).
#   Cable tray: along each array's side nearest the inverter, then over the roof to the
#     edge nearest the inverter and down the wall.
#   Earthing (owner): 3 pits — DC, AC (beside the inverter) and LA, 3 m apart (owner: at least 2 m, 3 m if possible); lightning arresters on
#     the highest roof, how many by inverter kW (the app's own LA bands, Rates → BOM
#     Components). Earthing runs from each array to the DC pit, LA down-conductor to the LA pit.
#   AC cable: inverter to the meter mark (per inverter).
# Routes are square to the building and approximate — "verify on site" is on every sheet.
import math
import os

from PIL import Image, ImageDraw

from handlers import panels, views
from nrg import render

PIT_GAP = 3.0   # m between earth pits (owner: at least 2 m, 3 m if possible)
LA_BANDS = [(0, 100, 1), (101, 250, 2), (251, 500, 3), (501, 750, 4), (751, 1000, 5)]   # app default (lib/bom-generator.ts)


def _la_count(job, inverter_kw: float) -> int:
    try:
        rows = job.db.select('bom_la_qty_bands', {'select': 'min_kw,max_kw,quantity', 'order': 'min_kw.asc'})
        bands = [(float(r['min_kw']), float(r['max_kw']), int(r['quantity'])) for r in rows] or LA_BANDS
    except Exception:
        bands = LA_BANDS
    for lo, hi, q in bands:
        if lo <= inverter_kw <= hi:
            return q
    return max(bands, key=lambda b: b[1])[2] if bands else 1


def _walkways(arr) -> list:
    """[(p0, p1)] walkway centre lines between consecutive row groups of one array (sheet roofs)."""
    p = arr['_pack']
    if p['kind'] != 'sheet':
        return []
    g = max(1, p.get('group_rows') or 4)
    rows = {}
    for m in arr['_mods']:
        rows.setdefault(m.row, []).append(m)
    out = []
    groups = sorted({r // g for r in rows})
    for a, b in zip(groups, groups[1:]):
        last = rows.get(max(r for r in rows if r // g == a))
        first = rows.get(min(r for r in rows if r // g == b))
        if not last or not first:
            continue
        ms = last + first
        lo, hi = min(ms, key=lambda m: m.u), max(ms, key=lambda m: m.u)
        # midpoint between the downhill edge of the last row and the uphill edge of the next group
        def mid(m_last, m_first, i_last, i_first):
            (x1, y1), (x2, y2) = m_last.corners[i_last], m_first.corners[i_first]
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        l_lo, f_lo = min(last, key=lambda m: m.u), min(first, key=lambda m: m.u)
        l_hi, f_hi = max(last, key=lambda m: m.u), max(first, key=lambda m: m.u)
        out.append((mid(l_lo, f_lo, 3, 0), mid(l_hi, f_hi, 2, 1)))
    return out


def _tray(site, arr) -> list:
    """Polyline (site metres): along the array's side nearest the inverter, then square to the building to the inverter."""
    ms = arr['_mods']
    if not site.inverter or not ms:
        return []
    ix, iy = site.inverter
    cols = {}
    for m in ms:
        cols.setdefault(round(m.u, 1), []).append(m)
    near = min(cols.values(), key=lambda c: min(abs(m.x - ix) + abs(m.y - iy) for m in c))
    near = sorted(near, key=lambda m: m.row)
    a, b = (near[0].x, near[0].y), (near[-1].x, near[-1].y)
    end = min((a, b), key=lambda p: abs(p[0] - ix) + abs(p[1] - iy))
    return [a, b, end, (ix, end[1]), (ix, iy)] if end == b else [b, a, end, (ix, end[1]), (ix, iy)]


def _len(poly) -> float:
    return sum(math.dist(p, q) for p, q in zip(poly, poly[1:]))


def _draw(site, base, arrays, layer: str, items: dict, title: str, lines: list, out_path: str):
    img, k = render.base_canvas(base, site.W, site.H)
    d = ImageDraw.Draw(img, 'RGBA')
    P = lambda x, y: tuple(v * k for v in site.to_px(x, y))
    for r in site.roofs:
        d.polygon([P(x, y) for x, y in r['poly'].exterior.coords], outline=(217, 119, 6), width=2)
    for a in arrays:
        for m in a['_mods']:
            d.polygon([P(x, y) for x, y in m.corners], fill=(37, 99, 235, 90 if layer != 'walkway' else 140), outline=(255, 255, 255, 120))
    if layer == 'walkway':
        for p0, p1 in items['walkways']:
            d.line([P(*p0), P(*p1)], fill=(87, 83, 78, 235), width=max(4, int(0.6 * site.ppm * k)))
    if layer == 'tray':
        for poly in items['trays']:
            d.line([P(*p) for p in poly], fill=(234, 88, 12, 240), width=6, joint='curve')
    if layer == 'earthing':
        for poly in items['earth']:
            d.line([P(*p) for p in poly], fill=(21, 128, 61, 230), width=4)
        for poly in items['la_runs']:
            d.line([P(*p) for p in poly], fill=(185, 28, 28, 230), width=4)
        for (x, y) in items['la']:
            px, py = P(x, y)
            d.polygon([(px, py - 18), (px - 12, py + 8), (px + 12, py + 8)], fill=(185, 28, 28))
            d.text((px + 16, py), 'LA', fill=(185, 28, 28), font=render.font(18, True), anchor='lm', stroke_width=3, stroke_fill='white')
        for i, (name, (x, y)) in enumerate(items['pits']):
            px, py = P(x, y)
            d.ellipse([px - 14, py - 14, px + 14, py + 14], outline=(21, 128, 61), width=4, fill=(255, 255, 255))
            d.text((px, py), str(i + 1), fill=(21, 128, 61), font=render.font(17, True), anchor='mm')
    if site.inverter:
        ix, iy = P(*site.inverter)
        d.rectangle([ix - 15, iy - 10, ix + 15, iy + 10], fill=(234, 88, 12))
        d.text((ix - 18, iy - 18), 'INVERTER', fill=(234, 88, 12), font=render.font(17, True), anchor='rm', stroke_width=3, stroke_fill='white')
    if items.get('meter'):
        mx, my = P(*items['meter'])
        d.rectangle([mx - 12, my - 12, mx + 12, my + 12], outline=(124, 58, 237), width=4)
        d.text((mx + 16, my - 18), 'METER', fill=(124, 58, 237), font=render.font(17, True), anchor='lm', stroke_width=3, stroke_fill='white')
    W, H = img.size
    panel = Image.new('RGB', (W, 32 + 44 + 26 * len(lines)), 'white')
    pd = ImageDraw.Draw(panel)
    pd.text((16, 16), title, fill=render.INK, font=render.font(28, True))
    for i, ln in enumerate(lines):
        pd.text((16, 58 + i * 26), ln, fill=render.INK if i == 0 else render.MUTED, font=render.font(17))
    out = Image.new('RGB', (W, H + panel.height), 'white')
    out.paste(panel, (0, 0)); out.paste(img, (0, panel.height))
    out.save(out_path, optimize=True)


def run(job) -> dict:
    P = panels.plan(job)
    opt, _ = views.chosen_option(job, P)
    site, arrays = P['site'], opt['arrays']
    base = panels.base_picture(job, P['model'])
    marks = job.design.get('marks') or {}
    sv = job.latest_version('stringing', job.row.get('layout_id'))
    inv = ((sv or {}).get('data') or {}).get('inverter') or {}
    inv_count, inv_kw = int(inv.get('count') or 1), float(inv.get('acKw') or 0)

    # walkways
    walkways = [w for a in arrays for w in _walkways(a)]
    walk_m = round(sum(math.dist(*w) for w in walkways), 1)
    # cable tray
    trays = [t for t in (_tray(site, a) for a in arrays) if t]
    roof_h = {a['face']: max(max(m.z) for m in a['_mods']) for a in arrays}
    tray_m = round(sum(_len(t) for t in trays) + sum(roof_h.values()), 1) if trays else 0.0
    # earthing: DC + AC pits beside the inverter, LA pit under the arresters
    pits, earth, la_runs, la_pts = [], [], [], []
    hi_arr = max(arrays, key=lambda a: roof_h[a['face']]) if arrays else None
    total_kw = inv_count * inv_kw or opt['kwp']
    la_n = _la_count(job, total_kw)
    if site.inverter:
        ix, iy = site.inverter
        pits = [('EP-1 (DC)', (ix - PIT_GAP, iy + 3.0)), ('EP-2 (AC)', (ix, iy + 3.0))]
        for a in arrays:
            cx = sum(m.x for m in a['_mods']) / len(a['_mods']); cy = sum(m.y for m in a['_mods']) / len(a['_mods'])
            earth.append([(cx, cy), (ix - PIT_GAP, cy), (ix - PIT_GAP, iy + 3.0)])
    if hi_arr:
        ms = hi_arr['_mods']
        lo, hi = min(ms, key=lambda m: m.u), max(ms, key=lambda m: m.u)
        for i in range(la_n):
            f = (i + 1) / (la_n + 1)
            la_pts.append((lo.x + (hi.x - lo.x) * f, lo.y + (hi.y - lo.y) * f))
        drop = la_pts[0] if la_pts else (lo.x, lo.y)
        ref = site.inverter or drop
        la_pit = (ref[0] + PIT_GAP, ref[1] + 3.0)
        pits.append(('EP-3 (LA)', la_pit))
        for p in la_pts:
            la_runs.append([p, (la_pit[0], p[1]), la_pit])
    earth_m = round(sum(_len(e) for e in earth) + sum(roof_h.values()) + 5 * len(earth), 1)
    la_m = round(sum(_len(r) for r in la_runs) + (roof_h[hi_arr['face']] + 3) * len(la_runs), 1) if hi_arr else 0.0
    # AC cable: inverter to the meter mark, per inverter
    meter = site.to_m(marks['meter']) if marks.get('meter') and site.inverter else None
    ac_m = round(inv_count * (abs(meter[0] - site.inverter[0]) + abs(meter[1] - site.inverter[1]) + 5), 1) if meter else None

    items = {'walkways': walkways, 'trays': trays, 'earth': earth, 'la_runs': la_runs, 'la': la_pts, 'pits': pits, 'meter': meter}
    note = 'Routes are square to the building and approximate — verify on site.'
    for layer, dtype, title, lines in (
        ('walkway', 'walkway_layout_drawing', 'Walkway layout', [f'FRP walkway between the row groups: {walk_m:,} m (0.6 m wide)', 'Grey bands = walkway', note]),
        ('tray', 'cable_tray_layout_drawing', 'Cable tray layout', [f'Cable tray: {tray_m:,} m (incl. the drop down the wall)' + (f' · AC cable to the meter: {ac_m:,} m' if ac_m else ''), 'Orange = tray route', note]),
        ('earthing', 'earthing_layout_drawing', 'Earthing layout', [f'3 earth pits (DC, AC, LA) · {la_n} lightning arrester(s) for {total_kw:g} kW · structure earthing {earth_m:,} m · LA down-conductor {la_m:,} m',
                                                                    'Pits 3 m apart: 1 = DC, 2 = AC, 3 = LA · green = structure earthing to pit 1 · red = LA down-conductor to pit 3', note])):
        path = os.path.join(job.workdir, f'{title}.png')
        _draw(site, base, arrays, layer, items, f'{title} — {opt["name"]} · {opt["kwp"]} kWp', lines, path)
        job.file_output(path, dtype, title=title)

    bom = {**((job.layout or {}).get('bom_required') or {}), 'walkwayM': walk_m, 'cableTrayM': tray_m, 'earth40M': earth_m, 'laCableM': la_m,
           'earthingPits': 3, 'laCount': la_n}
    if ac_m is not None:
        bom['acCableM'] = ac_m
    job.db.update('design_layouts', {'layout_id': f"eq.{job.row['layout_id']}"}, {'bom_required': bom})
    return {'summary': f"Walkway {walk_m:,} m · cable tray {tray_m:,} m · earthing {earth_m:,} m + LA {la_m:,} m · 3 pits, {la_n} LA"
                       + (f" · AC cable {ac_m:,} m" if ac_m else ' · AC cable: mark the meter in Site & marks') + ' — written into the BOM.',
            'walkwayM': walk_m, 'cableTrayM': tray_m, 'earth40M': earth_m, 'laCableM': la_m, 'laCount': la_n, 'acCableM': ac_m, 'option': opt['name']}
