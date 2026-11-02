# Design Lab worker v1.14.0 (2026-11-02) — stage 'panels' (per quote / layout):
# v1.14.0 (owner: "start from scratch or upload basic 3D design … this gives you the layout as well as the panel
#   placement"): when the design has a Base design (handlers/base.py) read off the same picture as the roofs, the
#   panels are THOSE panels, table by table — not placed here. One option, "As in the base design"; the tables carry
#   their rows × panels and front leg to Structure, and Stringing / 3D / layouts use them unchanged.
# v1.11.0: DC cable estimate drops to the inverter's floor (Site questions), not a flat 8 m; each table carries
#   its front leg / low-edge height (the roof's structure height) for the Structure stage.
# v1.10.0: reads Site questions → Mounting. "Elevated structure" puts flat roofs on raised portrait tables of
#   3 + 2 rows (nrg/packer.py); GI tables are portrait only. Best generation breaks a tie in favour of the
#   bigger roof (fewer arrays) before distance, so equal roofs don't split the plant needlessly.
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
from nrg.inputs import roof_model, base_picture, panel_spec, placement
from nrg import generation as gen
from nrg.inputs import answers, _num

STRING = 20          # panels per string for the DC cable estimate (as at Pluga)


def _dist(site, m) -> float:
    if not site.inverter:
        return 0.0
    if site.inverter_z is None:
        return abs(m.x - site.inverter[0]) + abs(m.y - site.inverter[1]) + 8.0   # along the roof + ~8 m down the wall
    # along the roof, then down (or up) to the inverter's floor, + 2 m to dress in (v1.11.0)
    return abs(m.x - site.inverter[0]) + abs(m.y - site.inverter[1]) + abs(min(m.z) - site.inverter_z) + 2.0


