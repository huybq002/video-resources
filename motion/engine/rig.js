// Character rig: a hand-inked stick person with coloured clothes, drawn fresh every frame with PixiJS Graphics.
//
// The rule that matters (owner, 2026-11-17): NO MOTION WITHOUT A PURPOSE. A character at rest only breathes and blinks.
// Everything else comes from a VERB in the film's action list (walk, run, give, hug, kneel, point, beg, eat, ...), each
// with anticipation and settle from the react-spring model, and the mouth moves only on the words the character speaks.
import { Graphics, Container } from 'pixi.js';
import { clamp, lerp, smooth, easeInOut, noise1, hash, hex, mulberry } from './util.js';
import { springWindow, SPRING } from './springs.js';
import { paintActor } from './figure.js';

const INK = 0x2b2622;
const H = 360;                       // standing height in world px at scale 1 (feet to top of head)
const L = { thigh: 78, shin: 78, upper: 62, fore: 58, torso: 112, neck: 10, head: 34 };

// ---------------------------------------------------------------- poses -------------------------------------------------
// angles in radians, 0 = hanging straight down, positive = forward (toward facing)
const REST = { lean: 0, crouch: 0, bob: 0, head: 0, headDrop: 0, aL: [0.12, 0.08], aR: [0.12, 0.08], lL: [0.07, 0], lR: [-0.07, 0], shrug: 0 };

function mix(a, b, w) {
  const o = {};
  for (const k in a) o[k] = Array.isArray(a[k]) ? a[k].map((v, i) => lerp(v, b[k][i], w)) : lerp(a[k], b[k], w);
  return o;
}

// each verb returns a pose for local time lt (seconds since start) and progress u (0..1)
const VERBS = {
  kneel: () => ({ ...REST, crouch: 0.55, lL: [1.5, -1.6], lR: [-0.1, -1.4], lean: 0.12, headDrop: 0.25, aL: [0.5, 0.6], aR: [0.5, 0.6] }),
  lie: () => ({ ...REST, crouch: 0.95, lean: 1.45, headDrop: 0.2, lL: [-1.45, 0.1], lR: [-1.35, 0.1], aL: [0.25, 0.1], aR: [0.35, 0.2] }),
  sit: () => ({ ...REST, crouch: 0.78, lL: [1.55, -2.2], lR: [1.45, -2.25], lean: 0.25, headDrop: 0.6, aL: [0.9, 1.1], aR: [0.95, 1.05] }),
  despair: () => ({ ...REST, crouch: 0.7, lL: [1.5, -2.1], lR: [1.4, -2.2], lean: 0.45, headDrop: 0.9, aL: [1.9, 2.1], aR: [2.0, 2.0] }),
  hug: () => ({ ...REST, lean: 0.08, aL: [1.35, 0.9], aR: [1.45, 0.85] }),
  beg: () => ({ ...REST, lean: 0.25, headDrop: 0.15, aL: [1.1, -0.2], aR: [1.15, -0.25] }),
  give: (lt, u) => ({ ...REST, lean: 0.06, aR: [lerp(0.2, 1.35, smooth(u * 2)), lerp(0.5, 0.05, smooth(u * 2))] }),
  take: (lt, u) => ({ ...REST, lean: 0.05, aR: [lerp(0.2, 1.3, smooth(u * 2.5)) - 0.9 * smooth((u - 0.6) * 2.5), lerp(0.4, 0.1, smooth(u * 2))] }),
  point: () => ({ ...REST, aR: [1.75, 0.0], head: 0.15 }),
  wave: lt => ({ ...REST, aR: [2.5, -0.4 + 0.45 * Math.sin(lt * 9)] }),
  cheer: lt => ({ ...REST, aL: [2.75, 0.2], aR: [2.8, 0.15], bob: Math.abs(Math.sin(lt * 6)) * 14 }),
  toast: lt => ({ ...REST, aR: [lerp(1.2, 2.6, smooth((lt % 2.2) / 0.5)) - 1.4 * smooth(((lt % 2.2) - 1.2) / 0.5), 0.6] }),
  drink: lt => ({ ...REST, head: -0.25, aR: [1.4, 2.0] }),
  eat: lt => ({ ...REST, headDrop: 0.15, aR: [lerp(0.9, 1.25, (Math.sin(lt * 4.5) + 1) / 2), lerp(1.2, 2.3, (Math.sin(lt * 4.5) + 1) / 2)] }),
  count: () => ({ ...REST, headDrop: 0.45, aL: [0.9, 1.2], aR: [0.95, 1.25], lean: 0.08 }),
  sigh: lt => ({ ...REST, headDrop: 0.35, shrug: -0.6 * Math.sin(Math.min(Math.PI, lt * 2.2)), aL: [0.05, 0.05], aR: [0.05, 0.05] }),
  shout: () => ({ ...REST, lean: -0.08, head: -0.15, aL: [0.4, 1.2], aR: [0.6, 0.2] }),
  armsOpen: () => ({ ...REST, aL: [1.8, 0.25], aR: [1.85, 0.2], head: -0.1 }),
  carry: () => ({ ...REST, aR: [0.05, 0.25] }),
  look: () => ({ ...REST }),
  nod: lt => ({ ...REST, headDrop: 0.18 * Math.max(0, Math.sin(lt * 9)) }),
  shake: lt => ({ ...REST, head: 0 }),
  turnAway: () => ({ ...REST, headDrop: 0.2, lean: -0.04 }),
  crossArms: () => ({ ...REST, aL: [1.05, 1.75], aR: [1.1, 1.7], head: -0.08 }),
  dig: lt => ({ ...REST, lean: 0.5, crouch: 0.15, aL: [1.2 + 0.35 * Math.sin(lt * 5), 0.4], aR: [1.3 + 0.35 * Math.sin(lt * 5), 0.4] }),
};
export const VERB_NAMES = [...Object.keys(VERBS), 'walk', 'run', 'talk', 'face'];

