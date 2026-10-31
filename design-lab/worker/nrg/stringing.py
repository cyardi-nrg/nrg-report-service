# Design Lab worker v1.7.0 (2026-10-31) — stringing: strings, MPPTs, DC cable runs.
# v1.7 (owner): Y pairs join where the SAME poles meet ("+ and + or − and − need to come close
#   to each other"); strings of 18–20 (19+19, 18+18 are fine); a mix of Y pairs and single strings —
#   each pair is made only where its Y is cheaper; strings on one MPPT are always the same length.
#
# Owner's rules:
#  * the inverter is picked per design (Design Lab → Stringing); the module's
#    electrical values come with it (defaults: Adani 625 Wp N-TOPCon, as on the
#    Jain CEIG set — "check the datasheet");
#  * strings of 18–20: on sheet roofs a 20-string is 4 columns of a 5-row
#    landscape group, snaking out and back, so both ends land on the walkway
#    side; strings stay inside their row group and never cross roof faces;
#  * single runs vs Y-connectors: "work out what works best ... 4 sq mm single
#    lines × 2 runs vs 6 sq mm Y connector × 1 run" — priced pair by pair.
# Electrical checks as on the Jain sheet: Voc at 5 °C × N ≤ inverter max DC V;
# Vmp at 70 °C … 5 °C × N inside the MPPT range; Imp / Isc per MPPT within limits.
import math

DEFAULT_MODULE = {'name': 'Adani 625 Wp N-TOPCon (typical — check the datasheet)', 'voc': 49.8, 'vmp': 41.6, 'isc': 15.96, 'imp': 15.03,
                  'tcVoc': -0.25, 'tcVmp': -0.29}
T_COLD, T_HOT = 5.0, 70.0          # °C: coldest morning, hot cell
TAIL_ARRAY, TAIL_INV = 1.0, 1.5    # m per conductor: slack at the array end / dressing into the inverter (Jain sheet)
COLORS = ['#e6194b', '#f58231', '#3cb44b', '#008080', '#4363d8', '#911eb4', '#f032e6', '#9a6324', '#800000', '#808000', '#000075', '#469990',
          '#dcbeff', '#aaffc3', '#ffd8b1', '#fabed4']


def limits(mod: dict, inv: dict) -> dict:
    voc_c = mod['voc'] * (1 + mod['tcVoc'] / 100 * (T_COLD - 25))
    vmp_c = mod['vmp'] * (1 + mod['tcVmp'] / 100 * (T_COLD - 25))
    vmp_h = mod['vmp'] * (1 + mod['tcVmp'] / 100 * (T_HOT - 25))
    n_max = min(math.floor(inv['vmax'] / voc_c), math.floor(inv['mpptMax'] / vmp_c))
    n_min = math.ceil(inv['mpptMin'] / vmp_h)
    per_mppt = min(int(inv['inputsPerMppt']), math.floor(inv['imaxPerMppt'] / mod['imp'] + 1e-9),
                   math.floor(inv.get('iscMaxPerMppt', 1e9) / mod['isc'] + 1e-9))
    return {'vocCold': voc_c, 'vmpCold': vmp_c, 'vmpHot': vmp_h, 'nMin': n_min, 'nMax': n_max, 'stringsPerMppt': max(1, per_mppt)}


BAND = (18, 20)   # owner: "not necessary that the string should be 20 + 20 only ... could be 19+19 or 18+18"


ADJ_M = 2.5       # m: a Y pair needs at least one pole's two ends this close ("ideally next to each other")


