# Design Lab worker v1.14.0 (2026-11-02) — Base design round trip: read a base design picture (stand-in Supabase /
# Drive), sketch roofs, then Panel placement uses those panels.
#   .venv/bin/python3 tests/test_base.py <picture> [panel_wp]   → ends with "BASE OK"
import sys, os, shutil
W = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, W)
os.environ.update(SUPABASE_URL='http://x', SUPABASE_SERVICE_ROLE_KEY='k', GOOGLE_SERVICE_ACCOUNT_EMAIL='a@b', GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY='k',
                  GOOGLE_DRIVE_ROOT_FOLDER_ID='ROOT', WORKER_NAME='TestMac')
sys.argv += [] if len(sys.argv) > 1 else [os.path.join(W, 'tests', 'base-sample.jpg')]
PIC = os.path.abspath(sys.argv[1]); WP = int(sys.argv[2]) if len(sys.argv) > 2 else 625
OUT = os.environ.get('BASE_TEST_OUT')
sys.argv = sys.argv[:1]
import importlib.util
spec = importlib.util.spec_from_file_location('tw', os.path.join(W, 'tests', 'test_worker.py'))
tw = importlib.util.module_from_spec(spec)
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(tw)          # the stand-ins (and its own checks)
T, job, w = tw.T, tw.job, tw.w
import handlers as H
w.caps = H.capabilities()
tw.worker.handlers = H
saved = []
orig_upload = tw.FakeDrive.upload
def upload(s, folder, filename, mime, path):
    if OUT:
        shutil.copy(path, os.path.join(OUT, os.path.basename(filename)))
    saved.append(filename)
    fid = orig_upload(s, folder, filename, mime, path)
    keep = os.path.join(os.path.dirname(PIC_COPY), fid + os.path.splitext(path)[1]); shutil.copy(path, keep); FILES[fid] = keep
    return fid
import tempfile
PIC_COPY = os.path.join(tempfile.mkdtemp(), 'x'); FILES = {'BASE1': PIC}
tw.FakeDrive.upload = upload
tw.FakeDrive.download = lambda s, fid, path: shutil.copy(FILES[fid], path)
NORTH = os.environ.get('BASE_TEST_NORTH', 'up')
T['design_layouts'][0].update(panel_wp=WP, kwp=0, panel_count=None)
T['documents'].append({'document_id': 'B1', 'project_id': 'P1', 'document_type': 'site_drawing', 'google_drive_file_id': 'BASE1',
                       'upload_date': '2026-11-02', 'extracted_data': {'original_name': os.path.basename(PIC)}})
T['design_stage_versions'].append({'design_id': 'D1', 'layout_id': None, 'stage': 'questions', 'version': 1, 'status': 'approved',
                                   'data': {'floors': '2', 'mounting': 'elevated'}})
jb = job('base'); jb['layout_id'] = None; jb['input'] = {'document_id': 'B1', 'north': NORTH}
r = w.next_job(); w.run_job(r)
print('base job:', jb['status'], jb.get('error') or jb.get('output', {}).get('summary'))
assert jb['status'] == 'done', jb.get('error')
bv = [v for v in T['design_stage_versions'] if v['stage'] == 'base'][-1]
rv = [v for v in T['design_stage_versions'] if v['stage'] == 'roofs'][-1]
print('tables:', [(t['name'], t['rows'], t['cols'], len(t['panels'])) for t in bv['data']['tables']])
print('roofs:', [(r['name'], len(r['points']), r['heightM']) for r in rv['data']['model']['roofs']], 'pxPerM', rv['data']['model']['pxPerM'])
assert rv['data']['model']['baseDocumentId'] == bv['data']['pictureDocumentId']
# Panel placement on those panels (the real handler, not the test stand-in)
H.HANDLERS['panels'] = H._panels.run
jp = job('panels'); jp['input'] = {}
r = w.next_job(); w.run_job(r)
print('panels job:', jp['status'], jp.get('error') or jp.get('output', {}).get('summary'))
assert jp['status'] == 'done', jp.get('error')
pv = [v for v in T['design_stage_versions'] if v['stage'] == 'panels'][-1]['data']
o = pv['options'][0]
print('option:', o['name'], o['modules'], 'panels', o['kwp'], 'kWp; blocks', [(b['name'], b['rows'], b['cols'], b.get('frontLegM')) for b in o['blocks']])
assert o['modules'] == bv['data']['panels'] and len(pv['options']) == 1
print('files:', saved[-6:])
print('BASE OK')
