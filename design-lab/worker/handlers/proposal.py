# Design Lab worker v1.13.0 (2026-11-02) — stage 'proposal' (per quote / layout): the client DESIGN PROPOSAL PDF.
#
# Owner's ask (Rotex, Nov 2026): "make a pdf file with the details of the system with my logo ... so that i can send it
# to them ... send the design to them before i send the quote ... lets make this a standard practice".
# Built from this layout's own data — nothing typed twice:
#   * Panel placement (approved, else latest): the chosen option — panels, kWp, tables (rows × panels), tilt,
#     expected units a year (NREL SAM);
#   * Structure (saved, if any): front-leg heights per table;
#   * the latest Panel layout drawing and 3D view pictures of this layout (run those stages first);
#   * the NRG logo (viewer/nrg-logo.png); optional contact line from .env NRG_PROPOSAL_CONTACT.
# Output: an A4 PDF filed as a Design Report "Design proposal"; the result carries a ready email (subject + text)
# that the Client pack stage offers.
import datetime as dt
import html
import math
import os

from PIL import Image

from nrg import shots
from nrg.inputs import panel_spec

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(HERE, 'viewer', 'nrg-logo.png')
E = html.escape
kw2 = lambda w: math.floor(w / 10 + 0.5 + 1e-9) / 100          # watts → kWp, 2 decimals, half up (108 125 W → 108.13)
COMPANY = ('ltd', 'limited', 'pvt', 'llp', 'industries', 'enterprises', 'corporation', 'company', 'co.', 'trust', 'society', 'hospital', 'school')


def _chosen_option(job):
    lid = job.row.get('layout_id')
    v = job.latest_version('panels', lid, approved_only=True) or job.latest_version('panels', lid)
    data = (v or {}).get('data') or {}
    opts = data.get('options') or []
    if not opts:
        raise RuntimeError('Run Panel placement first — the proposal shows its layout.')
    return next((o for o in opts if o.get('name') == data.get('recommended')), opts[0])


def _layout_docs(job, types):
    lid = job.row.get('layout_id')
    rows = job.db.select('documents', {'project_id': f"eq.{job.design['project_id']}", 'document_type': f"in.({','.join(types)})",
                                       'select': 'document_id,document_type,google_drive_file_id,upload_date,extracted_data', 'order': 'upload_date.desc'})
    out = []
    for d in rows:
        x = d.get('extracted_data') or {}
        if x.get('design_id') == job.design['design_id'] and x.get('layout_id') == lid and (x.get('mime_type') or '').startswith('image/'):
            out.append(d)
    return out


def _latest_run(docs):
    """Per picture type, only the pictures from the most recent run (older runs may show an older design)."""
    newest = {}
    for d in docs:                                        # docs come newest first
        newest.setdefault(d['document_type'], (d.get('extracted_data') or {}).get('job_id'))
    return [d for d in docs if (d.get('extracted_data') or {}).get('job_id') == newest[d['document_type']]]


def _jpg(job, doc, name, max_w=1800):
    path = job.fetch(doc)
    im = Image.open(path).convert('RGB')
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)))
    out = os.path.join(job.workdir, name)
    im.save(out, quality=84, optimize=True)
    return os.path.basename(out)


