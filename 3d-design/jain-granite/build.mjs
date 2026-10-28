// Version: v1 (2026-10-28) — builds the single-file 3D viewer for Jain Granite & Marble.
// Inlines three.js r158 (MIT, src/vendor) into src/viewer.template.html so the output opens offline.
//   node build.mjs            -> output/Jain-Granite_3D-Viewer_v1.html
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const VERSION = 'v1';
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'output');
mkdirSync(out, { recursive: true });

const tpl = readFileSync(join(here, 'src/viewer.template.html'), 'utf8');
const three = readFileSync(join(here, 'src/vendor/three-r158.min.js'), 'utf8')
  .replace(/^console\.warn\([^)]*\)/, '0');   // silence the "build/three.min.js is deprecated" console banner

if (!tpl.includes('/*__THREE__*/')) throw new Error('THREE placeholder missing from template');
const html = tpl.replace('/*__THREE__*/', () => three);
const file = join(out, `Jain-Granite_3D-Viewer_${VERSION}.html`);
writeFileSync(file, html);
console.log(`wrote ${file} (${(html.length / 1024).toFixed(0)} KB)`);
