// How a person is drawn (PixiJS Graphics, every frame). Storybook style: round outlined limbs with volume, tunics and long
// robes that follow the legs, mantles, sashes, headcloths, hair and beards with shape, eyes with whites and highlights,
// sandals, a soft cell shade on the side away from the light and a ground shadow.
//
// look keys: skin shirt(=tunic or robe colour) sleeve vest apron belt sash trim mantle headcloth band hair hairStyle(short|long|bald|curly)
//            beard moustache shoes sandals legs robe(true: tunic reaches the feet) skirt rags pack
import { clamp, lerp, hex, mulberry } from './util.js';

const INK = 0x2b2622;

export function shade(c, f) {
  const r = (c >> 16) & 255, g = (c >> 8) & 255, b = c & 255;
  const m = v => Math.max(0, Math.min(255, Math.round(v * f)));
  return (m(r) << 16) | (m(g) << 8) | m(b);
}
const mid = (a, b, u = 0.5) => [lerp(a[0], b[0], u), lerp(a[1], b[1], u)];
const add = (a, b, k = 1) => [a[0] + b[0] * k, a[1] + b[1] * k];
const rad = d => d * Math.PI / 180;

export const DIM = { thigh: 74, shin: 72, upper: 58, fore: 54, torso: 108, neck: 8, head: 40 };

// a limb as a thick outlined sausage: ink pass over every segment, then colour passes on top (no seams at the joints)
function sausage(g, pts, w, outline, fills) {
  g.moveTo(pts[0][0], pts[0][1]); for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.stroke({ width: w + outline * 2, color: INK, cap: 'round', join: 'round' });
  fills.forEach(([a, b, col], i) => {
    g.moveTo(pts[a][0], pts[a][1]); g.lineTo(pts[b][0], pts[b][1]);
    g.stroke({ width: w, color: col, cap: 'round', join: 'round' });
  });
}

