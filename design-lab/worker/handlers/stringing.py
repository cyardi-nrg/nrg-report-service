# Design Lab worker v1.6.0 (2026-10-31) — stage 'stringing' (per quote / layout).
# The inverter (and the module's electrical values, and cable rates) are picked in the
# Design Lab's Stringing stage — the owner chooses the inverter per design. This works out
# the strings for the chosen panel option, which MPPT each goes to, every + / − run to
# the inverter, single 4 sq mm runs vs Y-connectors with 6 sq mm runs (the cheaper wins),
# draws it, and writes the DC cable / MC4 figures into the BOM's "as per design" column.
import os

from PIL import ImageDraw

from handlers import panels, views
from nrg import render, stringing as S

DEFAULT_RATES = {'dc4': 40.0, 'dc6': 60.0, 'ySet': 400.0}   # ₹ per metre of conductor / per pair of Y-connectors — editable in the Design Lab


def inputs(job) -> dict:
    v = job.latest_version('stringing', job.row.get('layout_id'))
    d = (v or {}).get('data') or {}
    inv = d.get('inverter')
    if not inv or not inv.get('mppts'):
        raise RuntimeError('Pick the inverter first — Design Lab → Stringing → “Inverter for this design” → Save, then run on the Mac.')
    rates = {**DEFAULT_RATES, **{k: float(v) for k, v in (d.get('rates') or {}).items() if v not in (None, '')}}
    return {'inverter': inv, 'module': {**S.DEFAULT_MODULE, **(d.get('module') or {})}, 'rates': rates}


