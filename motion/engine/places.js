// Places: the world a scene happens in, painted once per place into parallax layers.
//   p5.js     paints the generative parts: the sky gradient, paper grain, wheat-field strokes, mud, wood grain, starfields.
//   paper.js  draws the hand-inked shapes: hills, houses, fences, roads, tables, doors, walls (smoothed, roughened vector
//             paths with an ink outline), rasterised to canvases.
// PixiJS shows each layer as a sprite; the camera moves them at different depths (parallax).
import paper from 'paper';
import p5 from 'p5';
import { mulberry, hash, hex } from './util.js';

export const W = 1920, HGT = 1080;
const INK = '#2b2622';
let P5 = null;

export function initP5() {
  if (P5) return Promise.resolve(P5);
  return new Promise(res => {
    const host = document.createElement('div'); host.style.display = 'none'; document.body.appendChild(host);
    new p5(s => { s.setup = () => { s.noCanvas(); P5 = s; res(s); }; }, host);
  });
}

function canvas(w = W, h = HGT) { const c = document.createElement('canvas'); c.width = w; c.height = h; c.setAttribute('hidpi', 'off'); return c; }

// ------------------------------------------------------------ p5 painters ---------------------------------------------
function p5Layer(w, h, seed, paint) {
  const s = P5, g = s.createGraphics(w, h); g.pixelDensity(1);
  s.randomSeed(seed); s.noiseSeed(seed); g.randomSeed(seed); g.noiseSeed(seed);
  paint(g, s); return g.elt;
}

export function paintSky(sky, seed) {
  return p5Layer(W, HGT, seed, (g) => {
    const top = g.color(sky.top || '#9fd3ec'), bot = g.color(sky.bottom || '#f8ead0');
    for (let y = 0; y < HGT; y++) { g.stroke(g.lerpColor(top, bot, Math.pow(y / HGT, 0.9))); g.line(0, y, W, y); }
    if (sky.stars) { g.noStroke(); for (let i = 0; i < 260; i++) { g.fill(255, 250, 220, g.random(90, 255)); g.circle(g.random(W), g.random(HGT * 0.7), g.random(1, 3.4)); } }
    if (sky.sun) { const [x, y, r] = sky.sun; for (let k = 6; k > 0; k--) { g.noStroke(); g.fill(255, 236, 170, 18); g.circle(x, y, r * 2 + k * 40); } g.fill(sky.sunColor || '#ffd56a'); g.stroke(INK); g.strokeWeight(3); g.circle(x, y, r * 2); }
    if (sky.moon) { const [x, y, r] = sky.moon; g.noStroke(); g.fill(255, 248, 210, 30); g.circle(x, y, r * 3.2); g.fill('#fff4c8'); g.stroke(INK); g.strokeWeight(3); g.circle(x, y, r * 2); g.noStroke(); g.fill(sky.top || '#1d2550'); g.circle(x + r * 0.45, y - r * 0.2, r * 1.7); }
    paperGrain(g, 10);
  });
}

function paperGrain(g, a = 12) { g.noStroke(); for (let i = 0; i < 9000; i++) { g.fill(80, 60, 40, g.random(a * 0.3, a)); g.rect(g.random(W), g.random(HGT), 1.6, 1.6); } }

export function paintGrain(seed) {      // a full-frame paper-grain overlay used by the post pass
  return p5Layer(512, 512, seed, (g) => { g.clear(); g.noStroke(); for (let i = 0; i < 26000; i++) { const v = g.random(); g.fill(v > 0.5 ? 255 : 30, v > 0.5 ? 255 : 20, v > 0.5 ? 250 : 10, g.random(4, 18)); g.rect(g.random(512), g.random(512), 1.3, 1.3); } });
}

