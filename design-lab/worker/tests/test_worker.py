# Design Lab worker v1.2.0 (2026-10-31) — round-trip test with stand-ins for Supabase and Drive.
#   .venv/bin/python3 tests/test_worker.py      → ends with "ALL OK" and "CAD OK"
import sys, os, uuid, datetime as dt, re
W=__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))); sys.path.insert(0, W)
os.environ.update(SUPABASE_URL='http://x', SUPABASE_SERVICE_ROLE_KEY='k', GOOGLE_SERVICE_ACCOUNT_EMAIL='a@b', GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY='k', GOOGLE_DRIVE_ROOT_FOLDER_ID='ROOT', WORKER_NAME='TestMac')
import worker, handlers
from nrg import jobs

# ---- in-memory PostgREST
T = {k: [] for k in ['design_jobs','design_projects','design_layouts','projects','documents','design_stage_versions','design_workers']}
def match(row, params):
    for k, v in params.items():
        if k in ('select','order','limit'): continue
        if k == 'or':
            m = re.match(r'\(run_after\.is\.null,run_after\.lte\.(.+)\)', v); ra = row.get('run_after')
            if not (ra is None or ra <= m.group(1)): return False; continue
        op, val = v.split('.', 1)
        x = row.get(k)
        if op == 'eq' and str(x) != val: return False
        if op == 'is' and x is not None: return False
        if op == 'in' and str(x) not in val.strip('()').split(','): return False
    return True
class FakeSupa:
    def select(self, t, p):
        rows=[r for r in T[t] if match(r,p)]
        if p.get('order','').startswith('version.desc'): rows.sort(key=lambda r:-r['version'])
        if p.get('order','').startswith('created_at'): rows.sort(key=lambda r:r['created_at'])
        return [dict(r) for r in rows[:int(p.get('limit',1000))]]
    def one(self,t,p):
        r=self.select(t,{**p,'limit':1}); 
        if r and t=='projects': r[0]['customers']={'name':'Pluga Pumps'}
        return r[0] if r else None
    def insert(self,t,row,returning=True):
        row=dict(row); row.setdefault({'documents':'document_id'}.get(t,'id'),str(uuid.uuid4())); T[t].append(row); return [row]
    def upsert(self,t,row,on_conflict):
        T[t]=[r for r in T[t] if r.get(on_conflict)!=row[on_conflict]]+[row]
    def update(self,t,f,patch):
        out=[]
        for r in T[t]:
            if match(r,f): r.update(patch); out.append(dict(r))
        return out
class FakeDrive:
    def __init__(s): s.folders={}; s.files=[]
    def create_folder(s,parent,name): fid=f'F{len(s.folders)}'; s.folders[fid]=(parent,name); return fid
    def find_or_create_folder(s,parent,name):
        for k,v in s.folders.items():
            if v==(parent,name): return k
        return s.create_folder(parent,name)
    def upload(s,folder,filename,mime,path): s.files.append((folder,filename,mime,os.path.getsize(path))); return f'D{len(s.files)}'
    def folder_name(s,i): return 'NRG Projects'

# ---- data
now=dt.datetime.now(dt.timezone.utc)
T['projects'].append({'project_id':'P1','site_address':'Savli','google_drive_folder_id':None,'category_folder_ids':{}})
T['design_projects'].append({'design_id':'D1','project_id':'P1','name':'Pluga'})
T['design_layouts'].append({'layout_id':'L1','design_id':'D1','kwp':300})
def job(stage, run_after=None, mins=0, status='queued', worker=None):
    j={'job_id':str(uuid.uuid4()),'design_id':'D1','layout_id':'L1','stage':stage,'status':status,'input':{},'run_after':run_after,'created_at':(now+dt.timedelta(minutes=mins)).isoformat(),'worker':worker}
    T['design_jobs'].append(j); return j
j_tonight=job('views', (now+dt.timedelta(hours=5)).isoformat(), 0)
j_now=job('views', None, 1)
j_cant=job('video', None, 2)
j_stale=job('views', None, 3, status='running', worker='TestMac')
j_boom=job('panels', None, 4)

