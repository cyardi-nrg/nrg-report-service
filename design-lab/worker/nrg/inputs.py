# Design Lab worker v1.2.0 (2026-10-31) — what the layout stages read.
import math


def roof_model(job) -> tuple[dict, dict]:
    """The roof model the owner drew (Roof design stage): the latest approved version, else the latest."""
    v = job.latest_version('roofs', None, approved_only=True) or job.latest_version('roofs', None)
    model = ((v or {}).get('data') or {}).get('model')
    if not model or not model.get('roofs'):
        raise RuntimeError('No roofs drawn yet — open Roof design in the Design Lab, draw the roofs and save.')
    return model, v


def base_picture(job, model: dict) -> str | None:
    rows = job.db.select('documents', {'document_id': f"eq.{model['baseDocumentId']}", 'select': 'document_id,document_type,google_drive_file_id,extracted_data'})
    if not rows or rows[0]['google_drive_file_id'].startswith('NO-DRIVE-'):
        return None
    try:
        return job.fetch(rows[0])
    except Exception:
        return None  # drawings still come out, on white


def panel_spec(layout: dict | None) -> dict:
    """Panel size from the layout's Wp (same table as the app's lib/structure panelSizeFor)."""
    wp = int((layout or {}).get('panel_wp') or 625)
    if wp >= 600:
        L, W = 2.382, 1.134
    elif wp >= 530:
        L, W = 2.278, 1.134
    elif wp >= 400:
        L, W = 1.762, 1.134
    else:
        L, W = 1.65, 0.992
    kwp = float((layout or {}).get('kwp') or 0)
    target = int((layout or {}).get('panel_count') or (math.ceil(kwp * 1000 / wp) if kwp else 0))
    return {'wp': wp, 'L': L, 'W': W, 'target': target, 'make': (layout or {}).get('panel_make')}
