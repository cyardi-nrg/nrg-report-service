# Design Lab worker v1.0.0 (2026-10-31) — Google Drive, as the same service
# account the SolarConnect app uses (it must be a member of the Shared
# Drive). Mirrors the app's own filing exactly (lib/google-drive.ts and
# app/(app)/documents/actions.ts ensureProjectDriveFolder /
# ensureCategoryFolder): project folder → category subfolder, cached on
# projects.category_folder_ids. supportsAllDrives everywhere, as the app.
import json
import time
import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request

API = 'https://www.googleapis.com/drive/v3'
UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files'
FOLDER = 'application/vnd.google-apps.folder'

# Same labels as lib/document-types.ts CATEGORY_FOLDER_LABELS (keep in step).
CATEGORY_FOLDER_LABELS = {
    'sales_financial': 'Sales & Financial', 'accounts': 'Accounts', 'geda_discom': 'GEDA & DISCOM', 'ceig': 'CEIG',
    'dispatch': 'Dispatch', 'site': 'Site', 'national_portal': 'National List', 'application_documents': 'Application Documents',
    'design': 'Design', 'site_photos': 'Site Photos', 'bom': 'BOM', 'other': 'Other',
}
# Which category a Design Lab output files under (lib/document-types.ts DOCUMENT_GROUPS).
DESIGN_TYPES = {'google_maps_screenshot', 'site_sketch', 'cad_plan', 'survey_photo', 'autocad_drawing', 'site_drawing', 'panel_layout_drawing',
                'structural_drawing', 'walkway_layout_drawing', 'cable_tray_layout_drawing', 'design_3d_view', 'design_video', 'design_report'}
CEIG_TYPES = {'single_line_diagram', 'earthing_layout_drawing', 'equipment_layout_drawing', 'wiring_layout_drawing'}


def category_for(document_type: str) -> str:
    if document_type in DESIGN_TYPES:
        return 'design'
    if document_type in CEIG_TYPES:
        return 'ceig'
    return 'other'


class Drive:
    def __init__(self, sa_email: str, private_key: str):
        self._info = {'type': 'service_account', 'client_email': sa_email, 'private_key': private_key, 'token_uri': 'https://oauth2.googleapis.com/token'}
        self.creds = None  # made on first use, so a bad key gives a plain message instead of stopping the worker at start
        self.s = requests.Session()

    def _h(self) -> dict:
        if self.creds is None:
            try:
                self.creds = service_account.Credentials.from_service_account_info(self._info, scopes=['https://www.googleapis.com/auth/drive'])
            except ValueError as e:
                raise RuntimeError('GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY in .env is not a valid key — copy it again exactly from Railway '
                                   '(it starts with -----BEGIN PRIVATE KEY-----)') from e
        if not self.creds.valid:
            self.creds.refresh(Request())
        return {'Authorization': f'Bearer {self.creds.token}'}

    def _check(self, r: requests.Response, what: str):
        if r.status_code >= 400:
            raise RuntimeError(f'Drive {what} failed ({r.status_code}): {r.text[:400]}')
        return r

    def folder_name(self, folder_id: str) -> str:
        r = self._check(self.s.get(f'{API}/files/{folder_id}', params={'fields': 'name', 'supportsAllDrives': 'true'}, headers=self._h(), timeout=60), 'read folder')
        return r.json()['name']

    def find_or_create_folder(self, parent: str, name: str) -> str:
        q = f"'{parent}' in parents and mimeType = '{FOLDER}' and name = '{name.replace(chr(39), chr(92) + chr(39))}' and trashed = false"
        r = self._check(self.s.get(f'{API}/files', params={'q': q, 'fields': 'files(id)', 'pageSize': 1, 'supportsAllDrives': 'true', 'includeItemsFromAllDrives': 'true'}, headers=self._h(), timeout=60), 'list folder')
        files = r.json().get('files', [])
        if files:
            return files[0]['id']
        return self.create_folder(parent, name)

    def create_folder(self, parent: str, name: str) -> str:
        r = self._check(self.s.post(f'{API}/files', params={'fields': 'id', 'supportsAllDrives': 'true'}, headers={**self._h(), 'Content-Type': 'application/json'},
                                    data=json.dumps({'name': name, 'mimeType': FOLDER, 'parents': [parent]}), timeout=60), 'create folder')
        return r.json()['id']

    def upload(self, folder_id: str, filename: str, mime: str, path: str) -> str:
        """Resumable upload — fine for big videos as well as small pictures."""
        meta = {'name': filename, 'parents': [folder_id]}
        init = self._check(self.s.post(UPLOAD, params={'uploadType': 'resumable', 'supportsAllDrives': 'true', 'fields': 'id'},
                                       headers={**self._h(), 'Content-Type': 'application/json; charset=UTF-8', 'X-Upload-Content-Type': mime},
                                       data=json.dumps(meta), timeout=60), 'start upload')
        url = init.headers['Location']
        for attempt in range(4):
            try:
                with open(path, 'rb') as f:
                    r = self.s.put(url, data=f, headers={**self._h(), 'Content-Type': mime}, timeout=3600)
                return self._check(r, 'upload').json()['id']
            except (requests.ConnectionError, requests.Timeout):
                if attempt == 3:
                    raise
                time.sleep(2 ** (attempt + 1))
        raise RuntimeError('upload failed')

    def download(self, file_id: str, path: str) -> None:
        with self.s.get(f'{API}/files/{file_id}', params={'alt': 'media', 'supportsAllDrives': 'true'}, headers=self._h(), stream=True, timeout=600) as r:
            self._check(r, 'download')
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
