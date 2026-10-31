# Design Lab worker v1.3.0 (2026-10-31) — pictures and video of the 3D viewer,
# in a headless browser (Playwright + Chromium, installed by mac/install.sh).
import os
import sys
import time


def _launch(p):
    args = ['--ignore-gpu-blocklist']
    if sys.platform != 'darwin':                       # no GPU (servers / test box): software WebGL
        args += ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    exe = os.environ.get('CHROMIUM_PATH') or None
    return p.chromium.launch(args=args, executable_path=exe)


def stills(html_path: str, out_dir: str, size=(1920, 1080)) -> list[tuple[str, str]]:
    """One picture per named view. Returns [(view, png path)]."""
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={'width': size[0], 'height': size[1]}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto('file://' + os.path.abspath(html_path) + '?capture=1')
        page.wait_for_function('window.__nrg3d', timeout=120000)
        time.sleep(1.0)                                    # ground picture texture
        for v in page.evaluate('window.__nrg3d.views'):
            page.evaluate('v => window.__nrg3d.view(v)', v)
            page.wait_for_timeout(250)
            path = os.path.join(out_dir, f'3D-{v}.png')
            page.screenshot(path=path)
            out.append((v, path))
        browser.close()
        if errors:
            raise RuntimeError('3D viewer error: ' + errors[0])
    return out


def video(html_path: str, out_path: str, fps: int = 30, size=(1920, 1080), crf: int = 21, maxrate: str = '6M', seconds: float | None = None, log=None) -> dict:
    """Plays the walk-around (window.__nrg3d.time) frame by frame and encodes H.264 MP4 with ffmpeg
    (imageio-ffmpeg's own copy — nothing to install separately). Frames go straight into ffmpeg, never to disk."""
    import subprocess
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    with sync_playwright() as p:
        browser = _launch(p)
        page = browser.new_page(viewport={'width': size[0], 'height': size[1]}, device_scale_factor=1)
        page.goto('file://' + os.path.abspath(html_path) + '?capture=1')
        page.wait_for_function('window.__nrg3d', timeout=120000)
        time.sleep(1.0)
        duration = float(seconds or page.evaluate('window.__nrg3d.duration'))
        n = int(round(duration * fps))
        enc = subprocess.Popen([ff, '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps), '-c:v', 'mjpeg', '-i', '-',
                                '-c:v', 'libx264', '-preset', 'medium', '-crf', str(crf), '-maxrate', maxrate, '-bufsize', '12M',
                                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-metadata', 'artist=NRG Technologists', out_path],
                               stdin=subprocess.PIPE)
        started = time.time()
        for i in range(n):
            page.evaluate('t => window.__nrg3d.time(t)', i / fps)
            enc.stdin.write(page.screenshot(type='jpeg', quality=92))
            if log and i and i % (fps * 5) == 0:
                log(f'video: {i}/{n} frames ({time.time() - started:.0f} s)')
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError('ffmpeg could not encode the video')
        browser.close()
    return {'frames': n, 'seconds': duration, 'bytes': os.path.getsize(out_path)}


def shrink(src: str, out_path: str, height: int = 720, target_mb: float = 15.0, seconds: float = 40.0) -> int:
    """A WhatsApp copy: 720p and under 16 MB (bitrate worked out from the length)."""
    import subprocess
    import imageio_ffmpeg
    import shutil as _sh
    kbps = int(target_mb * 8 * 1024 / max(1.0, seconds) * 0.92)
    src_kbps = os.path.getsize(src) * 8 / 1024 / max(1.0, seconds)
    if src_kbps <= kbps and _height(src) <= height:          # already small enough — never make it bigger
        _sh.copyfile(src, out_path)
        return os.path.getsize(out_path)
    kbps = min(kbps, int(src_kbps))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', src, '-vf', f'scale=-2:{height}', '-c:v', 'libx264',
                    '-preset', 'medium', '-b:v', f'{kbps}k', '-maxrate', f'{kbps}k', '-bufsize', f'{kbps * 2}k', '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart', out_path], check=True)
    return os.path.getsize(out_path)


def _height(path: str) -> int:
    import subprocess, re
    import imageio_ffmpeg
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-i', path], capture_output=True, text=True)
    m = re.search(r', (\d{2,5})x(\d{2,5})', r.stderr)
    return int(m.group(2)) if m else 99999
