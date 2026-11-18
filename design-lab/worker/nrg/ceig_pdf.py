# Design Lab worker v1.8.0 (2026-10-31) — prints CEIG sheets (HTML with one A3 SVG each) to PDF
# with the worker's own Chromium (the same one the 3D pictures use), plus a PNG preview, and joins
# a set into one PDF for the CEIG submission.
import os


def render(sheets: list[tuple[str, str]], out_dir: str, preview: bool = True) -> list[dict]:
    """sheets: [(name, html)] → [{'name', 'pdf', 'png'}]"""
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        from nrg.shots import _launch
        browser = _launch(p)          # same Chromium the 3D pictures use (and its sandbox fallback)
        try:
            for name, doc in sheets:
                page = browser.new_page(viewport={'width': 1680, 'height': 1188}, device_scale_factor=1.5)
                page.set_content(doc, wait_until='load')
                pdf = os.path.join(out_dir, name + '.pdf')
                page.pdf(path=pdf, width='420mm', height='297mm', print_background=True, margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'})
                png = None
                if preview:
                    png = os.path.join(out_dir, name + '.png')
                    page.screenshot(path=png, full_page=True)
                page.close()
                out.append({'name': name, 'pdf': pdf, 'png': png})
        finally:
            browser.close()
    return out


def join(pdfs: list[str], out_path: str) -> str:
    """One PDF from several (the whole CEIG set). Uses pypdf if present, else Chromium can't join — returns ''."""
    try:
        from pypdf import PdfWriter
    except ImportError:
        return ''
    w = PdfWriter()
    for f in pdfs:
        w.append(f)
    with open(out_path, 'wb') as fh:
        w.write(fh)
    return out_path
