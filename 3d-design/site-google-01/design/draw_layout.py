# Version: v4 (2026-10-31) — draws design/layout.json on the satellite screenshot -> Pluga-Pumps_300kWp_Layout_v3.png
import json, math, os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
F = '/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf'
def font(n, b=False, i=False): return ImageFont.truetype(F % ('BoldItalic' if b and i else 'Bold' if b else 'Italic' if i else 'Regular'), n)
L = json.load(open(os.path.join(HERE, 'layout.json'))); R = json.load(open(os.path.join(ROOT, 'src', 'roofs.json')))
S = 10.75; PADL = 340
src = Image.open(os.path.join(ROOT, 'src', 'google-satellite.webp')).convert('RGBA')
im = Image.new('RGBA', (src.width + PADL, src.height), (226, 232, 240, 255)); im.paste(src, (PADL, 0))
def X(x): return x + PADL
ov = Image.new('RGBA', im.size, (0, 0, 0, 0)); g = ImageDraw.Draw(ov)
for r in R['roofs']:                                           # roof outlines (light), excluded roofs hatched grey
    x0, x1, y0, y1 = X(r['x'][0]), X(r['x'][1]), r['y'][0], r['y'][1]
    col = (156, 163, 175) if r.get('exclude') else (14, 165, 233) if r.get('new_building') else (255, 255, 255)
    g.rectangle([x0, y0, x1, y1], fill=col + (40 if not r.get('exclude') else 90,), outline=col + (230,), width=3)
    if r.get('ridge_y'): g.line([x0 + 6, r['ridge_y'], x1 - 6, r['ridge_y']], fill=(255, 255, 255, 200), width=2)
ex = R['existing_solar']
for gx in ex['groups_x']:
    g.rectangle([X(gx[0]), ex['rows_y'][0][0], X(gx[1]), ex['rows_y'][-1][1]], fill=(100, 116, 139, 120), outline=(226, 232, 240, 255), width=2)
COL = {'1S': (37, 99, 235), '7S': (14, 116, 144), '35S': (22, 163, 74), '1N': (124, 58, 237)}
for a in L['arrays']:
    c = COL[a['roof']]; hw = 2.382 * S / 2; hd = a['dp'] * S / 2
    for x, y in a['mods_px']:
        g.rectangle([X(x) - hw, y - hd, X(x) + hw, y + hd], fill=c + (235,), outline=(255, 255, 255, 220), width=1)
for r in L.get('skylights_px', []):
    g.rectangle([X(r[0]), r[2], X(r[1]), r[3]], fill=(207, 227, 239, 230), outline=(220, 38, 38, 255), width=2)
for vx, vy in L.get('vents_px', []):
    r = 0.9 * S; g.ellipse([X(vx) - r, vy - r, X(vx) + r, vy + r], fill=(255, 255, 255, 120), outline=(220, 38, 38, 255), width=3)
im = Image.alpha_composite(im, ov); g = ImageDraw.Draw(im)
# array labels
lab = {'1S': (600, 400), '7S': (0, 330), '35S': (258, 812), '1N': (1010, 255)}
for a in L['arrays']:
    x, y = lab[a['roof']]; x = X(x); c = COL[a['roof']]
    t1 = f"{a['name'].split(' (')[0]}"; t2 = f"{a['modules']} × 625 Wp = {a['kwp']:.1f} kWp · faces {a['faces']}"
    w = max(g.textlength(t1, font=font(21, True)), g.textlength(t2, font=font(19))) + 24
    g.rounded_rectangle([x - w / 2, y - 28, x + w / 2, y + 28], 8, fill=(255, 255, 255, 240), outline=c + (255,), width=3)
    g.text((x, y - 11), t1, fill=c, font=font(21, True), anchor='mm'); g.text((x, y + 13), t2, fill=(30, 41, 59), font=font(19), anchor='mm')
