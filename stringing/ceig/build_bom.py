# Version: v2 (2026-10-28) — wording: Jain modules are landscape (long side along the ridge)
# Bill of material for Jain Granite & Marble — stringing, DC cabling, MC4, cable tray, walkway.
# Quantities are computed from the same geometry as the drawings (generate_ceig_drawings.py v5),
# so a change to the layout there flows straight into this BOM.
#   python3 build_bom.py   ->  Jain-Granite_BOM_Stringing-Tray-Walkway_v1.xlsx

import math
import os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

import generate_ceig_drawings as g

BOM_VERSION = 'v2'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'Jain-Granite_BOM_Stringing-Tray-Walkway_{BOM_VERSION}.xlsx')

RATES = {'4sqmm': 58}                   # owner's current rates, ₹/m (2.5 sq mm ₹44, 6 sq mm ₹84 for reference)
CABLE_WASTE = 1.05                      # +5 % on DC cable
TRAY_WASTE = 1.10                       # +10 % on tray
WALK_WASTE = 1.05                       # +5 % on walkway
TRAY_LEN = 2.5                          # m per standard tray length
ROW_TURNS_PER_STRING = 3                # 4-row snake → 3 turns between vertically stacked modules
JUMPER_LEN = 2.5                        # m of 4 sq mm per row-turn jumper (next row is one module length, 2.4 m, away)
ROOF_SUPPORT_SPACING = 1.5
WALL_BRACKET_SPACING = 1.2
WALK_CLAMP_SPACING = 1.2


def up(x, step=1):
    return int(math.ceil(x / step - 1e-9) * step)


def quantities():
    sched = g.dc_cable_schedule()
    plus = sum(r[4] for r in sched)
    minus = sum(r[5] for r in sched)
    n_str = len(sched)
    jumpers = n_str * ROW_TURNS_PER_STRING
    jumper_m = jumpers * JUMPER_LEN

    segs = g.tray_segments()
    tray_total = sum(s[5] for s in segs)
    tray_lengths = up(tray_total * TRAY_WASTE / TRAY_LEN)
    roof_tray = sum(s[5] for s in segs if s[0] != 'T4')
    wall_tray = sum(s[5] for s in segs if s[0] == 'T4')
    straight_joints = sum(max(up(s[5] / TRAY_LEN) - 1, 0) for s in segs)
    fittings = {'flat_bend': 2, 'tee': 1, 'vertical_bend': 2, 'end_cap': 2}
    fitting_joints = fittings['flat_bend'] * 2 + fittings['tee'] * 3 + fittings['vertical_bend'] * 2
    couplers = straight_joints + fitting_joints

    ns, con, wa1, wa2 = g.walk_lengths()
    walk_total = sum(l for _, l, _ in ns) + con + wa1 + wa2

    earth_bus = (segs[0][5] + segs[1][5] + segs[2][5] + segs[3][5] + segs[4][5] + 5.0)   # tray route + ≈5 m to EP-1
    return dict(sched=sched, plus=plus, minus=minus, n_str=n_str, jumpers=jumpers, jumper_m=jumper_m,
                segs=segs, tray_total=tray_total, tray_lengths=tray_lengths, roof_tray=roof_tray, wall_tray=wall_tray,
                couplers=couplers, fittings=fittings, ns=ns, con=con, wa1=wa1, wa2=wa2, walk_total=walk_total,
                earth_bus=earth_bus)


THIN = Side(style='thin', color='999999')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill('solid', fgColor='1F3BB8')
SEC_FILL = PatternFill('solid', fgColor='E8ECFB')
WRAP = Alignment(wrap_text=True, vertical='top')


