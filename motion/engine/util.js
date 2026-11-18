// Small deterministic helpers. Nothing here may read the clock or Math.random: every frame is a pure function of t.

export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
export const lerp = (a, b, u) => a + (b - a) * u;
export const smooth = u => { u = clamp(u); return u * u * (3 - 2 * u); };
export const easeInOut = u => { u = clamp(u); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
export const easeOut = u => 1 - Math.pow(1 - clamp(u), 3);
export const easeIn = u => Math.pow(clamp(u), 3);

// seeded PRNG (mulberry32) and a string hash, so "random" choices are the same on every render
export function mulberry(seed) {
  let a = seed >>> 0;
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function hash(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }

// 1D value noise (smooth, seeded): wind, sway, wobble
export function noise1(x, seed = 0) {
  const i = Math.floor(x), f = x - i, r = k => mulberry(hash(seed + ':' + k))();
  return lerp(r(i), r(i + 1), smooth(f)) * 2 - 1;
}

// piecewise keyframes: [{t, v}] -> value at t (eased between keys)
export function keyed(keys, t, ease = easeInOut) {
  if (!keys.length) return 0;
  if (t <= keys[0].t) return keys[0].v;
  for (let i = 1; i < keys.length; i++) if (t <= keys[i].t) {
    const a = keys[i - 1], b = keys[i], u = (t - a.t) / Math.max(1e-6, b.t - a.t);
    return lerp(a.v, b.v, (b.ease || ease)(u));
  }
  return keys[keys.length - 1].v;
}

export const hex = c => typeof c === 'number' ? c : parseInt(String(c).replace('#', ''), 16);
