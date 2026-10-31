# Design Lab worker v1.3.0 (2026-10-31) — stage 'video' (per quote / layout): the
# walk-around video of the chosen panel layout option. Owner's own ask: render it
# "after 9 PM or 10 PM when my MacBook will be on ... overnight ... send it to the
# client the next day morning" — the Design Lab queues it for tonight by default.
# Output: 1080p MP4 + a 720p WhatsApp copy under 16 MB, filed under Design.
import logging
import os

from handlers import panels, views
from nrg import scene as scenemod, shots

log = logging.getLogger('designlab')


def run(job) -> dict:
    P = panels.plan(job)
    opt, mods = views.chosen_option(job, P)
    base = panels.base_picture(job, P['model'])
    note = (f"Concept visualisation from the NRG Design Lab · roofs as drawn (Roof design v{P['roof_v']['version']}); "
            'heights as entered — verify on site')
    sc = scenemod.build_scene(P['site'], opt, mods, P['spec'], job.customer, base, note)
    html = os.path.join(job.workdir, 'walkaround.html')
    scenemod.write_viewer(sc, html)
    fps = int(job.input.get('fps') or 30)
    w, h = (int(v) for v in str(job.input.get('size') or '1920x1080').split('x'))
    secs = float(job.input.get('seconds') or sc['duration'])
    full = os.path.join(job.workdir, f'Walk-around {h}p.mp4')
    info = shots.video(html, full, fps=fps, size=(w, h), seconds=secs, log=log.info)
    small = os.path.join(job.workdir, 'Walk-around WhatsApp 720p.mp4')
    small_bytes = shots.shrink(full, small, seconds=info['seconds'])
    job.file_output(full, 'design_video', title=f"{opt['name'].split(' · ')[0]} — walk-around {h}p")
    job.file_output(small, 'design_video', title=f"{opt['name'].split(' · ')[0]} — WhatsApp copy 720p")
    return {'summary': f"Walk-around video of {opt['name']} ({opt['kwp']} kWp): {info['seconds']:.0f} s at {h}p "
                       f"({info['bytes'] / 1e6:.1f} MB) + WhatsApp copy ({small_bytes / 1e6:.1f} MB).",
            'option': opt['name'], 'seconds': info['seconds'], 'mb': round(info['bytes'] / 1e6, 1), 'whatsappMb': round(small_bytes / 1e6, 1)}
