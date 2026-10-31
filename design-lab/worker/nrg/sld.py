# Design Lab worker v1.8.1 (2026-10-31) — the single line diagram (SLD), made general from the
# owner-approved Jain Granite SLD (stringing/ceig/generate_ceig_drawings.py v7, sheet 01).
#
# Everything on the sheet comes from the design:
#   * strings, MPPTs, inputs and Y pairs  — the Stringing stage (nrg/stringing.py result)
#   * inverter + module electrical values — picked per design in the Design Lab (Stringing)
#   * AC cable length                     — the Walkway, earthing & tray stage (inverter → meter)
# Sizing (marked * / ** on the sheet where it is an estimate to verify):
#   * inverter AC current = AC kW / (√3 × 400 V) unless the inverter's own max AC current is given
#   * breaker ≥ 1.25 × current (next standard rating); contactor = breaker
#   * AC cable: Al XLPE armoured 3.5C, catalogue rating in air × 0.8 (grouping / ambient) ≥ 1.25 × current
#     — the same ladder that gave Jain its 95 sq mm for an 80 kW inverter
#   * v1.8.1 (owner): cable size = current, length AND voltage drop — AC cables are made bigger (or doubled)
#     until inverter → LT panel drop ≤ the allowed AC drop; DC runs come sized from the Stringing stage
#   * string fuses only when > 2 strings share an MPPT
import math

from nrg.ceigkit import (T, TL, R, L, C, table, sym_module, sym_inverter, sym_earth, sym_breaker, sym_contactor, sym_spd,
                         sym_meter, sym_lamp, sym_cable, legend_block, system_block, title_block, page, TB_X0)

AL_3_5C = [(25, 99), (35, 120), (50, 145), (70, 178), (95, 216), (120, 248), (150, 280), (185, 319), (240, 374), (300, 426)]  # sq mm, A in air
BREAKERS = [16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3200]
DC_MCB = [16, 20, 25, 32, 40, 50, 63]
FUSES = [10, 12, 15, 16, 20, 25, 30, 32]
DC_AMPS = {4: 55, 6: 70, 10: 98, 16: 132}   # EN 50618 solar cable, in air (catalogue)
DERATE = 0.8
RHO_AL, RHO_CU = 0.034, 0.0216      # Ω·mm²/m at operating temperature
RED = '#d62828'


def _next(ladder, need):
    return next((v for v in ladder if v >= need), ladder[-1])


def ac_cable(design_a: float, max_runs: int = 6) -> tuple[int, int, int]:
    """(runs, sq mm, catalogue amps per run) for a design current."""
    for runs in range(1, max_runs + 1):
        need = design_a / runs / DERATE
        hit = next(((s, a) for s, a in AL_3_5C if a >= need), None)
        if hit:
            return runs, hit[0], hit[1]
    return max_runs, AL_3_5C[-1][0], AL_3_5C[-1][1]


