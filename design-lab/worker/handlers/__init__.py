# Design Lab worker v1.15.0 (2026-11-02) — what the Mac can do, stage by stage.
#
# Each handler gets a Job (nrg/jobs.py), files its drawings with
# job.file_output(...) and returns {'summary': '...', ...data}. The data
# is saved as the stage's new version (draft) for the owner to approve.
#
# Built in phases (owner's order: core first, then roof model, layouts,
# 3D / video, then stringing / walkway / earthing / tray / SLD / CEIG).
# A stage that is not built yet fails with a plain message instead of
# pretending — the Design Lab shows it on the stage.
from nrg.jobs import Job, NotBuiltYet

from handlers import cad as _cad, roofs as _roofs, panels as _panels, views as _views, video as _video, structure as _structure, stringing as _stringing, layouts as _layouts, sld as _sld, ceig as _ceig, proposal as _proposal

# v1.14.1: Base design needs scipy + pymupdf. If they are not installed yet the rest of the worker still runs, and a
# Base design job fails with the reason instead of the whole worker stopping.
try:
    from handlers import base as _base
    _base_run = _base.run
except Exception as _e:                                     # noqa: BLE001
    import os as _os
    _why = f'{type(_e).__name__}: {_e}'
    _p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'logs', 'packages-error.txt')
    if _os.path.exists(_p):
        _why += ' — pip said: ' + open(_p).read().replace('\n', ' | ')[:400]

    def _base_run(job, _why=_why):
        raise RuntimeError(f'Base design can’t run on this Mac yet — a package it needs is missing ({_why}). '
                           'Send this message to Claude.')

HANDLERS: dict = {
    'base': _base_run,      # v1.14.0: start from a base design (SolarEdge screenshot / AutoCAD PDF) — panels + roofs read off it
    'cad': _cad.run,        # phase 2: AutoCAD → plan picture with scale + roof suggestions
    'roofs': _roofs.run,    # phase 3: roof & shade report
    'panels': _panels.run,  # phase 3: panel layout options for the quote
    'views': _views.run,    # phase 4: interactive 3D + still pictures of the chosen option
    'video': _video.run,    # phase 4: walk-around video (queued for tonight by the Design Lab)
    'structure': _structure.run,  # structure drawing sheets for the saved structure
    'stringing': _stringing.run,  # phase 5: strings, MPPTs, single vs Y-connector runs, DC cable into the BOM
    'layouts': _layouts.run,      # phase 5: walkway, cable tray, earthing layouts + lengths into the BOM
    'sld': _sld.run,              # phase 5c: single line diagram (A3 PDF)
    'ceig': _ceig.run,            # phase 5c: the CEIG drawing set — SLD + 5 layout sheets + one combined PDF
    'proposal': _proposal.run,    # client design proposal PDF (logo, system, layout, 3D views) — sent before the quote
}

PHASE = {
    'roofs': 'phase 2 (roof model)', 'panels': 'phase 3 (panel layout engine)', 'structure': 'phase 3 (structure drawings)',
    'views': 'phase 4 (3D)', 'video': 'phase 4 (video)', 'stringing': 'phase 5', 'layouts': 'phase 5', 'bom': 'phase 5',
    'sld': 'phase 5', 'ceig': 'phase 5',
}


def run(job: Job) -> dict:
    h = HANDLERS.get(job.stage)
    if not h:
        raise NotBuiltYet(f"The Mac can't do “{job.stage}” yet — it comes in {PHASE.get(job.stage, 'a later phase')}. Nothing was changed.")
    return h(job)


def capabilities() -> list[str]:
    return sorted(HANDLERS)
