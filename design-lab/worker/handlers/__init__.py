# Design Lab worker v1.13.0 (2026-11-02) — what the Mac can do, stage by stage.
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

HANDLERS: dict = {
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