// --------------------------------------------------------------- the actor ---------------------------------------------
export class Actor {
  constructor(id, look, actions, words) {
    this.id = id; this.look = look; this.actions = actions.slice().sort((a, b) => a.t0 - b.t0); this.words = words || [];
    this.g = new Graphics(); this.view = new Container(); this.view.addChild(this.g);
    this.seed = hash(id);
    this.travel = this.actions.filter(a => a.verb === 'walk' || a.verb === 'run');
  }

  // where the actor stands at t (world x, y of the feet) and how far it has travelled (for the gait phase)
  place(t, x0, y0) {
    let x = x0, y = y0, dist = 0, moving = null, facing = this.look.facing ?? 1;
    for (const a of this.actions) if (a.verb === 'face' && t >= a.t0) facing = a.dir;
    for (const a of this.travel) {
      if (t < a.t0) break;
      const tx = a.to?.[0] ?? x, ty = a.to?.[1] ?? y, d = Math.hypot(tx - x, ty - y);
      const u = clamp((t - a.t0) / Math.max(0.2, a.t1 - a.t0));
      const e = a.verb === 'run' ? easeRun(u) : easeWalk(u);
      if (Math.abs(tx - x) > 1) facing = Math.sign(tx - x);
      if (t <= a.t1) { moving = a; dist += d * e; x = lerp(x, tx, e); y = lerp(y, ty, e); break; }
      dist += d; x = tx; y = ty;
    }
    return { x, y, dist, moving, facing };
  }