def run(job) -> dict:
    lay = job.layout or {}
    opt = _chosen_option(job)
    spec = panel_spec(lay)
    wp = spec['wp']
    n = int(opt.get('modules') or 0)
    kwp = kw2(n * wp)
    units = float(opt.get('annualKwh') or 0)
    make = (lay.get('panel_make') or '').strip()
    st = ((lay.get('structure') or {}).get('input') or {})
    default_front = st.get('frontLegM')
    st_front = {b.get('name'): b.get('frontLegM') for b in (st.get('blocks') or [])}
    arrays = opt.get('arrays') or []
    tilt = st.get('tiltDeg') or (arrays[0].get('tilt') if arrays else None)
    ft = lambda m: f"{m / 0.3048:.1f} ft"

    rows_html, tables = [], 0
    for a in arrays:
        for b in a.get('blocks') or []:
            cnt = int(b['rows']) * int(b['cols'])
            fl = st_front.get(b['name']) or b.get('frontLegM') or default_front
            rows_html.append(f"<tr><td>{E(b['name'])}</td><td>{b['rows']} × {b['cols']}</td><td class='n'>{cnt}</td>"
                             f"<td class='n'>{kw2(cnt * wp):.2f}</td><td>{ft(fl) + ' front leg' if fl else ''}</td></tr>")
            tables += 1
    orient = 'portrait' if (opt.get('orientation') or 'portrait') == 'portrait' else 'landscape'

    # pictures: the panel layout drawing for this option + up to 8 3D views (latest runs only)
    docs = _latest_run(_layout_docs(job, ['panel_layout_drawing', 'design_3d_view']))
    letter = (opt.get('name') or '').split(' · ')[0]                   # "Option A"
    plans = [d for d in docs if d['document_type'] == 'panel_layout_drawing']
    plan = next((d for d in plans if letter and letter in ((d.get('extracted_data') or {}).get('title') or '')), plans[0] if plans else None)
    views = [d for d in docs if d['document_type'] == 'design_3d_view'][:8]
    plan_img = _jpg(job, plan, 'plan.jpg', 2200) if plan else None
    view_imgs = [(_jpg(job, d, f'view{i}.jpg'), (d.get('extracted_data') or {}).get('title') or '3D view') for i, d in enumerate(views)]
    logo = os.path.basename(LOGO)
    Image.open(LOGO).save(os.path.join(job.workdir, logo))

    customer = job.customer
    site = (job.project or {}).get('site_address') or ''
    today = dt.date.today().strftime('%-d %B %Y')
    ref = f"NRG-{''.join(ch for ch in customer.upper() if ch.isalnum())[:10]}-{(lay.get('layout_id') or '')[:4].upper()}"
    contact = os.environ.get('NRG_PROPOSAL_CONTACT', '').strip()
    lakh = f"{units / 1e5:.2f} lakh" if units >= 1e5 else f"{units:,.0f}"
    hero = view_imgs[0][0] if view_imgs else plan_img
    pages = []
    hdr = (f"<div class='hdr'><img src='{logo}'><div class='r'>{E(customer)}<br>Rooftop solar design proposal</div></div>")

    def ftr(i, total):
        return f"<div class='ftr'><span>NRG Technologists Pvt. Ltd. · Vadodara, Gujarat{' · ' + E(contact) if contact else ''}</span><span>Page {i} of {total}</span></div>"

    pages.append(f"""<div class='page'>
  <div class='hdr'><img src='{logo}'><div class='r'><b>NRG Technologists Pvt. Ltd.</b><br>Solar EPC · Vadodara, Gujarat</div></div>
  <div class='kick'>ROOFTOP SOLAR · DESIGN PROPOSAL</div>
  <h1>{E(customer)}</h1>
  <p class='lead'>{kwp:g} kWp rooftop solar · {n} × {wp} Wp panels{(' · ' + E(site)) if site else ''}</p>
  {f"<img class='hero' src='{hero}'>" if hero else ''}
  <div class='kpis'>
    <div class='kpi'><div class='v'>{kwp:g} kWp</div><div class='l'>System size (DC)</div></div>
    <div class='kpi'><div class='v'>{n}</div><div class='l'>Panels, {wp} Wp, {orient}</div></div>
    <div class='kpi'><div class='v'>{'≈ ' + lakh if units else '—'}</div><div class='l'>Units a year (estimate)</div></div>
    <div class='kpi'><div class='v'>{f'{tilt:g}°' if tilt else '—'}</div><div class='l'>Tilt, facing south</div></div>
  </div>
  <p class='small'>Prepared on {today} · Design reference {E(ref)}<br>This design is shared ahead of our quotation so that the layout can be agreed first.</p>
  @@FTR@@</div>""")
    pages.append(f"""<div class='page'>{hdr}
  <h2>The system</h2>
  <table><tr><th>Item</th><th>Details</th></tr>
    <tr><td>System size</td><td><b>{kwp:g} kWp</b> (DC)</td></tr>
    <tr><td>Panels</td><td>{n} × {wp} Wp{(' · ' + E(make)) if make else ''}, all in <b>{orient}</b></td></tr>
    <tr><td>Mounting</td><td>{'GI tables tilted <b>' + f'{tilt:g}' + '° to the south</b>' if tilt else 'As per the layout'}{(', front leg ' + ft(default_front)) if default_front else ''}</td></tr>
    <tr><td>Expected generation</td><td>{('About <b>' + f'{units:,.0f}' + ' units a year</b> (typical year, NREL SAM) — an estimate, refined with the final design') if units else 'To follow'}</td></tr>
    <tr><td>Electrical</td><td>Inverter selection, string design, cabling and single-line diagram follow with our quotation</td></tr>
  </table>
  <h3>Panel tables</h3>
  <table><tr><th>Table</th><th>Rows × panels</th><th class='n'>Panels</th><th class='n'>kWp</th><th>Height</th></tr>
    {''.join(rows_html)}
    <tr class='tot'><td>Total</td><td></td><td class='n'>{n}</td><td class='n'>{kwp:.2f}</td><td></td></tr></table>
  <h3>Next steps</h3>
  <ol><li>You confirm the layout (or tell us what to change).</li><li>We send the quotation with the structure and electrical design.</li>
      <li>Final measurements are checked on the roof before fabrication.</li></ol>
  <div class='note'>Based on our site visit and the roof information available. Final dimensions are checked on the roof before fabrication.</div>
  @@FTR@@</div>""")
    if plan_img:
        pages.append(f"<div class='page'>{hdr}<h2>Roof layout</h2><img class='plan' src='{plan_img}'>@@FTR@@</div>")
    rest = view_imgs[1:] if hero == (view_imgs[0][0] if view_imgs else None) else view_imgs
    for i in range(0, len(rest), 2):
        pair = rest[i:i + 2]
        body = ''.join(f"<img class='view' src='{src}'><p class='cap'>{E(cap)}</p>" for src, cap in pair)
        pages.append(f"<div class='page'>{hdr}{'<h2>3D views</h2>' if i == 0 else ''}{body}@@FTR@@</div>")
    total = len(pages)
    pages = [p.replace('@@FTR@@', ftr(i + 1, total)) for i, p in enumerate(pages)]

    doc = f"""<!DOCTYPE html><html><head><meta charset='utf-8'><title>Design proposal — {E(customer)}</title><style>
  @page {{ size: A4; margin: 0; }} * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: Inter, 'Segoe UI', Arial, sans-serif; color: #111827; }}
  .page {{ width: 210mm; height: 297mm; padding: 14mm 14mm 16mm; position: relative; page-break-after: always; overflow: hidden; }}
  .page:last-child {{ page-break-after: auto; }}
  .hdr {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1e3a8a; padding-bottom: 4mm; margin-bottom: 6mm; }}
  .hdr img {{ height: 13mm; }} .hdr .r {{ text-align: right; font-size: 8.5pt; color: #374151; line-height: 1.5; }}
  .ftr {{ position: absolute; left: 14mm; right: 14mm; bottom: 8mm; display: flex; justify-content: space-between; font-size: 7.5pt; color: #6b7280; border-top: 1px solid #e5e7eb; padding-top: 2mm; }}
  .kick {{ font-size: 10pt; color: #6b7280; font-weight: 700; letter-spacing: 1px; }}
  h1 {{ font-size: 26pt; margin: 0 0 2mm; color: #1e3a8a; }} h2 {{ font-size: 14pt; margin: 0 0 3mm; color: #1e3a8a; }} h3 {{ font-size: 10.5pt; margin: 4mm 0 1.5mm; }}
  p, li {{ font-size: 9pt; line-height: 1.45; }} .lead {{ font-size: 11pt; margin: 0; }} .small {{ font-size: 9pt; color: #374151; }}
  .hero {{ width: 100%; border-radius: 3mm; margin: 6mm 0; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 3mm; margin: 4mm 0; }}
  .kpi {{ background: #eff6ff; border-radius: 2.5mm; padding: 3mm; }} .kpi .v {{ font-size: 15pt; font-weight: 800; color: #1e3a8a; }} .kpi .l {{ font-size: 8pt; color: #374151; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 9pt; }} th, td {{ text-align: left; padding: 1.4mm 2mm; border-bottom: 1px solid #e5e7eb; }}
  th {{ background: #f3f4f6; }} td.n, th.n {{ text-align: right; }} tr.tot td {{ font-weight: 800; border-top: 2px solid #1e3a8a; }}
  .note {{ font-size: 8.5pt; color: #374151; background: #f9fafb; border-left: 3px solid #1e3a8a; padding: 2.5mm 3.5mm; margin-top: 4mm; }}
  .plan {{ width: 100%; max-height: 235mm; object-fit: contain; display: block; margin: 0 auto; }}
  .view {{ width: 100%; border-radius: 2mm; margin-bottom: 2mm; }} .cap {{ font-size: 9pt; font-weight: 700; margin: 0 0 6mm; }}
</style></head><body>{''.join(pages)}</body></html>"""
    src = os.path.join(job.workdir, 'proposal.html')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(doc)
    pdf = os.path.join(job.workdir, 'Design proposal.pdf')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = shots._launch(p)
        pg = b.new_page()
        pg.goto('file://' + src)
        pg.wait_for_load_state('networkidle')
        pg.pdf(path=pdf, format='A4', print_background=True, prefer_css_page_size=True)
        b.close()
    doc_id = job.file_output(pdf, 'design_report', title='Design proposal', extra={'proposal': True})

    is_co = any(w in customer.lower() for w in COMPANY)
    first = 'Sir / Madam' if (is_co or not customer) else customer.split()[0]
    subject = f"Rooftop solar design for {customer} — {kwp:g} kWp (for your review before our quotation)"
    body = '\n'.join([
        f"Dear {first},", '',
        f"Thank you for the opportunity to propose a rooftop solar system for {customer}.", '',
        'Before we send our quotation, we would like you to see and agree on the design. Please find attached our design proposal '
        'with the roof layout and 3D views of the system on your roof.', '',
        'In short:',
        f"- System size: {kwp:g} kWp ({n} panels of {wp} Wp, {orient})",
        *([f"- Panels tilted {tilt:g}° to the south on GI tables"] if tilt else []),
        *([f"- Expected generation: about {units:,.0f} units a year (estimate)"] if units else []),
        '', 'The design is based on our site visit; final measurements are checked on the roof before fabrication.', '',
        'Please let us know if the layout works for you, or if you would like any changes. Once you confirm, we will send '
        'the quotation with the structure and electrical design.', '',
        'Warm regards,', 'NRG Technologists Pvt. Ltd.', 'Solar EPC · Vadodara, Gujarat', *([contact] if contact else []),
    ])
    return {'summary': f"Design proposal PDF — {kwp:g} kWp, {n} × {wp} Wp, {tables} tables, {len(view_imgs)} 3D views"
                       + ('' if plan_img else ' (no layout drawing found — run Panel placement)')
                       + ('' if view_imgs else ' (no 3D views found — run 3D views first)') + '.',
            'documentId': doc_id, 'kwp': kwp, 'panels': n, 'wp': wp, 'annualKwh': units, 'email': {'subject': subject, 'body': body}}
