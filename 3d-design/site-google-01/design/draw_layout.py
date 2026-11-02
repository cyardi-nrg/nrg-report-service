# Version: v5 (2026-11-01) — draws design/layout.json (3 options) on the satellite screenshot:
#   ../Pluga-Pumps_300kWp_Option-1_v5.png, _Option-2_v5.png, _Option-3_v5.png and ../Pluga-Pumps_300kWp_Options-Compared_v5.png
import json, math, os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
VER = 'v5'
F = '/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf'
def font(n, b=False, i=False): return ImageFont.truetype(F % ('BoldItalic' if b and i else 'Bold' if b else 'Italic' if i else 'Regular'), n)
L = json.load(open(os.path.join(HERE, 'layout.json'))); R = json.load(open(os.path.join(ROOT, 'src', 'roofs.json')))
S = 10.75; PADL = 340
MW, ML = L['module']['W'], L['module']['L']
COL = {'1S': (37, 99, 235), '7S': (14, 116, 144), '35S': (22, 163, 74), '7N': (234, 88, 12), '1N': (124, 58, 237)}
LAB = {'1S': (600, 400), '7S': (0, 885), '35S': (300, 815), '7N': (0, 300), '1N': (1010, 255)}
def X(x): return x + PADL

def draw(opt):
    src = Image.open(os.path.join(ROOT, 'src', 'google-satellite.webp')).convert('RGBA')
    im = Image.new('RGBA', (src.width + PADL, src.height), (226, 232, 240, 255)); im.paste(src, (PADL, 0))
    ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(ov)
    for r in R['roofs']:
        x0, x1, y0, y1 = X(r['x'][0]), X(r['x'][1]), r['y'][0], r['y'][1]
        col = (156, 163, 175) if r.get('exclude') else (14, 165, 233) if r.get('new_building') else (255, 255, 255)
        g.rectangle([x0, y0, x1, y1], fill=col + (40 if not r.get('exclude') else 90,), outline=col + (230,), width=3)
        if r.get('ridge_y'): g.line([x0 + 6, r['ridge_y'], x1 - 6, r['ridge_y']], fill=(255, 255, 255, 200), width=2)
    g.line([X(150), 545, X(365), 545], fill=(255, 255, 255, 230), width=3)                       # roof 3 ridge
    h = L['shade_cell_px'] / 2
    for x, y in L['shade_px']: g.rectangle([X(x) - h, y - h, X(x) + h, y + h], fill=(30, 41, 59, 110))   # winter shadow zone
    ex = R['existing_solar']
    for gx in ex['groups_x']:
        g.rectangle([X(gx[0]), ex['rows_y'][0][0], X(gx[1]), ex['rows_y'][-1][1]], fill=(100, 116, 139, 120), outline=(226, 232, 240, 255), width=2)
    for sk in L['skylights']:
        a = sk['px']; g.rectangle([X(a[0]), a[2], X(a[1]), a[3]], fill=(207, 227, 239, 200), outline=(220, 38, 38, 255), width=2)
    for vx, vy in L['vents_px']:
        r = 0.9 * S; g.ellipse([X(vx) - r, vy - r, X(vx) + r, vy + r], fill=(255, 255, 255, 120), outline=(220, 38, 38, 255), width=3)
    for a in opt['arrays']:
        c = COL[a['key']]; sl = math.radians(a['slope_deg'])
        for x, y, o in a['mods_px']:
            hw = (ML if o == 'L' else MW) * S / 2; hd = (MW if o == 'L' else ML) * math.cos(sl) * S / 2
            g.rectangle([X(x) - hw, y - hd, X(x) + hw, y + hd], fill=c + (235,), outline=(255, 255, 255, 220), width=1)
    im = Image.alpha_composite(im, ov); g = ImageDraw.Draw(im)
    for a in opt['arrays']:
        x, y = LAB[a['key']]; x = X(x); c = COL[a['key']]
        t1 = a['name']; t2 = f"{a['modules']} × 625 Wp = {a['kwp']:.2f} kWp · faces {a['faces']}"
        w = max(g.textlength(t1, font=font(21, True)), g.textlength(t2, font=font(19))) + 24
        g.rounded_rectangle([x - w / 2, y - 28, x + w / 2, y + 28], 8, fill=(255, 255, 255, 240), outline=c + (255,), width=3)
        g.text((x, y - 11), t1, fill=c, font=font(21, True), anchor='mm'); g.text((x, y + 13), t2, fill=(30, 41, 59), font=font(19), anchor='mm')
    g.rounded_rectangle([X(700), 652, X(1215), 684], 8, fill=(255, 255, 255, 230))
    g.text((X(958), 668), 'EXISTING SOLAR (≈ 90–95 kWp)', fill=(51, 65, 85), font=font(19, True), anchor='mm')
    ix, iy = L['inverter']['px']; tx, ty = L['transformer']['px']
    g.rectangle([X(ix) - 6, iy - 22, X(ix) + 8, iy + 22], fill=(234, 88, 12), outline='white', width=2)
    g.rectangle([X(tx) - 14, ty - 14, X(tx) + 14, ty + 14], fill=(220, 38, 38), outline='white', width=2)
    g.text((X(tx), ty), 'T', fill='white', font=font(18, True), anchor='mm')
    g.line([X(ix) + 10, iy, X(1330), 600], fill=(234, 88, 12), width=3); g.line([X(tx) + 16, ty + 4, X(1330), 700], fill=(220, 38, 38), width=3)
    g.rounded_rectangle([X(1330), 570, X(1560), 630], 8, fill=(255, 255, 255, 240), outline=(234, 88, 12), width=3)
    g.text((X(1445), 588), 'INVERTERS + ACDB', fill=(194, 65, 12), font=font(19, True), anchor='mm'); g.text((X(1445), 611), 'roof 1, south-east corner', fill=(30, 41, 59), font=font(16), anchor='mm')
    g.rounded_rectangle([X(1330), 670, X(1560), 730], 8, fill=(255, 255, 255, 240), outline=(220, 38, 38), width=3)
    g.text((X(1445), 688), 'TRANSFORMER', fill=(185, 28, 28), font=font(19, True), anchor='mm'); g.text((X(1445), 711), 'next to the inverters', fill=(30, 41, 59), font=font(16), anchor='mm')
    # legend panel
    W, Hh = im.size; out = Image.new('RGB', (W + 720, Hh), 'white'); out.paste(im.convert('RGB'), (0, 0)); d = ImageDraw.Draw(out)
    x = W + 28; y = 22
    d.text((x, y), f"PLUGA PUMPS — 300 kWp · OPTION {opt['id']}", fill=(15, 23, 42), font=font(30, True)); y += 42
    d.text((x, y), opt['title'].split('· ', 1)[1], fill=(71, 85, 105), font=font(20, True)); y += 30
    d.text((x, y), f'Savli · north ↑ · 20 m = 215 px · layout {VER} · 2026-11-01', fill=(100, 116, 139), font=font(18)); y += 40
    rows = [('Array (in fill order)', 'Modules', 'kWp', 'Faces')] + [(a['name'], f"{a['modules']}", f"{a['kwp']:.2f}", a['faces']) for a in opt['arrays']] + \
           [('TOTAL (new)', str(opt['modules']), f"{opt['kwp']:.1f}", '')]
    cw = [390, 100, 100, 70]
    for i, r in enumerate(rows):
        xx = x; bold = i in (0, len(rows) - 1)
        if bold: d.rectangle([x - 6, y - 4, x + sum(cw), y + 30], fill=(241, 245, 249))
        for j, cell in enumerate(r):
            colr = COL[opt['arrays'][i - 1]['key']] if 0 < i < len(rows) - 1 and j == 0 else (15, 23, 42)
            d.text((xx, y), cell, fill=colr, font=font(21, bold)); xx += cw[j]
        y += 35
    y += 8
    for t, warn in [(f"South-facing {opt['kwp_south']:.2f} kWp · north-facing {opt['kwp_north']:.2f} kWp", False),
                    (f"Energy ≈ {opt['kwh_year']/1e5:.2f} lakh kWh/yr (S 1,500 · N 1,435 kWh/kWp)", False),
                    (f"DC string cable ≈ {opt['dc_cable_m']:,.0f} m (all strings to the inverters)", False),
                    ('Module (assumed): 625 Wp, 2382 × 1134 mm, flush on sheet', False),
                    ('Grey shading = winter shadow zone (21 Dec, 9 am – 3 pm)', False),
                    ('   of the new building: no panels placed there', False),
                    ('Red boxes = skylights kept free · red circles = turbo ventilators', False),
                    ('New building: turbovents removed (owner); panels upright or', False),
                    ('   sideways per band, whichever fits more around the skylights', False),
                    ('Roof 3 north half (faces north): not used', False),
                    ('Not used: roofs 2, 4, 6 (owner)', True),
                    ('New building roof: PEB under construction — ask the vendor', True),
                    ('   now to design purlins for the module load (~15 kg/m²)', True),
                    ('Check with MGVCL: AC capacity vs 225 kVA contract demand', True)]:
        d.text((x, y), t, fill=(185, 28, 28) if warn else (51, 65, 85), font=font(18, warn and not t.startswith('   '))); y += 26
    d.text((x, Hh - 40), 'Positions scaled from the satellite screenshot — verify on site before BOQ.', fill=(100, 116, 139), font=font(17, False, True))
    f = os.path.join(ROOT, f"Pluga-Pumps_300kWp_Option-{opt['id']}_{VER}.png"); out.save(f); return f

