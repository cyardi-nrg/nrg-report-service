# Design Lab worker v1.2.0 (2026-10-31) — regression check against the owner-approved Pluga layout
# (3d-design/site-google-01: 300 kWp, 480 × 625 Wp). Rebuilds Pluga as a drawn roof model and runs the
# panel engine. Expect: roof 3/5 ≈ 42 (approved 43), new building S ≈ 67 (74), N ≈ 165 (171);
# recommended = nearest the inverter (roof 1 S + N), ≈ 439,500 units a year (approved option 3: 435,050).
#   .venv/bin/python3 tests/pluga_check.py      (drawings are written to a temp folder, printed at the end)
import sys, json, math, time, os, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from nrg import site as sitemod, sun as sunmod, packer, render
from handlers import panels as H
OUT = tempfile.mkdtemp(prefix='pluga-')
S = 10.75; IW, IH = 1890, 1276
pc = lambda x, y: {'x': x / IW * 100, 'y': y / IH * 100}
rect = lambda x0, x1, y0, y1: [pc(x0, y0), pc(x1, y0), pc(x1, y1), pc(x0, y1)]
J = json.load(open(os.path.join(HERE, '..', '..', '..', '3d-design', 'site-google-01', 'src', 'roofs.json')))
R = {r['id']: r for r in J['roofs']}
def mono(r, no, name, use=True, setback=1.0):
    depth = (r['x'][1]-r['x'][0]) / S if r['down'] in 'EW' else (r['y'][1]-r['y'][0]) / S
    return dict(id=str(no), no=no, name=name, kind='sheet_mono', points=rect(*r['x'], *r['y']), heightM=r['low'], downhill=r['down'], pitch=round((r['high']-r['low'])/depth, 4), use=use, setbackM=setback)
roofs = [
  dict(id='1', no=1, name='Main shed', kind='sheet_gable', points=rect(*R[1]['x'], *R[1]['y']), heightM=8.0, pitch=0.1, ridge='EW', use=True, setbackM=1.0),
  dict(id='2', no=2, name='North-west shed', kind='sheet_gable', points=rect(*R[2]['x'], *R[2]['y']), heightM=6.5, pitch=0.1, ridge='EW', use=False, setbackM=1.0),
  mono(R[3], 3, 'Roof 3 north half'), mono(R[4], 4, 'Link lean-to', use=False), mono(R[5], 5, 'Roof 3 south half + roof 5'),
  mono(R[6], 6, 'North lean-to', use=False), mono(R[7], 7, 'New building south'), mono(R[8], 8, 'New building north'),
]
obs = []
ry = 445; obs.append(dict(id='ridge', kind='other', points=rect(430, 1232, ry - 2.3*S, ry + 2.3*S), heightM=0.5))   # ridge vent band (Pluga: 2.6 m clear of the ridge)
ex = J['existing_solar']; obs.append(dict(id='ex', kind='existing_solar', points=rect(690 - 0.5*S, 1220, 505, 645), heightM=0.3))
for x, y in [(208, 462), (272, 462), (340, 462), (203, 593), (273, 592), (342, 592), (230, 708), (273, 707), (340, 703)]:
    obs.append(dict(id=f'v{x}{y}', kind='turbo_vent', points=[pc(x + 0.3*S*math.cos(i/8*2*math.pi), y + 0.3*S*math.sin(i/8*2*math.pi)) for i in range(8)], heightM=0.6))
for c in (191, 257, 328): obs.append(dict(id=f's{c}', kind='skylight', points=rect(c - 5.4, c + 5.4, 400, 775), heightM=0))
NBX0, NBE = -153, 581
for c in (3.69, 9.10, 15.2, 22.7):
    for a, b in ((0.44, 3.45), (9.6, 12.6)): obs.append(dict(id=f'k{c}{a}', kind='skylight', points=rect(NBX0 + (c-.5)*S, NBX0 + (c+.5)*S, NBE + a*S, NBE + b*S), heightM=0))
    for a, b in ((4.57, 7.44), (12.35, 15.4), (19.5, 22.3)): obs.append(dict(id=f'n{c}{a}', kind='skylight', points=rect(NBX0 + (c-.5)*S, NBX0 + (c+.5)*S, NBE - b*S, NBE - a*S), heightM=0))
for c in (15.2, 22.7): obs.append(dict(id=f'm{c}', kind='skylight', points=rect(NBX0 + (c-.5)*S, NBX0 + (c+.5)*S, NBE - 27.7*S, NBE - 24.7*S), heightM=0))
model = dict(version=1, baseDocumentId='B', pxPerM=S, imageW=IW, imageH=IH, roofs=roofs, obstacles=obs)
marks = {'inverter': pc(1236, 652), 'northUp': True, 'screenshotDocumentId': 'B'}
json.dump({'model': model, 'marks': marks}, open(os.path.join(OUT, 'model.json'), 'w'))

class FakeJob:
    def __init__(s):
        s.workdir = OUT; os.makedirs(s.workdir, exist_ok=True); s.files = []
        s.layout = {'kwp': 300, 'panel_wp': 625, 'panel_count': 480, 'panel_make': 'Waaree'}
        s.design = {'marks': marks}; s.customer = 'Pluga Pumps'
    def file_output(s, path, t, title=None, extra=None): s.files.append((t, title, path))
import nrg.inputs as I
H.roof_model = lambda job: (model, {'version': 1, 'status': 'approved'})
H.base_picture = lambda job, m: os.path.join(HERE, '..', '..', '..', '3d-design', 'site-google-01', 'src', 'google-satellite.webp')
t0 = time.time(); job = FakeJob(); res = H.run(job)
print('time', round(time.time() - t0, 1), 's'); print(res['summary'])
print('capacity per face:', {a['face']: a['capacity'] for o in res['options'] for a in o['arrays']})
for o in res['options']: print(o['name'], o['modules'], o['kwp'], o['annualKwh'], o['dcCableM'], [(a['face'], a['modules'], a['orient']) for a in o['arrays']], o['note'])
print(job.files)

print('drawings in', OUT)
