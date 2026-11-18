// hezb-motion: a film is this page. It reads film.json, builds every scene, and exposes
//   window.DUR, window.FPS, window.render(t) (async, deterministic), window.READY, window.EV (sound events)
// tools/render.mjs opens it in headless Chromium and captures frames in order.
import { Application, Container, Sprite, Texture, Graphics } from 'pixi.js';
import { initP5, paintPlace, paintProp, paintGrain, W, HGT } from './places.js';
import { Actor } from './rig.js';
import { drawAmbient } from './env.js';
import { initPhysics, simulateSpills, simulateHangers } from './physics.js';
import { ParticleLayer } from './particles.js';
import { Post } from './post.js';
import { Insert3D } from './three3d.js';
import { Overlay } from './overlay.js';
import { clamp, lerp, easeInOut, smooth, noise1, hash, keyed } from './util.js';
import { springStep, SPRING } from './springs.js';

const DEPTH = { sky: 0.08, far: 0.35, mid: 1, act: 1, near: 1.3 };

async function boot() {
  const q = new URLSearchParams(location.search);
  const film = await (await fetch(q.get('film') || 'film.json')).json();
  const FPS = +(q.get('fps') || film.fps || 30), [FW, FH] = (q.get('size') ? q.get('size').split('x').map(Number) : film.size || [1920, 1080]);
  window.DUR = film.duration; window.FPS = FPS;
  await initP5(); await initPhysics();
  if (document.fonts) { try { await document.fonts.load('48px "Patrick Hand"'); } catch {} }

  // ---- canvases: Pixi draws the world, a 2D canvas keeps the outgoing shot, OGL composites onto the visible canvas
  const app = new Application();
  await app.init({ width: W, height: HGT, background: '#f4ead6', antialias: FW >= 1920, preference: 'webgl', preserveDrawingBuffer: true, autoStart: false, resolution: FW / W });   // the world is 1920x1080; a 720p film draws it at 2/3 (2.25x fewer pixels for software GL)
  app.ticker.stop();
  const snap = document.createElement('canvas'); snap.width = app.canvas.width; snap.height = app.canvas.height; const snapCtx = snap.getContext('2d');
  const out = document.getElementById('out'); out.width = FW; out.height = FH;
  const post = new Post(out, FW, FH, paintGrain(7));
  const ins3d = new Insert3D(post.gl, FW, FH);
  for (const [name, url] of Object.entries(film.models || {})) await ins3d.load(name, url);
  const overlay = new Overlay(document.getElementById('overlay'), film.theme || {});
  overlay.addCards(film.cards || []);

  // ---- props (paper.js drawings) as textures
  const propTex = {};
  const tex = name => (propTex[name] ??= Texture.from(paintProp(name, 256)));

  // ---- physics, precomputed
  const allSpills = film.scenes.flatMap(s => s.spills || []), spills = simulateSpills(allSpills);
  const allHangers = film.scenes.flatMap(s => (s.hangers || []).map(h => ({ ...h }))), hangers = simulateHangers(allHangers, film.duration);

  // ---- scenes
  const placeCache = {};
  const scenes = {};
  for (const sc of film.scenes) {
    const place = film.places[sc.place];
    const painted = (placeCache[sc.place] ??= paintPlace(place, sc.place));
    const root = new Container(), layers = {};
    for (const d of ['sky', 'far', 'farAmb', 'mid', 'midAmb', 'partFar', 'act', 'front', 'near', 'nearAmb', 'partNear']) { layers[d] = new Container(); root.addChild(layers[d]); }
    for (const d of ['sky', 'far', 'mid', 'front', 'near']) if (painted[d]) layers[d].addChild(new Sprite(Texture.from(painted[d])));
    const amb = { far: new Graphics(), mid: new Graphics(), near: new Graphics() };
    layers.farAmb.addChild(amb.far); layers.midAmb.addChild(amb.mid); layers.nearAmb.addChild(amb.near);
    const ambient = [...(place.ambient || []), ...(sc.ambient || [])];
    // actors (one per cast member in this scene); words come from the captions of that speaker
    const actors = {};
    for (const [id, c] of Object.entries(sc.cast || {})) {
      const look = { ...(film.cast[c.as || id] || {}), ...(c.look || {}), facing: c.facing ?? 1 };
      const acts = (sc.actions || []).filter(a => a.who === id);
      const words = (film.words || []).filter(w => w.who === (c.as || id) && w.t0 >= sc.t0 && w.t1 <= sc.t1);
      const a = new Actor(id + '@' + sc.id, look, acts, words);
      a.home = [c.x, c.y ?? 900]; a.s = c.s ?? 1; a.z = c.z ?? 0;
      actors[id] = a; layers.act.addChild(a.view);
    }
    // props on stage
    const props = (sc.props || []).map(p => { const sp = new Sprite(tex(p.prop)); sp.anchor.set(0.5); layers.act.addChild(sp); return { ...p, sp }; });
    // physics sprites
    const spillSprites = (sc.spills || []).map(s => ({ id: s.id, sprites: [...Array(s.n ?? 1)].map(() => { const sp = new Sprite(tex(s.prop || 'coin')); sp.anchor.set(0.5); sp.width = sp.height = (s.size ?? 34) * 1.15; layers.act.addChild(sp); return sp; }) }));
    const hangSprites = (sc.hangers || []).map(hh => { const rope = new Graphics(), sp = new Sprite(tex(hh.prop || 'lantern')); sp.anchor.set(0.5, 0.1); sp.width = sp.height = hh.size ?? 110; layers.mid.addChild(rope); layers.mid.addChild(sp); return { id: hh.id, rope, sp, h: hh }; });
    // particles
    const parts = [];
    for (const p of [...(place.particles || []), ...(sc.particles || [])]) {
      const layer = new ParticleLayer({ ...p, id: (p.id || p.preset) + '@' + sc.id }, FPS); await layer.init();
      const sp = new Sprite(Texture.from(layer.canvas)); sp.x = layer.area[0]; sp.y = layer.area[1];
      (p.near ? layers.partNear : layers.partFar).addChild(sp); parts.push({ layer, sp, t0: p.t0 ?? sc.t0, t1: p.t1 ?? sc.t1 });
    }
    scenes[sc.id] = { sc, place, root, layers, amb, ambient, actors, props, spillSprites, hangSprites, parts };
  }

  // ---- one frame of one shot into the Pixi canvas
  async function drawShot(shot, t) {
    const S = scenes[shot.scene]; if (!S) throw new Error('shot without scene ' + shot.scene);
    const sc = S.sc, lt = t;
    // ambient life by depth
    const byDepth = { far: [], mid: [], near: [] };
    for (const e of S.ambient) byDepth[e.depth || (e.type === 'wheat' ? 'near' : e.type === 'clouds' || e.type === 'birds' ? 'far' : 'mid')].push(e);
    drawAmbient(S.amb.far, lt, byDepth.far); drawAmbient(S.amb.mid, lt, byDepth.mid); drawAmbient(S.amb.near, lt, byDepth.near);
    // actors (depth sort by feet y)
    const drawn = [];
    for (const [id, a] of Object.entries(S.actors)) {
      const hide = (shot.hide || []).includes(id) || (sc.enter?.[id] != null && t < sc.enter[id]) || (sc.exit?.[id] != null && t > sc.exit[id]);
      a.view.visible = !hide; if (hide) continue;
      a.draw(t, a.home[0], a.home[1], a.s); drawn.push(a);
    }
    drawn.sort((p, q) => p.at.y - q.at.y).forEach((a, i) => S.layers.act.setChildIndex(a.view, Math.min(i, S.layers.act.children.length - 1)));
    // props: placed, held in a hand, or handed over
    for (const p of S.props) {
      const vis = (p.from == null || t >= p.from) && (p.until == null || t <= p.until); p.sp.visible = vis; if (!vis) continue;
      let x = p.x, y = p.y, s = p.s ?? 0.5, rot = p.rot ?? 0;
      const hold = (p.held || []).find(hh => t >= hh.t0 && t <= hh.t1);
      if (hold && S.actors[hold.who]?.hands) { const hd = S.actors[hold.who].hands; const pt = hd[hold.hand || 'front']; x = pt[0]; y = pt[1] + (hold.dy ?? 10) * hd.scale; s = (p.s ?? 0.5) * hd.scale; }
      else if (p.keys) { const K = n => keyed(p.keys.filter(k => k[n] != null).map(k => ({ t: k.t, v: k[n] })), t); x = K('x') || x; y = K('y') || y; if (p.keys.some(k => k.s != null)) s = K('s'); if (p.keys.some(k => k.r != null)) rot = K('r'); }
      if (p.pop != null) s *= clamp(springStep(t - p.pop, SPRING.wobbly), 0, 1.3);
      p.sp.x = x; p.sp.y = y; p.sp.scale.set(s); p.sp.rotation = rot;
    }
    for (const ss of S.spillSprites) { const fr = spills.sample(ss.id, t); ss.sprites.forEach((sp, i) => { sp.visible = !!fr; if (fr) { sp.x = fr[i].x; sp.y = fr[i].y; sp.rotation = fr[i].a; } }); }
    for (const hs of S.hangSprites) { const b = hangers.sample(hs.id, t); if (!b) continue; hs.rope.clear().moveTo(hs.h.x, hs.h.y).lineTo(b.x, b.y - 20).stroke({ width: 3, color: 0x2b2622 }); hs.sp.x = b.x; hs.sp.y = b.y - 30; hs.sp.rotation = -b.a; }
    // particles: step to this frame
    const f = Math.round(t * FPS);
    for (const p of S.parts) { p.sp.visible = t >= p.t0 && t <= p.t1; if (!p.sp.visible) continue; await p.layer.seekFrame(f - Math.round(p.t0 * FPS)); p.sp.texture.source.update(); }
    // camera: one world -> screen function, applied per depth (parallax)
    const cam = camera(shot, t, S);
    for (const [d, f2] of [['sky', DEPTH.sky], ['far', DEPTH.far], ['farAmb', DEPTH.far], ['mid', 1], ['midAmb', 1], ['partFar', 1], ['act', 1], ['front', 1], ['near', DEPTH.near], ['nearAmb', DEPTH.near], ['partNear', DEPTH.near]]) {
      const L = S.layers[d], z = lerp(1, cam.z, Math.min(1, f2)) * (f2 > 1 ? 1 + (cam.z - 1) * (f2 - 1) * 0.5 : 1);
      L.scale.set(z); L.x = W / 2 - (cam.x * f2 + (W / 2) * (1 - f2)) * z; L.y = HGT / 2 - (cam.y * Math.min(1, f2) + (HGT / 2) * (1 - Math.min(1, f2))) * z;
    }
    app.renderer.render(S.root);
    return app.canvas;
  }

  function camera(shot, t, S) {
    const c = shot.cam || {}, u = (c.ease === 'linear' ? (x => x) : easeInOut)(clamp((t - shot.t0) / Math.max(0.01, shot.t1 - shot.t0)));
    const zz = c.z || [1, 1.05], cc = c.c || [[W / 2, HGT / 2]];
    let z = lerp(zz[0], zz[1] ?? zz[0], u), x = lerp(cc[0][0], (cc[1] || cc[0])[0], u), y = lerp(cc[0][1], (cc[1] || cc[0])[1], u);
    if (c.follow && S.actors[c.follow]?.at) { const a = S.actors[c.follow]; x = a.at.x + (c.lead ?? 0) * a.at.facing; y = (c.followY ?? (a.at.y - 170 * a.s)); }
    if (c.shake) { x += noise1(t * 9, 1) * c.shake; y += noise1(t * 9, 2) * c.shake; }
    // never show outside the painted world
    const hw = W / 2 / z, hh = HGT / 2 / z; x = clamp(x, hw, W - hw); y = clamp(y, hh, HGT - hh);
    return { x, y, z };
  }

  const shots = film.shots.slice().sort((a, b) => a.t0 - b.t0);
  const shotAt = t => { let s = shots[0]; for (const x of shots) if (x.t0 <= t + 1e-6) s = x; return s; };

  window.render = async t => {
    const i = shots.indexOf(shotAt(t)), shot = shots[i], prev = shots[i - 1];
    const tr = shot.transition, look = { ...(film.places[scenes[shot.scene].sc.place].look || {}), ...(shot.look || {}) };
    let from, to = null, trans = null;
    const pic = async s => s.insert3d ? ins3d.render({ ...s.insert3d, t0: s.t0 }, t) : (await drawShot(s, t), app.canvas);
    if (tr && prev && t < shot.t0 + tr.dur) {
      const a = await pic(prev);
      if (!prev.insert3d) { snapCtx.drawImage(a, 0, 0); from = snap; } else from = a;
      to = await pic(shot); trans = { name: tr.name, progress: smooth((t - shot.t0) / tr.dur), params: tr.params };
    } else from = await pic(shot);
    post.draw(from, to, t, trans, look);
    const cap = (film.captions || []).find(c => t >= c.t0 && t <= c.t1);
    overlay.render(t, cap);
  };
  window.EV = film.events || [];
  window.READY = true;
}

boot().catch(e => { console.error('BOOT FAILED', e && (e.stack || e)); window.BOOT_ERROR = String(e && (e.stack || e)); });
