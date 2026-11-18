// Version: v1 (2026-11-02) — stills (PNG) of the Express Cranes 3D viewer with headless Chromium (Playwright).
//   node build.mjs && node render.mjs      -> output/stills/Express-Cranes_3D_0X-<view>_v1.png
// No video unless the owner asks for one.
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }
const VERSION = 'v1';
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'output'); mkdirSync(join(out, 'stills'), { recursive: true });
const only = process.argv.includes('--only') ? process.argv[process.argv.indexOf('--only') + 1].split(',') : null;
const url = pathToFileURL(join(out, `Express-Cranes_3D-Viewer_${VERSION}.html`)).href + '?capture=1';
const browser = await playwright.chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
let bad = false;
page.on('pageerror', (e) => { bad = true; console.error('PAGE ERROR', e.message); });
page.on('console', (m) => { if (m.type() === 'error') console.error('console:', m.text()); });
await page.goto(url);
await page.waitForFunction(() => window.__nrg3d, null, { timeout: 120000 });
const views = await page.evaluate(() => window.__nrg3d.views);
let i = 0;
for (const v of views) {
  i++;
  if (only && !only.includes(v)) continue;
  await page.evaluate((v) => window.__nrg3d.view(v), v);
  await page.waitForTimeout(300);
  const f = join(out, 'stills', `Express-Cranes_3D_${String(i).padStart(2, '0')}-${v}_${VERSION}.png`);
  await page.screenshot({ path: f });
  console.log('still', f);
}
await browser.close();
if (bad) process.exit(1);