def _blocks(face_pack: dict, mods: list) -> list:
    rows = {}
    for m in mods:
        rows.setdefault(m.row, 0)
        rows[m.row] += 1
    if not rows:
        return []
    if face_pack['kind'] == 'flat' or face_pack.get('base'):   # tables of 1–3 rows / the base design's own tables
        tr = max(1, face_pack.get('table_rows') or 2)
        tables = {}
        for r, n in rows.items():
            tables.setdefault(r // tr, []).append(n)
        fl = face_pack.get('front_leg')
        names = face_pack.get('table_names') or {}
        return [{'name': (f"{face_pack['name']} · {names[t]}" if t in names else f"{face_pack['name']} · table row {t + 1}"),
                 'rows': len(ns), 'cols': max(ns), **({'frontLegM': fl} if fl is not None else {})}
                for t, ns in sorted(tables.items())]
    n_rows = len(rows)
    return [{'name': face_pack['name'], 'rows': n_rows, 'cols': math.ceil(len(mods) / n_rows)}]


def plan(job) -> dict:
    """Everything the layout needs, worked out (shared with the 3D stage, which rebuilds the chosen option)."""
    model, roof_v = roof_model(job)
    spec = panel_spec(job.layout)
    site = sitemod.build(model, job.design.get('marks'))
    placement(job, site)                     # inverter / meter heights from their floors (Site questions)
    sun = sunmod.winter_sun()
    qv = job.latest_version('questions', None)
    mounting = (((qv or {}).get('data') or {}).get('mounting') or '').lower()
    elevated = mounting == 'elevated'
    base_v = base_design(job, model)
    if base_v:                               # v1.14.0: the panels as placed in the base design
        packs = base_packs(base_v['data'], site, elevated, answers(job))
        if not spec['target']:
            spec['target'] = sum(len(p['modules']) for p in packs)
    else:
        if not spec['target']:
            raise RuntimeError('This quote / option has no kWp or panel count.')
        packs = [packer.pack_face(site, f, spec['L'], spec['W'], sun, elevated=elevated) for f in site.faces]
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

    return {'model': model, 'roof_v': roof_v, 'spec': spec, 'site': site, 'sun': sun, 'packs': packs, 'capacity': capacity,
            'mounting': mounting or None, 'base': base_v}


def base_design(job, model: dict) -> dict | None:
    """The Base design version to use (latest approved, else latest) — only if it was read off the same picture the
    roofs are drawn on (else its panels would land in the wrong place) and the owner has not switched it off."""
    v = job.latest_version('base', None, approved_only=True) or job.latest_version('base', None)
    d = (v or {}).get('data') or {}
    if not v or not d.get('tables') or d.get('off'):
        return None
    if d.get('pictureDocumentId') != model.get('baseDocumentId'):
        return None
    return v


def base_packs(d: dict, site, elevated: bool, a: dict) -> list:
    """Packs (as packer.pack_face returns) built from the base design's panels: each panel goes on the roof face under
    it (the highest one, else the nearest), each base table keeps its own rows × panels. Rows are numbered
    table × 100 + row (north to south) so a table is one group for Structure and Stringing."""
    if not site.faces:
        raise RuntimeError('No roof is marked “use for solar” in Roof design.')
    from shapely.geometry import Point
    tilt = float(d.get('tiltDeg') or packer.TILT_FLAT)
    t = math.radians(tilt)
    st_answer = _num(a.get('structureM'))
    by_face: dict = {}
    names: dict = {}
    for ti, tb in enumerate(d['tables']):
        mods = []
        for p in tb['panels']:
            cs = [site.to_m(c) for c in p['corners']]
            cx, cy = sum(c[0] for c in cs) / 4, sum(c[1] for c in cs) / 4
            pt = Point(cx, cy)
            under = [f for f in site.faces if f.poly.contains(pt)]
            face = max(under, key=lambda f: f.height_at(cx, cy)) if under else min(site.faces, key=lambda f: f.poly.distance(pt))
            mods.append((face, cs, cx, cy))
        if not mods:
            continue
        a_rad = math.radians(float(tb.get('angleDeg') or 0))
        u = lambda x, y: x * math.cos(a_rad) + y * math.sin(a_rad)
        v = lambda x, y: -x * math.sin(a_rad) + y * math.cos(a_rad)
        depth = sorted(max(v(*c) for c in cs) - min(v(*c) for c in cs) for _, cs, _, _ in mods)[len(mods) // 2]
        vs = sorted(v(cx, cy) for _, _, cx, cy in mods)
        rows_v = [vs[0]]
        for val in vs[1:]:
            if val - rows_v[-1] > 0.5 * depth:
                rows_v.append(val)
        front = max(v(*c) for _, cs, _, _ in mods for c in cs)        # the table's south (front, lowest) edge
        for face, cs, cx, cy in mods:
            r = max(i for i, rv in enumerate(rows_v) if v(cx, cy) >= rv - 0.5 * depth)
            if face.kind == 'sheet':
                z = [face.height_at(*c) + packer.LIFT for c in cs]
            else:
                lift = face.structure if face.structure is not None else (st_answer if st_answer is not None else
                                                                          (packer.ELEV_CLEAR if elevated else max(packer.FRONT_LEG, face.parapet)))
                z = [face.height_at(*c) + lift + (front - v(*c)) * math.tan(t) for c in cs]
            orient = tb.get('orient') or 'P'
            pk = by_face.setdefault(face.key, {'face': face, 'mods': [], 'orients': []})
            pk['mods'].append(packer.Module(face.key, cx, cy, cs, z, orient, ti * 100 + r, u(cx, cy)))
            pk['orients'].append(orient)
            names.setdefault(face.key, {})[ti] = tb.get('name') or f'T{ti + 1}'
    packs = []
    for key, pk in by_face.items():
        f = pk['face']
        lift = f.structure if f.structure is not None else (st_answer if st_answer is not None else
                                                            (packer.ELEV_CLEAR if elevated else max(packer.FRONT_LEG, f.parapet)))
        tilt_f = math.degrees(math.atan(f.pitch)) if f.kind == 'sheet' else tilt
        packs.append({'key': key, 'roof_no': f.roof_no, 'name': f.name, 'kind': f.kind, 'facing': f.facing,
                      'tilt_deg': round(tilt_f, 1), 'orient': max(set(pk['orients']), key=pk['orients'].count),
                      'table_rows': 100, 'group_rows': 100, 'modules': pk['mods'], 'shaded_out': 0,
                      'yield': packer.kwh_per_kwp(tilt_f, f.down), 'usable_m2': round(f.poly.area, 1),
                      'mounting': 'flush' if f.kind == 'sheet' else ('elevated' if lift >= packer.ELEV_MIN else 'tables'),
                      'front_leg': None if f.kind == 'sheet' else round(lift, 2), 'base': True, 'table_names': names.get(key, {})})
    return packs


STRING_UNIT = 20         # owner: strings of 20 preferred ...
STRING_MIN = 18          # ... "it could be 19+19 or 18+18 also" (v1.7)


def _stringable(n: int) -> bool:
    """n panels split into strings of 18–20 each."""
    return n == 0 or (n >= STRING_MIN and math.ceil(n / STRING_UNIT) * STRING_MIN <= n)


def _take_stringable(p: dict, n: int) -> list:
    """Which n panels of a roof to use. Nearest the inverter first (p['modules'] is already in that order),
    but each row group gets a count that strings cleanly — whole strings of 20, else strings of 18–20 — so no
    string has to jump from one row group to another or leave stray panels behind (v1.8.1, owner's review of
    the Pluga stringing). Falls back to plain nearest-first if no such split exists."""
    mods = p['modules']
    if n >= len(mods):
        return list(mods)
    g = max(1, p.get('group_rows') or 1)
    bands = {}
    for m in mods:                                   # keeps the nearest-first order inside each band
        bands.setdefault(m.row // g, []).append(m)
    keys = sorted(bands, key=lambda b: mods.index(bands[b][0]))      # bands in the order they are reached
    rank = {b: i for i, b in enumerate(keys)}
    short = {b: len({m.row for m in bands[b]}) < g for b in keys}         # a part group (fewer rows than g)
    for ok in ((lambda k: k % STRING_UNIT == 0), _stringable):
        # DP over bands: counts per band (0 or stringable, ≤ capacity) summing to n; cost prefers nearer bands
        # filled first and fewer part-filled bands
        best = {0: (0.0, [])}
        for b in keys:
            cap = len(bands[b])
            opts = [0] + [k for k in range(STRING_MIN, cap + 1) if ok(k)]
            nxt = {}
            for tot, (cost, picks) in best.items():
                for k in opts:
                    t = tot + k
                    if t > n:
                        break
                    # full row groups (all g rows) first — a part group at a roof edge only if needed (owner: 5 rows,
                    # mirrored about the walkway, so top and bottom strings face each other)
                    c = cost + k * rank[b] * 0.01 + (1.0 if 0 < k < cap else 0.0) + (3.0 if k and short[b] else 0.0)
                    if t not in nxt or c < nxt[t][0]:
                        nxt[t] = (c, picks + [(b, k)])
            best = nxt
        if n in best:
            want = dict(best[n][1])
            take = [m for b in keys for m in bands[b][:want.get(b, 0)]]
            return take
    return list(mods[:n])


def option_arrays(P: dict, order: list, whole_strings: bool = True) -> tuple[list, list]:
    """Fill the quote's panels roof by roof in this order (whole columns from the inverter end). A roof that
    can't take all that is left takes whole strings of 20 — or, if 20s can't reach the quote's total, as many
    as split into strings of 18–20 — so every roof strings cleanly; if neither reaches the total, every
    panel is used instead (the Stringing stage then uses whatever lengths the inverter allows)."""
    target = P['spec']['target']
    counts = None
    if P.get('base'):
        whole_strings = False        # the base design's panels as the owner placed them — none dropped to make strings
    if whole_strings and target >= STRING_MIN:
        # first try whole strings of 20 on every part-filled roof, then strings of 18–20
        for ok in ((lambda k: k % STRING_UNIT == 0), _stringable):
            left, plan_counts = target, []
            for p in order:
                if left <= 0:
                    break
                cap = len(p['modules'])
                if cap >= left and _stringable(left):
                    n = left
                else:
                    n = next((k for k in range(min(cap, left), 0, -1) if ok(k) and (left - k == 0 or left - k >= STRING_MIN)), 0)
                plan_counts.append((p, n))
                left -= n
            if left == 0:
                counts = {id(p): n for p, n in plan_counts}
                break
        if counts is None:    # neither reaches the total — use every panel instead
            return option_arrays(P, order, whole_strings=False)
    left, arrays, mods_all = target, [], []
    for p in order:
        if left <= 0:
            break
        n = counts.get(id(p), 0) if counts is not None else left
        if n <= 0:
            continue
        take = _take_stringable(p, min(n, left))
        left -= len(take)
        mods_all += take
        arrays.append({'face': p['key'], 'name': p['name'], 'facing': p['facing'], 'tilt': p['tilt_deg'], 'orient': p['orient'],
                       'modules': len(take), 'capacity': len(p['modules']), 'kwp': round(len(take) * P['spec']['wp'] / 1000, 2),
                       'kwh': round(len(take) * P['spec']['wp'] / 1000 * p['yield']), 'blocks': _blocks(p, take), '_mods': take, '_pack': p})
    return arrays, mods_all


def orders(packs: list) -> dict:
    if packs and packs[0].get('base'):      # v1.14.0: one option — the base design's own layout
        return {'A': ('As in the base design', sorted(packs, key=lambda p: (-p['yield'], -len(p['modules']), p['avg_dist'])))}
    return {
        # yields within ~1 % count as equal (same tilt and facing): then the bigger roof first, then the nearer
        'A': ('Best generation first', sorted(packs, key=lambda p: (-round(p['yield'] / 15), -len(p['modules']), p['avg_dist']))),
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
    notes = [f"Recommended: {best['name']}" + (f" — {best['why']}." if best.get('why') else ' — most units a year.'),
             (f"Base design v{P['base']['version']}: {capacity} panels of {spec['wp']} Wp ({round(capacity * spec['wp'] / 1000, 1)} kWp) as placed there." if P.get('base') else
              f"Room on the roofs for {capacity} panels of {spec['wp']} Wp ({round(capacity * spec['wp'] / 1000, 1)} kWp) after setbacks, obstacles and shade."),
             gen_note,
             f"Roofs from Roof design v{roof_v['version']}{' (approved)' if roof_v.get('status') == 'approved' else ' (not yet approved)'}."]
    if not site.inverter:
        notes.append('Inverter not marked in Site & marks — DC cable not estimated.')
    for k, opt, mods_all in drawq:   # option drawings — after SAM, so they carry its units
        n = opt['modules']
        lines = [f"{a['face']}|{a['name']} — {a['modules']} panels ({a['orient'] == 'P' and 'portrait' or 'landscape'}, {a['tilt']}°), {a['kwp']} kWp, {a['kwh']:,} units/yr" for a in opt['arrays']]
        lines.append(f"Total {n} × {spec['wp']} Wp = {opt['kwp']} kWp · about {opt['annualKwh']:,} units a year"
                     + (f" · DC cable about {int(opt['dcCableM']):,} m" if opt['dcCableM'] else ''))
        lines.append(('Panels as placed in the base design (Base design v' + str(P['base']['version']) + ').' if P.get('base') else
                      'Shade check: 21 Dec, 9 am – 3 pm; a panel is left out if any corner is shaded.') + (f" {opt['note']}" if opt['note'] else ''))
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
        'summary': ("From the base design — " if P.get('base') else '') + f"{len(options)} option{'' if len(options) == 1 else 's'} for {spec['target']} panels. Recommended {best['name']}: {best['kwp']} kWp, about {best['annualKwh']:,} units a year."
                   + (f" Roofs hold {capacity} panels at most." if capacity < spec['target'] else ''),
        'options': options, 'recommended': best['name'], 'capacityModules': capacity, 'roofsVersion': roof_v['version'],
        'panel': spec, **({'baseVersion': P['base']['version']} if P.get('base') else {}),
    }