export function paintActor(A, g, t, at, p, k) {
  const lk = A.look, F = at.facing, seed = A.seed;
  const skin = hex(lk.skin || '#f1c9a0'), skinD = shade(skin, 0.86);
  const shirt = hex(lk.shirt || '#4f86c6'), shirtD = shade(shirt, 0.8);
  const sleeve = hex(lk.sleeve || lk.shirt || '#4f86c6');
  const shoeC = hex(lk.shoes || '#5a3f28'), legC = lk.legs ? hex(lk.legs) : (lk.robe || lk.sandals ? skin : shade(shirt, 0.55));
  const OUT = 3.4 * k, X = at.x, Y = at.y;
  const robe = !!lk.robe;

  // ---- skeleton
  const crouch = p.crouch * (DIM.thigh + DIM.shin) * 0.88 * k;
  const hip = [X, Y - (DIM.thigh + DIM.shin) * k + crouch - p.bob * k];
  const lean = p.lean * F;
  const u = [Math.sin(lean), -Math.cos(lean)];                         // hip -> neck
  const n = [u[1] * -1, u[0]];                                          // across the body
  const nr = n[0] >= 0 ? n : [-n[0], -n[1]];                           // the side away from the light (light from the upper left)
  const neckB = add(hip, u, DIM.torso * k), sh = mid(hip, neckB, 0.88);
  sh[1] -= p.shrug * 6 * k;
  const limb = (base, a1, a2, l1, l2) => {
    const j = [base[0] + Math.sin(a1) * F * l1 * k, base[1] + Math.cos(a1) * l1 * k];
    return [base, j, [j[0] + Math.sin(a1 + a2) * F * l2 * k, j[1] + Math.cos(a1 + a2) * l2 * k]];
  };
  const legBack = limb(hip, p.lR[0], p.lR[1], DIM.thigh, DIM.shin), legFront = limb(hip, p.lL[0], p.lL[1], DIM.thigh, DIM.shin);
  const armBack = limb(sh, p.aR[0] + lean, p.aR[1], DIM.upper, DIM.fore), armFront = limb(sh, p.aL[0] + lean, p.aL[1], DIM.upper, DIM.fore);
  for (const leg of [legBack, legFront]) if (leg[2][1] > Y) { const d = leg[2][1] - Y; leg[1][1] -= d * 0.5; leg[2][1] = Y; }
  const hd = p.headDrop, ang = lean + hd * 0.6 + p.head * 0.2 * F;
  const R = DIM.head * k;
  const hc = [neckB[0] + Math.sin(ang) * (DIM.neck + DIM.head * 0.92) * k, neckB[1] - Math.cos(ang) * (DIM.neck + DIM.head * 0.92) * k];

  // ---- ground shadow
  g.ellipse(X, Y + 3 * k, 62 * k, 12 * k).fill({ color: 0x1a1208, alpha: 0.13 });
  g.ellipse(X, Y + 3 * k, 38 * k, 7 * k).fill({ color: 0x1a1208, alpha: 0.12 });

  const sway = Math.sin(t * 3 + seed % 5) * 4 * k, drag = at.moving ? -F * (at.moving.verb === 'run' ? 26 : 12) * k : 0;
  const TW = 30 * k, HW = (lk.skirt || robe ? 36 : 31) * k, len = (lk.skirt ? 56 : 44) * k;
  const Sa = add(sh, n, TW), Sb = add(sh, n, -TW);
  const wmid = mid(hip, sh, 0.42), Wa = add(wmid, n, 26 * k), Wb = add(wmid, n, -26 * k);
  const Ha = add(hip, n, HW), Hb = add(hip, n, -HW);

  // ---- mantle (behind everything: a cloak hanging from the shoulders)
  if (lk.mantle) {
    const m = hex(lk.mantle), tail = add(hip, u, -(robe ? 120 : 70) * k), tx = drag * 1.6 + sway * 0.6;
    g.moveTo(...add(sh, n, TW + 7 * k)).lineTo(...add(Ha, n, 14 * k)).quadraticCurveTo(tail[0] + n[0] * 30 * k + tx, tail[1] + 24 * k, tail[0] - n[0] * 30 * k + tx, tail[1] + 24 * k).lineTo(...add(Hb, n, -14 * k)).lineTo(...add(sh, n, -TW - 7 * k)).closePath()
      .fill(m).stroke({ width: OUT, color: INK, join: 'round' });
  }
  // ---- back leg and arm
  const foot = (leg, fr) => {
    const e = leg[2], dir = e[0] >= leg[1][0] ? 1 : -1, fdir = F;
    if (lk.sandals) {
      g.ellipse(e[0] + 8 * fdir * k, e[1] - 4 * k, 17 * k, 7.5 * k).fill(skin).stroke({ width: OUT * 0.7, color: INK });
      g.moveTo(e[0] - 6 * k, e[1] - 8 * k).lineTo(e[0] + 12 * fdir * k, e[1] - 9 * k).stroke({ width: 2.6 * k, color: shoeC });
    } else g.ellipse(e[0] + 9 * fdir * k, e[1] - 5 * k, 19 * k, 9 * k).fill(shoeC).stroke({ width: OUT * 0.8, color: INK });
  };
  const leg = (l, back) => {
    if (robe && !back) return;                                          // the robe hides the front leg; only the foot shows
    sausage(g, l, 22 * k, OUT, [[0, 1, legC], [1, 2, legC]]); foot(l);
  };
  const arm = (a) => {
    const longSleeve = lk.longSleeve || robe;
    sausage(g, a, 20 * k, OUT * 0.9, [[0, 1, sleeve], [1, 2, longSleeve ? sleeve : skin]]);
    if (!longSleeve) { g.moveTo(...mid(a[0], a[1], 0.86)).lineTo(...mid(a[0], a[1], 0.98)).stroke({ width: 20 * k, color: shade(sleeve, 0.85), cap: 'butt' }); }
    g.circle(a[2][0], a[2][1], 10.5 * k).fill(skin).stroke({ width: OUT * 0.8, color: INK });
  };
  leg(legBack, true); foot(legBack); arm(armBack);

  // ---- torso: tunic (to mid-thigh) or robe (follows the legs down to the feet)
  const hem = (lk.rags ? 0 : 1);
  const bodyPath = () => {
    g.moveTo(...Sa).lineTo(...Wa);
    if (robe) {
      // the hem is as wide as the body and hangs from the hips; it swings out toward the stepping foot
      const fF = legFront[2], fB = legBack[2], cx = (fF[0] + fB[0]) / 2 + drag * 0.4, hy = Math.max(Math.min(fF[1], Y), Math.min(fB[1], Y)) - 7 * k, hw = HW + 16 * k;
      const lying = Math.abs(p.lean) > 1;
      const hf = lying ? [fF[0], fF[1] - 6 * k] : [cx + hw, hy - (fF[1] < fB[1] ? 5 * k : 0)], hb = lying ? [fB[0], fB[1] - 6 * k] : [cx - hw, hy - (fB[1] < fF[1] ? 5 * k : 0)];
      g.lineTo(...add(Ha, n, 4 * k)).quadraticCurveTo(hf[0] + 4 * k, hip[1] + (hy - hip[1]) * 0.55, hf[0], hf[1])
        .quadraticCurveTo((hf[0] + hb[0]) / 2, Math.max(hf[1], hb[1]) + 9 * k, hb[0], hb[1])
        .quadraticCurveTo(hb[0] - 4 * k, hip[1] + (hy - hip[1]) * 0.55, ...add(Hb, n, -4 * k));
    } else {
      const Ea = add(add(hip, u, -len), n, HW + 9 * k), Eb = add(add(hip, u, -len), n, -HW - 9 * k);
      g.lineTo(...Ea).quadraticCurveTo(...add(mid(Ea, Eb), u, -9 * k + (at.moving ? 4 * k : 0)), ...Eb);
    }
    g.lineTo(...Wb).lineTo(...Sb).closePath();
  };
  bodyPath(); g.fill(shirt).stroke({ width: OUT, color: INK, join: 'round' });
  g.circle(Sa[0], Sa[1], 13 * k).fill(shirt).stroke({ width: OUT * 0.5, color: INK, alpha: 0 }); g.circle(Sb[0], Sb[1], 13 * k).fill(shirt);                 // rounded shoulders
  // cell shade on the side away from the light
  g.poly([...sh, ...add(sh, nr, TW), ...add(wmid, nr, 26 * k), ...add(hip, nr, HW), ...add(add(hip, u, -len * (robe ? 2.6 : 0.9)), nr, HW * 0.9), ...add(add(hip, u, -len * (robe ? 2.6 : 0.9)), u, 0)]).fill({ color: 0x000000, alpha: 0.08 });
  // details
  if (lk.trim) { const t0 = hex(lk.trim), e = robe ? mid(legFront[2], legBack[2]) : add(hip, u, -len + 4 * k); g.moveTo(...add(e, n, HW + 6 * k)).lineTo(...add(e, n, -HW - 6 * k)).stroke({ width: 7 * k, color: t0 }); }
  if (lk.vest) {
    const v = hex(lk.vest);
    g.poly([...add(sh, n, TW - 1 * k), ...add(wmid, n, 22 * k), ...add(hip, n, HW - 2 * k), ...add(hip, n, 8 * k), ...add(wmid, n, 9 * k), ...add(sh, n, 7 * k)]).fill(v).stroke({ width: OUT * 0.7, color: INK, join: 'round' });
    g.poly([...add(sh, n, -TW + 1 * k), ...add(wmid, n, -22 * k), ...add(hip, n, -HW + 2 * k), ...add(hip, n, -8 * k), ...add(wmid, n, -9 * k), ...add(sh, n, -7 * k)]).fill(shade(v, 0.92)).stroke({ width: OUT * 0.7, color: INK, join: 'round' });
  }
  if (lk.apron) g.poly([...add(add(sh, u, -8 * k), n, 19 * k), ...add(add(sh, u, -8 * k), n, -19 * k), ...add(add(hip, u, -52 * k), n, -27 * k), ...add(add(hip, u, -52 * k), n, 27 * k)]).fill(hex(lk.apron)).stroke({ width: OUT * 0.8, color: INK, join: 'round' });
  if (lk.sash || lk.belt) {
    const c = hex(lk.sash || lk.belt), th = lk.sash ? 15 * k : 8 * k, wb = add(hip, u, 14 * k);
    g.moveTo(...add(wb, n, HW - 3 * k)).lineTo(...add(wb, n, -HW + 3 * k)).stroke({ width: th + OUT, color: INK, cap: 'round' });
    g.moveTo(...add(wb, n, HW - 3 * k)).lineTo(...add(wb, n, -HW + 3 * k)).stroke({ width: th, color: c, cap: 'round' });
    if (lk.sash) { const kn = add(wb, nr, -HW * 0.5); g.circle(kn[0], kn[1], 7 * k).fill(c).stroke({ width: OUT * 0.7, color: INK }); g.poly([...kn, ...add(add(kn, u, -34 * k), nr, 7 * k + sway * 0.4), ...add(add(kn, u, -30 * k), nr, -5 * k)]).fill(c).stroke({ width: OUT * 0.6, color: INK, join: 'round' }); }
  }
  if (lk.rags) for (let i = 0; i < 5; i++) { const e = add(add(hip, u, -len + 2 * k), n, -HW + i * HW * 0.5); g.poly([...e, ...add(add(e, u, -16 * k), n, 7 * k), ...add(e, n, HW * 0.5)]).fill(shirt).stroke({ width: OUT * 0.6, color: INK, join: 'round' }); }
  if (lk.pack) { const pk = add(add(sh, u, -34 * k), n, -F * TW * 1.0); g.ellipse(pk[0], pk[1], 20 * k, 30 * k).fill(hex(lk.pack)).stroke({ width: OUT * 0.8, color: INK }); }
  // V neck
  g.poly([...add(sh, n, 12 * k), ...add(sh, n, -12 * k), ...add(sh, u, -17 * k)]).fill(skin).stroke({ width: OUT * 0.7, color: INK, join: 'round' });

  leg(legFront, false); if (!robe) { /* foot drawn by leg() */ } else foot(legFront);

  // ---- neck, head
  g.moveTo(...add(sh, u, 4 * k)).lineTo(...mid(sh, hc, 0.85)).stroke({ width: 17 * k + OUT * 2, color: INK, cap: 'round' });
  g.moveTo(...add(sh, u, 4 * k)).lineTo(...mid(sh, hc, 0.85)).stroke({ width: 17 * k, color: skinD, cap: 'round' });
  const hairC = hex(lk.hair || '#3a2a1e'), style = lk.hairStyle || 'short';
  const P = (deg, r = R) => [hc[0] + Math.cos(rad(deg)) * r, hc[1] + Math.sin(rad(deg)) * r];
  // behind the head: long hair, headcloth drape
  if (style === 'long') g.ellipse(hc[0] - F * R * 0.12, hc[1] + R * 0.55, R * 1.14, R * 1.35).fill(hairC).stroke({ width: OUT * 0.9, color: INK });
  if (lk.headcloth) {
    const c = hex(lk.headcloth), d = (F > 0 ? -1 : 1);
    g.poly([hc[0] + d * R * 0.2, hc[1] - R * 1.0, hc[0] - R * 1.2, hc[1] - R * 0.1, hc[0] - R * 1.45, hc[1] + R * 1.5, hc[0] + R * 1.45, hc[1] + R * 1.5, hc[0] + R * 1.2, hc[1] - R * 0.1])
      .fill(c).stroke({ width: OUT * 0.9, color: INK, join: 'round' });
  }
  // ear and head
  g.circle(hc[0] - F * R * 0.93, hc[1] + R * 0.1, R * 0.2).fill(skinD).stroke({ width: OUT * 0.7, color: INK });
  g.circle(hc[0], hc[1], R).fill(skin).stroke({ width: OUT, color: INK });
  g.moveTo(...P(-62)).arc(hc[0], hc[1], R * 0.97, rad(-62), rad(62)).closePath().fill({ color: 0x7a3a20, alpha: 0.1 });       // cheek shade, away from the light
  // hair / cloth over the head
  if (style !== 'bald') {
    const top = style === 'curly' ? 1.07 : 1.02;
    g.moveTo(...P(188, R * top)).arc(hc[0], hc[1], R * top, rad(188), rad(352)).quadraticCurveTo(hc[0] + F * R * 0.2, hc[1] - R * 0.2 - hd * R * 0.1, ...P(188, R * top)).closePath().fill(hairC).stroke({ width: OUT * 0.8, color: INK, join: 'round' });
    g.ellipse(hc[0] + F * R * 0.45, hc[1] - R * 0.74, R * 0.4, R * 0.2).fill(shade(hairC, 1.25));
    if (style === 'curly') for (let i = 0; i < 6; i++) { const q = P(196 + i * 28, R * 1.02); g.circle(q[0], q[1], R * 0.2).fill(hairC).stroke({ width: OUT * 0.5, color: INK }); }
  } else if (lk.fringe !== false && lk.hair) {
    g.moveTo(...P(150)).arc(hc[0], hc[1], R * 0.99, rad(150), rad(205)).stroke({ width: 7 * k, color: hairC, cap: 'round' });
    g.moveTo(...P(335)).arc(hc[0], hc[1], R * 0.99, rad(335), rad(30)).stroke({ width: 7 * k, color: hairC, cap: 'round' });
  }
  if (lk.headcloth) {
    const c = hex(lk.headcloth);
    g.moveTo(...P(195, R * 1.04)).arc(hc[0], hc[1], R * 1.04, rad(195), rad(345)).quadraticCurveTo(hc[0], hc[1] - R * 0.5, ...P(195, R * 1.04)).closePath().fill(c).stroke({ width: OUT * 0.9, color: INK, join: 'round' });
    g.moveTo(...P(200, R * 1.0)).quadraticCurveTo(hc[0], hc[1] - R * 1.05, ...P(340, R * 1.0)).stroke({ width: 8 * k, color: hex(lk.band || '#2b2622'), cap: 'round' });
  }
  paintFace(A, g, t, hc, R, F, k, p, hd, skin, lk.beard ? hex(lk.beard) : null);

  armFront && arm(armFront);
  A.hands = { front: armFront[2], back: armBack[2], head: hc, hip, facing: F, scale: k };
  A.at = at;
}