g.rounded_rectangle([X(700), 652, X(1215), 684], 8, fill=(255, 255, 255, 230))
g.text((X(958), 668), 'EXISTING SOLAR (≈ 90–95 kWp)', fill=(51, 65, 85), font=font(19, True), anchor='mm')
# inverter + transformer at the south-east corner of roof 1
ix, iy = L['inverter']['px']; tx, ty = L['transformer']['px']
g.rectangle([X(ix) - 6, iy - 22, X(ix) + 8, iy + 22], fill=(234, 88, 12), outline='white', width=2)
g.rectangle([X(tx) - 14, ty - 14, X(tx) + 14, ty + 14], fill=(220, 38, 38), outline='white', width=2)
g.text((X(tx), ty), 'T', fill='white', font=font(18, True), anchor='mm')
g.line([X(ix) + 10, iy, X(1330), 600], fill=(234, 88, 12), width=3); g.line([X(tx) + 16, ty + 4, X(1330), 700], fill=(220, 38, 38), width=3)
g.rounded_rectangle([X(1330), 570, X(1560), 630], 8, fill=(255, 255, 255, 240), outline=(234, 88, 12), width=3)
g.text((X(1445), 588), 'INVERTERS + ACDB', fill=(194, 65, 12), font=font(19, True), anchor='mm'); g.text((X(1445), 611), 'roof 1, south-east corner', fill=(30, 41, 59), font=font(16), anchor='mm')
g.rounded_rectangle([X(1330), 670, X(1560), 730], 8, fill=(255, 255, 255, 240), outline=(220, 38, 38), width=3)
g.text((X(1445), 688), 'TRANSFORMER', fill=(185, 28, 28), font=font(19, True), anchor='mm'); g.text((X(1445), 711), 'next to the inverters', fill=(30, 41, 59), font=font(16), anchor='mm')
# DC route: along roof 1's south eave and east gable to the inverters
g.line([X(1225), 455, X(1225), 682, X(1236), 682], fill=(234, 88, 12), width=4)
g.line([X(1225), 205, X(1225), 440], fill=(234, 88, 12), width=4)
g.line([X(-140), 745, X(1215), 745], fill=(234, 88, 12), width=4)
g.text((X(420), 752), 'DC cable route (indicative): west roofs → along the south wall → inverters', fill=(194, 65, 12), font=font(17, True, True))
# legend panel
W, H = im.size; out = Image.new('RGB', (W + 700, H), 'white'); out.paste(im.convert('RGB'), (0, 0)); d = ImageDraw.Draw(out)
x = W + 30; y = 22
d.text((x, y), 'PLUGA PUMPS & MOTORS — 300 kWp LAYOUT', fill=(15, 23, 42), font=font(30, True)); y += 44
d.text((x, y), 'Savli, Vadodara · north ↑ · 20 m = 215 px · layout v4 · 2026-10-31', fill=(71, 85, 105), font=font(19)); y += 40
rows = [('Array', 'Modules', 'kWp', 'Faces')] + [(a['name'].split(' (')[0], str(a['modules']), f"{a['kwp']:.1f}", a['faces']) for a in L['arrays']] + [('TOTAL (new)', str(L['total_modules']), f"{L['kwp']:.1f}", '')]
cw = [380, 100, 90, 70]
for i, r in enumerate(rows):
    xx = x; bold = i in (0, len(rows) - 1)
    if i == 0 or i == len(rows) - 1: d.rectangle([x - 6, y - 4, x + sum(cw), y + 30], fill=(241, 245, 249))
    for j, cell in enumerate(r):
        d.text((xx, y), cell, fill=COL[L['arrays'][i - 1]['roof']] if 0 < i < len(rows) - 1 and j == 0 else (15, 23, 42), font=font(21, bold)); xx += cw[j]
    y += 36
y += 10
for line in [
    ('Module (assumed): 625 Wp TOPCon, 2382 × 1134 mm, landscape, flush on sheet', False),
    ('480 modules = 24 strings × 20 · inverters ≈ 240–250 kW AC (DC:AC ≈ 1.2)', False),
    ('Rules: 1.0 m clear of eaves/gables · 2.6 m clear of the ridge vents', False),
    ('           blocks of 7 × 4 modules with 0.8 m walkways', False),
    ('Order (owner): south-facing roofs first → roof 1 north for the balance', False),
    ('   roof 1 north filled from the east end (nearest the inverters);', False),
    (f"   {[a for a in L['arrays'] if a['roof'] == '1N'][0]['north_capacity_left']} more modules fit there if needed later", False),
    ('South-facing: 254 modules = 158.75 kWp · north-facing: 226 = 141.25 kWp', False),
    ('Roof 1 south: west of the existing array only (1 m access path)', False),
    ('New building: south roof, skylights kept free (▭) — turbovents removed', False),
    ('Roof 3 = gable: south half + roof 5 = ONE south slope (used, full)', False),
    ('   roof 3 north half faces north: not used (reserve ≈ 48 modules)', False),
    ('   9 turbo ventilators kept clear (○)', False),
    ('   west part gets late-afternoon shade from the new building', True),
    ('Not used: roofs 2, 4, 6 (owner)', True),
    ('New building roof: PEB under construction — ask the PEB vendor', True),
    ('   now to design purlins for the module load (~15 kg/m²)', True),
    ('Check with MGVCL: AC capacity vs 225 kVA contract demand', True)]:
    d.text((x, y), line[0], fill=(185, 28, 28) if line[1] else (51, 65, 85), font=font(18, line[1] and line[0].startswith(('Not', 'New building roof', 'Check')))); y += 27
d.text((x, H - 40), 'Positions scaled from the satellite screenshot — verify on site before BOQ.', fill=(100, 116, 139), font=font(17, False, True))
out.save(os.path.join(ROOT, 'Pluga-Pumps_300kWp_Layout_v4.png')); print(out.size)