def build():
    q = quantities()
    wb = Workbook()
    ws = wb.active
    ws.title = 'BOM'
    ws['A1'] = 'JAIN GRANITE & MARBLE — 100.00 kWp ROOFTOP: BILL OF MATERIAL (STRINGING, DC CABLE, MC4, CABLE TRAY, WALKWAY)'
    ws['A1'].font = Font(bold=True, size=12)
    ws['A2'] = (f'BOM {BOM_VERSION} · 27-10-2026 · based on drawings {g.VERSION} (06 Stringing, 05 Cable Tray, 04 Walkway); modules LANDSCAPE · '
                '160 x Adani AB-G12R-132-625, GoodWe GW80K-MT, 8 strings x 20, no Y-connectors')
    ws['A3'] = 'Quantities marked * depend on lengths scaled from the layout photo — confirm with a site measurement before ordering.'
    ws['A3'].font = Font(italic=True, color='C00000')
    hdr = ['S.No', 'Item', 'Specification', 'Unit', 'Calculated qty', 'Qty to order', 'Rate (₹)', 'Amount (₹)', 'Basis / note']
    ws.append([])
    ws.append(hdr)
    hr = ws.max_row
    for c in range(1, len(hdr) + 1):
        cell = ws.cell(hr, c)
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        cell.border = BOX

    rows = []

    def section(title):
        rows.append(('SEC', title))

    def item(no, name, spec, unit, calc, order, rate, note):
        rows.append((no, name, spec, unit, calc, order, rate, note))

    section('A. DC CABLE (STRING HOME RUNS + ROW-TURN JUMPERS)')
    item('A1', 'DC solar cable 4 sq mm – RED (+VE)', '1C x 4 sq mm Cu, EN 50618 / H1Z2Z2-K, 1.5 kV DC, UV & XLPO', 'm',
         round(q['plus'], 1), up(q['plus'] * CABLE_WASTE, 10), RATES['4sqmm'],
         'Sum of 8 +VE home runs along tray route (see sheet "DC cable by string") + 5 %. *')
    item('A2', 'DC solar cable 4 sq mm – BLACK (–VE)', 'Same as A1', 'm',
         round(q['minus'], 1), up(q['minus'] * CABLE_WASTE, 10), RATES['4sqmm'],
         'Sum of 8 –VE home runs + 5 %. –VE runs are longer (row 4 / row 8 terminals). *')
    item('A3', 'DC solar cable 4 sq mm – row-turn jumpers', 'Same as A1 (either colour)', 'm',
         q['jumper_m'], up(q['jumper_m'] * CABLE_WASTE, 5), RATES['4sqmm'],
         f'{q["jumpers"]} jumpers ({ROW_TURNS_PER_STRING} row turns x {q["n_str"]} strings) x {JUMPER_LEN} m. Modules are landscape (long side along the ridge), so the next row is one module length (2.4 m) away; '
         'module leads do not reach. Drop if modules are ordered with long (≥ 1.2 m) leads that reach across the turn.')

    section('B. MC4 CONNECTORS')
    item('B1', 'MC4 connector pair – array end of home runs', '1 male + 1 female, 1500 V DC, 4–6 sq mm, IP68, SAME MAKE/TYPE AS MODULE CONNECTORS', 'pair',
         q['n_str'] * 2 / 2, q['n_str'], None,
         '16 conductors x 1 connector each at the array end = 16 halves = 8 pairs (one +, one – per string).')
    item('B2', 'MC4 connector pair – row-turn jumpers', 'Same as B1', 'pair',
         q['jumpers'], q['jumpers'], None, '1 pair per jumper (one end each). Not needed if A3 is dropped.')
    item('B3', 'MC4 connector pair – spares', 'Same as B1', 'pair',
         None, up((q['n_str'] + q['jumpers']) * 0.1), None, '≈ 10 % spare for re-termination on site.')
    item('B4', 'DC connectors – inverter end', 'GoodWe-supplied DC connectors (in the inverter box)', 'pair',
         q['n_str'], 0, None, '8 pairs needed (2 inputs x 4 MPPT). Use the GoodWe connectors supplied with the inverter (warranty / compatibility). '
         'Order 8 pairs of the inverter-compatible type ONLY if the box does not include them.')
    item('B5', 'MC4 crimping tool + spanner set', 'For 2.5 / 4 / 6 sq mm contacts', 'set', None, 1, None, 'Skip if the site team already has one.')

    section('C. DC CABLE TRAY (SHEET 05)')
    item('C1', 'Perforated cable tray 100 x 50 mm', 'HDG, 1.6 mm, standard 2.5 m lengths', 'length (2.5 m)',
         round(q['tray_total'], 1), q['tray_lengths'], None,
         f'Route T1 + T2 + T3a + T3b + T4 = {q["tray_total"]:.1f} m (see "Tray & walkway runs") + 10 % = {q["tray_lengths"] * TRAY_LEN:.1f} m. *')
    item('C2', 'Tray cover 100 mm', 'HDG, bolted / clip-on, 2.5 m', 'length (2.5 m)', None, q['tray_lengths'], None, 'Full length — UV and bird / monkey protection.')
    item('C3', 'Flat 90° bend 100 x 50', 'HDG', 'no.', 2, 2, None, 'T1 → north edge; wall vertical → along wall.')
    item('C4', 'Tee 100 x 50', 'HDG', 'no.', 1, 1, None, 'T2 joining the north-edge run.')
    item('C5', 'Vertical (riser) bend 100 x 50', 'HDG', 'no.', 2, 2, None, 'Over the east eave onto the wall; down into the inverter.')
    item('C6', 'Tray coupler / joint set', 'With bolts, nuts, washers', 'set', q['couplers'], up(q['couplers'] * 1.05), None,
         'One per joint between lengths and at each fitting end, + 5 %.')
    item('C7', 'End cap 100 x 50', 'HDG', 'no.', 2, 2, None, 'South ends of T1 and T2.')
    item('C8', 'Roof tray support / purlin clamp (75–100 mm raised)', 'HDG, with EPDM-sealed fixings', 'no.',
         up(q['roof_tray'] / ROOF_SUPPORT_SPACING) + 4, up((q['roof_tray'] / ROOF_SUPPORT_SPACING + 4) * 1.05), None,
         f'Every {ROOF_SUPPORT_SPACING} m on {q["roof_tray"]:.1f} m of roof tray + run ends. *')
    item('C9', 'Wall bracket for tray', 'HDG, anchor-fixed', 'no.', up(q['wall_tray'] / WALL_BRACKET_SPACING) + 1,
         up((q['wall_tray'] / WALL_BRACKET_SPACING + 1) * 1.05), None, f'Every {WALL_BRACKET_SPACING} m on the {q["wall_tray"]:.1f} m wall run (T4). *')
    item('C10', 'Tray earth-continuity jumper', '6 sq mm Cu with lugs (or couplers rated for continuity)', 'no.', q['couplers'], q['couplers'], None,
         'Across each joint, so the whole tray bonds to EP-1.')
    item('C11', 'Cable ties, UV-stabilised', '300 mm and 200 mm, black', 'pack of 100', None, 6, None,
         'Home runs in the vertical wall tray (every 0.5 m) + clipping module leads / jumpers to rails. Estimate.')
    item('C12', 'Cable markers', 'Printed / ferrule, S1+ … S8–', 'no.', 32, 40, None, 'Both ends of all 16 home-run conductors (32) + spare.')

    section('D. WALKWAY (SHEET 04)')
    item('D1', 'Walkway 300 mm wide', 'FRP or HDG anti-skid grating, UV-stabilised, ≥ 150 kg/m²', 'm',
         round(q['walk_total'], 1), up(q['walk_total'] * WALK_WASTE),
         None, f'W1 + W2 + WC + WA1 + WA2 = {q["walk_total"]:.1f} m + 5 %. In 3 m panels: {up(q["walk_total"] * WALK_WASTE / 3)} panels. *')
    item('D2', 'Walkway fixing clamp / support set', 'Purlin clamp, no sheet puncture (or EPDM-sealed)', 'set',
         up(q['walk_total'] / WALK_CLAMP_SPACING), up(q['walk_total'] / WALK_CLAMP_SPACING * 1.05), None,
         f'Every {WALK_CLAMP_SPACING} m (confirm purlin spacing on site). *')
    item('D3', 'Lifeline / handrail at ladder landing', 'Along WA2 (south eave) + ladder landing', 'm',
         round(q['wa2'], 1), up(q['wa2'] + 1.5), None, 'Only stretch of walkway near a roof edge.')

    section('E. RELATED – IN THE SAME TRAY (OPTIONAL, FROM EARTHING LAYOUT)')
    item('E1', 'Earth cable 16 sq mm Cu (green / yellow)', 'PV structure earth bus, laid in the DC tray', 'm',
         round(q['earth_bus'], 1), up(q['earth_bus'] * 1.10, 5), None, 'Tray route + ≈ 5 m from the wall to EP-1, + 10 %. *')

    sno_rows = []
    for r in rows:
        if r[0] == 'SEC':
            ws.append([r[1]])
            rr = ws.max_row
            ws.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=len(hdr))
            ws.cell(rr, 1).font = Font(bold=True, color='1F3BB8')
            ws.cell(rr, 1).fill = SEC_FILL
            continue
        no, name, spec, unit, calc, order, rate, note = r
        ws.append([no, name, spec, unit, calc, order, rate, None, note])
        rr = ws.max_row
        ws.cell(rr, 8).value = f'=IF(G{rr}="","",F{rr}*G{rr})'
        ws.cell(rr, 8).number_format = '#,##0'
        ws.cell(rr, 7).number_format = '#,##0'
        sno_rows.append(rr)
        for c in range(1, len(hdr) + 1):
            ws.cell(rr, c).border = BOX
            ws.cell(rr, c).alignment = WRAP
    ws.append([])
    ws.append(['', 'TOTAL (items with a rate)', '', '', '', '', '', f'=SUM(H{sno_rows[0]}:H{sno_rows[-1]})', 'Fill in rates in column G for the rest.'])
    tr = ws.max_row
    ws.cell(tr, 2).font = Font(bold=True)
    ws.cell(tr, 8).font = Font(bold=True)
    ws.cell(tr, 8).number_format = '#,##0'
    for col, w in zip('ABCDEFGHI', (6, 38, 44, 13, 13, 12, 10, 12, 70)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = ws.cell(hr + 1, 1)

    # ---- DC cable by string
    w2 = wb.create_sheet('DC cable by string')
    w2.append(['String', 'MPPT', 'Input', 'Slope', '+VE red (m)', '–VE black (m)', 'Pair (m)', 'How it is measured'])
    for c in range(1, 9):
        w2.cell(1, c).font = Font(bold=True, color='FFFFFF')
        w2.cell(1, c).fill = HEAD_FILL
    hy = g.TRAY_HY + g.TRAY_W / 2
    for s, m, i, sl, p, mi in q['sched']:
        w2.append([s, m, i, 'East' if sl == 'E' else 'West', round(p, 1), round(mi, 1), round(p + mi, 1),
                   'terminal row → tray in the block gap → north edge → east eave → 10 m down the wall → along wall to inverter, '
                   f'+ {g.TAIL_ARRAY} m array tail + {g.TAIL_INV} m at inverter'])
    n = w2.max_row
    w2.append(['TOTAL', '', '', '', f'=SUM(E2:E{n})', f'=SUM(F2:F{n})', f'=SUM(G2:G{n})', ''])
    for c in range(1, 8):
        w2.cell(w2.max_row, c).font = Font(bold=True)
    w2.append([])
    w2.append(['Row-turn jumpers', '', '', '', '', '', q['jumper_m'], f'{q["jumpers"]} x {JUMPER_LEN} m (3 per string)'])
    for col, wdt in zip('ABCDEFGH', (10, 7, 7, 8, 12, 13, 10, 90)):
        w2.column_dimensions[col].width = wdt

    # ---- tray & walkway runs
    w3 = wb.create_sheet('Tray & walkway runs')
    w3.append(['Run', 'Route', 'Length (m)', 'Contents / width'])
    for c in range(1, 5):
        w3.cell(1, c).font = Font(bold=True, color='FFFFFF')
        w3.cell(1, c).fill = HEAD_FILL
    for sid, desc, _, cab, st, ln in q['segs']:
        w3.append([sid, desc, round(ln, 2), f'{cab} ({st})'])
    w3.append(['', 'TOTAL DC TRAY', round(q['tray_total'], 2), '100 x 50 mm'])
    w3.append([])
    for n_, ln, d in q['ns']:
        w3.append([n_, d, round(ln, 2), '300 mm'])
    w3.append(['WC', 'Connector, just south of the arrays, W1 → W2', round(q['con'], 2), '300 mm'])
    w3.append(['WA1', 'Access: W1 continued south to the access strip *', round(q['wa1'], 2), '300 mm'])
    w3.append(['WA2', 'Access: along the south edge from the SW ladder *', round(q['wa2'], 2), '300 mm'])
    w3.append(['', 'TOTAL WALKWAY', round(q['walk_total'], 2), '300 mm'])
    for col, wdt in zip('ABCD', (8, 50, 12, 40)):
        w3.column_dimensions[col].width = wdt

    wb.save(OUT)
    return q, OUT


if __name__ == '__main__':
    q, out = build()
    print('saved', out)
    print(f"plus {q['plus']:.1f}  minus {q['minus']:.1f}  jumpers {q['jumper_m']}  tray {q['tray_total']:.1f} ({q['tray_lengths']} lengths)  "
          f"couplers {q['couplers']}  walkway {q['walk_total']:.1f}  earth {q['earth_bus']:.1f}")