function paintField(g, s, top, color, dark, density = 1) {      // wheat / grass strokes, denser and longer toward the viewer
  g.strokeWeight(2);
  for (let i = 0; i < 5200 * density; i++) {
    const y = top + Math.pow(g.random(), 0.7) * (HGT - top), d = (y - top) / (HGT - top), x = g.random(W);
    const len = 8 + d * 34, lean = (g.noise(x * 0.004, y * 0.01) - 0.5) * 18;
    g.stroke(g.lerpColor(g.color(color), g.color(dark), g.random(0.6)));
    g.line(x, y, x + lean, y - len);
  }
}

function paintPlanks(g, x, y, w, h, color, horizontal = true) {
  g.noStroke(); g.fill(color); g.rect(x, y, w, h); g.stroke(0, 0, 0, 40); g.strokeWeight(2);
  const n = horizontal ? Math.round(h / 34) : Math.round(w / 60);
  for (let i = 1; i < n; i++) horizontal ? g.line(x, y + i * h / n, x + w, y + i * h / n + g.random(-2, 2)) : g.line(x + i * w / n, y, x + i * w / n + g.random(-3, 3), y + h);
  for (let i = 0; i < w * h / 4000; i++) { g.stroke(0, 0, 0, 18); g.line(g.random(x, x + w), g.random(y, y + h), g.random(x, x + w), g.random(y, y + h)); }
}

// ------------------------------------------------------------ paper.js painters ---------------------------------------
function paperLayer(seed, draw) {
  const c = canvas(), scope = new paper.PaperScope(); scope.setup(c);
  const rnd = mulberry(seed);
  const style = (path, fill, w = 4) => { path.fillColor = fill; path.strokeColor = INK; path.strokeWidth = w; path.strokeJoin = 'round'; path.strokeCap = 'round'; return path; };
  // organic shapes (leaves, ground edges) are flattened, jittered and re-smoothed; built shapes (walls, roofs) only get
  // their corners nudged, so a house stays a house
  const rough = (path, amt = 2.4) => {
    const built = path.segments.length <= 6 && path.segments.every(s => s.handleIn.isZero() && s.handleOut.isZero());
    if (built) { for (const s of path.segments) s.point = s.point.add([(rnd() - 0.5) * amt * 1.5, (rnd() - 0.5) * amt * 1.5]); return path; }
    path.flatten(14); for (const s of path.segments) s.point = s.point.add([(rnd() - 0.5) * amt, (rnd() - 0.5) * amt]); path.smooth({ type: 'catmull-rom' }); return path;
  };
  draw({ scope, P: scope, rnd, style, rough });
  scope.view.update(); scope.view.draw();
  return c;
}

