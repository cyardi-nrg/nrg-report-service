# Design Lab worker v1.5.0 (2026-10-31) — stage 'panels' (per quote / layout):
# fit this quote's panels onto the drawn roofs, three ways, and draw them.
#
#   Option A  Best generation first  — south faces, then east / west, then north
#   Option B  Nearest the inverter   — least DC cable
#   Option C  Biggest roofs first    — fewest separate arrays
# A partly-filled roof takes the panels nearest the inverter (as at Pluga).
# Each option: panels per roof, kWp, units a year, DC cable estimate, and
# the panel tables (rows × panels) the Structure stage starts from.
import math
import os

from nrg import site as sitemod
from nrg import sun as sunmod
from nrg import packer
from nrg import render
from nrg.inputs import roof_model, base_picture, panel_spec
from nrg import generation as gen

STRING = 20          # panels per string for the DC cable estimate (as at Pluga)


def _dist(site, m) -> float:
    if not site.inverter:
        return 0.0
    return abs(m.x - site.inverter[0]) + abs(m.y - site.inverter[1]) + 8.0   # along the roof + ~8 m down the wall


def _blocks(face_pack: dict, mods: list) -> list:
    rows = {}
    for m in mods:
        rows.setdefault(m.row, 0)
        rows[m.row] += 1
    if not rows:
        return []
    if face_pack['kind'] == 'flat':   # tables of 1–3 rows
        tr = max(1, face_pack.get('table_rows') or 2)
        tables = {}
        for r, n in rows.items():
            tables.setdefault(r // tr, []).append(n)
        return [{'name': f"{face_pack['name']} · table row {t + 1}", 'rows': len(ns), 'cols': max(ns)} for t, ns in sorted(tables.items())]
    n_rows = len(rows)
    return [{'name': face_pack['name'], 'rows': n_rows, 'cols': math.ceil(len(mods) / n_rows)}]


def plan(job) -> dict:
    """Everything the layout needs, worked out (shared with the 3D stage, which rebuilds the chosen option)."""
    model, roof_v = roof_model(job)
    spec = panel_spec(job.layout)
    if not spec['target']:
        raise RuntimeError('This quote / option has no kWp or panel count.')
    site = sitemod.build(model, job.design.get('marks'))
    sun = sunmod.winter_sun()
    packs = [packer.pack_face(site, f, spec['L'], spec['W'], sun) for f in site.faces]
    packs = [p for p in packs if p['modules']]
    if not packs:
        raise RuntimeError('No panel fits on the roofs marked “use for solar” (check setbacks and obstacles).')
    for p in packs:
        p['avg_dist'] = sum(_dist(site, m) for m in p['modules']) / len(p['modules'])
        # a part-filled roof takes WHOLE COLUMNS, starting with the column nearest the inverter (as at Pluga)
        cols = {}
        for m in p['modules']:
            cols.setdefault(round(m.u, 1), []).append(m)
        col_d = {c: min(_dist(site, m) for m in ms) for c, ms in cols.items()}
        p['modules'].sort(key=lambda m: (col_d[round(m.u, 1)], round(m.u, 1), m.row))
    capacity = sum(len(p['modules']) for p in packs)

    return {'model': model, 'roof_v': roof_v, 'spec': spec, 'site': site, 'sun': sun, 'packs': packs, 'capacity': capacity}


def option_arrays(P: dict, order: list) -> tuple[list, list]:
    """Fill the quote's panels roof by roof in this order (whole columns from the inverter end)."""
    left, arrays, mods_all = P['spec']['target'], [], []
    for p in order:
        if left <= 0:
            break
        take = p['modules'][:left]
        left -= len(take)
        mods_all += take
        arrays.append({'face': p['key'], 'name': p['name'], 'facing': p['facing'], 'tilt': p['tilt_deg'], 'orient': p['orient'],
                       'modules': len(take), 'capacity': len(p['modules']), 'kwp': round(len(take) * P['spec']['wp'] / 1000, 2),
                       'kwh': round(len(take) * P['spec']['wp'] / 1000 * p['yield']), 'blocks': _blocks(p, take), '_mods': take, '_pack': p})
    return arrays, mods_all


def orders(packs: list) -> dict:
    return {
        'A': ('Best generation first', sorted(packs, key=lambda p: (-p['yield'], p['avg_dist']))),
        'B': ('Nearest the inverter (least DC cable)', sorted(packs, key=lambda p: (p['avg_dist'], -p['yield']))),
        'C': ('Biggest roofs first (fewest arrays)', sorted(packs, key=lambda p: (-len(p['modules']), -p['yield']))),
    }


def run(job) -> dict:
    P = plan(job)
    model, roof_v, spec, site, packs, capacity = P['model'], P['roof_v'], P['spec'], P['site'], P['packs'], P['capacity']
    options, seen, drawq = [], {}, []
    base = base_picture(job, model)
    for k, (title, order) in orders(packs).items():
        arrays, mods_all = option_arrays(P, order)
        n = len(mods_all)
        dc = sum(a['modules'] / STRING * 2 * (sum(_dist(site, m) for m in a['_mods']) / max(1, a['modules'])) for a in arrays)
        sig = tuple(sorted((round(m.x, 2), round(m.y, 2)) for m in mods_all))
        opt = {'name': f'Option {k} · {title}', 'kwp': round(n * spec['wp'] / 1000, 2), 'modules': n,
               'annualKwh': sum(a['kwh'] for a in arrays), 'dcCableM': round(dc, -1) if site.inverter else None,
               # the Structure stage needs one: the orientation most of the panels are in (per roof it is in 'arrays')
               'orientation': 'portrait' if sum(a['modules'] for a in arrays if a['orient'] == 'P') * 2 >= n else 'landscape',
               'blocks': [b for a in arrays for b in a['blocks']],
               'arrays': [{kk: v for kk, v in a.items() if not kk.startswith('_')} for a in arrays],
               'modulesXY': [[round(m.x, 2), round(m.y, 2), m.orient, m.face] for m in mods_all],
               'note': (f"Only {n} of {spec['target']} panels fit — {spec['target'] - n} short." if n < spec['target'] else None)}
        if sig in seen:
            opt['note'] = ((opt['note'] or '') + f" Same panels as {seen[sig]}.").strip()
        seen.setdefault(sig, opt['name'].split(' · ')[0])
        options.append(opt)
        drawq.append((k, opt, mods_all))

    # Expected generation, month by month — NREL SAM (PySAM) on a PVGIS typical year for the site.
    # Each roof face of each option is its own array (kWp, tilt, direction, flush or on tables).
    # If the weather can't be fetched (no internet), the options keep the simple per-kWp estimate.
    gen_note = None
    try:
        lat, lon, where = gen.site_location(job.project, job.design.get('marks'))
        resource = gen.tmy(lat, lon)
        for o in options:
            arrays_in = [{'name': a['name'], 'kwp': a['kwp'], 'tilt': a['tilt'], 'facing': a['facing'],
                          'mount': 'rack' if any(p['key'] == a['face'] and p['kind'] == 'flat' for p in packs) else 'roof'}
                         for a in o['arrays']]
            g = gen.simulate(arrays_in, resource)
            g['weather'] = f'PVGIS typical year at {lat:.3f}, {lon:.3f} ({where})'
            o['estimateKwh'] = o['annualKwh']
            o['annualKwh'], o['monthlyKwh'], o['kwhPerKwp'], o['pr'] = g['annualKwh'], g['monthlyKwh'], g['kwhPerKwp'], g['pr']
            o['generation'] = g
            for a, ga in zip(o['arrays'], g['arrays']):
                a['kwh'] = ga['annualKwh']
        gen_note = f"Units a year: NREL SAM (PVWatts v8) hour by hour on a PVGIS typical year — {where}."
    except Exception as e:  # keep going with the estimate; say so on the drawings
        gen_note = f"Units a year are estimates (SAM generation not run: {str(e)[:120]})."

    # Recommend the most units a year — unless another option gives almost as much (within 1.5 %) for
    # clearly less DC cable (15 % or more): the owner chose "closer to the inverters" at Pluga for that reason.
    full = [o for o in options if o['modules'] >= spec['target']] or options
    best = max(full, key=lambda o: (o['annualKwh'], -(o['dcCableM'] or 0)))
    if best['dcCableM']:
        cheaper = [o for o in full if o['dcCableM'] and o['annualKwh'] >= 0.985 * best['annualKwh'] and o['dcCableM'] <= 0.85 * best['dcCableM']]
        if cheaper:
            alt = min(cheaper, key=lambda o: o['dcCableM'])
            alt['why'] = (f"{round(100 * (1 - alt['annualKwh'] / best['annualKwh']), 1)} % fewer units a year than {best['name'].split(' · ')[0]} "
                          f"but {int(best['dcCableM'] - alt['dcCableM']):,} m less DC cable")
            best = alt
    rows = [[o['name'].split(' · ')[0], o['name'].split(' · ')[1], o['modules'], o['kwp'], f"{o['annualKwh']:,}", f"{int(o['dcCableM']):,} m" if o['dcCableM'] else '—',
             ' + '.join(f"{a['face']} {a['modules']}" for a in o['arrays'])] for o in options]
    notes = [f"Recommended: {best['name']}" + (f" — {best['why']}." if best.get('why') else ' — most units a year.'), f"Room on the roofs for {capacity} panels of {spec['wp']} Wp ({round(capacity * spec['wp'] / 1000, 1)} kWp) after setbacks, obstacles and shade.",
             gen_note,
             f"Roofs from Roof design v{roof_v['version']}{' (approved)' if roof_v.get('status') == 'approved' else ' (not yet approved)'}."]
    if not site.inverter:
        notes.append('Inverter not marked in Site & marks — DC cable not estimated.')
    for k, opt, mods_all in drawq:   # option drawings — after SAM, so they carry its units
        n = opt['modules']
        lines = [f"{a['face']}|{a['name']} — {a['modules']} panels ({a['orient'] == 'P' and 'portrait' or 'landscape'}, {a['tilt']}°), {a['kwp']} kWp, {a['kwh']:,} units/yr" for a in opt['arrays']]
        lines.append(f"Total {n} × {spec['wp']} Wp = {opt['kwp']} kWp · about {opt['annualKwh']:,} units a year"
                     + (f" · DC cable about {int(opt['dcCableM']):,} m" if opt['dcCableM'] else ''))
        lines.append('Shade check: 21 Dec, 9 am – 3 pm; a panel is left out if any corner is shaded.' + (f" {opt['note']}" if opt['note'] else ''))
        out = os.path.join(job.workdir, f'Option-{k}.png')
        render.draw_layout(site, base, [a['face'] for a in opt['arrays']], mods_all, f"{opt['name']} — {opt['kwp']} kWp", lines, out)
        job.file_output(out, 'panel_layout_drawing', title=f'Option {k}')

    for o in options:   # month-wise generation chart for each option
        if o.get('generation'):
            k = o['name'].split(' · ')[0]
            cp = os.path.join(job.workdir, f'{k} generation.png')
            gen.chart(o['generation'], f"{job.customer} — {o['kwp']} kWp: expected generation month by month",
                      f"{o['name']} · {o['modules']} × {spec['wp']} Wp", cp)
            job.file_output(cp, 'design_report', title=f'{k} — expected generation (month-wise)')
    out = os.path.join(job.workdir, 'Options-compared.png')
    render.draw_table(f"{job.customer} — {spec['target']} × {spec['wp']} Wp: options compared", ['', 'Option', 'Panels', 'kWp', 'Units / yr', 'DC cable', 'Panels per roof'], rows, notes, out)
    job.file_output(out, 'panel_layout_drawing', title='Options compared')

    for o in options:
        o.pop('_', None)
    return {
        'summary': f"{len(options)} options for {spec['target']} panels. Recommended {best['name']}: {best['kwp']} kWp, about {best['annualKwh']:,} units a year."
                   + (f" Roofs hold {capacity} panels at most." if capacity < spec['target'] else ''),
        'options': options, 'recommended': best['name'], 'capacityModules': capacity, 'roofsVersion': roof_v['version'],
        'panel': spec,
    }
