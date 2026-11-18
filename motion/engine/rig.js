// Character rig: a hand-inked stick person with coloured clothes, drawn fresh every frame with PixiJS Graphics.
//
// The rule that matters (owner, 2026-11-17): NO MOTION WITHOUT A PURPOSE. A character at rest only breathes and blinks.
// Everything else comes from a VERB in the film's action list (walk, run, give, hug, kneel, point, beg, eat, ...), each
// with anticipation and settle from the react-spring model, and the mouth moves only on the words the character speaks.
import { Graphics, Container } from 'pixi.js';
import { clamp, lerp, smooth, easeInOut, noise1, hash, hex, mulberry } from './util.js';
import { springWindow, SPRING } from './springs.js';

const INK = 0x2b2622;
const H = 360;                       // standing height in world px at scale 1 (feet to top of head)
const L = { thigh: 78, shin: 78, upper: 62, fore: 58, torso: 112, neck: 10, head: 34 };

// ---------------------------------------------------------------- poses -------------------------------------------------
// angles in radians, 0 = hanging straight down, positive = forward (toward facing)
const REST = { lean: 0, crouch: 0, bob: 0, head: 0, headDrop: 0, aL: [0.12, 0.08], aR: [0.12, 0.08], lL: [0, 0], lR: [0, 0], shrug: 0 };

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

  // draw at world position; s = scale (1 = full height H)
  draw(t, x0, y0, s = 1) {
    const at = this.place(t, x0, y0), p = this.pose(t, at), lk = this.look, g = this.g;
    const F = at.facing, k = s, boil = Math.floor(t * 12);                 // line boil on twos (hand-drawn life, not motion)
    g.clear();
    const jit = (i) => (mulberry(this.seed * 31 + boil * 7 + i)() - 0.5) * 0.9 * k;
    const ink = (pts, w = 4.2, col = INK) => { g.moveTo(pts[0][0] + jit(1), pts[0][1] + jit(2)); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0] + jit(i * 3), pts[i][1] + jit(i * 5)); g.stroke({ width: w * k, color: col, cap: 'round', join: 'round' }); };
    const X = at.x, Y = at.y;
    // shadow
    g.ellipse(X, Y + 2 * k, 46 * k, 9 * k).fill({ color: 0x000000, alpha: 0.12 });
    const crouch = p.crouch * (L.thigh + L.shin) * 0.9 * k;
    const hip = [X, Y - (L.thigh + L.shin) * k + crouch - p.bob * k];
    const lean = p.lean * F;
    const neckB = [hip[0] + Math.sin(lean) * L.torso * k, hip[1] - Math.cos(lean) * L.torso * k];
    const sh = [lerp(hip[0], neckB[0], 0.86), lerp(hip[1], neckB[1], 0.86) - p.shrug * 6 * k];
    const limb = (base, a1, a2, l1, l2) => {
      const j = [base[0] + Math.sin(a1) * F * l1 * k, base[1] + Math.cos(a1) * l1 * k];
      const e = [j[0] + Math.sin(a1 + a2) * F * l2 * k, j[1] + Math.cos(a1 + a2) * l2 * k];
      return [base, j, e];
    };
    const legBack = limb(hip, p.lR[0], p.lR[1], L.thigh, L.shin), legFront = limb(hip, p.lL[0], p.lL[1], L.thigh, L.shin);
    const armBack = limb(sh, p.aR[0] + lean, p.aR[1], L.upper, L.fore), armFront = limb(sh, p.aL[0] + lean, p.aL[1], L.upper, L.fore);
    // keep feet on the ground when standing (no sliding legs through the floor)
    const clampFoot = leg => { if (leg[2][1] > Y) { const d = leg[2][1] - Y; leg[1][1] -= d * 0.5; leg[2][1] = Y; } };
    clampFoot(legBack); clampFoot(legFront);
    const shoe = hex(lk.shoes || '#3c3a37'), skin = hex(lk.skin || '#f4dcc2'), shirt = hex(lk.shirt || '#4f86c6');
    const drawLeg = leg => { ink(leg, 4.4); g.ellipse(leg[2][0] + 7 * F * k, leg[2][1] - 3 * k, 12 * k, 6 * k).fill(shoe).stroke({ width: 2 * k, color: INK }); };
    const drawArm = (arm, sleeve) => {
      ink([arm[0], arm[1]], 9 * k > 0 ? 4.2 : 4.2);
      if (sleeve) { g.moveTo(arm[0][0], arm[0][1]); g.lineTo(lerp(arm[0][0], arm[1][0], 0.55), lerp(arm[0][1], arm[1][1], 0.55)); g.stroke({ width: 13 * k, color: sleeve, cap: 'round' }); }
      ink([arm[1], arm[2]], 4.2); g.circle(arm[2][0], arm[2][1], 6.5 * k).fill(skin).stroke({ width: 2 * k, color: INK });
    };
    drawLeg(legBack); drawArm(armBack, shirt);
    // torso: a tunic shape between shoulders and hips
    const tw = 30 * k, bw = (lk.skirt ? 44 : 34) * k;
    const nx = Math.cos(lean), ny = Math.sin(lean);
    const tunic = [sh[0] - tw * nx, sh[1] - tw * ny, sh[0] + tw * nx, sh[1] + tw * ny, hip[0] + bw * nx + 4 * k, hip[1] + bw * ny + 18 * k, hip[0] - bw * nx - 4 * k, hip[1] - bw * ny + 18 * k];
    g.poly(tunic).fill(shirt).stroke({ width: 3.2 * k, color: INK, join: 'round' });
    if (lk.vest) g.poly([tunic[0] + 6 * k, tunic[1], sh[0] - 6 * k * F, sh[1] + 4 * k, hip[0] - 4 * k * F, hip[1] + 14 * k, tunic[6] + 6 * k, tunic[7] - 4 * k]).fill(hex(lk.vest)).stroke({ width: 2.4 * k, color: INK });
    if (lk.apron) g.poly([hip[0] - 26 * k, sh[1] + 40 * k, hip[0] + 26 * k, sh[1] + 40 * k, hip[0] + 30 * k, hip[1] + 22 * k, hip[0] - 30 * k, hip[1] + 22 * k]).fill(hex(lk.apron)).stroke({ width: 2.4 * k, color: INK });
    if (lk.belt) { g.moveTo(hip[0] - bw * 0.9, hip[1] + 4 * k).lineTo(hip[0] + bw * 0.9, hip[1] + 4 * k).stroke({ width: 5 * k, color: hex(lk.belt) }); }
    if (lk.rags) for (let i = 0; i < 4; i++) { const xx = hip[0] - bw + i * bw * 0.6; g.poly([xx, hip[1] + 16 * k, xx + 9 * k, hip[1] + 30 * k, xx + 18 * k, hip[1] + 16 * k]).fill(shirt).stroke({ width: 2 * k, color: INK }); }
    drawLeg(legFront);
    // head
    const hd = p.headDrop, hc = [neckB[0] + Math.sin(lean + hd * 0.6) * (L.neck + L.head) * k, neckB[1] - Math.cos(lean + hd * 0.6) * (L.neck + L.head) * k];
    ink([neckB, [lerp(neckB[0], hc[0], 0.5), lerp(neckB[1], hc[1], 0.5)]], 4);
    const R = L.head * k;
    g.circle(hc[0], hc[1], R).fill(skin).stroke({ width: 3.2 * k, color: INK });
    this.drawHair(g, hc, R, F, k, lk);
    this.drawFace(g, t, hc, R, F, k, p, hd);
    drawArm(armFront, shirt);
    // held prop (drawn by the scene through this hook)
    this.hands = { front: armFront[2], back: armBack[2], head: hc, hip, facing: F, scale: k };
    this.at = at;
    return this.hands;
  }

  drawHair(g, c, R, F, k, lk) {
    const hair = hex(lk.hair || '#3a2a1e');
    if (lk.hairStyle === 'bald') { if (lk.fringe !== false) g.moveTo(c[0] - F * R * 0.25 + Math.cos(Math.PI * 1.05) * R * 0.95, c[1] - R * 0.1 + Math.sin(Math.PI * 1.05) * R * 0.95).arc(c[0] - F * R * 0.25, c[1] - R * 0.1, R * 0.95, Math.PI * 1.05, Math.PI * 1.35).stroke({ width: 5 * k, color: hex(lk.hair || '#d9d4cc') }); }
    else if (lk.hairStyle === 'long') { g.ellipse(c[0] - F * R * 0.2, c[1] - R * 0.35, R * 1.08, R * 0.75).fill(hair); g.rect(c[0] - F * R * 0.2 - R * 1.0, c[1] - R * 0.3, R * 0.5, R * 1.5).fill(hair); }
    else { g.ellipse(c[0] - F * R * 0.12, c[1] - R * 0.55, R * 1.02, R * 0.55).fill(hair).stroke({ width: 2.4 * k, color: INK }); }
    if (lk.headscarf) g.ellipse(c[0], c[1] - R * 0.5, R * 1.12, R * 0.62).fill(hex(lk.headscarf)).stroke({ width: 2.4 * k, color: INK });
    if (lk.beard) g.ellipse(c[0] + F * R * 0.25, c[1] + R * 0.62, R * 0.62, R * 0.42).fill(hex(lk.beard)).stroke({ width: 2 * k, color: INK });
  }

  drawFace(g, t, c, R, F, k, p, hd) {
    const turn = clamp(p.head, -0.6, 0.6), fx = c[0] + F * R * (0.32 + turn * 0.3), fy = c[1] + hd * R * 0.25;
    const e = this.emotion(t), shut = this.blink(t) || e === 'ashamed';
    const ex = [fx - R * 0.28, fx + R * 0.22], ey = fy - R * 0.12;
    // eyes
    for (const x of ex) {
      if (shut) g.moveTo(x - 4 * k, ey + 1 * k).lineTo(x + 4 * k, ey + 1 * k).stroke({ width: 2.6 * k, color: INK, cap: 'round' });
      else if (e === 'surprised') g.circle(x, ey, 4.6 * k).fill(0xffffff).stroke({ width: 2.2 * k, color: INK }).circle(x, ey, 2 * k).fill(INK);
      else g.ellipse(x, ey, 3.2 * k, 4.2 * k).fill(INK);
    }
    // brows: the emotion lives here (worried and angry are one flip apart: check at final size)
    const brow = { angry: [0.45, -0.45], worried: [-0.4, 0.4], sad: [-0.35, 0.35], surprised: [0, 0], happy: [-0.1, 0.1], ashamed: [-0.3, 0.3] }[e] || [0, 0];
    const by = ey - 9 * k - (e === 'surprised' ? 4 * k : 0);
    ex.forEach((x, i) => { const a = brow[i] * (i ? 1 : 1) * F; g.moveTo(x - 6 * k, by + Math.sin(-a) * 5 * k * (i ? -1 : 1)).lineTo(x + 6 * k, by + Math.sin(a) * 5 * k * (i ? -1 : 1)).stroke({ width: 2.6 * k, color: INK, cap: 'round' }); });
    // mouth: talking opens it, the emotion shapes it
    const m = this.mouth(t), mx = fx - R * 0.03, my = fy + R * 0.42;
    if (m > 0.05) g.ellipse(mx, my, (5 + 2 * m) * k, (2 + 6 * m) * k).fill(0x7a2e2a).stroke({ width: 2 * k, color: INK });
    else if (e === 'happy') g.moveTo(mx + Math.cos(0.15 * Math.PI) * 9 * k, my - 4 * k + Math.sin(0.15 * Math.PI) * 9 * k).arc(mx, my - 4 * k, 9 * k, 0.15 * Math.PI, 0.85 * Math.PI).stroke({ width: 2.6 * k, color: INK, cap: 'round' });
    else if (e === 'sad' || e === 'worried' || e === 'ashamed') g.moveTo(mx + Math.cos(1.2 * Math.PI) * 8 * k, my + 7 * k + Math.sin(1.2 * Math.PI) * 8 * k).arc(mx, my + 7 * k, 8 * k, 1.2 * Math.PI, 1.8 * Math.PI).stroke({ width: 2.6 * k, color: INK, cap: 'round' });
    else if (e === 'angry') g.moveTo(mx - 8 * k, my + 1 * k).lineTo(mx + 8 * k, my - 1 * k).stroke({ width: 3 * k, color: INK, cap: 'round' });
    else if (e === 'surprised') g.ellipse(mx, my, 5 * k, 7 * k).fill(0x7a2e2a).stroke({ width: 2 * k, color: INK });
    else g.moveTo(mx - 6 * k, my).lineTo(mx + 6 * k, my).stroke({ width: 2.6 * k, color: INK, cap: 'round' });
    if (this.look.moustache) g.moveTo(mx - 10 * k, my - 7 * k).quadraticCurveTo(mx, my - 12 * k, mx + 10 * k, my - 7 * k).stroke({ width: 4 * k, color: hex(this.look.moustache === true ? '#efe9df' : this.look.moustache), cap: 'round' });
    if (e === 'sad' && this.look.tears !== false && Math.floor(t * 2) % 2 === 0) g.circle(ex[0], ey + 9 * k + ((t * 30) % 14) * k, 2.4 * k).fill(0x7fb4e0);
    // cheeks
    g.circle(fx - R * 0.48, fy + R * 0.22, 5 * k).fill({ color: 0xe88a7a, alpha: 0.35 });
  }
}

function easeWalk(u) { const a = 0.12; if (u < a) return (u * u) / (2 * a * (1 - a)); if (u > 1 - a) return 1 - ((1 - u) * (1 - u)) / (2 * a * (1 - a)); return (u - a / 2) / (1 - a); }
function easeRun(u) { const a = 0.08; return easeWalk.call(null, u) * 0 + (u < a ? (u * u) / (2 * a * (1 - a)) : u > 1 - a ? 1 - ((1 - u) * (1 - u)) / (2 * a * (1 - a)) : (u - a / 2) / (1 - a)); }
export { H as ACTOR_HEIGHT };