files = [draw(o) for o in L['options']]
# comparison sheet: the three drawings (map part) side by side + a table
maps = [Image.open(f).crop((0, 0, 1890 + PADL, 950)) for f in files]
tw = 1100; th = round(950 * tw / (1890 + PADL))
sheet = Image.new('RGB', (3 * tw + 4 * 24, 150 + th + 60 + 470), 'white'); d = ImageDraw.Draw(sheet)
d.text((24, 26), 'PLUGA PUMPS & MOTORS, SAVLI — 300 kWp: THREE LAYOUT OPTIONS', fill=(15, 23, 42), font=font(44, True))
d.text((24, 88), f'480 × 625 Wp each · inverters + transformer at roof 1 south-east corner · shade-checked 21 Dec 9–15 h · layout {VER} · NRG Technologists', fill=(71, 85, 105), font=font(24))
for i, (mp, o) in enumerate(zip(maps, L['options'])):
    x = 24 + i * (tw + 24); sheet.paste(mp.resize((tw, th), Image.LANCZOS), (x, 150)); d.rectangle([x, 150, x + tw, 150 + th], outline=(203, 213, 225), width=2)
    d.text((x, 150 + th + 12), o['title'], fill=(15, 23, 42), font=font(24, True))
y = 150 + th + 70
hdr = ['', 'Option 1', 'Option 2', 'Option 3']
keys = ['1S', '7S', '35S', '7N', '1N']; names = {'1S': 'Roof 1 south', '7S': 'New building south', '35S': 'Roof 3 S half + roof 5', '7N': 'New building north', '1N': 'Roof 1 north'}
def cell(o, k):
    a = [a for a in o['arrays'] if a['key'] == k]; return f"{a[0]['modules']} ({a[0]['kwp']:.1f} kWp)" if a else '—'
rows = [hdr] + [[names[k]] + [cell(o, k) for o in L['options']] for k in keys] + \
       [['South / north kWp'] + [f"{o['kwp_south']:.1f} / {o['kwp_north']:.1f}" for o in L['options']],
        ['Energy, kWh/yr'] + [f"{o['kwh_year']:,}" for o in L['options']],
        ['DC string cable'] + [f"≈ {o['dc_cable_m']:,.0f} m" for o in L['options']],
        ['Depends on new building'] + ['Yes (both roofs)', 'Yes (south roof)', 'No']]
cw = [520, 560, 560, 560]
for i, r in enumerate(rows):
    xx = 24
    if i == 0 or i >= len(keys) + 1: d.rectangle([20, y - 4, 24 + sum(cw), y + 34], fill=(241, 245, 249) if i == 0 else (248, 250, 252))
    for j, c in enumerate(r):
        d.text((xx, y), c, fill=(15, 23, 42), font=font(26, i == 0 or j == 0)); xx += cw[j]
    y += 40
sheet.save(os.path.join(ROOT, f'Pluga-Pumps_300kWp_Options-Compared_{VER}.png'))
print(files, sheet.size)