def views(j):
    p=os.path.join(j.workdir,'view.png'); open(p,'wb').write(b'\x89PNG'+b'0'*100)
    j.file_output(p,'design_3d_view','South-east'); return {'summary':'1 view'}
def panels(j): raise ValueError('roof model missing')
handlers.HANDLERS.update(views=views, panels=panels)

cfg=worker.cfgmod.load()
w=worker.Worker(cfg); w.db=FakeSupa(); w.drive=FakeDrive(); w.caps=handlers.capabilities()
w.release_stale()
assert j_stale['status']=='queued', 'stale job released'
for _ in range(5):
    r=w.next_job()
    if not r: break
    w.run_job(r)
st={j['stage']+('-tonight' if j['run_after'] else '')+':'+j['job_id'][:4]: (j['status'], (j.get('error') or '')[:40]) for j in T['design_jobs']}
print(st)
assert j_tonight['status']=='queued', 'night job must wait'
assert j_now['status']=='done' and j_stale['status']=='done'
assert j_cant['status']=='queued', 'job the Mac cannot do stays queued'
assert j_boom['status']=='failed' and 'roof model missing' in j_boom['error']
print('drive folders', w.drive.folders); print('files', w.drive.files)
print('docs', [(d['document_type'], d['extracted_data']['stage'], d['extracted_data']['layout_id']) for d in T['documents']])
print('versions', [(v['stage'], v['version'], v['status'], v['data']['summary']) for v in T['design_stage_versions']])
print('project cache', T['projects'][0]['category_folder_ids'], T['projects'][0]['google_drive_folder_id'])
print('heartbeat', T['design_workers'])
assert [v['version'] for v in T['design_stage_versions']]==[1,2]
# night job becomes due
j_tonight['run_after']=(now-dt.timedelta(minutes=1)).isoformat()
r=w.next_job(); assert r and r['job_id']==j_tonight['job_id']; w.run_job(r); assert j_tonight['status']=='done'
print('ALL OK')

# ---- phase 2: AutoCAD job
import shutil, tempfile, ezdxf
CAD_DXF=os.path.join(tempfile.mkdtemp(),'plant_mm.dxf')
_d=ezdxf.new(); _d.header['$INSUNITS']=4; _m=_d.modelspace()
for _x,_y,_w,_h in [(0,0,60000,40000),(65000,0,30000,20000)]: _m.add_lwpolyline([(_x,_y),(_x+_w,_y),(_x+_w,_y+_h),(_x,_y+_h)],close=True)
_d.saveas(CAD_DXF)
FakeDrive.download=lambda s,fid,path: shutil.copy({'DXF1':CAD_DXF,'DWG1':CAD_DXF}[fid], path)
T['documents'].append({'document_id':'A1','project_id':'P1','document_type':'autocad_drawing','google_drive_file_id':'DXF1','upload_date':'2026-10-31','extracted_data':{'original_name':'Plant layout R3.dxf'}})
T['documents'].append({'document_id':'A2','project_id':'P1','document_type':'autocad_drawing','google_drive_file_id':'DWG1','upload_date':'2026-10-30','extracted_data':{'original_name':'Old plan.dwg'}})
import importlib, handlers as H; importlib.reload(H); w.caps=H.capabilities(); worker.handlers=H
jc=job('cad'); jc['layout_id']=None; jc['input']={'document_id':'A1'}
jd=job('cad'); jd['layout_id']=None; jd['input']={'document_id':'A2'}
for _ in range(3):
    r=w.next_job()
    if not r: break
    w.run_job(r)
print('cad job:', jc['status'], jc.get('output',{}).get('summary'))
print('dwg job:', jd['status'], (jd.get('error') or '')[:120])
plan=[d for d in T['documents'] if d['document_type']=='cad_plan'][0]
print('plan doc:', plan['extracted_data']['original_name'], plan['extracted_data']['px_per_m'], len(plan['extracted_data']['candidates']), 'candidates')
assert jc['status']=='done' and jd['status']=='failed' and 'ODA File Converter' in jd['error']
assert not [v for v in T['design_stage_versions'] if v['stage']=='cad']
print('CAD OK')