def sizing(d: dict) -> dict:
    inv, mod, strings = d['inverter'], d['module'], d['strings']
    n_inv = int(inv.get('count') or 1)
    i_inv = float(inv.get('iacMax') or 0) or inv['acKw'] * 1000 / (math.sqrt(3) * 400)
    i_inv_est = not inv.get('iacMax')
    br_inv = _next(BREAKERS, 1.25 * i_inv)
    i_tot = n_inv * i_inv
    br_main = _next(BREAKERS, 1.25 * i_tot)
    l_inv_acdb = 3.0
    l_feeder = float(d.get('acCableM') or 0) / max(1, n_inv) or 20.0
    vd = lambda i, l, a, runs: math.sqrt(3) * i * l * RHO_AL / (a * runs) / 415 * 100
    vmax_ac = float((d.get('rates') or {}).get('vdTargetAc') or 2.0)      # size for < 2 %, 3 % the limit (owner)
    # sized by current first (1.25 × I, catalogue × 0.8), then made bigger until the drop from the inverter to
    # the LT panel is ≤ the allowed AC drop — cheapest (least copper-equivalent) combination wins (owner: current,
    # length AND voltage drop decide the size). Fewest parallel runs first (each run is glands, lugs, labour),
    # then the smallest size
    def options(design_a):
        out = []
        for runs in range(1, 7):
            for sq, amps in AL_3_5C:
                if amps * DERATE * runs >= design_a:
                    out.append((runs, sq, amps))
        return out
    best = None
    for ri, si, ai in options(1.25 * i_inv):
        for rm, sm, am in options(1.25 * i_tot):
            drop = vd(i_inv, l_inv_acdb, si, ri) + vd(i_tot, l_feeder, sm, rm)
            if drop > vmax_ac:
                continue
            cost = (rm + ri, rm, ri, sm, si)          # fewest parallel runs first, then the smallest size
            if best is None or cost < best[0]:
                best = (cost, ri, si, ai, rm, sm, am, drop)
    if best is None:
        run_i, sq_i, amp_i = ac_cable(1.25 * i_inv)
        run_m, sq_m, amp_m = ac_cable(1.25 * i_tot)
        vd_ac = vd(i_inv, l_inv_acdb, sq_i, run_i) + vd(i_tot, l_feeder, sq_m, run_m)
    else:
        _, run_i, sq_i, amp_i, run_m, sq_m, amp_m, vd_ac = best
    by_current = ac_cable(1.25 * i_tot)
    upsized = (run_m, sq_m) != by_current[:2]
    # DC: each run already sized by the Stringing stage for current, length and drop (vdPct per string)
    drops = [float(s_.get('vdPct') or 0) for s_ in strings]
    dc_sizes = sorted({int(s_.get('sq') or 4) for s_ in strings if not s_.get('pair')})
    y_sizes = sorted({int(p.get('homeSq') or 6) for p in d.get('pairs', [])})
    per_mppt = {}
    for s in strings:
        if s.get('mppt'):
            per_mppt[(s['inverter'], s['mppt'])] = per_mppt.get((s['inverter'], s['mppt']), 0) + 1
    max_par = max(per_mppt.values(), default=1)
    fuse = _next(FUSES, 1.5 * mod['isc']) if max_par > 2 else None
    return {'n_inv': n_inv, 'i_inv': i_inv, 'i_inv_est': i_inv_est, 'br_inv': br_inv, 'run_i': run_i, 'sq_i': sq_i, 'amp_i': amp_i,
            'i_tot': i_tot, 'br_main': br_main, 'main_kind': 'ACB' if br_main > 630 else 'MCCB', 'run_m': run_m, 'sq_m': sq_m, 'amp_m': amp_m,
            'l_inv_acdb': l_inv_acdb, 'l_feeder': l_feeder, 'feeder_est': not d.get('acCableM'), 'vd_ac': vd_ac,
            'vd_dc': (min(drops, default=0), max(drops, default=0)), 'max_par': max_par, 'fuse': fuse,
            'mcb_single': _next(DC_MCB, 1.25 * mod['isc']), 'mcb_y': _next(DC_MCB, 2 * 1.25 * mod['isc']),
            'vmax_ac': vmax_ac, 'ac_upsized': upsized, 'dc_sizes': dc_sizes or [4], 'y_sizes': y_sizes,
            'vmax_dc': float((d.get('rates') or {}).get('vdTargetDc') or 2.0), 'lim_dc': float((d.get('rates') or {}).get('vdMaxDc') or 3.0),
            'lim_ac': float((d.get('rates') or {}).get('vdMaxAc') or 3.0)}


def _cable_txt(runs, sq):
    return f"1.1 KV, {runs}R X 3.5C X {sq} SQ.MM"


def _inputs(d: dict) -> dict:
    """(inverter, mppt) → [(input, [string, ...])] in input order; a Y pair is one input with two strings."""
    out = {}
    for s in d['strings']:
        if not s.get('mppt'):
            continue
        out.setdefault((s['inverter'], s['mppt']), {}).setdefault(s['input'], []).append(s)
    return {k: sorted(v.items()) for k, v in out.items()}


