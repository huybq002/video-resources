// Render the film's score with Tone.js offline: node motion/tools/score.mjs <film-dir> [--out <film-dir>/out/score.wav]
// reads film.json "score" (sections, hits); writes a 44.1 kHz stereo WAV
import fs from 'fs'; import path from 'path'; import http from 'http'; import { fileURLToPath } from 'url';
import { chromium } from 'playwright-core';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.resolve(process.argv[2] || '.'), i = process.argv.indexOf('--out');
const out = i > 0 ? path.resolve(process.argv[i + 1]) : path.join(dir, 'out', 'score.wav');
const film = JSON.parse(fs.readFileSync(path.join(dir, 'film.json'), 'utf8'));
const spec = { duration: film.duration, ...(film.score || { sections: [{ t0: 0, t1: film.duration, mood: 'calm' }] }) };
const server = http.createServer((req, res) => { const f = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]).replace(/^\/m\//, '')); if (!fs.existsSync(f)) { res.writeHead(404); return res.end(); } res.writeHead(200, { 'content-type': f.endsWith('.js') ? 'text/javascript' : 'text/html' }); fs.createReadStream(f).pipe(res); });
await new Promise(r => server.listen(0, '127.0.0.1', r));
const { chromePath } = await import('./chrome.mjs');
const browser = await chromium.launch({ executablePath: chromePath(), headless: true, args: ['--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage(); page.on('pageerror', e => console.error('page error', String(e)));
await page.goto(`http://127.0.0.1:${server.address().port}/m/score.html`);
await page.waitForFunction(() => window.SCORE_READY, null, { timeout: 60000 });
const b64 = await page.evaluate(s => window.composeScore(s), spec);
fs.mkdirSync(path.dirname(out), { recursive: true }); fs.writeFileSync(out, Buffer.from(b64, 'base64'));
console.log('score', out, (fs.statSync(out).size / 1e6).toFixed(1), 'MB');
await browser.close(); server.close();