const ELEMENTS = {
  hills: ({ P, rnd, style, rough }, e) => {
    const y = e.y ?? 640, amp = e.amp ?? 60, pts = [];
    for (let x = -40; x <= W + 40; x += 160) pts.push([x, y - amp * (0.4 + rnd() * 0.6)]);
    const path = new P.Path({ segments: [[-60, HGT + 20], ...pts, [W + 60, HGT + 20]], closed: true }); path.smooth({ type: 'catmull-rom', from: 1, to: pts.length });
    style(path, e.color || '#8fbf6a', 3.5);
  },
  ground: ({ P, style, rough }, e) => { const p = new P.Path.Rectangle([-20, e.y ?? 760], [W + 40, HGT]); rough(p, 3); style(p, e.color || '#d8c49a', 3); },
  road: ({ P, style }, e) => { const vx = e.vx ?? W / 2, top = e.y ?? 700; const p = new P.Path({ segments: [[vx - 20, top], [vx + 20, top], [vx + 520, HGT + 10], [vx - 520, HGT + 10]], closed: true }); style(p, e.color || '#cdb98a', 3); },
  house: ({ P, rnd, style, rough }, e) => {
    const { x, y, w = 360, h = 240 } = e;
    style(rough(new P.Path.Rectangle([x, y - h], [w, h]), 2), e.wall || '#e7d6b4', 4);
    style(rough(new P.Path({ segments: [[x - 30, y - h + 4], [x + w / 2, y - h - w * 0.42], [x + w + 30, y - h + 4]], closed: true }), 2), e.roof || '#b2563e', 4);
    style(new P.Path.Rectangle([x + w * 0.62, y - h * 0.62], [w * 0.2, h * 0.62]), e.door || '#6b4a34', 3.5);
    style(new P.Path.Rectangle([x + w * 0.14, y - h * 0.66], [w * 0.24, h * 0.26]), e.window || '#9fd3ec', 3.5);
    if (e.chimney) style(new P.Path.Rectangle([x + w * 0.7, y - h - w * 0.36], [w * 0.1, w * 0.2]), '#a5765a', 3);
  },
  tree: ({ P, rnd, style, rough }, e) => {
    const { x, y, s = 1 } = e;
    style(rough(new P.Path.Rectangle([x - 12 * s, y - 160 * s], [24 * s, 160 * s]), 2), '#7a5a3a', 3.5);
    for (const [dx, dy, r] of [[0, -230, 90], [-70, -180, 66], [70, -185, 70], [0, -160, 70]]) style(rough(new P.Path.Circle([x + dx * s, y + dy * s], r * s), 5), e.leaf || '#5f9a4e', 3.5);
  },
  fence: ({ P, style }, e) => { for (let x = e.x0; x <= e.x1; x += 70) style(new P.Path.Rectangle([x, e.y - 90], [12, 90]), '#a77b52', 3); for (const yy of [e.y - 70, e.y - 34]) style(new P.Path.Rectangle([e.x0 - 10, yy], [e.x1 - e.x0 + 32, 10]), '#b98a5e', 3); },
  wall: ({ P, style }, e) => style(new P.Path.Rectangle([-20, -20], [W + 40, (e.y ?? 760) + 20]), e.color || '#7a5a44', 0),
  floor: ({ P, style }, e) => style(new P.Path.Rectangle([-20, e.y ?? 760], [W + 40, HGT]), e.color || '#8a6a4a', 3),
  window: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y], [e.w || 220, e.h || 260]), e.glass || '#1d2550', 6); style(new P.Path.Line([e.x + (e.w || 220) / 2, e.y], [e.x + (e.w || 220) / 2, e.y + (e.h || 260)]), null, 5); },
  door: ({ P, style }, e) => style(new P.Path.Rectangle([e.x, e.y - (e.h || 330)], [e.w || 190, e.h || 330]), e.color || '#6b4a34', 5),
  table: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y], [e.w, 34]), e.color || '#a77b52', 4); for (const lx of [e.x + 30, e.x + e.w - 52]) style(new P.Path.Rectangle([lx, e.y + 34], [22, e.h || 120]), '#8a6238', 3.5); },
  shelf: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y], [e.w, 16]), '#8a6238', 3); for (let i = 0; i < (e.n || 6); i++) style(new P.Path.Rectangle([e.x + 20 + i * (e.w - 40) / (e.n || 6), e.y - 54], [34, 54]), ['#3f7a5a', '#a0482e', '#d9a441'][i % 3], 3); },
  pen: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x0, e.y - 20], [e.x1 - e.x0, 200]), e.mud || '#7a5a3e', 3); for (let x = e.x0; x <= e.x1; x += 90) style(new P.Path.Rectangle([x, e.y - 110], [12, 110]), '#8a6238', 3); style(new P.Path.Rectangle([e.x0 - 6, e.y - 92], [e.x1 - e.x0 + 24, 10]), '#9a7448', 3); },
  trough: ({ P, style }, e) => style(new P.Path.Rectangle([e.x, e.y - 40], [e.w || 200, 40]), '#7a5a3a', 3.5),
  shack: ({ P, style, rough }, e) => { style(rough(new P.Path.Rectangle([e.x, e.y - (e.h || 200)], [e.w || 260, e.h || 200]), 4), e.wall || '#9a8a72', 4); style(new P.Path({ segments: [[e.x - 20, e.y - (e.h || 200)], [e.x + (e.w || 260) + 20, e.y - (e.h || 200) - 30]], strokeWidth: 0 }), null, 10); },
  well: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y - 80], [120, 80]), '#9a9a92', 4); style(new P.Path.Rectangle([e.x + 4, e.y - 190], [10, 110]), '#7a5a3a', 3); style(new P.Path.Rectangle([e.x + 106, e.y - 190], [10, 110]), '#7a5a3a', 3); style(new P.Path.Rectangle([e.x - 10, e.y - 200], [140, 14]), '#8a6238', 3); },
  gate: ({ P, style }, e) => { for (const dx of [0, e.w || 300]) style(new P.Path.Rectangle([e.x + dx - 16, e.y - 260], [32, 260]), '#9a8a72', 4); style(new P.Path.Rectangle([e.x - 30, e.y - 280], [(e.w || 300) + 60, 30]), '#8a6238', 4); },
  stall: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y - 110], [e.w || 260, 110]), '#b98a5e', 4); style(new P.Path({ segments: [[e.x - 20, e.y - 240], [e.x + (e.w || 260) + 20, e.y - 240], [e.x + (e.w || 260), e.y - 190], [e.x, e.y - 190]], closed: true }), e.awning || '#c4544a', 4); for (const dx of [6, (e.w || 260) - 18]) style(new P.Path.Rectangle([e.x + dx, e.y - 240], [12, 130]), '#8a6238', 3); },
  sign: ({ P, style }, e) => { style(new P.Path.Rectangle([e.x, e.y - 220], [16, 220]), '#6b4a34', 3); style(new P.Path({ segments: [[e.x - 120, e.y - 210], [e.x + 90, e.y - 210], [e.x + 130, e.y - 180], [e.x + 90, e.y - 150], [e.x - 120, e.y - 150]], closed: true }), '#e9d6a8', 4); },
};