def sheet_sld(d: dict) -> str:
    """d: info, inverter, module, strings, pairs, kwp, modules, acCableM, system (rows), faces"""
    inv, mod, info = d['inverter'], d['module'], d['info']
    z = sizing(d)
    n_inv = z['n_inv']
    model = inv.get('model', 'INVERTER')
    o = []
    cx, gx = 720, 920

    # ---- grid / net meter / client LT panel
    o.append(L(gx, 62, gx, 200, RED, 1.6))
    o.append(f'<polygon points="{gx},52 {gx-6},64 {gx+6},64" fill="{RED}"/>')
    o.append(T(gx, 46, 'TO GRID (DISCOM, 415 V, 3Ø, 50 Hz)', 9, 'middle', 'bold'))
    o.append(R(gx - 16, 88, 32, 32, fill='#fff', sw=1.2) + C(gx, 104, 11, sw=1.2))
    o.append(TL(gx - 22, 100, ['NET METER', '(BI-DIRECTIONAL, BY DISCOM)'], 7.5, anchor='end'))
    o.append(R(470, 140, 520, 190, dash='6,4', sw=1))
    o.append(T(476, 153, 'CLIENT LT PANEL (EXISTING)', 8.5, 'start', 'bold'))
    o.append(sym_breaker(gx, 170, box=True))
    o.append(TL(gx + 16, 166, ['EXISTING MAIN', 'BREAKER'], 7))
    o.append(L(510, 200, 960, 200, '#000', 4))
    o.append(T(512, 194, '415 V, TPN BUS BAR (EXISTING)', 7.5))
    for lx in (540, 600):
        o.append(L(lx, 200, lx, 296, RED, 1.2) + sym_breaker(lx, 240) + f'<polygon points="{lx},306 {lx-5},296 {lx+5},296" fill="#000"/>')
        o.append(T(lx, 320, 'LOAD', 7.5, 'middle'))
    o.append(T(570, 275, 'EXISTING', 6.5, 'middle') + T(570, 284, 'LOADS', 6.5, 'middle'))
    o.append(L(cx, 200, cx, 380, RED, 1.6))
    o.append(sym_breaker(cx, 252, box=True))
    o.append(TL(cx + 18, 242, [f"{z['br_main']} A, 415 V, 4P {z['main_kind']}", 'O/C, S/C  (SOLAR FEEDER – NEW)', 'Icu ≥ FAULT LEVEL AT LT PANEL *'], 7.5))

    # ---- solar generation meter + feeder cable
    o.append(R(cx - 80, 352, 160, 56, sw=1, stroke='#1f3bb8'))
    o.append(sym_meter(cx, 380, 30))
    o.append(T(cx + 78, 362, 'SOLAR METER', 7.5, 'end', 'bold'))
    o.append(T(cx - 76, 404, 'GENERATION METER (AS PER DISCOM/GEDA)', 6, 'start'))
    o.append(L(cx, 408, cx, 500, RED, 1.6))
    o.append(sym_cable(cx - 28, cx + 28, 450))
    o.append(TL(cx + 36, 438, [_cable_txt(z['run_m'], z['sq_m']), 'AL. XLPE INSULATED, ARMOURED CABLE',
                               f"(CABLE LENGTH : ≈ {z['l_feeder']:.0f} M *)"], 7.5))

    # ---- ACDB: outgoing chain, then a bus with one incomer per inverter
    o.append(R(470, 500, 540, 262, dash='6,4', sw=1, stroke='#c026d3'))
    o.append(R(890, 500, 120, 26, sw=1, stroke='#c026d3'))
    o.append(T(950, 512, 'ACDB', 9, 'middle', 'bold'))
    o.append(T(950, 522, f'OUTDOOR TYPE {n_inv} IN / 1 OUT', 6, 'middle'))
    o.append(L(cx, 500, cx, 690, RED, 1.6))
    o.append(L(cx, 540, cx - 52, 540) + sym_spd(cx - 62, 540) + L(cx - 71, 540, cx - 90, 540) + sym_earth(cx - 90, 540, 0.7))
    o.append(TL(cx - 146, 562, ['AC SPD, 3Ø + N', 'Uc 320 V, 40 kA', 'TYPE : 2'], 7))
    for i, (c, lab) in enumerate((('#22c55e', 'ON'), ('#ef4444', 'OFF'))):
        o.append(sym_lamp(cx + 30 + i * 22, 548, c) + T(cx + 30 + i * 22, 566, lab, 6.5, 'middle'))
    for i, (c, lab) in enumerate((('#ef4444', 'R'), ('#facc15', 'Y'), ('#2563eb', 'B'))):
        o.append(sym_lamp(cx + 92 + i * 22, 548, c) + T(cx + 92 + i * 22, 566, lab, 6.5, 'middle'))
    o.append(sym_contactor(cx, 598) + TL(cx + 14, 596, ['CONTACTOR', f"{z['br_main']} A, 4P"], 7))
    o.append(R(cx + 40, 616, 34, 16, sw=1) + T(cx + 57, 628, 'NVR', 7.5, 'middle', 'bold') + L(cx + 6, 624, cx + 40, 624, dash='2,2'))
    o.append(sym_breaker(cx, 656, box=True) + TL(cx + 18, 650, [f"{z['br_main']} A, 415 V", f"4P {z['main_kind']} (OUTGOING)"], 7))
    o.append(L(990, 640, 1004, 640) + sym_earth(1004, 640, 0.8) + T(960, 672, 'EARTHING (EP-2)', 6.5))

    # ---- inverters across the bottom band
    x_a, x_b = 44, 1250
    gap = 18
    inv_w = (x_b - x_a - gap * (n_inv - 1)) / n_inv
    inv_x = [x_a + k * (inv_w + gap) for k in range(n_inv)]
    bus_l, bus_r = min(cx, inv_x[0] + inv_w / 2), max(cx, inv_x[-1] + inv_w / 2)
    o.append(L(max(476, bus_l), 690, min(1004, bus_r), 690, '#000', 3))
    o.append(T(max(478, bus_l) + 2, 685, '415 V BUS', 6.5))
    inputs = _inputs(d)
    iy0, iy1 = 800, 860
    dy0, dy1 = 940, 990
    mppts, per_in = int(inv['mppts']), int(inv['inputsPerMppt'])
    col_w = inv_w / (mppts * per_in)
    compact = col_w < 13
    for k in range(n_inv):
        x0 = inv_x[k]
        xc = x0 + inv_w / 2
        # incomer breaker inside the ACDB, then the cable down to the inverter
        bx = min(max(xc, 490), 990)
        o.append(L(bx, 690, bx, 762, RED, 1.4))
        o.append(f'<g transform="translate({bx} 728) scale(0.8) translate({-bx} -728)">' + sym_breaker(bx, 728, box=True) + '</g>')
        o.append(PL_([(bx, 762), (bx, 774), (xc, 774), (xc, iy0)], RED, 1.4))
        if k == 0:
            o.append(T(bx + 12, 730, f"{z['br_inv']} A, 4P MCCB (EACH INVERTER)", 6.5))
            o.append(TL(xc + 8 if n_inv > 1 else xc + 36, 786, [f"{_cable_txt(z['run_i'], z['sq_i'])} AL. XLPE ARMOURED", f"(≈ {z['l_inv_acdb']:.0f} M *, EACH INVERTER TO ACDB)"], 6.5))
        o.append(T(x0, iy0 - 4, f"INV-{k+1} – {inv['acKw']:g} kW {model}", 8.5 if inv_w > 200 else 7, weight='bold'))
        o.append(R(x0, iy0, inv_w, iy1 - iy0, sw=1.3))
        o.append(L(x0, iy1, x0 + inv_w, iy0, sw=0.9))
        o.append(f'<path d="M {x0+inv_w-60} {iy0+20} q 8 -12 16 0 t 16 0" stroke="#000" fill="none" stroke-width="1.2"/>')
        o.append(L(x0 + 14, iy1 - 18, x0 + 50, iy1 - 18, sw=1.2) + L(x0 + 14, iy1 - 10, x0 + 50, iy1 - 10, sw=1.2, dash='6,4'))
        sec = inv_w / mppts
        for m in range(mppts):
            sx = x0 + m * sec
            o.append(R(sx, iy1, sec, 16, sw=0.7) + T(sx + sec / 2, iy1 + 11, f'MPPT {m+1}' if sec > 46 else f'M{m+1}', 7 if sec > 46 else 6, 'middle', 'bold'))
            ins = dict(inputs.get((k + 1, m + 1), []))
            if compact:
                txt = [(f"{ins[i][0]['pair']} (A+B)" if len(ins[i]) > 1 else ins[i][0]['id']) for i in sorted(ins)]
                o.append(TL(sx + 3, iy1 + 30, txt or ['—'], 6.2, lh=8))
                continue
            for i in range(per_in):
                px = sx + (i + 0.5) * sec / per_in
                used = (i + 1) in ins
                o.append(R(sx + i * sec / per_in, iy1 + 16, sec / per_in, 12, sw=0.4) +
                         T(px, iy1 + 25, str(i + 1), 6, 'middle', 'bold' if used else 'normal', '#000' if used else '#aaa'))
                if not used:
                    continue
                grp = ins[i + 1]
                o.append(L(px, iy1 + 28, px, dy0, '#000', 1) + L(px, dy0 + 14, px, 1052, '#000', 1))
                o.append(f'<g transform="translate({px-6},{dy0+18})">' + R(0, 0, 12, 8, sw=0.7) + L(3, 7, 9, 1, sw=0.6) + '</g>')
                o.append(f'<path d="M {px} {dy0+34} l -4 5 m 4 -5 l 0 10" stroke="#000" fill="none"/>')
                if len(grp) > 1:   # Y-connector: two strings onto one input
                    o.append(L(px, 1052, px - 5, 1060) + L(px, 1052, px + 5, 1060) + T(px, 1049, 'Y', 6.5, 'middle', 'bold', '#7c3aed'))
                    o.append(sym_module(px - 4, 1070, 9, 7) + sym_module(px + 4, 1080, 9, 7))
                else:
                    o.append(sym_module(px, 1072, 12, 8))
                n = grp[0]['n']
                o.append(L(px - 4, 1090, px + 4, 1090) + L(px - 4, 1093, px + 4, 1093))
                o.append(sym_module(px, 1104, 12, 8) if len(grp) == 1 else sym_module(px, 1104, 10, 7))
                o.append(T(px, 1121, f"{'2×' if len(grp) > 1 else ''}{n}", 6, 'middle'))
                for j, s in enumerate(grp):
                    o.append(T(px, 1131 + j * 8, s['id'], 6.2 if col_w > 16 else 5.4, 'middle', 'bold'))
        o.append(L(x0, 830, x0 - 8, 830) + sym_earth(x0 - 8, 830, 0.6))
        # DCDB band
        o.append(R(x0, dy0, inv_w, dy1 - dy0, stroke='#ea580c', sw=1))
        o.append(L(x0, dy0 + 14, x0 + inv_w, dy0 + 14, '#ea580c', 0.7))
        used_in = sum(len(v) for (ki, _), v in inputs.items() if ki == k + 1)
        o.append(T(x0 + 4, dy0 + 10, f"DCDB-{k+1} ({used_in} IN / {used_in} OUT), IP65, 1500 V DC" if inv_w > 180 else f"DCDB-{k+1} ({used_in} IN/OUT)", 6.5, weight='bold'))
        if compact:
            o.append(T(x0 + 4, dy0 + 30, 'DC SPD + DC MCB PER INPUT', 6.5))
    o.append(T(44, 1150, f"{len(d['strings'])} STRINGS, {d['modules']} MODULES ON {n_inv} × {model}.  STRING CABLES: 1R X 1C X 4 SQ.MM XLPO UV Cu (EN 50618); "
                         f"Y-PAIR HOME RUNS: 1R X 1C X 6 SQ.MM — FOR +VE & –VE.", 6.8, fill='#333'))

    # ---- left column: note, cable details, design check, schedule
    o.append(R(44, 46, 400, 64, sw=1))
    o.append(TL(50, 60, ['* NOTE:', '1. VALUES MARKED * ARE ESTIMATES — VERIFY WITH DATASHEET / ON SITE.',
                         '2. DG SET / CHANGEOVER: NONE CONSIDERED. CONFIRM ON SITE; IF A DG',
                         '    EXISTS, ADD CHANGEOVER + INTERLOCK (SOLAR OFF ON DG).'], 7.5))
    rows = [(['CABLE SIZE'], ['CURRENT', 'RATING'], ['CABLE', 'CONNECTION'], ['CABLE TYPE']),
            ([f"1.1 KV, {z['run_i']}R X 3.5C", f"X {z['sq_i']} SQ MM"], [f"{z['amp_i']} A **"], ['INVERTER TO', 'ACDB'], ['AL. XLPE INSULATED', 'ARMOURED CABLE']),
            ([f"1.1 KV, {z['run_m']}R X 3.5C", f"X {z['sq_m']} SQ MM"], [f"{z['amp_m']} A **" + (' / RUN' if z['run_m'] > 1 else '')], ['ACDB TO CLIENT', 'LT PANEL'], ['AL. XLPE INSULATED', 'ARMOURED CABLE']),
            ([f"1R X 1C X {' / '.join(map(str, z['dc_sizes']))} SQ MM"], [' / '.join(f'{DC_AMPS.get(q, 0)} A' for q in z['dc_sizes']) + ' **'],
             ['STRING TO', 'DCDB / INVERTER'], ['XLPO UV Cu. CABLE', 'FOR +VE & –VE'])]
    if d.get('pairs'):
        rows.append((['1R X 1C X 4 SQ MM (LEGS)', f"+ {' / '.join(map(str, z['y_sizes']))} SQ MM (HOME RUN)"], [f"55 / {' / '.join(f'{DC_AMPS.get(q, 0)}' for q in z['y_sizes'])} A **"],
                     ['Y-CONNECTOR TO', 'DCDB / INVERTER'], ['XLPO UV Cu. CABLE', 'FOR +VE & –VE']))
    rows += [(['1R X 1C X 16 SQ MM'], ['—'], ['PV STRUCTURE', 'TO EP-1'], ['Cu EARTH CABLE']),
             (['1R X 1C X 25 SQ MM'], ['—'], ['INVERTER / ACDB', 'TO EP-2'], ['Cu EARTH CABLE']),
             (['1R X 1C X 50 SQ MM'], ['—'], ['LA TO EP-3'], ['Cu EARTH CABLE'])]
    tb, y = table(44, 124, [118, 62, 100, 120], rows, rh=17, size=7.2, head='CABLE DETAILS')
    o.append(tb)
    o.append(TL(46, y + 10, [f"** CATALOGUE RATING IN AIR × {DERATE} FOR GROUPING / AMBIENT. DESIGN CURRENT: AC 1.25 × {z['i_inv']:.0f} A = {1.25 * z['i_inv']:.0f} A PER INVERTER"
                             + (f", {1.25 * z['i_tot']:.0f} A TOTAL;" if n_inv > 1 else ';'),
                             f"    DC 1.25 × {mod['isc']:g} A = {1.25 * mod['isc']:.0f} A PER STRING. CHECK WITH THE CABLE MAKER'S TABLE."], 6.5))
    lim = d.get('limits') or {}
    nmax = max((s['n'] for s in d['strings']), default=0)
    nmin = min((s['n'] for s in d['strings']), default=0)
    chk = [(f"Voc @ 5 °C ({nmax} X {lim.get('vocCold', 0):.1f} V)", f"{nmax * lim.get('vocCold', 0):,.0f} V  <  {inv['vmax']:,} V  " + ('✓' if nmax * lim.get('vocCold', 0) < inv['vmax'] else '✗')),
           ('Vmp @ 70 °C / STC / 5 °C', f"{nmin * lim.get('vmpHot', 0):,.0f} / {nmax * mod['vmp']:,.0f} / {nmax * lim.get('vmpCold', 0):,.0f} V  ({inv['mpptMin']}–{inv['mpptMax']} V) "
            + ('✓' if nmin * lim.get('vmpHot', 0) >= inv['mpptMin'] and nmax * lim.get('vmpCold', 0) <= inv['mpptMax'] else '✗')),
           ('CURRENT PER MPPT (Imp / Isc)', f"{z['max_par'] * mod['imp']:.1f} A ≤ {inv['imaxPerMppt']} A  /  {z['max_par'] * mod['isc']:.1f} A ≤ {inv.get('iscMaxPerMppt', '—')} A "
            + ('✓' if z['max_par'] * mod['imp'] <= inv['imaxPerMppt'] else '✗')),
           ('DC VOLTAGE DROP (EACH RUN SIZED FOR IT)', f"{z['vd_dc'][0]:.2f} – {z['vd_dc'][1]:.2f} % (AIM < {z['vmax_dc']:g} %, MAX {z['lim_dc']:g} %) " + ('✓' if z['vd_dc'][1] <= z['lim_dc'] else '✗') + ' *'),
           (f"AC VOLTAGE DROP (INV. TO LT PANEL)", f"≈ {z['vd_ac']:.2f} % (AIM < {z['vmax_ac']:g} %, MAX {z['lim_ac']:g} %)" + (' — UPSIZED FOR DROP' if z['ac_upsized'] else '') + ' *'),
           ('STRING FUSE', f"REQUIRED, {z['fuse']} A gPV (> 2 STRINGS / MPPT)" if z['fuse'] else 'NOT REQUIRED (≤ 2 STRINGS / MPPT)'),
           ('DC / AC RATIO', f"{d['kwp'] / (n_inv * inv['acKw']):.2f}" if inv.get('acKw') else '—')]
    tb, y2 = table(44, y + 30, [190, 210], chk, rh=14, size=7, head='DESIGN CHECK')
    o.append(tb)
    # schedule: one row per inverter (MPPTs in groups of 4)
    srows = []
    for k in range(n_inv):
        for g0 in range(0, mppts, 4):
            cells = [f'INV-{k+1}' if g0 == 0 else '']
            for m in range(g0, min(g0 + 4, mppts)):
                ins = inputs.get((k + 1, m + 1), [])
                cells.append([(f"{grp[0]['pair']} (A+B)" if len(grp) > 1 else grp[0]['id']) for _, grp in ins][:3] or ['—'])
            while len(cells) < 5:
                cells.append('')
            srows.append(tuple(cells))
    head_cells = ('INV.',) + tuple(f'MPPT {g + 1}' + ('+' if mppts > 4 else '') for g in range(min(4, mppts)))
    tb, y3 = table(44, y2 + 12, [40, 90, 90, 90, 90], [head_cells + ('',) * (5 - len(head_cells))] + srows[:max(1, int((700 - y2) // 22))],
                   rh=13, size=6.5, head='STRING / MPPT SCHEDULE (MPPTs 5+ CONTINUE ON THE NEXT ROW)' if mppts > 4 else 'STRING / MPPT SCHEDULE')
    o.append(tb)
    o.append(TL(46, y3 + 12, [f"DCDB, PER INPUT: DC SPD 1200 V, 40 kA, TYPE 2 + DC MCB {z['mcb_single']} A (SINGLE STRING)",
                            f"/ {z['mcb_y']} A (Y PAIR), 1200 V DC, 2P.  Y = TWO STRINGS JOINED BY A Y-CONNECTOR",
                            'ON THE ROOF, THEN ONE HOME RUN (+VE AND –VE, 6 SQ.MM OR BIGGER) TO THE INPUT.'], 6.8, fill='#333'))

    # ---- inverter + module legends
    lx = 1030
    tb, y = table(lx, 46, [118, 106], [
        ('TOTAL PLANT SIZE', f"{d['kwp']:.2f} kWp"), ('NO. OF INVERTER', str(n_inv)), ('INVERTER MODEL', model),
        ('AC POWER', f"{inv['acKw']:g} kW"), ('MAX. DC VOLTAGE', f"{inv['vmax']:g} V"), (['MPPT VOLTAGE', 'RANGE'], f"{inv['mpptMin']:g} – {inv['mpptMax']:g} V"),
        ('NO. OF MPPT / INPUTS', f"{mppts} / {mppts * per_in}"), (['DC I/P CURRENT', 'PER MPPT'], f"{inv['imaxPerMppt']:g} A"),
        (['MAX. DC SHORT CKT', 'CURRENT PER MPPT'], f"{inv.get('iscMaxPerMppt', '—')} A"),
        (['MAX. AC O/P', 'CURRENT'], f"{z['i_inv']:.0f} A" + (' *' if z['i_inv_est'] else '')),
    ], rh=17, size=7.5, head='INVERTER LEGEND')
    o.append(tb)
    tb, y = table(lx, y + 14, [118, 106], [
        ('MODULE POWER', f"{d.get('wp', '—')} Wp"), ('NO. OF MODULE', str(d['modules'])), ('MODULE MODEL', [s for s in _wrap(mod.get('name', '—'), 22)][:3]),
        ('Voc', f"{mod['voc']:g} V *"), ('Vmp', f"{mod['vmp']:g} V *"), ('Isc', f"{mod['isc']:g} A *"), ('Imp', f"{mod['imp']:g} A *"),
        ('TEMP. COEFF. Voc', f"{mod['tcVoc']:g} %/°C *"),
    ], rh=17, size=7.5, head='MODULE LEGEND (STC)')
    o.append(tb)

    # ---- right column: symbols, system description, protection, title block
    sy_rows = [
        (lambda x, y: sym_module(x, y), 'PV MODULE'),
        (lambda x, y: sym_inverter(x, y), 'STRING INVERTER'),
        (lambda x, y: sym_earth(x, y - 7, 0.6), 'EARTHING'),
        (lambda x, y: sym_spd(x, y), 'SURGE PROTECTION DEVICE (SPD)'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_breaker(x, y) + '</g>', 'MINIATURE CIRCUIT BREAKER (MCB)'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_breaker(x, y, True) + '</g>', 'MOULDED CASE CIRCUIT BREAKER (MCCB)'),
        (lambda x, y: R(x - 8, y - 7, 16, 14, sw=0.8, stroke='#1f3bb8') + C(x, y, 5, sw=0.8), 'SOLAR ENERGY GENERATION METER'),
        (lambda x, y: R(x - 8, y - 7, 16, 14, sw=0.8) + C(x, y, 5, sw=0.8), 'NET METER (DISCOM)'),
        (lambda x, y: sym_lamp(x - 16, y, '#ef4444') + sym_lamp(x, y, '#facc15') + sym_lamp(x + 16, y, '#2563eb'), 'R, Y, B LIVE INDICATING LAMPS'),
        (lambda x, y: sym_lamp(x - 8, y, '#22c55e') + sym_lamp(x + 8, y, '#ef4444'), 'CIRCUIT BREAKER ON / OFF'),
        (lambda x, y: f'<g transform="translate({x} {y}) rotate(90) scale(0.55) translate({-x} {-y})">' + sym_contactor(x, y) + '</g>', 'CONTACTOR'),
        (lambda x, y: R(x - 14, y - 6, 28, 12, sw=0.8) + T(x, y + 3, 'NVR', 6.5, 'middle', 'bold'), 'NO VOLT RELAY'),
        (lambda x, y: L(x, y - 6, x - 6, y + 6) + L(x, y - 6, x + 6, y + 6) + T(x + 12, y + 3, 'Y', 7, weight='bold', fill='#7c3aed'), 'Y-CONNECTOR (2 STRINGS → 1 INPUT)'),
        (lambda x, y: sym_cable(x - 14, x + 14, y), 'CABLE'),
    ]
    tb, y = legend_block(52, 'SYMBOLS NOMENCLATURE', sy_rows, rh=16)
    o.append(tb)
    tb, y = system_block(d['system'], y + 6)
    o.append(tb)
    prot = [f'INVERTER PROTECTION :- {inv["acKw"]:g} kW ({model})', '1. DC REVERSE POLARITY PROTECTION', '2. AC SHORT CIRCUIT PROTECTION',
            '3. INSULATION RESISTANCE DETECTION', '4. RESIDUAL-CURRENT MONITORING UNIT (RCMU)', '5. ANTI-ISLANDING PROTECTION',
            '6. AC / DC SURGE PROTECTION TYPE II', '7. DC SWITCH (INTEGRATED)', '8. AC OVER / UNDER VOLTAGE & FREQUENCY PROTECTION',
            f'9. SAFETY STANDARDS : AS PER {model} DATASHEET']
    o.append(TL(TB_X0 + 6, y + 14, [p for p in prot if y + 14 + 11 * prot.index(p) < 780], 7.2, lh=11))
    o.append(title_block(info, '01', 'SINGLE LINE DIAGRAM', 'NTS', d.get('sheet', '01 OF 01')))
    return page(''.join(o), f"{info['file']}_01_SLD")


def PL_(pts, stroke='#000', sw=1):
    p = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    return f'<polyline points="{p}" stroke="{stroke}" stroke-width="{sw}" fill="none" stroke-linejoin="round"/>'


def _wrap(s: str, n: int) -> list:
    words, out, cur = str(s).split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            out.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        out.append(cur)
    return out or ['—']
