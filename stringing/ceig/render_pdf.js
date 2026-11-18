// Version: v1 (2026-10-27)
// Prints every Jain-Granite_*.html in this folder to an A3-landscape PDF (and a PNG preview
// when PREVIEW_DIR is set). Run after generate_ceig_drawings.py.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const dir = __dirname;
  const preview = process.env.PREVIEW_DIR;
  const browser = await chromium.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'] });
  try {
    for (const f of fs.readdirSync(dir).filter((n) => n.startsWith('Jain-Granite_') && n.endsWith('.html'))) {
      const page = await browser.newPage({ viewport: { width: 1680, height: 1188 } });
      await page.goto('file://' + path.join(dir, f));
      const base = f.replace(/\.html$/, '');
      await page.pdf({ path: path.join(dir, base + '.pdf'), width: '420mm', height: '297mm', printBackground: true, margin: { top: 0, right: 0, bottom: 0, left: 0 } });
      if (preview) await page.screenshot({ path: path.join(preview, base + '.png'), fullPage: true });
      await page.close();
      console.log('wrote', base + '.pdf');
    }
  } finally {
    await browser.close();
  }
})();
