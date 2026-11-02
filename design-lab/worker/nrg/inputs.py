# Design Lab worker v1.11.0 (2026-11-01) — what the layout stages read.
# v1.11.0: answers() — the Site questions; placement() — inverter / meter heights from their floors (owner:
#   "inverter placement needs to be defined on height … same terrace floor, 1 floor below, ground floor";
#   "meter is typically on the ground floor").
import math
import re

STOREY_M = 3.0      # floor-to-floor height when not given, m


def answers(job) -> dict:
    """The Site questions (latest version)."""
    v = job.latest_version('questions', None)
    return ((v or {}).get('data') or {}) if v else {}


def _num(text) -> float | None:
    m = re.search(r'[\d.]+', str(text or ''))
    return float(m.group()) if m else None


def floors_below(a: dict) -> int | None:
    """Floors below the terrace: the number box, else 'G+3' (= 4) / '4 floors' in the older text answer."""
    if a.get('floors') not in (None, ''):
        n = _num(a['floors'])
        return int(n) if n is not None else None
    t = str(a.get('heightOrFloors') or '')
    g = re.search(r'G\s*\+\s*(\d+)', t, re.I)
    if g:
        return int(g.group(1)) + 1
    f = re.search(r'(\d+)\s*(floor|storey|story)', t, re.I)
    if f:
        return int(f.group(1))
    return int(_num(t)) if re.fullmatch(r'\s*\d+\s*', t) else None


def _drop(where: str | None, floor, floors: int | None, storey: float, terrace_z: float) -> float:
    """How far below the terrace a floor is, m. where: terrace | below1 | ground | floor (with floor = its number, ground = 0)."""
    full = floors * storey if floors else terrace_z
    if where == 'terrace':
        return 0.0
    if where == 'below1':
        return storey
    if where == 'floor' and floor not in (None, '') and floors:
        return max(0.0, (floors - float(_num(floor) or 0)) * storey)
    return full     # ground floor (and anything not given)


def placement(job, site) -> None:
    """Inverter and meter heights from Site questions (inverterAt / inverterFloor, meterAt / meterFloor). The terrace
    is the roof under the inverter mark (else the highest roof in use). Not given: the inverter on the ground floor,
    as before; the meter on the ground floor."""
    a = answers(job)
    floors = floors_below(a)
    storey = _num(a.get('storeyM')) or STOREY_M
    if site.inverter and site.roofs:
        # the terrace the inverter mark is on: the LOWEST roof under the mark (a mark on a cabin's edge is still the
        # terrace), else the nearest roof
        from shapely.geometry import Point
        pt = Point(site.inverter)
        under = [r for r in site.roofs if r["poly"].buffer(2.0).contains(pt)]   # within 2 m: a mark by the cabin wall is on the terrace
        pick = min(under, key=lambda r: float(r.get('heightM') or 0)) if under else min(site.roofs, key=lambda r: r['poly'].distance(pt))
        terrace_z = float(pick.get('heightM') or 0)
    else:
        terrace_z = max((f.height_at(f.poly.centroid.x, f.poly.centroid.y) for f in site.faces), default=0.0)
    site.inverter_z = terrace_z - _drop(a.get('inverterAt') or 'ground', a.get('inverterFloor'), floors, storey, terrace_z)
    site.meter_z = terrace_z - _drop(a.get('meterAt') or 'ground', a.get('meterFloor'), floors, storey, terrace_z)


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
