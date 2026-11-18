# Design Lab worker v1.2.0 (2026-10-31) — drawings (PNG) on top of the base picture.
import math
import os

from PIL import Image, ImageDraw, ImageFont

FONTS = ['/System/Library/Fonts/Supplemental/Arial.ttf', '/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf']
BOLD = ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf']
TEAL, INK, MUTED = (14, 116, 144), (22, 26, 46), (90, 107, 133)
FACE_COL = [(37, 99, 235), (217, 119, 6), (5, 150, 105), (190, 24, 93), (124, 58, 237), (8, 145, 178), (101, 163, 13), (220, 38, 38)]
OBS_COL = {'turbo_vent': (124, 58, 237), 'skylight': (14, 165, 233), 'cabin': (180, 83, 9), 'tank': (3, 105, 161), 'lift_room': (154, 52, 18),
           'existing_solar': (30, 58, 138), 'tree': (21, 128, 61), 'other': (107, 114, 128)}


def font(size: int, bold: bool = False):
    for f in (BOLD if bold else []) + FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def base_canvas(base_path: str | None, W: int, H: int, max_w: int = 2400):
    k = min(1.0, max_w / W)
    if base_path and os.path.exists(base_path):
        img = Image.open(base_path).convert('RGB').resize((int(W * k), int(H * k)))
        img = Image.blend(img, Image.new('RGB', img.size, 'white'), 0.35)   # fade the photo so the drawing reads
    else:
        img = Image.new('RGB', (int(W * k), int(H * k)), 'white')
    return img, k


def draw_layout(site, base_path, faces_used: list, modules: list, title: str, lines: list[str], out_path: str, shade_cells=None):
    img, k = base_canvas(base_path, site.W, site.H)
    d = ImageDraw.Draw(img, 'RGBA')
    P = lambda x, y: tuple(v * k for v in site.to_px(x, y))
    for r in site.roofs:
        pts = [P(x, y) for x, y in r['poly'].exterior.coords]
        d.polygon(pts, outline=(217, 119, 6) if r.get('use', True) else (120, 120, 120), width=3)
        c = r['poly'].centroid
        cx, cy = P(c.x, c.y)
        d.ellipse([cx - 16, cy - 16, cx + 16, cy + 16], fill=(217, 119, 6) if r.get('use', True) else (120, 120, 120))
        d.text((cx, cy), str(r['no']), fill='white', font=font(20, True), anchor='mm')
    if shade_cells:
        for (x, y, s) in shade_cells:
            d.rectangle([P(x - s / 2, y - s / 2), P(x + s / 2, y + s / 2)], fill=(220, 38, 38, 90))
    for kind, poly, _, _ in site.obstacles:
        d.polygon([P(x, y) for x, y in poly.exterior.coords], fill=OBS_COL.get(kind, (107, 114, 128)) + (160,))
    col = {f: FACE_COL[i % len(FACE_COL)] for i, f in enumerate(faces_used)}
    for m in modules:
        d.polygon([P(x, y) for x, y in m.corners], fill=col.get(m.face, TEAL) + (230,), outline=(255, 255, 255))
    if site.inverter:
        ix, iy = P(*site.inverter)
        d.rectangle([ix - 14, iy - 10, ix + 14, iy + 10], fill=(234, 88, 12))
        d.text((ix + 18, iy), 'INVERTER', fill=(234, 88, 12), font=font(18, True), anchor='lm')
    # north arrow + scale bar
    W, H = img.size
    d.polygon([(W - 60, 30), (W - 72, 70), (W - 48, 70)], fill=INK)
    d.text((W - 60, 82), 'N', fill=INK, font=font(20, True), anchor='mt')
    bar = 10 if site.W / site.ppm < 150 else 50                     # under the north arrow, clear of map buttons
    bl = bar * site.ppm * k
    d.rectangle([W - 40 - bl - 10, 100, W - 30, 146], fill=(255, 255, 255, 200))
    d.line([(W - 35 - bl, 132), (W - 35, 132)], fill=INK, width=6)
    d.text((W - 35 - bl, 124), f'{bar} m', fill=INK, font=font(18), anchor='ld')
    # title + legend panel
    pad, lh = 16, 26
    box_h = pad * 2 + 34 + lh * len(lines)
    panel = Image.new('RGB', (W, box_h), 'white')
    pd = ImageDraw.Draw(panel)
    pd.text((pad, pad), title, fill=INK, font=font(28, True))
    for i, ln in enumerate(lines):
        y = pad + 40 + i * lh
        face = ln.split('|', 1)[0] if '|' in ln else None
        text = ln.split('|', 1)[1] if '|' in ln else ln
        x = pad
        if face and face in col:
            pd.rectangle([x, y + 4, x + 18, y + 20], fill=col[face])
            x += 26
        pd.text((x, y), text, fill=INK if face else MUTED, font=font(19))
    out = Image.new('RGB', (W, H + box_h), 'white')
    out.paste(panel, (0, 0))
    out.paste(img, (0, box_h))
    out.save(out_path, optimize=True)


def draw_table(title: str, header: list, rows: list, notes: list, out_path: str):
    f, fb = font(22), font(22, True)
    widths = [max(fb.getlength(str(header[i])), *(f.getlength(str(r[i])) for r in rows)) + 36 for i in range(len(header))]
    W = int(max(sum(widths) + 60, 1100))
    H = 120 + 44 * (len(rows) + 1) + 34 * len(notes) + 40
    img = Image.new('RGB', (W, H), 'white')
    d = ImageDraw.Draw(img)
    d.text((30, 30), title, fill=INK, font=font(32, True))
    y = 100
    x = 30
    for i, h in enumerate(header):
        d.text((x, y), str(h), fill=MUTED, font=fb)
        x += widths[i]
    d.line([(30, y + 36), (W - 30, y + 36)], fill=(220, 224, 232), width=2)
    for r in rows:
        y += 44
        x = 30
        for i, v in enumerate(r):
            d.text((x, y), str(v), fill=INK, font=fb if i == 0 else f)
            x += widths[i]
    y += 60
    for n in notes:
        d.text((30, y), n, fill=MUTED, font=font(19))
        y += 34
    img.save(out_path, optimize=True)
