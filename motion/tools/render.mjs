// Render a hezb-motion film: node motion/tools/render.mjs <film-dir> [--fps 30] [--workers 3] [--out <film-dir>/out/video.mp4]
//   [--still t1,t2,...]  write review stills instead (PNG, <film-dir>/out/still-<t>.png)
//   [--from s --to s]    render only part of the film (a test cut)
// Each worker opens its own headless Chromium on the film page and renders a contiguous range of frames in order
// (particles are stepped, so order matters inside a range); JPEG screenshots are piped to ffmpeg; the segments are joined.
// Technique after lemo-opuscar's core/render/video.mjs (MIT).
import fs from 'fs'; import path from 'path'; import http from 'http'; import { spawn, execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2), opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const dir = path.resolve(args[0] || '.');
const film = JSON.parse(fs.readFileSync(path.join(dir, 'film.json'), 'utf8'));
const FPS = +opt('--fps', film.fps || 30), WK = +opt('--workers', 3), [FW, FH] = (opt('--size', null) || (film.size || [1920, 1080]).join('x')).split('x').map(Number);
const out = path.resolve(opt('--out', path.join(dir, 'out', 'video.mp4')));
fs.mkdirSync(path.dirname(out), { recursive: true });

// ---- static server: /m/ = engine, /f/ = film folder
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.ttf': 'font/ttf', '.glb': 'model/gltf-binary', '.png': 'image/png', '.wasm': 'application/wasm' };
const server = http.createServer((req, res) => {
  const u = decodeURIComponent(req.url.split('?')[0]);
  const file = u.startsWith('/m/') ? path.join(ROOT, u.slice(3)) : u.startsWith('/f/') ? path.join(dir, u.slice(3)) : null;
  if (!file || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'content-type': TYPES[path.extname(file)] || 'application/octet-stream' }); fs.createReadStream(file).pipe(res);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const PORT = server.address().port;

import { chromePath } from './chrome.mjs';

async function openPage() {
  const browser = await chromium.launch({ executablePath: chromePath(), headless: true, args: [...(process.env.RENDER_GL === 'gpu' ? ['--use-angle=default', '--enable-gpu', '--ignore-gpu-blocklist'] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']), '--autoplay-policy=no-user-gesture-required'] });
  const page = await browser.newPage({ viewport: { width: FW, height: FH }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e))); page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  await page.goto(`http://127.0.0.1:${PORT}/m/page.html?film=/f/film.json&size=${FW}x${FH}&fps=${FPS}`);
  await page.waitForFunction(() => window.READY || window.BOOT_ERROR, null, { timeout: 180000 });
  const be = await page.evaluate(() => window.BOOT_ERROR);
  if (be) throw new Error('page failed to boot: ' + be);
  return { browser, page, errors };
}

const stills = opt('--still', null);
if (stills) {
  const { browser, page, errors } = await openPage();
  for (const s of stills.split(',').map(Number)) {
    await page.evaluate(t => window.render(t), s);
    const p = path.join(dir, 'out', `still-${String(s.toFixed(2)).padStart(7, '0')}.png`); await page.screenshot({ path: p }); console.log('still', p);
  }
  if (errors.length) console.log('page errors:', errors.slice(0, 5).join('\n'));
  await browser.close(); server.close(); process.exit(0);
}

const from = +opt('--from', 0), to = Math.min(+opt('--to', film.duration), film.duration);
const F0 = Math.round(from * FPS), F1 = Math.round(to * FPS), TOTAL = F1 - F0, per = Math.ceil(TOTAL / WK), t0 = Date.now();
const seg = fs.mkdtempSync(path.join(path.dirname(out), '.segs-'));
await Promise.all([...Array(WK)].map(async (_, w) => {
  const a = F0 + w * per, b = Math.min(F1, a + per); if (a >= b) return;
  const { browser, page, errors } = await openPage();
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', `seg_${w}.mp4`], { cwd: seg, stdio: ['pipe', 'inherit', 'inherit'] });
  const closed = new Promise(r => ff.on('close', r));
  for (let f = a; f < b; f++) {
    await page.evaluate(t => window.render(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - a) % 90 === 0) console.log(`w${w} ${f - a}/${b - a} ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end(); const code = await closed; await browser.close();
  if (errors.length) console.log(`w${w} page errors:`, errors.slice(0, 3).join(' | '));
  if (code !== 0) throw new Error('ffmpeg failed for worker ' + w);
}));
fs.writeFileSync(path.join(seg, 'list.txt'), [...Array(WK)].map((_, w) => `file 'seg_${w}.mp4'`).filter((_, w) => F0 + w * per < F1).join('\n'));
execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', 'list.txt', '-c', 'copy', 'joined.mp4'], { cwd: seg });
fs.renameSync(path.join(seg, 'joined.mp4'), out); fs.rmSync(seg, { recursive: true, force: true });
console.log('done', out, TOTAL, 'frames', ((Date.now() - t0) / 1000).toFixed(0) + 's');
server.close();
