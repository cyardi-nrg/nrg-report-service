// Version: v5 (2026-10-31) — builds the single-file 3D viewer for site-google-01 (roofs identified from a Google Maps screenshot).
// Inlines three.js r158 (MIT) and the NRG logo — both shared with ../jain-granite/src — into
// src/viewer.template.html so the output opens offline.
//   node build.mjs            -> output/Site-Google-01_3D-Viewer_v5.html
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const VERSION = 'v5';
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'output');
mkdirSync(out, { recursive: true });

const tpl = readFileSync(join(here, 'src/viewer.template.html'), 'utf8');
const three = readFileSync(join(here, '../jain-granite/src/vendor/three-r158.min.js'), 'utf8')
  .replace(/^console\.warn\([^)]*\)/, '0');   // silence the "build/three.min.js is deprecated" console banner
const logo = 'data:image/png;base64,' + readFileSync(join(here, '../jain-granite/src/assets/nrg-logo.png')).toString('base64');

for (const ph of ['/*__THREE__*/', '/*__LOGO__*/']) {
  if (!tpl.includes(ph)) throw new Error(`${ph} placeholder missing from template`);
}
import { existsSync } from 'node:fs';
const lj = join(here, 'design/layout.json');                    // v4: 300 kWp layout from design/layout.py
const layout = existsSync(lj) ? readFileSync(lj, 'utf8') : 'null';
const html = tpl.replace('/*__LOGO__*/', () => logo).replace('/*__THREE__*/', () => three).replace('/*__LAYOUT__*/null', () => layout);
const file = join(out, `Site-Google-01_3D-Viewer_${VERSION}.html`);
writeFileSync(file, html);
console.log(`wrote ${file} (${(html.length / 1024).toFixed(0)} KB)`);
