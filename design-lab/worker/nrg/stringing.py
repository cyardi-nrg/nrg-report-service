# Design Lab worker v1.6.0 (2026-10-31) — stringing: strings, MPPTs, DC cable runs.
#
# Owner's rules:
#  * the inverter is picked per design (Design Lab → Stringing); the module's
#    electrical values come with it (defaults: Adani 625 Wp N-TOPCon, as on the
#    Jain CEIG set — "check the datasheet");
#  * strings of 20 preferred: on sheet roofs a string is 4 columns of a 5-row
#    landscape group, snaking up and down, so + and − both land on the walkway
#    side; strings never cross from one roof face to another;
#  * single runs vs Y-connectors: "work out what works best ... 4 sq mm single
#    lines × 2 runs vs 6 sq mm Y connector × 1 run" — both are measured and
#    priced, the cheaper one is used.
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


def _snake(face_mods: list, group_rows: int) -> list:
    """Order a face's panels so consecutive panels make a tidy string: group by row group, then column by column,
    up one column and down the next."""
    g = max(1, group_rows or 1)
    groups = {}
    for m in face_mods:
        groups.setdefault(m.row // g, []).append(m)
    out = []
    for gk in sorted(groups):
        cols = {}
        for m in groups[gk]:
            cols.setdefault(round(m.u, 1), []).append(m)
        for j, c in enumerate(sorted(cols)):
            out += sorted(cols[c], key=lambda m: m.row, reverse=bool(j % 2))
    return out


def _sizes(total: int, lim: dict, prefer: int) -> list | None:
    """String lengths for `total` panels: all `prefer` when it divides, else as even as the limits allow."""
    lo, hi = lim['nMin'], lim['nMax']
    if total < lo:
        return None
    if lo <= prefer <= hi and total % prefer == 0:
        return [prefer] * (total // prefer)
    k = max(1, round(total / min(max(prefer, lo), hi)))
    for kk in sorted({k, k + 1, k - 1, math.ceil(total / hi)}):
        if kk >= 1 and lo <= total // kk and math.ceil(total / kk) <= hi:
            base, extra = divmod(total, kk)
            return [base + 1] * extra + [base] * (kk - extra)
    return None


def _run(site, x, y, z) -> float:
    """One conductor from a string end to the inverter: along the roof (square to the building), down the wall,
    along the ground, plus the tails."""
    if not site.inverter:
        return 0.0
    return abs(x - site.inverter[0]) + abs(y - site.inverter[1]) + max(0.0, z) + TAIL_ARRAY + TAIL_INV


def design(site, option_arrays: list, inv: dict, mod: dict, rates: dict) -> dict:
    lim = limits(mod, inv)
    if lim['nMin'] > lim['nMax']:
        raise RuntimeError(f"No string length works with {inv.get('model')}: needs at least {lim['nMin']} panels for the MPPT range but at most "
                           f"{lim['nMax']} for the voltage limit — check the inverter / module values.")
    strings, warnings = [], []
    for a in option_arrays:
        mods = a['_mods']
        g = a['_pack'].get('group_rows') or (5 if a['orient'] == 'L' else 2)
        prefer = 2 * g * max(1, round(20 / (2 * g))) if a['_pack']['kind'] == 'sheet' else 20
        sizes = _sizes(len(mods), lim, prefer)
        if not sizes:
            warnings.append(f"{a['name']}: {len(mods)} panels can't make a string of {lim['nMin']}–{lim['nMax']} — move them to another roof or leave them out.")
            continue
        seq, i = _snake(mods, g), 0
        for n in sizes:
            chain = seq[i:i + n]
            i += n
            strings.append({'face': a['face'], 'faceName': a['name'], 'n': n, 'mods': chain, 'plus': chain[0], 'minus': chain[-1]})
    # MPPTs: fill face by face so a face's strings share MPPTs; never mix faces on one MPPT
    slots = [(k + 1, m + 1) for k in range(int(inv.get('count', 1))) for m in range(int(inv['mppts']))]
    per = lim['stringsPerMppt']
    si, slot_i, last_face, used = 0, 0, None, 0
    for st in strings:
        if slot_i >= len(slots):
            warnings.append(f"Not enough MPPT inputs for {len(strings)} strings — add an inverter or pick a bigger one.")
            st['mppt'] = None
            continue
        if last_face is not None and (st['face'] != last_face or used >= per):
            slot_i += 1
            used = 0
            if slot_i >= len(slots):
                warnings.append(f"Not enough MPPT inputs for {len(strings)} strings — add an inverter or pick a bigger one.")
                st['mppt'] = None
                continue
        st['inverter'], st['mppt'] = slots[slot_i]
        used += 1
        last_face = st['face']
        st['input'] = used
    for k, st in enumerate(strings):
        st['id'] = f'S{k + 1}'
        st['color'] = COLORS[k % len(COLORS)]
        st['plusM'] = round(_run(site, st['plus'].x, st['plus'].y, max(st['plus'].z)), 1)
        st['minusM'] = round(_run(site, st['minus'].x, st['minus'].y, max(st['minus'].z)), 1)

    # single runs (4 sq mm) vs Y-connectors (pairs on one MPPT joined on the roof, one 6 sq mm run)
    single_4 = sum(st['plusM'] + st['minusM'] for st in strings)
    by_mppt = {}
    for st in strings:
        if st.get('mppt'):
            by_mppt.setdefault((st['inverter'], st['mppt']), []).append(st)
    y_4, y_6, y_sets = 0.0, 0.0, 0
    for group in by_mppt.values():
        for p in range(0, len(group), 2):
            pair = group[p:p + 2]
            if len(pair) == 1:
                y_4 += pair[0]['plusM'] + pair[0]['minusM']
                continue
            a, b = pair
            for pole in ('plus', 'minus'):
                ma, mb = a[pole], b[pole]
                jx, jy, jz = (ma.x + mb.x) / 2, (ma.y + mb.y) / 2, max(max(ma.z), max(mb.z))
                y_4 += abs(ma.x - jx) + abs(ma.y - jy) + abs(mb.x - jx) + abs(mb.y - jy) + 2 * TAIL_ARRAY
                y_6 += _run(site, jx, jy, jz) - TAIL_ARRAY
            y_sets += 1
    cost_single = single_4 * rates['dc4']
    cost_y = y_4 * rates['dc4'] + y_6 * rates['dc6'] + y_sets * rates['ySet']
    use_y = y_sets > 0 and cost_y < cost_single
    checks = {
        'vocCold': f"Voc at {T_COLD:g} °C: {max((s['n'] for s in strings), default=0)} × {lim['vocCold']:.1f} = {max((s['n'] for s in strings), default=0) * lim['vocCold']:,.0f} V ≤ {inv['vmax']:,} V",
        'vmpRange': f"Vmp {T_HOT:g} °C … {T_COLD:g} °C: {min((s['n'] for s in strings), default=0) * lim['vmpHot']:,.0f} – {max((s['n'] for s in strings), default=0) * lim['vmpCold']:,.0f} V inside {inv['mpptMin']}–{inv['mpptMax']} V",
        'current': f"Up to {per} string(s) per MPPT: Imp {per * mod['imp']:.1f} A ≤ {inv['imaxPerMppt']} A"
                   + (f"; Isc {per * mod['isc']:.1f} A ≤ {inv['iscMaxPerMppt']} A" if inv.get('iscMaxPerMppt') else ''),
    }
    return {
        'strings': strings, 'limits': lim, 'checks': checks, 'warnings': warnings, 'stringsPerMppt': per,
        'compare': {'single': {'m4': round(single_4), 'cost': round(cost_single)},
                    'y': {'m4': round(y_4), 'm6': round(y_6), 'ySets': y_sets, 'cost': round(cost_y)},
                    'rates': rates, 'choice': 'Y-connectors' if use_y else 'single runs'},
        'useY': use_y,
    }
