# Design Lab worker v1.8.3 (2026-10-31) — stringing: strings, MPPTs, DC cable runs.
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
          '#c026d3', '#0e7490', '#b45309', '#4d7c0f', '#be123c', '#1d4ed8', '#7c2d12', '#15803d', '#6d28d9', '#a16207', '#0f766e', '#9f1239']


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


def _path(face_mods: list, g: int) -> list:
    """One unbroken snake over a face: row group by row group, column by column, up one column and down the
    next (never restarting), so every panel touches the next one. Each group starts on its walkway row; the
    next group is walked from whichever end is nearer to where the last one finished. Returns
    [(module, group_no, on_walkway_row)] in path order. (v1.8.1 — owner: no skipped panels, no stray panels.)"""
    groups = {}
    for m in face_mods:
        groups.setdefault(m.row // g, []).append(m)
    keys = sorted(groups)
    path, last = [], None
    for gi, gk in enumerate(keys):
        walk_high = gi % 2 == 0 and gi + 1 < len(keys)      # 0|1, 2|3 … face the walkway between them
        cols = {}
        for m in groups[gk]:
            cols.setdefault(round(m.u, 1), []).append(m)
        order = sorted(cols)
        if last is not None:                                   # start from the end nearer the previous group's last panel
            first = min(cols[order[0]], key=lambda m: _pdist(m, last))
            final = min(cols[order[-1]], key=lambda m: _pdist(m, last))
            if _pdist(final, last) < _pdist(first, last):
                order = order[::-1]
        for j, c in enumerate(order):
            col = sorted(cols[c], key=lambda m: m.row, reverse=walk_high)      # walkway row first
            seq = col if j % 2 == 0 else col[::-1]
            for k, m in enumerate(seq):
                path.append((m, gi, m is col[0]))
        last = path[-1][0]
    return path


def _cut(path: list, lim: dict) -> list | None:
    """Where to cut the snake into strings (lengths in order). Best cuts by cost: fewest strings, 20 panels
    each (18–19 allowed, outside 18–20 only if the inverter's limits force it), ends on the walkway row, and
    never a gap inside a string — a string may cross into the next row group only where the two meet."""
    N = len(path)
    p_hi = min(BAND[1], lim['nMax'])
    p_lo = max(min(BAND[0], p_hi), lim['nMin'])
    # strings of 18–20 only; the inverter's wider range only if 18–20 can't cover this roof
    for lo_e, hi_e in ((p_lo, p_hi), (lim['nMin'], lim['nMax'])):
        sizes = _cut_range(path, N, lo_e, hi_e, p_lo, p_hi)
        if sizes:
            return sizes
    return None


def _cut_range(path, N, lo_e, hi_e, p_lo, p_hi):
    if N < lo_e:
        return None
    step = [0.0] + [_pdist(path[i][0], path[i - 1][0]) for i in range(1, N)]
    adj = 2.7      # m: next panel along a row (landscape ≈ 2.4 m) or a column — anything further is a gap
    gap_pen = [0.0] * N
    for i in range(1, N):
        if step[i] > 25:
            gap_pen[i] = 1e6                                   # never: a 25 m+ jump inside a string
        elif step[i] > 8:
            gap_pen[i] = 400 + 20 * step[i]                    # only if nothing else works
        elif step[i] > adj:
            gap_pen[i] = 30 + 20 * (step[i] - adj) + (25 if path[i][1] != path[i - 1][1] else 0)
    cum = [0.0]
    for i in range(N):
        cum.append(cum[-1] + gap_pen[i])
    INF = float('inf')
    dp, back = [0.0] + [INF] * N, [0] * (N + 1)
    for end in range(lo_e, N + 1):
        for n in range(lo_e, min(hi_e, end) + 1):
            st = end - n
            if dp[st] == INF:
                continue
            c = 100.0
            c += 0 if n == p_hi else (6 * (p_hi - n) if p_lo <= n < p_hi else 60 + 12 * min(abs(n - p_lo), abs(n - p_hi)))
            c += cum[end] - cum[st + 1]                              # gaps inside the string (not the one before it)
            c += (0 if path[st][2] else 5) + (0 if path[end - 1][2] else 5)
            if dp[st] + c < dp[end]:
                dp[end], back[end] = dp[st] + c, n
    if dp[N] == INF or dp[N] >= 1e6:
        return None
    sizes, i = [], N
    while i > 0:
        sizes.append(back[i])
        i -= back[i]
    return sizes[::-1]


def _pdist(a, b) -> float:
    return abs(a.x - b.x) + abs(a.y - b.y)


def _run(site, x, y, z) -> float:
    """One conductor from a string end to the inverter: along the roof (square to the building), down the wall,
    along the ground, plus the tails."""
    if not site.inverter:
        return 0.0
    return abs(x - site.inverter[0]) + abs(y - site.inverter[1]) + max(0.0, z) + TAIL_ARRAY + TAIL_INV


DC_SIZES = [4, 6, 10, 16]     # sq mm, solar DC cable (EN 50618)
DC_VD_MAX = 3.0                # % — acceptance limit (owner: "DC cable 3% loss is ok")
DC_VD_TARGET = 2.0             # % — what each run is sized for (owner: "ideal would be below 2%") — each string's DC voltage drop, string end to inverter (owner: size by current, length AND drop)
RHO_CU = 0.0216                # Ω·mm²/m, copper at operating temperature


def rate(rates: dict, sq: int) -> float:
    """₹ per metre of conductor for a size (rates from the Design Lab; bigger sizes default ~ in proportion)."""
    return float(rates.get(f'dc{sq}') or {4: 40, 6: 60, 10: 95, 16: 150}.get(sq, 10 * sq))


def vd_pct(i: float, cond_m: float, sq: float, v: float) -> float:
    return i * RHO_CU * cond_m / sq / v * 100 if v else 0.0


def size_single(st: dict, mod: dict, rates: dict, vmax: float = DC_VD_MAX) -> tuple:
    """A string's own + and − runs: the smallest size (4 sq mm up) whose voltage drop is ≤ DC_VD_MAX."""
    cond = st['plusM'] + st['minusM']
    v = st['n'] * mod['vmp']
    sq = next((q for q in DC_SIZES if vd_pct(mod['imp'], cond, q, v) <= vmax), DC_SIZES[-1])
    return sq, cond, vd_pct(mod['imp'], cond, sq, v), cond * rate(rates, sq)


def size_y(m4: float, m6: float, n: int, mod: dict, rates: dict, vmax: float = DC_VD_MAX) -> tuple:
    """A Y pair: 4 sq mm legs to the joint (one string's current), the home run carries both strings — 6 sq mm
    up, the smallest whose total drop (leg + home run) is ≤ DC_VD_MAX."""
    v, i = n * mod['vmp'], mod['imp']
    leg = vd_pct(i, m4 / 2, 4, v)
    sq = next((q for q in DC_SIZES if q >= 6 and leg + vd_pct(2 * i, m6, q, v) <= vmax), DC_SIZES[-1])
    return sq, leg + vd_pct(2 * i, m6, sq, v), m4 * rate(rates, 4) + m6 * rate(rates, sq) + rates['ySet']


def _meet_edges(strings: list) -> dict:
    """Where string ends meet: i → [(end of i, j, end of j)] for ends within ADJ_M (same roof face)."""
    n = len(strings)
    edges = {i: [] for i in range(n)}
    for i in range(n):
        for j in range(i + 1, n):
            if strings[i]['face'] != strings[j]['face']:
                continue
            for ki, ei in enumerate((strings[i]['mods'][0], strings[i]['mods'][-1])):
                for kj, ej in enumerate((strings[j]['mods'][0], strings[j]['mods'][-1])):
                    if _pdist(ei, ej) <= ADJ_M:
                        edges[i].append((ki, j, kj))
                        edges[j].append((kj, i, ki))
    return edges


def _orient(strings: list, edges: dict, fixed: dict) -> tuple[list, int]:
    """Which end of each string is + (o[i] = 0: first panel of the snake, 1: last) so that, wherever two strings
    meet, the ends are the same colour. `fixed` holds the Y-pair strings (their + ends together). Returns
    (o, number of red-next-to-black meetings left)."""
    n = len(strings)
    o = [fixed.get(i) for i in range(n)]
    near = lambda i, e: _pdist(strings[i]['mods'][-e[0]], strings[e[1]]['mods'][-e[2]])

    def spread(start):
        queue = [start]
        while queue:
            i = queue.pop(0)
            for ki, j, kj in sorted(edges[i], key=lambda e: near(i, e)):
                if o[j] is None:
                    o[j] = kj if ki == o[i] else 1 - kj         # same colour as i's end here
                    queue.append(j)
    for i in range(n):
        if o[i] is not None:
            spread(i)
    for i in range(n):
        if o[i] is None:
            o[i] = min(edges[i], key=lambda e: near(i, e))[0] if edges[i] else 0     # red at its first meeting
            spread(i)
    clash_at = lambda i: sum(1 for ki, j, kj in edges[i] if (ki == o[i]) != (kj == o[j]))
    improved = True
    while improved:                                    # corners: flip free strings while it helps
        improved = False
        for i in range(n):
            if i in fixed or not edges[i]:
                continue
            before = clash_at(i)
            o[i] = 1 - o[i]
            if clash_at(i) < before:
                improved = True
            else:
                o[i] = 1 - o[i]
    clashes = sum(1 for i in range(n) for ki, j, kj in edges[i] if i < j and (ki == o[i]) != (kj == o[j]))
    return o, clashes


def _pair_fix(strings: list, i: int, j: int, bp, bm) -> dict:
    """The two strings of a Y pair, wired so their + (red) ends are the ones side by side (owner's rule)."""
    A, B = strings[i], strings[j]
    a0, a1 = A['mods'][0], A['mods'][-1]
    if _pdist(a0, bp) <= _pdist(a1, bm):
        pa, pb = a0, bp
    else:
        pa, pb = a1, bm
    return {i: 0 if pa is a0 else 1, j: 0 if pb is B['mods'][0] else 1}


def _apply_poles(site, strings: list, pairs: list) -> int:
    """Sets every string's + / − ends by the two rules and returns how many red-next-to-black meetings are left."""
    fixed = {k: v for q in pairs for k, v in q.get('_fix', {}).items()}
    o, clashes = _orient(strings, _meet_edges(strings), fixed)
    for i, st in enumerate(strings):
        a, b = st['mods'][0], st['mods'][-1]
        st['plus'], st['minus'] = (a, b) if o[i] == 0 else (b, a)
        st['plusM'] = round(_run(site, st['plus'].x, st['plus'].y, max(st['plus'].z)), 1)
        st['minusM'] = round(_run(site, st['minus'].x, st['minus'].y, max(st['minus'].z)), 1)
    for q in pairs:
        q.pop('_fix', None)
    return clashes


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
    vmax = float(rates.get('vdTargetDc') or DC_VD_TARGET)   # each run sized for this drop, % — set in the Design Lab (Stringing)
    if lim['nMin'] > lim['nMax']:
        raise RuntimeError(f"No string length works with {inv.get('model')}: needs at least {lim['nMin']} panels for the MPPT range but at most "
                           f"{lim['nMax']} for the voltage limit — check the inverter / module values.")
    strings, warnings = [], []
    for a in option_arrays:
        g = a['_pack'].get('group_rows') or (5 if a['orient'] == 'L' else 2)
        path = _path(a['_mods'], g)
        sizes = _cut(path, lim)
        if not sizes:
            warnings.append(f"{a['name']}: {len(path)} panels can't make a string of {lim['nMin']}–{lim['nMax']} — move them to another roof or leave them out.")
            continue
        i = 0
        for n in sizes:
            chain = [m for m, _, _ in path[i:i + n]]
            i += n
            strings.append({'face': a['face'], 'faceName': a['name'], 'n': n, 'mods': chain, 'plus': chain[0], 'minus': chain[-1], 'pair': None,
                            'maxStepM': round(max((_pdist(p, q) for p, q in zip(chain, chain[1:])), default=0), 2)})
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
                m4, m6, _ = _y_cost(site, a0, a1, bp, bm, rates)
                hsq, hvd, cy = size_y(m4, m6, A['n'], mod, rates, vmax)
                runs = lambda p_, m_: {'plusM': _run(site, p_.x, p_.y, max(p_.z)), 'minusM': _run(site, m_.x, m_.y, max(m_.z)), 'n': A['n']}
                cs = size_single(runs(a0, a1), mod, rates, vmax)[3] + size_single(runs(bp, bm), mod, rates, vmax)[3]
                if cy < cs:
                    cands.append((d1 + d2, i, j, bp, bm, m4, m6, cy, cs, min(d1, d2), max(d1, d2), hsq, hvd))
        # RULES (owner): in a Y pair the RED (+) ends are the ones side by side; and wherever two strings meet the
        # ends are the same colour. Along a row the meetings alternate red-red / black-black, so a Y pair can only
        # sit at a red meeting: a pair is kept only if every meeting can still be matched.
        edges = _meet_edges(strings)
        fixed, used = {}, set()
        _, base = _orient(strings, edges, fixed)
        for d, i, j, bp, bm, m4, m6, cy, cs, near, far, hsq, hvd in sorted(cands, key=lambda c: c[0]):
            if i in used or j in used:
                continue
            fx = _pair_fix(strings, i, j, bp, bm)
            trial = {**fixed, **fx}
            if _orient(strings, edges, trial)[1] > base:
                continue
            fixed = trial
            used |= {i, j}
            pairs.append({'a': i, 'b': j, 'nearM': round(near, 1), 'farM': round(far, 1), 'm4': m4, 'm6': m6, 'homeSq': hsq, 'vdPct': round(hvd, 2),
                          'cost': cy, 'singleCost': cs, '_fix': fx})
    pole_clashes = _apply_poles(site, strings, pairs)
    if pole_clashes:
        warnings.append(f'{pole_clashes} place(s) where a red (+) end meets a black (−) end could not be avoided — see the stringing drawing.')
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
    # each MPPT group goes to the inverter carrying the fewest strings so far (that still has a free MPPT),
    # biggest groups first, so all inverters end up about equally loaded (v1.8)
    n_inv, n_mppt = int(inv.get('count', 1)), int(inv['mppts'])
    load, used_m = [0] * n_inv, [0] * n_inv
    order = sorted(range(len(mppts)), key=lambda j: (-mppts[j]['strings'], j))
    placed = {}
    for j in order:
        free = [k for k in range(n_inv) if used_m[k] < n_mppt]
        if not free:
            break
        k = min(free, key=lambda k: (load[k], k))
        used_m[k] += 1
        load[k] += mppts[j]['strings']
        placed[j] = (k + 1, used_m[k])
    # number each inverter's MPPTs in the order of the roof (original group order), not by size
    for k in range(n_inv):
        mine = sorted(j for j, (kk, _) in placed.items() if kk == k + 1)
        for m, j in enumerate(mine):
            placed[j] = (k + 1, m + 1)
    for j, mp in enumerate(mppts):
        if j not in placed:
            continue
        for kin, u in enumerate(mp['units']):
            for i in u['idx']:
                strings[i]['inverter'], strings[i]['mppt'], strings[i]['input'] = placed[j][0], placed[j][1], kin + 1
    for i, st in enumerate(strings):
        st.setdefault('mppt', None)
        st['id'] = f'S{i + 1}'
        st['color'] = COLORS[i % len(COLORS)]

    # cable: everything as single runs vs the chosen mix (Y pairs where they pay, single runs for the rest)
    # every run sized by current AND voltage drop (≤ DC_VD_MAX), so the comparison uses the sizes really needed
    paired = {i for q in pairs for i in (q['a'], q['b'])}
    all_single, plan = {}, {}
    cost_single = cost_plan = 0.0
    for i, st in enumerate(strings):
        sq, cond, vd, c = size_single(st, mod, rates, vmax)
        all_single[sq] = all_single.get(sq, 0) + cond
        cost_single += c
        if i in paired:
            continue
        st['sq'], st['vdPct'] = sq, round(vd, 2)
        plan[sq] = plan.get(sq, 0) + cond
        cost_plan += c
    for q in pairs:
        for i in (q['a'], q['b']):
            strings[i]['sq'], strings[i]['vdPct'] = q['homeSq'], q['vdPct']
        plan[4] = plan.get(4, 0) + q['m4']
        plan[q['homeSq']] = plan.get(q['homeSq'], 0) + q['m6']
        cost_plan += q['cost']
    single_4 = sum(all_single.values())
    plan_4 = plan.get(4, 0)
    plan_6 = sum(v for k, v in plan.items() if k > 4)
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
        'compare': {'single': {'m4': round(single_4), 'bySize': {str(k): round(v) for k, v in sorted(all_single.items())}, 'cost': round(cost_single)},
                    'y': {'m4': round(plan_4), 'm6': round(plan_6), 'bySize': {str(k): round(v) for k, v in sorted(plan.items())},
                          'ySets': len(pairs), 'singles': n_single, 'cost': round(cost_plan)},
                    'vdMax': vmax, 'vdLimit': float(rates.get('vdMaxDc') or DC_VD_MAX),
                    'rates': rates, 'choice': choice},
        'useY': bool(pairs),
    }