def draw(site, base, res: dict, opt: dict, inv: dict, out_path: str):
    img, k = render.base_canvas(base, site.W, site.H)
    d = ImageDraw.Draw(img, 'RGBA')
    P = lambda x, y: tuple(v * k for v in site.to_px(x, y))
    for r in site.roofs:
        d.polygon([P(x, y) for x, y in r['poly'].exterior.coords], outline=(217, 119, 6), width=2)
    hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    for st in res['strings']:
        c = hexc(st['color'])
        for m in st['mods']:
            d.polygon([P(x, y) for x, y in m.corners], fill=c + (215,), outline=(255, 255, 255))
        mid = st['mods'][len(st['mods']) // 2]
        x, y = P(mid.x, mid.y)
        d.rounded_rectangle([x - 44, y - 13, x + 44, y + 13], 6, fill=(255, 255, 255, 230))
        d.text((x, y), st['id'] + (f" · {st['inverter']}-M{st['mppt']}" if st.get('mppt') else ''), fill=(17, 17, 17), font=render.font(15, True), anchor='mm')
        for pole, col in (('plus', (220, 38, 38)), ('minus', (17, 17, 17))):
            mx, my = P(st[pole].x, st[pole].y)
            d.ellipse([mx - 7, my - 7, mx + 7, my + 7], fill=col, outline=(255, 255, 255))
            if site.inverter:
                ix, iy = P(*site.inverter)
                d.line([(mx, my), (ix, my), (ix, iy)], fill=c + (140,), width=2)
    if site.inverter:
        ix, iy = P(*site.inverter)
        d.rectangle([ix - 16, iy - 11, ix + 16, iy + 11], fill=(234, 88, 12))
        d.text((ix + 20, iy), f"{inv.get('model', 'INVERTER')}", fill=(234, 88, 12), font=render.font(18, True), anchor='lm')
    W, H = img.size
    c = res['compare']
    lines = [f"{len(res['strings'])} strings ({', '.join(sorted({str(s['n']) for s in res['strings']}))} panels each) on {inv.get('count', 1)} × {inv.get('model')} "
             f"({inv['mppts']} MPPT, up to {res['stringsPerMppt']} strings per MPPT)",
             f"DC cable — single runs: {c['single']['m4']:,} m of 4 sq mm (₹{c['single']['cost']:,})  ·  Y-connectors: {c['y']['m4']:,} m of 4 sq mm + "
             f"{c['y']['m6']:,} m of 6 sq mm + {c['y']['ySets']} Y pairs (₹{c['y']['cost']:,})  →  {c['choice']}",
             '   '.join(res['checks'].values()),
             '● red = + end   ● black = − end   (cable lengths: along the roof square to the building, down the wall, to the inverter; verify on site)']
    lines += res['warnings'][:3]
    pad, lh = 16, 26
    from PIL import Image
    panel = Image.new('RGB', (W, pad * 2 + 40 + lh * len(lines)), 'white')
    pd = ImageDraw.Draw(panel)
    pd.text((pad, pad), f"Stringing — {opt['name']} · {opt['kwp']} kWp", fill=render.INK, font=render.font(28, True))
    for i, ln in enumerate(lines):
        pd.text((pad, pad + 40 + i * lh), ln, fill=render.INK if i < 2 else render.MUTED, font=render.font(17))
    out = Image.new('RGB', (W, H + panel.height), 'white')
    out.paste(panel, (0, 0)); out.paste(img, (0, panel.height))
    out.save(out_path, optimize=True)


def run(job) -> dict:
    ins = inputs(job)
    P = panels.plan(job)
    opt, _mods = views.chosen_option(job, P)
    res = S.design(P['site'], opt['arrays'], ins['inverter'], ins['module'], ins['rates'])
    if not res['strings']:
        raise RuntimeError('No strings could be made: ' + '; '.join(res['warnings']))
    base = panels.base_picture(job, P['model'])
    pic = os.path.join(job.workdir, 'Stringing layout.png')
    draw(P['site'], base, res, opt, ins['inverter'], pic)
    job.file_output(pic, 'wiring_layout_drawing', title='Stringing layout')
    rows = [[s['id'], f"{s.get('inverter', '—')}/{s.get('mppt', '—')}/{s.get('input', '—')}", s['n'], s['faceName'], f"{s['plusM']:,}", f"{s['minusM']:,}"] for s in res['strings']]
    sched = os.path.join(job.workdir, 'String schedule.png')
    c = res['compare']
    render.draw_table(f"{job.customer} — string schedule ({opt['kwp']} kWp)", ['String', 'Inv / MPPT / in', 'Panels', 'Roof', '+ run m', '− run m'], rows,
                      list(res['checks'].values()) + [f"Chosen: {c['choice']} (single ₹{c['single']['cost']:,} vs Y ₹{c['y']['cost']:,} at ₹{c['rates']['dc4']:g}/m 4 sq mm, "
                                                     f"₹{c['rates']['dc6']:g}/m 6 sq mm, ₹{c['rates']['ySet']:g} per Y pair)."] + res['warnings'], sched)
    job.file_output(sched, 'wiring_layout_drawing', title='String schedule')

    # BOM "as per design": DC cable per colour (the main run's size) and MC4 connectors
    per_colour = round((c['y']['m6'] if res['useY'] else c['single']['m4']) / 2)
    bom = {**((job.layout or {}).get('bom_required') or {}), 'dcCableM': per_colour, 'mc4Sets': 2 * len(res['strings'])}
    job.db.update('design_layouts', {'layout_id': f"eq.{job.row['layout_id']}"}, {'bom_required': bom})

    strings_out = [{k: v for k, v in s.items() if k not in ('mods', 'plus', 'minus')} for s in res['strings']]
    return {'summary': f"{len(res['strings'])} strings on {ins['inverter'].get('count', 1)} × {ins['inverter'].get('model')}; {c['choice']} "
                       f"(₹{min(c['single']['cost'], c['y']['cost']):,} of DC cable). BOM: DC cable {per_colour:,} m per colour."
                       + (f" Warnings: {'; '.join(res['warnings'])}" if res['warnings'] else ''),
            'inverter': ins['inverter'], 'module': ins['module'], 'rates': ins['rates'], 'strings': strings_out,
            'compare': c, 'checks': res['checks'], 'warnings': res['warnings'], 'option': opt['name']}