function paintFace(A, g, t, c, R, F, k, p, hd, skin, beardC) {
  const lk = A.look, turn = clamp(p.head, -0.6, 0.6), fx = c[0] + F * R * (0.3 + turn * 0.28), fy = c[1] + hd * R * 0.22 + R * 0.04;
  const e = A.emotion(t), shut = A.blink(t) || e === 'ashamed';
  const ex = [fx - R * 0.34, fx + R * 0.3], ey = fy - R * 0.06;
  const OUT = 3 * k;
  // beard first (so the mouth sits on it)
  if (beardC) {
    g.moveTo(c[0] - R * 0.86, c[1] + R * 0.02).quadraticCurveTo(c[0] - R * 0.95, c[1] + R * 1.2, c[0] + F * R * 0.05, c[1] + R * 1.34).quadraticCurveTo(c[0] + R * 0.95, c[1] + R * 1.2, c[0] + R * 0.86, c[1] + R * 0.02)
      .quadraticCurveTo(c[0] + R * 0.5, c[1] + R * 0.5, c[0], c[1] + R * 0.5).quadraticCurveTo(c[0] - R * 0.5, c[1] + R * 0.5, c[0] - R * 0.86, c[1] + R * 0.02).closePath().fill(beardC).stroke({ width: OUT * 0.8, color: INK, join: 'round' });
  }
  for (const x of ex) {
    if (shut) g.moveTo(x - 6 * k, ey + 1 * k).quadraticCurveTo(x, ey + 5 * k, x + 6 * k, ey + 1 * k).stroke({ width: 2.8 * k, color: INK, cap: 'round' });
    else {
      const sur = e === 'surprised', rx = (sur ? 6.4 : 5.2) * k, ry = (sur ? 8.4 : 6.8) * k;
      g.ellipse(x, ey, rx, ry).fill(0xffffff).stroke({ width: 1.5 * k, color: INK });
      const px = x + F * 2 * k + turn * 2 * k, py = ey + 1 * k + (hd > 0.3 ? 2 * k : 0);
      g.circle(px, py, 3.3 * k).fill(0x2b2622); g.circle(px + 1.1 * k, py - 1.3 * k, 1.1 * k).fill(0xffffff);
    }
  }
  const brow = { angry: [0.5, -0.5], worried: [-0.45, 0.45], sad: [-0.4, 0.4], surprised: [0, 0], happy: [-0.12, 0.12], ashamed: [-0.35, 0.35], doubt: [0.1, -0.3] }[e] || [0, 0];
  const by = ey - 12 * k - (e === 'surprised' ? 5 * k : 0);
  ex.forEach((x, i) => { const a = brow[i] * F, d = (i ? -1 : 1) * 5.5 * k; g.moveTo(x - 7.5 * k, by + Math.sin(-a) * d).quadraticCurveTo(x, by - 2 * k, x + 7.5 * k, by + Math.sin(a) * d).stroke({ width: 3.2 * k, color: lk.beard ? hex(lk.hair || lk.beard) : 0x3a2a1e, cap: 'round' }); });
  g.moveTo(fx + F * 2 * k, ey + 8 * k).quadraticCurveTo(fx + F * 9 * k, ey + 17 * k, fx + F * 1 * k, ey + 19 * k).stroke({ width: 2.4 * k, color: 0x7a4a30, cap: 'round', alpha: 0.8 });   // nose
  const m = A.mouth(t), mx = fx - R * 0.02, my = fy + R * 0.46;
  const lumB = beardC ? (((beardC >> 16) & 255) * 0.3 + ((beardC >> 8) & 255) * 0.59 + (beardC & 255) * 0.11) : 0, mc = beardC && lumB < 130 ? 0xffe0cf : INK;
  if (m > 0.05) g.ellipse(mx, my, (6 + 2.4 * m) * k, (2.4 + 7 * m) * k).fill(0x6a2420).stroke({ width: 2.2 * k, color: INK });
  else if (e === 'happy') g.moveTo(mx - 10 * k, my - 3 * k).quadraticCurveTo(mx, my + 9 * k, mx + 10 * k, my - 3 * k).stroke({ width: 3 * k, color: mc, cap: 'round' });
  else if (e === 'sad' || e === 'worried' || e === 'ashamed') g.moveTo(mx - 9 * k, my + 5 * k).quadraticCurveTo(mx, my - 3 * k, mx + 9 * k, my + 5 * k).stroke({ width: 3 * k, color: mc, cap: 'round' });
  else if (e === 'angry') g.moveTo(mx - 9 * k, my + 2 * k).lineTo(mx + 9 * k, my - 1 * k).stroke({ width: 3.4 * k, color: mc, cap: 'round' });
  else if (e === 'surprised') g.ellipse(mx, my, 6 * k, 8 * k).fill(0x6a2420).stroke({ width: 2.2 * k, color: INK });
  else g.moveTo(mx - 7 * k, my + 1 * k).quadraticCurveTo(mx, my + 3 * k, mx + 7 * k, my + 1 * k).stroke({ width: 2.8 * k, color: mc, cap: 'round' });
  if (lk.moustache) g.moveTo(mx - 12 * k, my - 8 * k).quadraticCurveTo(mx, my - 15 * k, mx + 12 * k, my - 8 * k).stroke({ width: 5 * k, color: hex(lk.moustache === true ? '#efe9df' : lk.moustache), cap: 'round' });
  if (e === 'sad' && lk.tears !== false && Math.floor(t * 2) % 2 === 0) g.ellipse(ex[0], ey + 12 * k + ((t * 30) % 16) * k, 2.4 * k, 3.4 * k).fill(0x7fb4e0);
  g.circle(fx - R * 0.5, fy + R * 0.24, 6 * k).fill({ color: 0xe88a7a, alpha: 0.32 });
}
