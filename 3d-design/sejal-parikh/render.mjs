// Version: v1 (2026-10-29) — renders the stills (PNG) and the walk-around video (MP4, H.264) for
// Mrs. Sejal Parikh Residence from the built viewer, using headless Chromium (Playwright) + ffmpeg.
// Same script as ../jain-granite/render.mjs, with this project's file names.
//   node build.mjs && node render.mjs                 -> stills + 1080p video
//   node render.mjs --stills                          -> stills only
//   node render.mjs --video --fps 30 --size 1920x1080 -> video only
//   node render.mjs --only 10,20,35                   -> test frames at those seconds
//   node render.mjs --rebrand output/<older>.mp4      -> lay this version's brand box + footnote over an older video
import { spawn } from 'node:child_process';
import { mkdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('/opt/node22/lib/node_modules/playwright'); }

const VERSION = 'v1';
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, 'output');
mkdirSync(join(out, 'stills'), { recursive: true });

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const doStills = args.includes('--stills') || !args.includes('--video');
const doVideo = args.includes('--video') || !args.includes('--stills');
const fps = Number(opt('--fps', 30));
const [W, H] = opt('--size', '1920x1080').split('x').map(Number);
const only = opt('--only', null);          // e.g. --only 10,20,35  -> test frames at those seconds
const rebrand = opt('--rebrand', null);    // older video to re-brand

const url = pathToFileURL(join(out, `Sejal-Parikh_3D-Viewer_${VERSION}.html`)).href + '?capture=1';
const browser = await playwright.chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
page.on('pageerror', (e) => console.error('PAGE ERROR', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.error('console:', m.text()); });
await page.goto(url);
await page.waitForFunction(() => window.__nrg3d);
const info = await page.evaluate(() => ({ d: window.__nrg3d.duration, v: window.__nrg3d.views }));

if (only) {
  for (const t of only.split(',').map(Number)) {
    await page.evaluate((t) => window.__nrg3d.time(t), t);
    await page.screenshot({ path: join(out, `test_t${String(t).padStart(2, '0')}.png`) });
    console.log('test frame', t);
  }
  await browser.close();
  process.exit(0);
}

if (rebrand) {
  // transparent full-frame PNG holding only the brand box and the footnote, exactly as the page lays them out
  const png = join(out, `_overlay_${W}x${H}_${VERSION}.png`);
  await page.evaluate(() => {
    for (const id of ['c', 'labels', 'caption', 'spec', 'compass']) document.getElementById(id).style.visibility = 'hidden';
    document.documentElement.style.background = document.body.style.background = 'transparent';
  });
  await page.screenshot({ path: png, omitBackground: true });
  await browser.close();
  const file = join(out, `Sejal-Parikh_Walkaround_${H}p_${VERSION}.mp4`);
  await new Promise((res, rej) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-i', rebrand, '-i', png,
    '-filter_complex', `[0:v]scale=${W}:${H}[b];[b][1:v]overlay=0:0:format=auto`,
    '-c:v', 'libx264', '-preset', 'slow', '-crf', H >= 1080 ? '21' : '22', '-maxrate', H >= 1080 ? '3.2M' : '1.8M', '-bufsize', '6M',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-metadata', `title=Mrs. Sejal Parikh Residence 42.48 kWp rooftop solar walk-around ${VERSION}`, '-metadata', 'artist=NRG Technologists', file],
  { stdio: 'inherit' }).on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
  console.log('video', file, (statSync(file).size / 1e6).toFixed(1), 'MB');
  process.exit(0);
}

if (doStills) {
  for (const [i, v] of info.v.entries()) {
    await page.evaluate((v) => window.__nrg3d.view(v), v);
    const f = join(out, 'stills', `Sejal-Parikh_3D_${String(i + 1).padStart(2, '0')}-${v}_${VERSION}.png`);
    await page.screenshot({ path: f });
    console.log('still', f);
  }
}

if (doVideo) {
  const file = join(out, `Sejal-Parikh_Walkaround_${H}p_${VERSION}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', H >= 1080 ? '21' : '22', '-maxrate', H >= 1080 ? '3.2M' : '1.8M', '-bufsize', '6M',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-metadata', `title=Mrs. Sejal Parikh Residence 42.48 kWp rooftop solar walk-around ${VERSION}`, '-metadata', 'artist=NRG Technologists', file],
  { stdio: ['pipe', 'inherit', 'inherit'] });
  const done = new Promise((res, rej) => ff.on('close', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
  const n = Math.round(info.d * fps);
  const t0 = Date.now();
  for (let i = 0; i <= n; i++) {
    await page.evaluate((t) => window.__nrg3d.time(t), i / fps);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % (fps * 2) === 0) console.log(`frame ${i}/${n}  ${((Date.now() - t0) / 1000).toFixed(0)} s`);
  }
  ff.stdin.end();
  await done;
  console.log('video', file, (statSync(file).size / 1e6).toFixed(1), 'MB');
}
await browser.close();