const P5_ELEMENTS = {
  field: (g, s, e) => paintField(g, s, e.y ?? 700, e.color || '#e2b84e', e.dark || '#b98a2e', e.density || 1),
  grass: (g, s, e) => paintField(g, s, e.y ?? 760, e.color || '#8fbf6a', e.dark || '#5f8f46', e.density || 0.6),
  mud: (g, s, e) => { g.noStroke(); for (let i = 0; i < 700; i++) { g.fill(70 + g.random(30), 50 + g.random(20), 30, 120); g.ellipse(g.random(e.x0 ?? 0, e.x1 ?? W), g.random(e.y ?? 800, HGT), g.random(20, 80), g.random(6, 18)); } },
  planks: (g, s, e) => paintPlanks(g, e.x ?? 0, e.y ?? 760, e.w ?? W, e.h ?? (HGT - (e.y ?? 760)), e.color || '#8a6a4a', e.horizontal !== false),
  bricks: (g, s, e) => { g.noFill(); g.stroke(0, 0, 0, 30); g.strokeWeight(2); for (let y = e.y0 ?? 0; y < (e.y1 ?? 760); y += 44) for (let x = ((y / 44) % 2) * 60; x < W; x += 120) g.rect(x + g.random(-2, 2), y, 120, 44); },
  stones: (g, s, e) => { g.stroke('#2b2622'); g.strokeWeight(2); for (let i = 0; i < 260; i++) { g.fill(g.lerpColor(g.color('#b9b2a2'), g.color('#8f887a'), g.random())); g.ellipse(g.random(W), g.random(e.y ?? 780, HGT), g.random(30, 70), g.random(10, 24)); } },
};