def _segments(face_mods: list, g: int) -> list:
    """One path over the face: row group by row group (a walkway between each), each walked column by column
    from its walkway row, alternate groups walked back the other way so the path turns at the roof end instead
    of jumping across the roof. Returns [[column, ...]] — columns ordered from the walkway row outwards."""
    groups = {}
    for m in face_mods:
        groups.setdefault(m.row // g, []).append(m)
    keys = sorted(groups)
    path = []
    for i, gk in enumerate(keys):
        # groups 0|1, 2|3 ... face the walkway between them: the ends go to that side
        walk_high = i % 2 == 0 and i + 1 < len(keys)
        cols = {}
        for m in groups[gk]:
            cols.setdefault(round(m.u, 1), []).append(m)
        order = sorted(cols, reverse=bool(i % 2))
        path += [sorted(cols[c], key=lambda m: m.row, reverse=walk_high) for c in order]
    return [path]


def _walk(cols: list, sizes: list) -> list:
    """Cut a segment into strings. Each string starts at the walkway end of what is left of its column and
    snakes column by column (out to the far row, back to the walkway row), so its ends land near the walkway."""
    left = [list(c) for c in cols]
    ci, out = 0, []
    for n in sizes:
        chain, at_walk = [], True
        while len(chain) < n and ci < len(left):
            col = left[ci]
            take = min(n - len(chain), len(col))
            if at_walk:                       # walkway side → outwards
                chain += col[:take]; del col[:take]
            else:                             # far side → back to the walkway
                chain += col[::-1][:take]; del col[len(col) - take:]
            if not col:                       # column finished: we are now at its other end
                ci += 1
                at_walk = not at_walk
        out.append(chain)
    return out


def _sizes(total: int, lim: dict) -> list | None:
    """String lengths for `total` panels: 18–20 each (fewest strings, as even as possible); outside that,
    whatever the inverter's voltage limits allow."""
    lo_e, hi_e = lim['nMin'], lim['nMax']
    if total < lo_e:
        return None
    p_hi = min(BAND[1], hi_e)
    p_lo = max(min(BAND[0], p_hi), lo_e)
    tries = [(p_lo, p_hi), (lo_e, hi_e)]
    for lo, hi in tries:
        k = math.ceil(total / hi)
        if k >= 1 and total >= k * lo:
            base, extra = divmod(total, k)
            return [base + 1] * extra + [base] * (k - extra)
    return None


def _pdist(a, b) -> float:
    return abs(a.x - b.x) + abs(a.y - b.y)


def _run(site, x, y, z) -> float:
    """One conductor from a string end to the inverter: along the roof (square to the building), down the wall,
    along the ground, plus the tails."""
    if not site.inverter:
        return 0.0
    return abs(x - site.inverter[0]) + abs(y - site.inverter[1]) + max(0.0, z) + TAIL_ARRAY + TAIL_INV


def _y_cost(site, pa, ma, pb, mb, rates):
    """A Y pair: 4 sq mm legs from each end to the joint (midway between the same-pole ends), one 6 sq mm run
    per pole from the joint to the inverter. Returns (m4, m6, cost)."""
    m4 = m6 = 0.0
    for ea, eb in ((pa, pb), (ma, mb)):
        jx, jy, jz = (ea.x + eb.x) / 2, (ea.y + eb.y) / 2, max(max(ea.z), max(eb.z))
        m4 += abs(ea.x - jx) + abs(ea.y - jy) + abs(eb.x - jx) + abs(eb.y - jy) + 2 * TAIL_ARRAY
        m6 += _run(site, jx, jy, jz) - TAIL_ARRAY
    return m4, m6, m4 * rates['dc4'] + m6 * rates['dc6'] + rates['ySet']


def design(site, option_arrays: list, inv: dict, mod: dict, rates: dict) -> dict:
    lim = limits(mod, inv)
    if lim['nMin'] > lim['nMax']:
        raise RuntimeError(f"No string length works with {inv.get('model')}: needs at least {lim['nMin']} panels for the MPPT range but at most "
                           f"{lim['nMax']} for the voltage limit — check the inverter / module values.")
    strings, warnings = [], []
    for a in option_arrays:
        g = a['_pack'].get('group_rows') or (5 if a['orient'] == 'L' else 2)
        for seg in _segments(a['_mods'], g):
            total = sum(len(c) for c in seg)
            sizes = _sizes(total, lim)
            if not sizes:
                warnings.append(f"{a['name']}: {total} panels can't make a string of {lim['nMin']}–{lim['nMax']} — move them to another roof or leave them out.")
                continue
            for chain in _walk(seg, sizes):
                strings.append({'face': a['face'], 'faceName': a['name'], 'n': len(chain), 'mods': chain, 'plus': chain[0], 'minus': chain[-1], 'pair': None})
    for st in strings:
        st['plusM'] = round(_run(site, st['plus'].x, st['plus'].y, max(st['plus'].z)), 1)
        st['minusM'] = round(_run(site, st['minus'].x, st['minus'].y, max(st['minus'].z)), 1)
    per = lim['stringsPerMppt']

    # Y pairs (owner): two strings of the SAME length on one face, joined where their same-pole ends meet —
    # "+ and + or − and − need to come close to each other". Each string's + end is chosen so that happens;
    # closest pairs first; a pair is made only where the Y is cheaper than the two strings' own runs.
    pairs = []
    if per >= 2 and site.inverter:
        cands = []
        for i, A in enumerate(strings):
            for j in range(i + 1, len(strings)):
                B = strings[j]
                if A['face'] != B['face'] or A['n'] != B['n']:
                    continue
                a0, a1, b0, b1 = A['mods'][0], A['mods'][-1], B['mods'][0], B['mods'][-1]
                # B's + end is chosen so the same poles meet; the pair needs one pole's ends side by side
                opts = [((b0, b1), _pdist(a0, b0), _pdist(a1, b1)), ((b1, b0), _pdist(a0, b1), _pdist(a1, b0))]
                (bp, bm), d1, d2 = min(opts, key=lambda o: (min(o[1], o[2]) > ADJ_M, o[1] + o[2]))
                if min(d1, d2) > ADJ_M:
                    continue
                m4, m6, cy = _y_cost(site, a0, a1, bp, bm, rates)
                single = 0.0
                for e in (a0, a1, bp, bm):
                    single += _run(site, e.x, e.y, max(e.z))
                cs = single * rates['dc4']
                if cy < cs:
                    cands.append((d1 + d2, i, j, bp, bm, m4, m6, cy, cs, min(d1, d2), max(d1, d2)))
        used = set()
        for d, i, j, bp, bm, m4, m6, cy, cs, near, far in sorted(cands, key=lambda c: c[0]):
            if i in used or j in used:
                continue
            used |= {i, j}
            A, B = strings[i], strings[j]
            A['plus'], A['minus'] = A['mods'][0], A['mods'][-1]
            B['plus'], B['minus'] = bp, bm
            for st in (B,):
                st['plusM'] = round(_run(site, st['plus'].x, st['plus'].y, max(st['plus'].z)), 1)
                st['minusM'] = round(_run(site, st['minus'].x, st['minus'].y, max(st['minus'].z)), 1)
            pairs.append({'a': i, 'b': j, 'nearM': round(near, 1), 'farM': round(far, 1), 'm4': m4, 'm6': m6, 'cost': cy, 'singleCost': cs})
    for k, pr in enumerate(sorted(pairs, key=lambda q: min(q['a'], q['b']))):
        pr['id'] = f'Y{k + 1}'
        strings[pr['a']]['pair'] = strings[pr['b']]['pair'] = pr['id']

    # MPPTs: a Y pair takes one input, a single string one input; every string on an MPPT has the same length
    # (parallel strings must match in voltage); a face's strings share MPPTs — faces are mixed only if inputs run out.
    units = []
    done = set()
    for i, st in enumerate(strings):
        if i in done:
            continue
        pr = next((q for q in pairs if i in (q['a'], q['b'])), None)
        idx = [pr['a'], pr['b']] if pr else [i]
        done |= set(idx)
        units.append({'idx': idx, 'face': st['face'], 'n': st['n']})
    slots = [(k + 1, m + 1) for k in range(int(inv.get('count', 1))) for m in range(int(inv['mppts']))]
    in_max = int(inv['inputsPerMppt'])

    def assign(mix_faces: bool):
        out, cur = [], None
        for u in sorted(units, key=lambda u: (u['face'], -u['n'], min(u['idx'])) if not mix_faces else (-u['n'], u['face'], min(u['idx']))):
            fits = cur and cur['n'] == u['n'] and (mix_faces or cur['face'] == u['face']) \
                and cur['strings'] + len(u['idx']) <= per and cur['inputs'] + 1 <= in_max
            if not fits:
                cur = {'n': u['n'], 'face': u['face'], 'strings': 0, 'inputs': 0, 'units': []}
                out.append(cur)
            cur['strings'] += len(u['idx']); cur['inputs'] += 1; cur['units'].append(u)
        return out
    mppts = assign(False)
    if len(mppts) > len(slots):
        mppts = assign(True)
        if len(mppts) <= len(slots):
            warnings.append('Some MPPTs take strings from two roof faces (same string length) — there are not enough MPPTs to keep faces apart.')
    if len(mppts) > len(slots):
        warnings.append(f"Not enough MPPTs: {len(mppts)} needed, {len(slots)} available — add an inverter or pick a bigger one.")
    for slot, mp in zip(slots, mppts):
        for k, u in enumerate(mp['units']):
            for i in u['idx']:
                strings[i]['inverter'], strings[i]['mppt'], strings[i]['input'] = slot[0], slot[1], k + 1
    for i, st in enumerate(strings):
        st.setdefault('mppt', None)
        st['id'] = f'S{i + 1}'
        st['color'] = COLORS[i % len(COLORS)]

    # cable: everything as single runs vs the chosen mix (Y pairs where they pay, single runs for the rest)
    single_4 = sum(st['plusM'] + st['minusM'] for st in strings)
    paired = {i for q in pairs for i in (q['a'], q['b'])}
    plan_4 = sum(strings[i]['plusM'] + strings[i]['minusM'] for i in range(len(strings)) if i not in paired) + sum(q['m4'] for q in pairs)
    plan_6 = sum(q['m6'] for q in pairs)
    cost_single = single_4 * rates['dc4']
    cost_plan = plan_4 * rates['dc4'] + plan_6 * rates['dc6'] + len(pairs) * rates['ySet']
    n_single = len(strings) - len(paired)
    lens = [s['n'] for s in strings]
    checks = {
        'vocCold': f"Voc at {T_COLD:g} °C: {max(lens, default=0)} × {lim['vocCold']:.1f} = {max(lens, default=0) * lim['vocCold']:,.0f} V ≤ {inv['vmax']:,} V",
        'vmpRange': f"Vmp {T_HOT:g} °C … {T_COLD:g} °C: {min(lens, default=0) * lim['vmpHot']:,.0f} – {max(lens, default=0) * lim['vmpCold']:,.0f} V inside {inv['mpptMin']}–{inv['mpptMax']} V",
        'current': f"Up to {per} string(s) per MPPT: Imp {per * mod['imp']:.1f} A ≤ {inv['imaxPerMppt']} A"
                   + (f"; Isc {per * mod['isc']:.1f} A ≤ {inv['iscMaxPerMppt']} A" if inv.get('iscMaxPerMppt') else ''),
    }
    choice = (f"{len(pairs)} Y pair(s)" + (f" + {n_single} single string(s)" if n_single else '')) if pairs else 'single runs'
    return {
        'strings': strings, 'pairs': [{k: v for k, v in q.items()} for q in pairs], 'limits': lim, 'checks': checks, 'warnings': warnings,
        'stringsPerMppt': per,
        'compare': {'single': {'m4': round(single_4), 'cost': round(cost_single)},
                    'y': {'m4': round(plan_4), 'm6': round(plan_6), 'ySets': len(pairs), 'singles': n_single, 'cost': round(cost_plan)},
                    'rates': rates, 'choice': choice},
        'useY': bool(pairs),
    }