  pose(t, at) {
    let p = { ...REST, aL: [...REST.aL], aR: [...REST.aR], lL: [...REST.lL], lR: [...REST.lR] };
    // breathing: the only motion of a figure at rest
    const br = Math.sin(t * 1.6 + this.seed % 7) * 0.5 + 0.5;
    p.bob = br * 1.6;
    // verbs, blended with springs (anticipation, overshoot, settle)
    let head = 0, shakeW = 0;
    for (const a of this.actions) {
      const f = VERBS[a.verb]; if (!f) { if (a.verb === 'shake') shakeW = 1; continue; }
      if (t < a.t0 - 0.05 || t > a.t1 + 1.2) continue;
      const w = clamp(springWindow(t, a.t0, a.t1, a.spring ? SPRING[a.spring] : SPRING.default, SPRING.gentle), 0, 1.15);
      if (w <= 0.001) continue;
      const lt = t - a.t0, u = clamp(lt / Math.max(0.1, a.t1 - a.t0));
      p = mix(p, f(lt, u, a), Math.min(1, w));
      if (a.verb === 'shake' && t <= a.t1) head = 0.3 * Math.sin(lt * 10);
    }
    // gait
    if (at.moving) {
      const run = at.moving.verb === 'run', stride = run ? 150 : 95, ph = at.dist / stride * Math.PI;
      const amp = run ? 0.75 : 0.45, s = Math.sin(ph);
      const gw = smooth(Math.min(1, (t - at.moving.t0) / 0.25)) * smooth(Math.min(1, (at.moving.t1 - t) / 0.25));
      const gait = {
        ...p, lean: run ? 0.28 : 0.06, bob: (run ? 16 : 7) * Math.abs(Math.cos(ph)),
        lL: [amp * s, -Math.max(0, -Math.cos(ph)) * (run ? 1.4 : 0.8) - 0.1], lR: [-amp * s, -Math.max(0, Math.cos(ph)) * (run ? 1.4 : 0.8) - 0.1],
        aL: run ? [-0.9 * s + 0.3, 1.5] : [-0.5 * s + 0.1, 0.25], aR: run ? [0.9 * s + 0.3, 1.5] : [0.5 * s + 0.1, 0.25],
      };
      if (at.moving.open) { gait.aL = [1.7, 0.2]; gait.aR = [1.75, 0.2]; }       // running with open arms
      if (at.moving.carry) gait.aR = [0.05, 0.25];
      p = mix(p, gait, gw);
    }
    p.head += head;
    return p;
  }

  // mouth: open only on the spoken words of this character (word times from faster-whisper)
  mouth(t) {
    for (const w of this.words) if (t >= w.t0 && t <= w.t1) { const u = (t - w.t0) / Math.max(0.05, w.t1 - w.t0); return 0.35 + 0.65 * Math.sin(u * Math.PI); }
    return 0;
  }

  emotion(t) {
    let e = this.look.mood || 'neutral';
    for (const a of this.actions) if (a.emotion && t >= a.t0 - 0.1 && t <= (a.hold ?? a.t1 + 0.6)) e = a.emotion;
    return e;
  }

  blink(t) { const r = mulberry(this.seed + Math.floor(t / 3.7))(); const k = (t % 3.7) - (1.2 + r * 2); return k > 0 && k < 0.12; }

  // draw at world position; s = scale (1 = full height H). The drawing itself is engine/figure.js
  draw(t, x0, y0, s = 1) {
    const at = this.place(t, x0, y0), p = this.pose(t, at);
    this.g.clear();
    paintActor(this, this.g, t, at, p, s);
    return this.hands;
  }
}

function easeWalk(u) { const a = 0.12; if (u < a) return (u * u) / (2 * a * (1 - a)); if (u > 1 - a) return 1 - ((1 - u) * (1 - u)) / (2 * a * (1 - a)); return (u - a / 2) / (1 - a); }
function easeRun(u) { const a = 0.08; return easeWalk.call(null, u) * 0 + (u < a ? (u * u) / (2 * a * (1 - a)) : u > 1 - a ? 1 - ((1 - u) * (1 - u)) / (2 * a * (1 - a)) : (u - a / 2) / (1 - a)); }
export { H as ACTOR_HEIGHT };