// a place = sky + far + mid + near layers; each layer is a list of elements; returns canvases by depth
export function paintPlace(spec, name) {
  const seed = hash(name);
  const out = { sky: paintSky(spec.sky || {}, seed) };
  for (const depth of ['far', 'mid', 'front', 'near']) {
    const els = spec[depth]; if (!els) continue;
    const c = canvas(), ctx = c.getContext('2d');
    for (const e of els) {
      if (P5_ELEMENTS[e.type]) ctx.drawImage(p5Layer(W, HGT, seed + els.indexOf(e), (g, s) => { g.clear(); P5_ELEMENTS[e.type](g, s, e); }), 0, 0);
      else if (ELEMENTS[e.type]) ctx.drawImage(paperLayer(seed + els.indexOf(e) * 13, k => ELEMENTS[e.type](k, e)), 0, 0);
      else console.warn('unknown place element', e.type);
    }
    out[depth] = c;
  }
  return out;
}

// props drawn with paper.js (inserts and hand-held objects): name -> canvas (size, anchor)
export const PROPS = {
  bag: k => { const { P, style } = k; style(new P.Path({ segments: [[60, 40], [140, 40], [175, 170], [25, 170]], closed: true }).set({}), '#c79a5b', 5); style(new P.Path.Rectangle([70, 20], [60, 26]), '#a77b45', 4); },
  coin: k => { const { P, style } = k; style(new P.Path.Circle([100, 100], 80), '#e8b84a', 6); style(new P.Path.Circle([100, 100], 54), null, 4); },
  cup: k => { const { P, style } = k; style(new P.Path({ segments: [[50, 40], [150, 40], [135, 170], [65, 170]], closed: true }), '#d9c27a', 5); },
  bread: k => { const { P, style } = k; style(new P.Path.Ellipse([[20, 60], [160, 90]]), '#d99a52', 5); for (const x of [60, 100, 140]) style(new P.Path.Line([x - 10, 80], [x + 10, 120]), null, 4); },
  ring: k => { const { P, style } = k; style(new P.Path.Circle([100, 110], 60), null, 14).strokeColor = '#d9a441'; style(new P.Path.Circle([100, 46], 20), '#9fd3ec', 4); },
  robe: k => { const { P, style } = k; style(new P.Path({ segments: [[70, 20], [130, 20], [180, 190], [20, 190]], closed: true }), '#b8342c', 5); style(new P.Path.Line([100, 20], [100, 190]), null, 6).strokeColor = '#e8c25a'; },
  sandals: k => { const { P, style } = k; for (const x of [40, 120]) { style(new P.Path.Ellipse([[x, 60], [50, 120]]), '#a77b52', 4); style(new P.Path.Line([x + 4, 100], [x + 46, 100]), null, 5); } },
  lantern: k => { const { P, style } = k; style(new P.Path.Line([100, 0], [100, 40]), null, 4); style(new P.Path.Rectangle([62, 40], [76, 110]), '#f2c14e', 5); style(new P.Path.Ellipse([[78, 66], [44, 58]]), '#fff3b0', 3); },
  pod: k => { const { P, style } = k; style(new P.Path({ segments: [[20, 120], [100, 60], [180, 90], [110, 140]], closed: true }), '#8a7a3a', 4); },
  stick: k => { const { P, style } = k; style(new P.Path.Line([20, 180], [180, 20]), null, 10).strokeColor = '#7a5a3a'; },
};
export function paintProp(name, size = 200) {
  const c = document.createElement('canvas'); c.width = c.height = size; c.setAttribute('hidpi', 'off');
  const scope = new paper.PaperScope(); scope.setup(c); scope.view.scale(size / 200, [0, 0]);
  const style = (path, fill, w = 4) => { path.fillColor = fill; path.strokeColor = INK; path.strokeWidth = w; path.strokeJoin = 'round'; path.strokeCap = 'round'; return path; };
  PROPS[name]({ P: scope, style, rnd: mulberry(hash(name)) }); scope.view.update(); scope.view.draw(); return c;
}
