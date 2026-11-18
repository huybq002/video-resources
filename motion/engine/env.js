// Ambient life: the world keeps living around the story, at its own pace, and reacts to story moments.
// Every element is a pure function of t, drawn with PixiJS Graphics in world coordinates (so the camera and parallax
// apply). These are not decoration loops on the actors: they are the place's own life (birds cross, smoke rises, wheat
// bends under a gust, pigs root, a candle flickers), and the film can trigger them (a gust when the door opens, birds
// scatter when the father runs).
import { Graphics } from 'pixi.js';
import { mulberry, hash, noise1, clamp, lerp, smooth, hex } from './util.js';

const INK = 0x2b2622;

export const AMBIENT = {
  // drifting clouds: {n, y, speed, color}
  clouds(g, t, e) {
    const r = mulberry(hash('cl' + (e.seed || 0)));
    for (let i = 0; i < (e.n ?? 4); i++) {
      const w = 160 + r() * 200, y = (e.y ?? 140) + r() * 120, sp = (e.speed ?? 8) * (0.6 + r() * 0.8);
      const x = ((r() * 2400 + t * sp) % 2600) - 340;
      g.ellipse(x, y, w * 0.5, w * 0.16).fill({ color: hex(e.color || '#ffffff'), alpha: 0.85 }).stroke({ width: 3, color: INK, alpha: 0.6 });
      g.ellipse(x - w * 0.18, y - w * 0.09, w * 0.22, w * 0.14).fill({ color: hex(e.color || '#ffffff'), alpha: 0.9 });
      g.ellipse(x + w * 0.12, y - w * 0.12, w * 0.26, w * 0.16).fill({ color: hex(e.color || '#ffffff'), alpha: 0.9 });
    }
  },
  // a flock crossing the sky every `every` seconds; `scatter` = story time when they burst up (startled)
  birds(g, t, e) {
    const every = e.every ?? 14, k = Math.floor(t / every), lt = t - k * every, r = mulberry(hash('b' + k + (e.seed || 0)));
    const dir = r() > 0.5 ? 1 : -1, y0 = (e.y ?? 220) + r() * 120, n = e.n ?? 5;
    const scat = e.scatter != null && t > e.scatter ? t - e.scatter : null;
    for (let i = 0; i < n; i++) {
      const lag = i * 0.35, u = (lt - lag) / (every * 0.8);
      if (u < 0 || u > 1) continue;
      let x = dir > 0 ? lerp(-100, 2020, u) : lerp(2020, -100, u), y = y0 + Math.sin(i * 1.7) * 30 + Math.sin(lt * 1.3 + i) * 10;
      if (scat != null) { y -= scat * 220 * (1 + i * 0.1); x += dir * scat * 140; }
      const flap = Math.sin(t * (scat != null ? 22 : 12) + i * 1.3) * 9, s = e.size ?? 1;
      g.moveTo(x - 14 * s, y - flap * s).quadraticCurveTo(x - 6 * s, y - 4 * s, x, y).quadraticCurveTo(x + 6 * s, y - 4 * s, x + 14 * s, y - flap * s).stroke({ width: 3, color: INK, cap: 'round' });
    }
  },
  // chimney smoke puffs from (x,y)
  smoke(g, t, e) {
    for (let i = 0; i < 9; i++) {
      const born = Math.floor(t / 0.7) * 0.7 - i * 0.7, age = t - born; if (age < 0) continue;
      const u = age / 6.3, x = e.x + age * 14 + noise1(born + age * 0.4, 3) * 18, y = e.y - age * 46, r = 12 + age * 9;
      g.circle(x, y, r).fill({ color: hex(e.color || '#d9d4cc'), alpha: 0.5 * (1 - u) });
    }
  },
  // wheat or tall grass in the foreground, bending in wind; gusts = [{t, strength}] travel across the frame
  wheat(g, t, e) {
    const r = mulberry(hash('wh' + (e.seed || 0))), n = e.n ?? 140, y0 = e.y ?? 980;
    for (let i = 0; i < n; i++) {
      const x = r() * 2000 - 40, h = (e.h ?? 120) * (0.7 + r() * 0.6), yb = y0 + r() * 100;
      let bend = noise1(t * 0.5 + x * 0.004, 11) * 0.12 + 0.05;
      for (const gu of e.gusts || []) { const front = (t - gu.t) * 700; const d = x - front; if (d < 0 && d > -500) bend += gu.strength * Math.sin((-d / 500) * Math.PI) * 0.5; }
      const tx = x + Math.sin(bend) * h, ty = yb - Math.cos(bend) * h;
      g.moveTo(x, yb).quadraticCurveTo(x + Math.sin(bend) * h * 0.3, yb - h * 0.6, tx, ty).stroke({ width: 3, color: hex(e.color || '#c8962e'), cap: 'round' });
      g.ellipse(tx, ty, 5, 12).fill(hex(e.head || '#e8bf52')).stroke({ width: 1.6, color: INK });
    }
  },
  // pigs that root, walk a little and flick their tails: {pigs:[[x,y,dir,s]]}
  pigs(g, t, e) {
    (e.pigs || []).forEach(([x0, y, dir, s = 1], i) => {
      const r = mulberry(hash('pig' + i)), wander = Math.sin(t * 0.25 + i * 2) * 40;
      const x = x0 + wander, root = Math.max(0, Math.sin(t * 2.4 + i)) * 10 * s, d = Math.cos(t * 0.25 + i * 2) > 0 ? dir : -dir;
      g.ellipse(x, y - 40 * s, 70 * s, 42 * s).fill(0xf2a7b5).stroke({ width: 3, color: INK });
      g.circle(x + d * 66 * s, y - 34 * s + root, 26 * s).fill(0xf2a7b5).stroke({ width: 3, color: INK });
      g.ellipse(x + d * 88 * s, y - 30 * s + root, 10 * s, 8 * s).fill(0xe48a9a).stroke({ width: 2, color: INK });
      g.circle(x + d * 70 * s, y - 44 * s + root, 3 * s).fill(INK);
      for (const lx of [-40, -16, 18, 42]) g.moveTo(x + lx * s, y - 6 * s).lineTo(x + lx * s, y + 8 * s + (Math.abs(wander) > 1 ? Math.sin(t * 6 + lx) * 3 : 0)).stroke({ width: 5 * s, color: INK, cap: 'round' });
      const tw = Math.sin(t * 8 + i) * 6;
      g.moveTo(x - d * 68 * s, y - 52 * s).quadraticCurveTo(x - d * 86 * s, y - 70 * s + tw, x - d * 80 * s, y - 50 * s).stroke({ width: 3, color: INK });
    });
  },
  // candle / lamp glow that flickers: {lights:[[x,y,r]]}
  glow(g, t, e) {
    (e.lights || []).forEach(([x, y, r], i) => {
      const f = 0.85 + noise1(t * 6 + i * 10, 21) * 0.15;
      for (let k = 4; k > 0; k--) g.circle(x, y, r * f * (k / 4)).fill({ color: hex(e.color || '#ffd27a'), alpha: 0.07 });
    });
  },
  // a flag or cloth on a line that ripples: {x,y,w,h,color}
  cloth(g, t, e) {
    const pts = [];
    for (let i = 0; i <= 10; i++) { const u = i / 10; pts.push(e.x + u * e.w, e.y + Math.sin(t * 4 - u * 6) * 8 * u); }
    for (let i = 10; i >= 0; i--) { const u = i / 10; pts.push(e.x + u * e.w, e.y + e.h + Math.sin(t * 4 - u * 6 + 0.6) * 10 * u); }
    g.poly(pts).fill(hex(e.color || '#e8dcc0')).stroke({ width: 3, color: INK });
  },
  // ripples in puddles while it rains: {puddles:[[x,y,w]]}
  ripples(g, t, e) {
    (e.puddles || []).forEach(([x, y, w], i) => {
      g.ellipse(x, y, w, w * 0.22).fill({ color: 0x8aa0b8, alpha: 0.6 }).stroke({ width: 2, color: INK, alpha: 0.5 });
      for (let k = 0; k < 3; k++) { const ph = ((t * 1.3 + k / 3 + i * 0.37) % 1); g.ellipse(x + (k - 1) * w * 0.4, y, w * 0.3 * ph, w * 0.07 * ph).stroke({ width: 2, color: 0xffffff, alpha: 1 - ph }); }
    });
  },
  // a crackling fire: {x,y,s}
  fire(g, t, e) {
    const s = e.s ?? 1;
    for (let i = 0; i < 5; i++) { const h = (60 + noise1(t * 7 + i * 3, 4) * 25) * s, w = 22 * s; const x = e.x + (i - 2) * 16 * s;
      g.poly([x - w / 2, e.y, x, e.y - h, x + w / 2, e.y]).fill({ color: i % 2 ? 0xffb03a : 0xff7a2e, alpha: 0.9 }); }
    for (let k = 4; k > 0; k--) g.circle(e.x, e.y - 30 * s, 120 * s * k / 4).fill({ color: 0xffb04a, alpha: 0.05 });
  },
  // passers-by silhouettes in the far background (a street that does not stop for him): {y, every, color}
  passers(g, t, e) {
    const every = e.every ?? 4;
    for (let k = Math.floor(t / every) - 3; k <= Math.floor(t / every); k++) {
      const r = mulberry(hash('ps' + k)), dir = r() > 0.5 ? 1 : -1, lt = t - k * every, sp = 90 + r() * 50;
      const x = dir > 0 ? -60 + lt * sp : 1980 - lt * sp, y = e.y ?? 700, s = 0.55 + r() * 0.15, ph = lt * 5;
      if (x < -80 || x > 2000) continue;
      const c = hex(e.color || '#6d6a66');
      g.circle(x, y - 150 * s, 18 * s).fill(c);
      g.roundRect(x - 16 * s, y - 130 * s, 32 * s, 70 * s, 8 * s).fill(c);
      g.moveTo(x, y - 60 * s).lineTo(x + Math.sin(ph) * 20 * s, y).stroke({ width: 7 * s, color: c, cap: 'round' });
      g.moveTo(x, y - 60 * s).lineTo(x - Math.sin(ph) * 20 * s, y).stroke({ width: 7 * s, color: c, cap: 'round' });
    }
  },
};

export function drawAmbient(g, t, list) { g.clear(); for (const e of list || []) AMBIENT[e.type]?.(g, t, e); }
