// Version: v2 (2026-10-30) — builds the single-file 3D viewer for the Architect's Residence (15 modules).
// Inlines three.js r158 (MIT) and the NRG logo — both shared with ../jain-granite/src — into
// src/viewer.template.html so the output opens offline.
//   node build.mjs            -> output/Architect-Residence_3D-Viewer_v2.html
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const VERSION = 'v2';
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
const html = tpl.replace('/*__LOGO__*/', () => logo).replace('/*__THREE__*/', () => three);
const file = join(out, `Architect-Residence_3D-Viewer_${VERSION}.html`);
writeFileSync(file, html);
console.log(`wrote ${file} (${(html.length / 1024).toFixed(0)} KB)`);
