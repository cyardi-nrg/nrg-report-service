# Design Lab worker v1.0.0 (2026-10-31) — one job: everything a stage needs
# to read (design, layout, project, inputs), and everything it hands back
# (files filed into Drive + documents rows, a new stage version, the
# job's summary). Mirrors the SolarConnect app's own rules:
#   * documents rows like the app's system-generated documents
#     (ai_status 'confirmed', ai_confidence 1), extracted_data carrying
#     design_id / layout_id / stage so the Design Lab shows them on the
#     right stage (app/(app)/design-lab/[id]/design-board.tsx EngineStage);
#   * file names like lib/document-types.ts buildDocumentFilename;
#   * every result is a NEW stage version (draft) for the owner to approve.
import datetime as dt
import mimetypes
import os
import re
import tempfile

from .drive import Drive, CATEGORY_FOLDER_LABELS, category_for
from .supa import Supa

# Same human labels as lib/document-types.ts (only the ones the worker writes).
LABELS = {
    'panel_layout_drawing': 'Panel Layout Drawing', 'structural_drawing': 'Structural Drawing', 'walkway_layout_drawing': 'Walkway Layout',
    'cable_tray_layout_drawing': 'Cable Tray Layout', 'design_3d_view': '3D View', 'design_video': 'Walk-around Video', 'design_report': 'Design Report',
    'single_line_diagram': 'Single Line Diagram', 'equipment_layout_drawing': 'Equipment Layout', 'earthing_layout_drawing': 'Earthing Details',
    'wiring_layout_drawing': 'Wiring Layout',
}
INPUT_TYPES = ['google_maps_screenshot', 'site_sketch', 'survey_photo', 'autocad_drawing', 'site_drawing', 'electricity_bill']


class NotBuiltYet(Exception):
    """A stage the Mac cannot do yet — the job is marked failed with this message, so the Design Lab says so plainly."""


class Job:
    def __init__(self, db: Supa, drive: Drive, row: dict, worker_name: str):
        self.db, self.drive, self.row, self.worker = db, drive, row, worker_name
        self.job_id, self.stage = row['job_id'], row['stage']
        self.design = db.one('design_projects', {'design_id': f"eq.{row['design_id']}", 'select': '*'})
        if not self.design:
            raise RuntimeError('The design for this job no longer exists.')
        self.layout = db.one('design_layouts', {'layout_id': f"eq.{row['layout_id']}", 'select': '*'}) if row.get('layout_id') else None
        self.project = db.one('projects', {'project_id': f"eq.{self.design['project_id']}", 'select': 'project_id,site_address,google_drive_folder_id,category_folder_ids,customers(name)'})
        self.customer = ((self.project or {}).get('customers') or {}).get('name') or self.design['name']
        self.workdir = tempfile.mkdtemp(prefix=f'designlab-{self.stage}-')
        self.document_ids: list[str] = []

    # ------------------------------------------------------------ reading
    @property
    def input(self) -> dict:
        return self.row.get('input') or {}

    def latest_version(self, stage: str, layout_id: str | None = None, approved_only: bool = False) -> dict | None:
        p = {'design_id': f"eq.{self.design['design_id']}", 'stage': f'eq.{stage}', 'select': '*', 'order': 'version.desc'}
        p['layout_id'] = f'eq.{layout_id}' if layout_id else 'is.null'
        if approved_only:
            p['status'] = 'eq.approved'
        return self.db.one('design_stage_versions', p)

    def input_documents(self, types: list[str] | None = None) -> list[dict]:
        t = ','.join(types or INPUT_TYPES)
        return self.db.select('documents', {'project_id': f"eq.{self.design['project_id']}", 'document_type': f'in.({t})',
                                            'select': 'document_id,document_type,google_drive_file_id,upload_date,extracted_data', 'order': 'upload_date.desc'})

    def fetch(self, doc: dict) -> str:
        """Downloads one input document into the job's work folder; returns its path."""
        name = (doc.get('extracted_data') or {}).get('original_name') or f"{doc['document_type']}-{doc['document_id'][:8]}"
        path = os.path.join(self.workdir, re.sub(r'[\\/:*?"<>|]', '-', name))
        self.drive.download(doc['google_drive_file_id'], path)
        return path

    # ------------------------------------------------------------ writing
    def _category_folder(self, category: str) -> str:
        """documents/actions.ts ensureCategoryFolder, step for step."""
        proj = self.db.one('projects', {'project_id': f"eq.{self.design['project_id']}", 'select': 'google_drive_folder_id,category_folder_ids'})
        cache = (proj or {}).get('category_folder_ids') or {}
        if cache.get(category):
            return cache[category]
        folder = (proj or {}).get('google_drive_folder_id')
        if not folder or folder.startswith('NO-DRIVE-'):
            folder = self.drive.create_folder(self.drive_root, self.customer)
            self.db.update('projects', {'project_id': f"eq.{self.design['project_id']}"}, {'google_drive_folder_id': folder, 'updated_at': now_iso()})
        sub = self.drive.find_or_create_folder(folder, CATEGORY_FOLDER_LABELS.get(category, category))
        self.db.update('projects', {'project_id': f"eq.{self.design['project_id']}"}, {'category_folder_ids': {**cache, category: sub}})
        return sub

    drive_root = ''  # set by the worker

    def file_output(self, path: str, document_type: str, title: str | None = None) -> str:
        """Uploads one output into the project's Drive folder and records it as a document of this design / layout / stage."""
        ext = os.path.splitext(path)[1].lstrip('.').lower() or 'bin'
        mime = mimetypes.guess_type(path)[0] or {'glb': 'model/gltf-binary', 'dxf': 'image/vnd.dxf', 'dwg': 'image/vnd.dwg'}.get(ext, 'application/octet-stream')
        kw = f"{float(self.layout['kwp']):g}kW" if self.layout and self.layout.get('kwp') else None
        date = dt.datetime.now().strftime('%d %b %Y')
        parts = [self.customer, kw, LABELS.get(document_type, document_type.replace('_', ' ')), title, date]
        safe = lambda s: re.sub(r'[\\/:*?"<>|]', '-', s).strip()
        filename = ' — '.join(safe(p) for p in parts if p) + f'.{ext}'
        folder = self._category_folder(category_for(document_type))
        file_id = self.drive.upload(folder, filename, mime, path)
        row = self.db.insert('documents', {
            'project_id': self.design['project_id'], 'google_drive_file_id': file_id, 'document_type': document_type,
            'uploaded_by': None, 'ai_status': 'confirmed', 'ai_confidence': 1,
            'extracted_data': {'design_id': self.design['design_id'], 'layout_id': self.row.get('layout_id'), 'stage': self.stage,
                               'job_id': self.job_id, 'original_name': filename, 'mime_type': mime, 'title': title, 'source': 'design_lab_worker'},
        })[0]
        self.document_ids.append(row['document_id'])
        return row['document_id']

    def save_version(self, data: dict) -> None:
        last = self.latest_version(self.stage, self.row.get('layout_id'))
        self.db.insert('design_stage_versions', {
            'design_id': self.design['design_id'], 'layout_id': self.row.get('layout_id'), 'stage': self.stage,
            'version': (last['version'] if last else 0) + 1, 'status': 'draft',
            'data': {**data, 'document_ids': self.document_ids, 'job_id': self.job_id, 'worker': self.worker},
            'note': None, 'created_by': None,
        }, returning=False)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()
