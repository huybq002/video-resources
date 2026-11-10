(function () {
  const D = __DATA__;
  const tl = gsap.timeline({ paused: true });
  // run timeline-building code so that it applies IMMEDIATELY (base state before the timeline's first frame)
  const now = (fn) => { const S_ = tl.set, T_ = tl.to, F_ = tl.fromTo, strip = (v) => { const o = { ...v }; for (const k of ["duration", "ease", "yoyo", "repeat", "delay"]) delete o[k]; return o; };
    tl.set = (g, v) => { gsap.set(g, strip(v)); return tl; }; tl.to = (g, v) => { gsap.set(g, strip(v)); return tl; }; tl.fromTo = (g, a, v) => { gsap.set(g, strip(v)); return tl; };
    try { fn(); } finally { tl.set = S_; tl.to = T_; tl.fromTo = F_; } };
  const $ = (id) => document.getElementById(id);
  const R = D.rigs;
  let seed = 12345;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  const SINK = document.createElement("g");
  const VSUF = { f: "", s: "-s", b: "-b" };
  const part = (c, p) => (c.ext && (p === "life" || p === "body" || p === "root")) ? $(c.cid + "-ext") : ($(c.cid + (VSUF[c.view || "f"]) + "-" + p) || SINK);
  const VROOT = { f: "vf", s: "vs", b: "vb" };
  const eachView = (c, fn) => { const keep = c.view; for (const v of ["f", "s"]) { if (v === "s" && !$(c.cid + "-vs")) continue; c.view = v; fn(); } c.view = keep; };
  const SG = { l: 1, r: -1 };   // sign that raises an arm outward: arm-l positive, arm-r negative
  function setup(c) {
    for (const v of ["f", "s", "b"]) { if (!$(c.cid + "-" + VROOT[v])) continue; c.view = v;
      const P = R[c.k + (v === "f" ? "" : ":" + v)].parts;
      for (const p of Object.keys(P)) { if (p === "root") continue; const e = part(c, p); if (e !== SINK && P[p].pivot) gsap.set(e, { svgOrigin: P[p].pivot[0] + " " + P[p].pivot[1] }); }
      gsap.set(part(c, "root"), { svgOrigin: "200 780" });
      gsap.set([part(c, "lid-l"), part(c, "lid-r"), part(c, "lidp-l"), part(c, "lidp-r")], { scaleY: 0 });
      gsap.set([part(c, "mouth-open"), part(c, "mouth-sad"), part(c, "mouth-smile"), part(c, "mouth-e"), part(c, "mouth-o"), part(c, "mouth-smirk")], { opacity: 0 });
      gsap.set($(c.cid + "-" + VROOT[v]), { svgOrigin: "200 0", opacity: v === "f" ? 1 : 0, scaleX: 1 }); }
    c.view = "f";
    gsap.set([part(c, "lid-l"), part(c, "lid-r"), part(c, "lidp-l"), part(c, "lidp-r")], { scaleY: 0 });
    gsap.set(part(c, "ear-l"), { svgOrigin: "112 184" }); gsap.set(part(c, "ear-r"), { svgOrigin: "288 184" });
    gsap.set([part(c, "tears"), part(c, "sweat"), part(c, "profile"), part(c, "mouth-e"), part(c, "mouth-o"), part(c, "mouth-smirk")], { opacity: 0 });
    gsap.set([part(c, "mouth-open"), part(c, "mouth-sad"), part(c, "mouth-smile")], { opacity: 0 });
    gsap.set([part(c, "eyes-happy"), part(c, "eyes-heart"), part(c, "eyes-angry")], { opacity: 0 });
  }
  // eye states: normal | happy (^ ^) | heart | angry
  const eyes = (c, t, st) => { const vis = { normal: ["eye-l", "eye-r"], happy: ["eyes-happy"], heart: ["eyes-heart"], angry: ["eyes-angry"] };
    for (const g of ["eye-l", "eye-r", "eyes-happy", "eyes-heart", "eyes-angry"]) tl.set(part(c, g), { opacity: vis[st].includes(g) ? 1 : 0 }, t); };
  const mouth = (c, t, m) => eachView(c, () => { for (const n of ["closed", "smile", "open", "e", "o", "smirk", "sad"]) tl.set(part(c, "mouth-" + n), n === m ? { opacity: 1, scaleY: 1 } : { opacity: 0 }, t); });
  // viseme from the lip-sync track: a (wide), e (spread), o (round), m (closed), smile; open = jaw amount 0.3-1.2
  const viseme = (c, t, sh, op) => { const m = { a: "open", e: "e", o: "o", m: "closed", smile: "smile" }[sh] || "closed";
    eachView(c, () => { for (const n of ["closed", "smile", "open", "e", "o", "smirk", "sad"]) tl.set(part(c, "mouth-" + n), n === m ? { opacity: 1, scaleY: m === "open" || m === "e" || m === "o" ? op : 1 } : { opacity: 0 }, t); }); };
  const browsLR = (c, t, l, r) => { tl.to(part(c, "brow-l"), { rotation: l, y: Math.min(0, l) * 0.6, duration: 0.25, ease: "power2.out" }, t); tl.to(part(c, "brow-r"), { rotation: -r, y: Math.min(0, r) * 0.6, duration: 0.25, ease: "power2.out" }, t); };
  const lids = (c, t, a) => { for (const s of ["l", "r"]) tl.to(part(c, "lidp-" + s), { scaleY: a, duration: 0.3, ease: "power2.out" }, t); };
  const tears = (c, t, dur) => { tl.set(part(c, "tears"), { opacity: 1 }, t);
    tl.fromTo([part(c, "tear-l"), part(c, "tear-r")], { y: 0, opacity: 1 }, { y: 36, opacity: 0, duration: 0.9, ease: "power1.in", repeat: Math.max(0, Math.floor(dur / 0.9) - 1) }, t); tl.set(part(c, "tears"), { opacity: 0 }, t + dur); };
  const sweat = (c, t) => { tl.fromTo(part(c, "sweat"), { opacity: 0, y: -6 }, { opacity: 1, y: 8, duration: 0.5 }, t); tl.to(part(c, "sweat"), { opacity: 0, duration: 0.3 }, t + 1.6); };
  const brows = (c, t, r) => { tl.to(part(c, "brow-l"), { rotation: r, duration: 0.25, ease: "power2.out" }, t); tl.to(part(c, "brow-r"), { rotation: -r, duration: 0.25, ease: "power2.out" }, t); };
  const blink = (c, t) => { for (const s of ["l", "r"]) { tl.to(part(c, "lid-" + s), { scaleY: 1, duration: 0.06 }, t); tl.to(part(c, "lid-" + s), { scaleY: 0, duration: 0.1 }, t + 0.08); }
    tl.to(part(c, "headsway"), { y: 2, duration: 0.07, yoyo: true, repeat: 1 }, t); };
  // arm(): shoulder rotation + a lagging, overlapping elbow (follow-through)
  const arm = (c, s, t, rot, d, ease) => { d = d || 0.45; const e = ease || "power3.out";
    tl.to(part(c, "arm-" + s), { rotation: rot, duration: d, ease: e }, t);
    tl.to(part(c, "forearm-" + s), { rotation: rot * 0.22, duration: d * 1.25, ease: e }, t + 0.07); };
  const fore = (c, s, t, rot, d, ease) => tl.to(part(c, "forearm-" + s), { rotation: rot, duration: d || 0.3, ease: ease || "sine.inOut" }, t);
  const head = (c, t, rot, d) => tl.to(part(c, "head"), { rotation: rot, duration: d || 0.35, ease: "sine.inOut" }, t);
  const body = (c, t, rot, d) => tl.to(part(c, "body"), { rotation: rot, duration: d || 0.45, ease: "sine.inOut" }, t);
  const viewSet = (c, t, to, dir) => { const cur = c.view || "f";
    if (cur === to) { if (to === "s" && dir != null && c.vdir !== dir) { tl.set($(c.cid + "-vs"), { scaleX: dir * (c.flip ? -1 : 1) }, t); c.vdir = dir; } return; }
    if (to === "s") c.vdir = dir == null ? 1 : dir; const oldG = $(c.cid + "-" + VROOT[cur]), newG = $(c.cid + "-" + VROOT[to]); if (!newG) return;
    const dsg = (dir == null ? 1 : dir) * (c.flip ? -1 : 1); tl.set(oldG, { opacity: 0 }, t); tl.set(newG, { opacity: 1, scaleX: to === "s" ? dsg : 1 }, t); c.view = to; };
  const rootTo = (c, t, props, d, ease) => tl.to(part(c, "root"), Object.assign({ duration: d || 0.2, ease: ease || "power2.out" }, props), t);
  // squash before a jump / stretch in the air / squash on landing
  const jump = (c, t, h) => { rootTo(c, t, { scaleY: 0.92, scaleX: 1.05, y: 8 }, 0.12, "power1.in"); rootTo(c, t + 0.12, { scaleY: 1.06, scaleX: 0.96, y: -h }, 0.2, "power2.out");
    rootTo(c, t + 0.32, { y: 0, scaleY: 1, scaleX: 1 }, 0.22, "power2.in"); rootTo(c, t + 0.54, { scaleY: 0.94, scaleX: 1.04 }, 0.07); rootTo(c, t + 0.61, { scaleY: 1, scaleX: 1 }, 0.14, "back.out(2)"); };
  // proper walk: contact/passing poses, knee flex on the lifted leg, opposite arm swing with elbow, hip bob and sway
  const walkCycle = (c, t, dur, sd) => { const N = Math.max(1, Math.round(dur / (sd || 0.46))), d = dur / N;
    for (let i = 0; i < N; i++) { const a = i % 2 ? 1 : -1, ts = t + i * d, lift = a > 0 ? "r" : "l", plant = a > 0 ? "l" : "r";
      tl.to(part(c, "leg-l"), { rotation: 19 * a, duration: d, ease: "sine.inOut" }, ts); tl.to(part(c, "leg-r"), { rotation: -19 * a, duration: d, ease: "sine.inOut" }, ts);
      tl.to(part(c, "shin-" + lift), { rotation: 40, duration: d * 0.5, ease: "power2.out" }, ts); tl.to(part(c, "shin-" + lift), { rotation: 6, duration: d * 0.5, ease: "power2.in" }, ts + d * 0.5);
      tl.to(part(c, "shin-" + plant), { rotation: 3, duration: d, ease: "sine.inOut" }, ts);
      tl.to(part(c, "foot-" + lift), { rotation: -22, duration: d * 0.5, ease: "power2.out" }, ts); tl.to(part(c, "foot-" + lift), { rotation: 8, duration: d * 0.5 }, ts + d * 0.5);
      tl.to(part(c, "arm-l"), { rotation: -20 * a, duration: d, ease: "sine.inOut" }, ts); tl.to(part(c, "arm-r"), { rotation: -20 * a, duration: d, ease: "sine.inOut" }, ts);
      tl.to(part(c, "forearm-l"), { rotation: a < 0 ? 22 : 4, duration: d, ease: "sine.inOut" }, ts); tl.to(part(c, "forearm-r"), { rotation: a > 0 ? -22 : -4, duration: d, ease: "sine.inOut" }, ts);
      tl.to(part(c, "body"), { y: -9, duration: d / 2, yoyo: true, repeat: 1, ease: "sine.out" }, ts);
      tl.to(part(c, "body"), { rotation: -2.4 * a, duration: d, ease: "sine.inOut" }, ts); }
    tl.to([part(c, "leg-l"), part(c, "leg-r"), part(c, "arm-l"), part(c, "arm-r"), part(c, "body")], { rotation: 0, duration: 0.3, ease: "power2.out" }, t + dur);
    tl.to([part(c, "shin-l"), part(c, "shin-r"), part(c, "foot-l"), part(c, "foot-r"), part(c, "forearm-l"), part(c, "forearm-r")], { rotation: 0, duration: 0.3, ease: "power2.out" }, t + dur); };
  const ACT = {
    // idle "life": breathing, weight shift, drifting head (all finite, loops return to the start pose)
    breathe(c, t, dur) { const per = 1.3, n = Math.max(1, Math.floor(dur / per)), per2 = 3.1, n2 = Math.max(1, Math.floor(dur / per2)), per3 = 2.3, n3 = Math.max(1, Math.floor(dur / per3));
      tl.to(part(c, "torso"), { scaleY: 1.025, duration: per / 2, yoyo: true, repeat: 2 * n - 1, ease: "sine.inOut" }, t);
      tl.to(part(c, "life"), { y: -3, duration: per / 2, yoyo: true, repeat: 2 * n - 1, ease: "sine.inOut" }, t);
      tl.to(part(c, "life"), { x: 3, rotation: 0.5, duration: per2, yoyo: true, repeat: 2 * n2 - 1, ease: "sine.inOut" }, t);
      tl.to(part(c, "headsway"), { rotation: 1.8, duration: per3, yoyo: true, repeat: 2 * n3 - 1, ease: "sine.inOut" }, t + 0.4); },
    bend(c, t) { body(c, t, 9, 0.6); head(c, t, 10, 0.6); arm(c, "r", t + 0.1, -30, 0.6); },
    nod(c, t) { head(c, t, 10, 0.22); head(c, t + 0.26, -2, 0.22); head(c, t + 0.52, 8, 0.22); head(c, t + 0.8, 0, 0.3); },
    shake(c, t) { for (let i = 0; i < 3; i++) head(c, t + i * 0.34, i % 2 ? 11 : -11, 0.17); head(c, t + 1.05, 0, 0.25); },
    think(c, t) { arm(c, "r", t, -52, 0.6); fore(c, "r", t + 0.1, -118, 0.55, "power2.out"); head(c, t + 0.2, -7, 0.5); brows(c, t, 6); },
    worry(c, t) { brows(c, t, 12); mouth(c, t, "sad"); head(c, t, -6, 0.5); body(c, t, -2, 0.6); },
    relief(c, t) { brows(c, t, -4); mouth(c, t, "smile"); head(c, t, 0, 0.5); body(c, t, 0, 0.6); },
    lean(c, t) { body(c, t, -5, 0.9); },
    sad(c, t) { brows(c, t, 14); mouth(c, t, "sad"); head(c, t, 12, 0.7); body(c, t, 3, 0.7); arm(c, "l", t, 4, 0.6); arm(c, "r", t, -4, 0.6); },
    surprise(c, t) { mouth(c, t, "open"); brows(c, t, -14); jump(c, t, 46); body(c, t + 0.1, -8, 0.2); arm(c, "l", t + 0.1, 42, 0.25); arm(c, "r", t + 0.1, -42, 0.25);
      body(c, t + 1.3, 0, 0.5); arm(c, "l", t + 1.3, 0, 0.5); arm(c, "r", t + 1.3, 0, 0.5); },
    wave(c, t) { arm(c, "r", t, -128, 0.42, "back.out(1.6)");
      for (let i = 0; i < 4; i++) { fore(c, "r", t + 0.5 + i * 0.4, -38, 0.2); fore(c, "r", t + 0.7 + i * 0.4, -2, 0.2); }
      arm(c, "r", t + 2.3, 0, 0.5, "power2.inOut"); mouth(c, t, "closed"); },
    stir(c, t, n) { arm(c, "r", t, -48, 0.4); for (let i = 0; i < (n || 3); i++) { fore(c, "r", t + 0.5 + i * 0.7, -30, 0.35); fore(c, "r", t + 0.85 + i * 0.7, 6, 0.35); } },
    receive(c, t) { arm(c, "l", t, 55, 0.4); head(c, t, -6, 0.4); mouth(c, t + 0.4, "open"); mouth(c, t + 1.4, "closed"); },
    stamp(c, t) { arm(c, "r", t - 0.5, -125, 0.45, "power2.out"); arm(c, "r", t, -12, 0.12, "power4.in"); tl.to(part(c, "body"), { y: 12, duration: 0.08, yoyo: true, repeat: 1 }, t); arm(c, "r", t + 0.9, 0, 0.5); },
    // anticipation (a small pull-back), overshoot (back.out), then settle: what makes a gesture read as intent
    point(c, t) { body(c, t, 3, 0.14); arm(c, "r", t + 0.12, -88, 0.5, "back.out(1.6)"); fore(c, "r", t + 0.22, -4, 0.3); head(c, t + 0.12, -4, 0.4); body(c, t + 0.14, 0, 0.3);
      arm(c, "r", t + 2.2, 0, 0.5); head(c, t + 2.2, 0, 0.4); },
    cheer(c, t) { mouth(c, t, "open"); brows(c, t, -10); arm(c, "l", t, 152, 0.3, "power2.out"); arm(c, "r", t, -152, 0.3, "power2.out");
      jump(c, t, 56); jump(c, t + 0.7, 50); arm(c, "l", t + 1.6, 0, 0.5); arm(c, "r", t + 1.6, 0, 0.5); mouth(c, t + 1.6, "closed"); },
    laugh(c, t) { mouth(c, t, "open"); head(c, t, -8, 0.3); for (let i = 0; i < 6; i++) body(c, t + i * 0.18, i % 2 ? 3 : -3, 0.09); body(c, t + 1.2, 0, 0.3); mouth(c, t + 1.3, "closed"); head(c, t + 1.3, 0, 0.3); },
    angry(c, t) { brows(c, t, -13); mouth(c, t, "closed"); head(c, t, 5, 0.3); arm(c, "l", t, 12, 0.3); arm(c, "r", t, -12, 0.3); },
    cry(c, t) { brows(c, t, 14); mouth(c, t, "sad"); head(c, t, 14, 0.6); arm(c, "r", t + 0.3, -60, 0.5); fore(c, "r", t + 0.4, -125, 0.5); for (let i = 0; i < 4; i++) body(c, t + 0.9 + i * 0.25, i % 2 ? 2 : -2, 0.12); },
    walk(c, t, n) { walkCycle(c, t, (n || 4) * 0.46); },
    // view: "front" | "side" (profile, facing screen-right when dir>0) | "back". Later acts in the list act on the new drawing.
    view(c, t, v, dir) { const to = ({ front: "f", side: "s", back: "b", f: "f", s: "s", b: "b" })[v] || "f", cur = c.view || "f"; if (to === cur) return;
      const dsg = (dir == null ? 1 : dir) * (c.flip ? -1 : 1), oldG = $(c.cid + "-" + VROOT[cur]), newG = $(c.cid + "-" + VROOT[to]); if (!newG) return;
      tl.to(oldG, { scaleX: 0.55, duration: 0.11, ease: "power1.in" }, t); tl.set(oldG, { opacity: 0, scaleX: 1 }, t + 0.11);
      tl.fromTo(newG, { opacity: 1, scaleX: 0.55 * (to === "s" ? dsg : 1) }, { scaleX: to === "s" ? dsg : 1, duration: 0.2, ease: "back.out(1.7)" }, t + 0.11); c.view = to; },
    // walking across the frame turns the character to profile, then back to front when it arrives
    walkTo(c, t, dx, d) { const dd = d || Math.max(1, Math.abs(dx) / 220), has = !!$(c.cid + "-vs"); if (has) ACT.view(c, t, "side", dx >= 0 ? 1 : -1);
      tl.to($(c.cid + "-wrap"), { x: "+=" + dx, duration: dd, ease: "sine.inOut" }, t + (has ? 0.2 : 0)); walkCycle(c, t + (has ? 0.2 : 0), dd - (has ? 0.3 : 0)); if (has) ACT.view(c, t + dd, "front", 1); },
    look(c, t, dx, dy) { for (const s of ["l", "r"]) tl.to(part(c, "pupil-" + s), { x: (dx || 0) * 6, y: (dy || 0) * 5, duration: 0.22, ease: "power2.out" }, t); head(c, t, (dx || 0) * 6, 0.45); },
    reach(c, t, side) { const s = side || "r"; arm(c, s, t, SG[s] * -8, 0.14, "power1.out"); body(c, t, SG[s] * 4, 0.14);
      arm(c, s, t + 0.14, SG[s] * 75, 0.5, "back.out(1.4)"); fore(c, s, t + 0.3, SG[s] * 8, 0.35); body(c, t + 0.14, SG[s] * -4, 0.5);
      head(c, t + 0.25, SG[s] * -3, 0.4); arm(c, s, t + 1.6, 0, 0.5); body(c, t + 1.6, 0, 0.5); head(c, t + 1.6, 0, 0.4); },
    shrug(c, t) { arm(c, "l", t, 22, 0.3); arm(c, "r", t, -22, 0.3); fore(c, "l", t + 0.1, 55, 0.3); fore(c, "r", t + 0.1, -55, 0.3); head(c, t, 6, 0.3);
      tl.to(part(c, "life"), { y: -8, duration: 0.2, yoyo: true, repeat: 1 }, t); arm(c, "l", t + 0.9, 0, 0.4); arm(c, "r", t + 0.9, 0, 0.4); head(c, t + 0.9, 0, 0.4); },
    // dialogue: mouth flaps per syllable, head beats, alternating hand gestures
    talk(c, t, dur) { dur = dur || 3; let u = t, k = 0;
      while (u < t + dur - 0.1) { const op = 0.09 + rnd() * 0.07, sh = 0.05 + rnd() * 0.06; mouth(c, u, "open"); mouth(c, u + op, "closed"); u += op + sh + (k % 5 === 4 ? 0.2 : 0); k++; }
      mouth(c, t + dur, "closed");
      for (let b = 0; b < dur / 0.55; b++) tl.to(part(c, "headsway"), { y: -3, duration: 0.14, yoyo: true, repeat: 1, ease: "sine.out" }, t + b * 0.55);
      for (let g = 0; g < Math.floor(dur / 1.4); g++) { const s = g % 2 ? "l" : "r", T = t + 0.3 + g * 1.4; arm(c, s, T, SG[s] * (28 + rnd() * 22), 0.32, "power2.out"); fore(c, s, T + 0.2, SG[s] * 20, 0.3); arm(c, s, T + 0.75, 0, 0.45, "power2.inOut"); } },
    // yaw -1 (looks to screen-left, profile) … 0 front … +1 (profile right). 0.5 = three-quarter view.
    turn(c, t, yaw, d) {
      // a real 3/4 turn: switch to the drawn 3/4 view (face, hair and body all turn together). The old fake turn slid
      // the face sideways UNDER a front hairstyle, so long hair cut across the eye and the face looked broken (2026-11-09).
      if ($(c.cid + "-vs") && !c.hold) { if (Math.abs(yaw) >= 0.3) viewSet(c, t + 0.04, "s", yaw > 0 ? 1 : -1); else if (!c.face) viewSet(c, t + 0.04, "f", 1); return; }
      d = d || 0.55; const a = Math.abs(yaw), prof = a >= 0.85, ez = "power2.inOut";
      tl.to(part(c, "turn"), { scaleX: 1 - 0.34 * a, x: yaw * 10, duration: d, ease: ez }, t);
      tl.to(part(c, "face"), { x: yaw * 34, scaleX: 1 - 0.2 * a, duration: d, ease: ez }, t);
      tl.to(part(c, "nose"), { x: yaw * 10, duration: d, ease: ez }, t);
      tl.to(part(c, "ear-l"), { scaleX: yaw > 0 ? 1 - 0.8 * a : 1 + 0.2 * a, duration: d, ease: ez }, t); tl.to(part(c, "ear-r"), { scaleX: yaw < 0 ? 1 - 0.8 * a : 1 + 0.2 * a, duration: d, ease: ez }, t);
      const half = t + d * 0.5;
      for (const g of ["face", "head-shape", "ears", "glasses"]) { const ge = part(c, g); if (ge) tl.set(ge, { opacity: prof ? 0 : 1 }, half); }
      tl.set(part(c, "profile"), { opacity: prof ? 1 : 0, scaleX: yaw < 0 ? -1 : 1 }, half); },
    emote(c, t, name) { const E = {
      joy: () => { eyes(c, t, "happy"); mouth(c, t, "smile"); browsLR(c, t, -6, -6); head(c, t, -4, 0.3); lids(c, t, 0); },
      sad: () => { eyes(c, t, "normal"); mouth(c, t, "sad"); browsLR(c, t, 14, 14); lids(c, t, 0.3); head(c, t, 10, 0.6); },
      cry: () => { E.sad(); tears(c, t + 0.3, 3); },
      fear: () => { eyes(c, t, "normal"); mouth(c, t, "o"); browsLR(c, t, -16, -16); lids(c, t, 0); sweat(c, t + 0.2); head(c, t, -5, 0.2); body(c, t, -4, 0.3); },
      anger: () => { eyes(c, t, "angry"); mouth(c, t, "closed"); browsLR(c, t, -13, -13); head(c, t, 4, 0.3); },
      doubt: () => { eyes(c, t, "normal"); mouth(c, t, "smirk"); browsLR(c, t, -14, 7); lids(c, t, 0.25); head(c, t, 7, 0.4); },
      smirk: () => { eyes(c, t, "normal"); mouth(c, t, "smirk"); browsLR(c, t, -8, 2); lids(c, t, 0.1); head(c, t, 3, 0.4); },
      surprise: () => { eyes(c, t, "normal"); mouth(c, t, "o"); browsLR(c, t, -16, -16); lids(c, t, 0); },
      sleepy: () => { eyes(c, t, "normal"); mouth(c, t, "closed"); browsLR(c, t, 6, 6); lids(c, t, 0.65); head(c, t, 6, 0.8); },
      neutral: () => { eyes(c, t, "normal"); mouth(c, t, "closed"); browsLR(c, t, 0, 0); lids(c, t, 0); head(c, t, 0, 0.3); } };
      (E[name] || E.neutral)(); },
    lidsAct(c, t, a) { lids(c, t, a); },
    gesture(c, t, dur) { dur = dur || 3; for (let g = 0; g < Math.floor(dur / 1.4); g++) { const s = g % 2 ? "l" : "r", T = t + 0.3 + g * 1.4; arm(c, s, T, SG[s] * (28 + rnd() * 22), 0.32, "power2.out"); fore(c, s, T + 0.2, SG[s] * 20, 0.3); arm(c, s, T + 0.75, 0, 0.45, "power2.inOut"); } },
    happy(c, t) { eyes(c, t, "happy"); mouth(c, t, "smile"); brows(c, t, -6); body(c, t, 0, 0.3); for (let i = 0; i < 4; i++) tl.to(part(c, "life"), { y: -14, duration: 0.14, yoyo: true, repeat: 1, ease: "power1.out" }, t + 0.1 + i * 0.4); },
    heart(c, t) { eyes(c, t, "heart"); brows(c, t, -6); head(c, t, -5, 0.4); },
    glare(c, t) { eyes(c, t, "angry"); brows(c, t, -13); head(c, t, 4, 0.3); },
    normal(c, t) { eyes(c, t, "normal"); brows(c, t, 0); mouth(c, t, "closed"); head(c, t, 0, 0.3); body(c, t, 0, 0.3); },
    offer(c, t) { arm(c, "r", t, -62, 0.7); arm(c, "l", t, 62, 0.7); fore(c, "r", t + 0.2, -20, 0.5); fore(c, "l", t + 0.2, 20, 0.5); head(c, t, 4, 0.7); mouth(c, t + 0.2, "closed"); brows(c, t, 5); },
    // ---- film actions (2026-11-08): what the narration says a character DOES, they now do on screen ----
    // sit on an (implied or drawn) seat: body drops, knees out, feet in
    // Sitting is drawn in profile: in a front view the thigh points at the camera and cannot be drawn without
    // foreshortening, which is what broke the knees before. Hips drop by exactly the thigh length (rig "hip"/"knee"),
    // so the knee ends level with the hip and the foot stays on the floor. inst = already seated when the shot opens.
    sit(c, t, dir, inst) { const has = !!$(c.cid + "-vs"), d = inst ? 0.001 : 0.45;
      if (dir === "b" && $(c.cid + "-vb")) {   // seated at a desk against the back wall: seen from behind. The thighs point
        // away from the camera (foreshortened to almost nothing), the shins hang from the seat to the floor.
        viewSet(c, t, "b", 1); const rg = R[c.k + ":b"] || R[c.k] || {}, L = (rg.knee || 650) - (rg.hip || 540), k = 0.12;
        rootTo(c, t, { y: c.seatDrop != null ? c.seatDrop : L * (1 - k) }, d, "power2.inOut");
        tl.to([part(c, "leg-l"), part(c, "leg-r")], { scaleY: k, duration: d }, t);
        tl.to([part(c, "shin-l"), part(c, "shin-r")], { scaleY: (c.shinK || 1) / k, duration: d }, t);
        c.seated = true; c.seatBack = true; return; }
      if (has) { if (inst) viewSet(c, t, "s", dir); else ACT.view(c, t, "side", dir == null ? 1 : dir); }
      const t1 = (has && !inst) ? t + 0.3 : t, rg = R[c.k + (c.view === "s" ? ":s" : "")] || {}, L = (rg.knee || 650) - (rg.hip || 540);
      if (c.view === "s") {
        rootTo(c, t1, { y: L }, d, "power2.inOut");
        tl.to(part(c, "leg-l"), { rotation: -88, duration: d, ease: "power2.inOut" }, t1); tl.to(part(c, "shin-l"), { rotation: 88, duration: d, ease: "power2.inOut" }, t1);
        tl.to(part(c, "leg-r"), { rotation: -82, duration: d, ease: "power2.inOut" }, t1); tl.to(part(c, "shin-r"), { rotation: 82, duration: d, ease: "power2.inOut" }, t1);
        tl.to([part(c, "foot-l"), part(c, "foot-r")], { rotation: 0, duration: d }, t1); body(c, t1, -3, d);
        // hands rest on the lap, not hanging through the seat (a later act - type, drink, phone - moves them again)
        arm(c, "l", t1, -38, d); arm(c, "r", t1, -32, d); fore(c, "l", t1 + 0.05, -42, d); fore(c, "r", t1 + 0.05, -36, d);
      } else {   // no profile drawing: knees out, shins straight down, a small drop (a perch, never crossed legs)
        rootTo(c, t1, { y: L * 0.14 }, d, "power2.inOut");
        tl.to(part(c, "leg-l"), { rotation: 30, duration: d }, t1); tl.to(part(c, "shin-l"), { rotation: -30, duration: d }, t1);
        tl.to(part(c, "leg-r"), { rotation: -30, duration: d }, t1); tl.to(part(c, "shin-r"), { rotation: 30, duration: d }, t1);
      } c.seated = true; },
    // back to standing from sit / crouch / lie
    stand(c, t) { tl.set(part(c, "root"), { transformOrigin: "50% 100%" }, t); rootTo(c, t, { y: 0, rotation: 0, scaleX: 1, scaleY: 1 }, 0.45, "power2.out");
      tl.to([part(c, "leg-l"), part(c, "leg-r"), part(c, "shin-l"), part(c, "shin-r"), part(c, "body"), part(c, "head")], { rotation: 0, duration: 0.4, ease: "power2.out" }, t); lids(c, t, 0);
      if (c.seatBack) { tl.to([part(c, "leg-l"), part(c, "leg-r"), part(c, "shin-l"), part(c, "shin-r")], { scaleY: 1, duration: 0.4 }, t); c.seatBack = false; }
      if (c.seated && (c.view === "s" || c.view === "b")) ACT.view(c, t + 0.45, "front", 1); c.seated = false; },
    // run across the frame: fast cycle, forward lean, bigger arm swing
    run(c, t, dx, d) { const dist = dx || 500, dd = d || Math.max(0.8, Math.abs(dist) / 600), has = !!$(c.cid + "-vs"); if (has) ACT.view(c, t, "side", dist >= 0 ? 1 : -1);
      const t1 = t + (has ? 0.15 : 0); tl.to($(c.cid + "-wrap"), { x: "+=" + dist, duration: dd, ease: "power1.inOut" }, t1);
      walkCycle(c, t1, dd - 0.1, 0.24); body(c, t1, (dist >= 0 ? 1 : -1) * -8, 0.2); body(c, t1 + dd, 0, 0.3); if (has) ACT.view(c, t1 + dd, "front", 1); },
    // a real jump with squash and stretch
    jump(c, t, h) { jump(c, t, h || 70); arm(c, "l", t + 0.1, 120, 0.25); arm(c, "r", t + 0.1, -120, 0.25); arm(c, "l", t + 0.6, 0, 0.3); arm(c, "r", t + 0.6, 0, 0.3); },
    // fall over (trip, faint, shock): pivots on the feet and lands on the floor; stays down until "stand"
    fall(c, t, dir) { const g = dir || 1; tl.set(part(c, "root"), { transformOrigin: "50% 100%" }, t); mouth(c, t, "open"); brows(c, t, -8);
      arm(c, "l", t, 130, 0.25); arm(c, "r", t, -130, 0.25); rootTo(c, t + 0.1, { rotation: 84 * g, y: 26 }, 0.55, "power2.in");
      tl.to(part(c, "root"), { y: 18, duration: 0.08, yoyo: true, repeat: 1 }, t + 0.65); arm(c, "l", t + 0.7, 40, 0.3); arm(c, "r", t + 0.7, -40, 0.3); },
    // lie down (sleep, collapse onto a bed): horizontal, eyes closed; h lifts the body onto a bed (px, default 0 = floor)
    lie(c, t, h, inst) { const d = inst ? 0.001 : 0.7; tl.set(part(c, "root"), { transformOrigin: "50% 100%" }, t); rootTo(c, t, { rotation: -88, y: -(h || 0) }, d, "power2.inOut");
      if (!c.awake) { lids(c, t + (inst ? 0 : 0.4), 1); mouth(c, t + (inst ? 0 : 0.4), "closed"); } arm(c, "l", t, 10, inst ? 0.001 : 0.6); arm(c, "r", t, -10, inst ? 0.001 : 0.6); },
    sleep(c, t, h) { ACT.lie(c, t, h == null ? 120 : h); },
    // bend down and pick something up, then stand again
    pickup(c, t) { rootTo(c, t, { y: 34 }, 0.35); body(c, t, 26, 0.4); head(c, t, 14, 0.4); arm(c, "r", t + 0.1, -18, 0.4); fore(c, "r", t + 0.2, -10, 0.3);
      rootTo(c, t + 1.2, { y: 0 }, 0.4); body(c, t + 1.2, 0, 0.4); head(c, t + 1.2, 0, 0.4); arm(c, "r", t + 1.25, -55, 0.4); },
    // typing on a keyboard / phone: both forearms forward, fingers tapping
    type(c, t, dur) { const D = dur || 2.4; arm(c, "l", t, 30, 0.3); arm(c, "r", t, -30, 0.3); head(c, t, 6, 0.4);
      for (let i = 0; i < Math.floor(D / 0.18); i++) { fore(c, i % 2 ? "l" : "r", t + 0.3 + i * 0.18, (i % 2 ? 1 : -1) * 28, 0.09); fore(c, i % 2 ? "l" : "r", t + 0.39 + i * 0.18, (i % 2 ? 1 : -1) * 14, 0.09); }
      arm(c, "l", t + D + 0.3, 0, 0.4); arm(c, "r", t + D + 0.3, 0, 0.4); head(c, t + D + 0.3, 0, 0.4); },
    // texting on a phone held in front of the chest: both forearms up and in, head down, thumbs tapping
    text(c, t, dur) { const D = dur || 2.4; arm(c, "r", t, 16, 0.35); arm(c, "l", t, -16, 0.35); fore(c, "r", t + 0.05, 112, 0.35); fore(c, "l", t + 0.05, -112, 0.35); head(c, t, 10, 0.4);
      for (let i = 0; i < Math.floor(D / 0.22); i++) fore(c, i % 2 ? "l" : "r", t + 0.45 + i * 0.22, (i % 2 ? -1 : 1) * (i % 4 < 2 ? 104 : 116), 0.11);
      arm(c, "l", t + D + 0.3, 0, 0.4); arm(c, "r", t + D + 0.3, 0, 0.4); fore(c, "l", t + D + 0.3, 0, 0.4); fore(c, "r", t + D + 0.3, 0, 0.4); head(c, t + D + 0.3, 0, 0.4); },
    // drink from a cup in the right hand
    drink(c, t) { arm(c, "r", t, -150, 0.45, "power2.out"); fore(c, "r", t + 0.1, -105, 0.35); head(c, t + 0.3, -10, 0.35);
      arm(c, "r", t + 1.6, -40, 0.45); fore(c, "r", t + 1.6, 0, 0.4); head(c, t + 1.6, 0, 0.4); },
    // phone held to the ear for dur seconds
    phone(c, t, dur) { const D = dur || 2.6; arm(c, "r", t, -152, 0.45, "power2.out"); fore(c, "r", t + 0.1, -118, 0.35); head(c, t + 0.2, 9, 0.35);
      arm(c, "r", t + D, -20, 0.45); fore(c, "r", t + D, 0, 0.4); head(c, t + D, 0, 0.4); },
    // throw: wind up behind, release forward
    throw(c, t) { arm(c, "r", t, -160, 0.28, "power2.out"); body(c, t, 6, 0.28); arm(c, "r", t + 0.3, -40, 0.14, "power4.in"); body(c, t + 0.3, -8, 0.16);
      arm(c, "r", t + 1.0, 0, 0.4); body(c, t + 1.0, 0, 0.4); },
    // crouch / hide: small, head down, arms over the head
    crouch(c, t, dur) { const D = dur || 2.2; rootTo(c, t, { scaleY: 0.8, y: 42 }, 0.3); arm(c, "l", t, 140, 0.3); arm(c, "r", t, -140, 0.3);
      fore(c, "l", t + 0.1, 70, 0.25); fore(c, "r", t + 0.1, -70, 0.25); head(c, t, 12, 0.3); sweat(c, t + 0.3);
      rootTo(c, t + D, { scaleY: 1, y: 0 }, 0.35); arm(c, "l", t + D, 0, 0.35); arm(c, "r", t + D, 0, 0.35); fore(c, "l", t + D, 0, 0.3); fore(c, "r", t + D, 0, 0.3); head(c, t + D, 0, 0.3); },
    // panic: arms flailing, body shaking, sweat, open mouth
    panic(c, t) { mouth(c, t, "open"); brows(c, t, 12); sweat(c, t);
      for (let i = 0; i < 6; i++) { arm(c, "l", t + i * 0.22, i % 2 ? 150 : 95, 0.18); arm(c, "r", t + i * 0.22, i % 2 ? -95 : -150, 0.18); body(c, t + i * 0.22, i % 2 ? 5 : -5, 0.18); }
      arm(c, "l", t + 1.5, 0, 0.4); arm(c, "r", t + 1.5, 0, 0.4); body(c, t + 1.5, 0, 0.4); mouth(c, t + 1.6, "closed"); },
  };
  const camShake = (cam, t) => { for (let i = 0; i < 6; i++) tl.to(cam, { x: "+=" + (i % 2 ? 12 : -12) * (1 - i / 6), duration: 0.04 }, t + i * 0.04); };

  for (const sh of D.shots) {
    const el = $(sh.dom), cam = $(sh.dom + "-cam");
    const t0 = sh.t0, t1 = sh.t1, dur = t1 - t0;
    // only the active shots are laid out (keeps long films fast): hidden until 0.45 s before the cut, hidden again 0.8 s after the shot ends
    if (!sh.first) { gsap.set(el, { display: "none" }); tl.set(el, { display: "block" }, Math.max(0, t0 - 0.45)); }
    tl.set(el, { display: "none" }, t1 + 0.8);
    const prevEl = sh.prev ? $(sh.prev) : null, tr = sh.trans || (sh.cut ? "cut" : "fade");
    gsap.set(el, { transformOrigin: "50% 55%" });
    if (sh.first) gsap.set(el, { opacity: 1 });
    else if (tr === "cut" || tr === "flash") { tl.set(el, { opacity: 1 }, t0); if (prevEl) tl.set(prevEl, { opacity: 0 }, t0 + 0.04);
      if (tr === "flash") { const f = $("flash-" + D.sceneId); tl.fromTo(f, { opacity: 0 }, { opacity: 0.95, duration: 0.05 }, t0 - 0.03).to(f, { opacity: 0, duration: 0.35 }, t0 + 0.02); } }
    else if (tr === "whip") { tl.set(el, { opacity: 1 }, t0);
      tl.fromTo(el, { x: D.W * 0.28, filter: "blur(44px)" }, { x: 0, filter: "blur(0px)", duration: 0.34, ease: "power3.out" }, t0 - 0.06);
      if (prevEl) { tl.to(prevEl, { x: -D.W * 0.28, filter: "blur(44px)", duration: 0.26, ease: "power2.in" }, t0 - 0.12); tl.set(prevEl, { opacity: 0, x: 0, filter: "blur(0px)" }, t0 + 0.3); } }
    else if (tr === "zoom") { tl.fromTo(el, { opacity: 0, scale: 0.72 }, { opacity: 1, scale: 1, duration: 0.5, ease: "power2.out" }, t0);
      if (prevEl) { tl.to(prevEl, { scale: 3.4, opacity: 0, duration: 0.5, ease: "power2.in" }, t0 - 0.06); tl.set(prevEl, { opacity: 0, scale: 1 }, t0 + 0.5); } }
    else if (tr === "dip") { if (prevEl) tl.to(prevEl, { opacity: 0, duration: 0.3, ease: "power1.in" }, t0 - 0.3);
      tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.45, ease: "power1.out" }, t0 + 0.05); }
    else { tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.4, ease: "power1.inOut" }, t0); if (prevEl) tl.set(prevEl, { opacity: 0 }, t0 + 0.42); }
    // camera (layered parallax when the setting was rendered with depth layers)
    const K = [sh.cam[0], sh.cam[1], sh.cam[2], sh.cam[3], sh.cam[4], sh.cam[5]];
    if (sh.layers) { for (const L of sh.layers) { const e = $(L.dom); gsap.set(e, { transformOrigin: "50% 62%" });
        tl.fromTo(e, { scale: 1 + (K[0] - 1) * L.k, x: K[1] * L.k, y: K[2] * L.k }, { scale: 1 + (K[3] - 1) * L.k, x: K[4] * L.k, y: K[5] * L.k, duration: dur + 0.4, ease: "none" }, t0); } }
    else { for (const ce of (sh.panes ? sh.panes.map($) : [cam])) { gsap.set(ce, { transformOrigin: "50% 62%" });
        tl.fromTo(ce, { scale: K[0], x: K[1], y: K[2] }, { scale: K[3], x: K[4], y: K[5], duration: dur + 0.4, ease: "none" }, t0); } }
    if (sh.sway) { const sw = $(sh.dom + "-sway"), per = 1.7, n = Math.max(1, Math.floor((dur + 0.4) / per));
      tl.fromTo(sw, { x: -5, y: -3, rotation: -0.25 }, { x: 5, y: 3, rotation: 0.25, duration: per, yoyo: true, repeat: 2 * n - 1, ease: "sine.inOut" }, t0); }
    // crowd (simple silhouettes, seeded, finite bobbing)
    (sh.crowd || []).forEach((f) => { const e = $(f.id), per = 0.35 + f.a * 0.25, n = Math.max(1, Math.floor(dur / per));
      tl.to(e, { y: -(5 + f.a * 7), duration: per, yoyo: true, repeat: 2 * n - 1, ease: "sine.inOut" }, t0 + f.d); });
    // overlays: chips, counters, bursts, bubbles, titles
    for (const o of sh.overlays || []) { const e = $(o.id), T = t0 + o.t, end = T + o.dur; if (o.abs) gsap.set(e, { xPercent: -50, yPercent: -50 });
      if (o.type === "screen") { tl.fromTo(e, { opacity: 0, y: 60, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: "back.out(1.4)" }, T); tl.to(e, { opacity: 0, y: -20, duration: 0.25 }, end - 0.25); }
      else if (o.type === "chip") { tl.fromTo(e, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }, T); tl.to(e, { opacity: 0, y: -6, duration: 0.2 }, end - 0.2); }
      else if (o.type === "counter") { const num = $(o.id + "-n"), pr = { v: o.from }; const fmt = (v) => String(Math.round(v)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        num.textContent = fmt(o.from);
        tl.fromTo(e, { opacity: 0, y: 16, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.35, ease: "back.out(1.5)" }, T);
        tl.to(pr, { v: o.to, duration: Math.max(0.4, o.dur - 0.9), ease: "power2.out", onUpdate: () => { num.textContent = fmt(pr.v); } }, T + 0.25);
        tl.to(e, { opacity: 0, duration: 0.25 }, end - 0.25); }
      else if (o.type === "burst") { tl.fromTo(e, { opacity: 0, scale: 0.2, rotation: -14 }, { opacity: 1, scale: 1.12, rotation: -5, duration: 0.22, ease: "power3.out" }, T); tl.to(e, { scale: 1, duration: 0.15 }, T + 0.22); tl.to(e, { opacity: 0, scale: 0.9, duration: 0.18 }, end - 0.18); }
      else if (o.type === "graph") { tl.fromTo(e, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: 0.35, ease: "power2.out" }, T);
        const pl = e.querySelector("polyline"); if (pl && pl.getTotalLength) { const L = pl.getTotalLength(); gsap.set(pl, { strokeDasharray: L, strokeDashoffset: L }); tl.to(pl, { strokeDashoffset: 0, duration: Math.max(0.6, o.dur * 0.5), ease: "power2.out" }, T + 0.3); }
        tl.to(e, { opacity: 0, duration: 0.25 }, end - 0.25); }
      else if (o.type === "clock") { tl.fromTo(e, { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(1.6)" }, T); tl.to(e, { opacity: 0, duration: 0.2 }, end - 0.2); }
      else if (o.type === "flash") { tl.fromTo(e, { opacity: 0.95 }, { opacity: 0, duration: Math.min(0.6, o.dur), ease: "power2.out" }, T); }
      else if (o.type === "ripple") { tl.set(e, { opacity: 1 }, T); e.querySelectorAll(".rp").forEach((r, k) => {
          tl.fromTo(r, { scale: 0.08, opacity: 0.95 }, { scale: 1.5 + k * 0.35, opacity: 0, duration: Math.min(1.1, o.dur), ease: "power2.out" }, T + k * 0.14); });
        tl.set(e, { opacity: 0 }, end); }
      else if (o.type === "speedlines") { tl.fromTo(e, { opacity: 0, scale: 1.25 }, { opacity: 0.85, scale: 1, duration: 0.18, ease: "power3.out" }, T);
        tl.to(e, { scale: 1.04, duration: 0.12, yoyo: true, repeat: Math.max(1, Math.floor((o.dur - 0.4) / 0.12)), ease: "none" }, T + 0.18); tl.to(e, { opacity: 0, duration: 0.2 }, end - 0.2); }
      else if (o.type === "chain") { const ch = e.querySelectorAll(".ch");
        tl.fromTo(e, { opacity: 0 }, { opacity: 1, duration: 0.15 }, T);
        tl.fromTo(ch, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.25, ease: "power2.out", stagger: Math.min(0.45, (o.dur * 0.6) / Math.max(1, ch.length)) }, T + 0.1);
        tl.to(e, { opacity: 0, duration: 0.25 }, end - 0.25); }
      else if (o.type === "bubble" || o.type === "title") { const ch = e.querySelectorAll(".ch");
        tl.fromTo(e, { opacity: 0, y: 10, scale: 0.95 }, { opacity: 1, y: 0, scale: 1, duration: 0.2, ease: "power2.out" }, T);
        tl.fromTo(ch, { opacity: 0 }, { opacity: 1, duration: 0.01, stagger: Math.min(0.06, (o.dur * 0.6) / Math.max(1, ch.length)) }, T + 0.15);
        tl.to(e, { opacity: 0, duration: 0.25 }, end - 0.25); } }
    for (const c of sh.chars) {
      setup(c);
      const w = $(c.cid + "-wrap");
      if (c.enter != null) { const D = Math.max(1.8, Math.abs(c.enter) / 230);
        const has = !!$(c.cid + "-vs"); if (has) ACT.view(c, t0, "side", c.enter < 0 ? 1 : -1);
        tl.fromTo(w, { x: c.enter }, { x: 0, duration: D, ease: "power1.out" }, t0 + (has ? 0.2 : 0)); walkCycle(c, t0 + (has ? 0.2 : 0), D - (has ? 0.3 : 0));
        // arrived at an object: turn to it (profile), not back to the camera, so the act that follows is done AT it
        if (has) ACT.view(c, t0 + D, c.face ? "side" : "front", c.face || 1); }
      if (c.face && !c.hold && c.enter == null) viewSet(c, t0, "s", c.face);     // two-shot: in profile, facing the other person
      if (c.back && !c.path) viewSet(c, t0, "b", 1);
      if (c.path) { const p = c.path, wv = $(c.cid + "-wrap");   // an extra walking through: across, toward or away from the camera
        if (p.view === "s") viewSet(c, t0, "s", p.dir || 1); else if (p.view === "b") viewSet(c, t0, "b", 1);
        gsap.set(wv, { transformOrigin: "50% 97%" });
        tl.fromTo(wv, { x: 0, y: 0, scale: 1 }, { x: p.dx, y: p.dy, scale: p.k, duration: p.d, ease: "none" }, t0); walkCycle(c, t0, p.d); }
      // a HELD pose must already be there on the shot's first frame: an "instant" tween starting AT t0 is still at
      // progress 0 on that frame, so every cut flashed the person standing for one frame (2026-11-09 audit).
      // Pose them just before the cut (the shot is still hidden then); at the very start of a scene, set it outright.
      if (c.hold) { const tH = t0 > 0.02 ? t0 - 0.012 : 0;
        const pose = () => { if (c.hold === "lie") ACT.lie(c, tH, 0, true); else if (c.hold === "sit") ACT.sit(c, tH, c.holdDir, true); };
        if (t0 <= 0.02) now(pose);
        pose(); }
      let b = 0.9 + rnd(); while (b < dur - 0.3) { if (c.hold !== "lie" || c.awake) blink(c, t0 + b); b += 2.3 + rnd() * 2.2; }
      let hasBreath = false;
      for (const a of c.acts) { if (a[1] === "breathe") hasBreath = true; if (!ACT[a[1]]) { console.warn("unknown act", a[1]); continue; } ACT[a[1]](c, t0 + a[0], a[1] === "breathe" ? dur - a[0] : a[2], a[3]); }
      if (!hasBreath) ACT.breathe(c, t0 + 0.2, dur - 0.2);
    }
    for (const v of sh.vehicles || []) { const e = $(v.dom);   // traffic: a car drives along its lane
      tl.set(e, { opacity: 1 }, t0 + v.t); tl.fromTo(e, { x: 0, y: 0, scale: 1 }, { x: v.dx, y: v.dy, scale: v.k, duration: v.d, ease: v.back ? "power2.out" : "power2.in" }, t0 + v.t);
      tl.set(e, { opacity: 0 }, t0 + v.t + v.d); }
    for (const L of sh.lip || []) { const c = sh.chars.find((x) => x.k === L.k); if (!c) continue; for (const ev of L.ev) viseme(c, t0 + ev[0], ev[1], ev[2]); }
    for (const p of sh.props || []) { const e = $(p.dom);
      if (p.mode === "place") { gsap.set(e, { opacity: 0 }); tl.fromTo(e, { opacity: 1, x: p.fx || 0, y: p.fy || 0, scale: 0.9 }, { x: 0, y: 0, scale: 1, duration: 0.55, ease: "power2.inOut" }, t0 + (p.t || 0)); }
      else if (p.mode === "take") { gsap.set(e, { opacity: 1 }); tl.to(e, { x: p.fx || 0, y: p.fy || 0, duration: 0.5, ease: "power2.inOut" }, t0 + (p.t || 0)); tl.to(e, { opacity: 0, duration: 0.2 }, t0 + (p.t || 0) + 0.5); }
      else if (p.mode === "pop") { tl.fromTo(e, { opacity: 0, scale: 0.4 }, { opacity: 1, scale: 1, duration: 0.3, ease: "back.out(2)" }, t0 + (p.t || 0)); }
      else if (p.mode === "on") { gsap.set(e, { opacity: 1 }); }
      else if (p.mode === "static") { gsap.set(e, { opacity: 1 }); tl.fromTo(e, { scale: 1 }, { scale: 1.06, duration: 1.2, yoyo: true, repeat: Math.max(1, Math.floor(dur / 2.4) * 2 - 1), ease: "sine.inOut" }, t0 + (p.t || 0)); }
      else tl.fromTo(e, { opacity: 0, y: -260, rotation: 14 }, { opacity: 1, y: 0, rotation: -3, duration: 0.55, ease: "bounce.out" }, t0 + (p.t || 0));
      if (p.lift != null) tl.to(e, { y: -30, rotation: -4, duration: 0.5, ease: "power2.out" }, t0 + p.lift); }
    if (sh.rain) { const rs = document.querySelectorAll("#" + sh.dom + " .rain");
      rs.forEach((r, i) => { tl.fromTo(r, { y: -240, opacity: 0.5 }, { y: 1300, opacity: 0.25, duration: 0.5 + (i % 5) * 0.06, ease: "none", repeat: Math.floor(dur / 0.6) }, t0 + (i % 9) * 0.05); }); }
    if (sh.shake) for (const s of sh.shake) camShake(cam, t0 + s);
    if (sh.flash !== undefined) { const f = $("flash-" + D.sceneId); tl.fromTo(f, { opacity: 0 }, { opacity: 0.9, duration: 0.05 }, t0 + sh.flash).to(f, { opacity: 0, duration: 0.4 }, t0 + sh.flash + 0.05); }
  }
  for (const c of D.caps) { const e = $(c.id);
    tl.fromTo(e, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.25, ease: "power2.out" }, c.t0 + 0.05);
    if (!c.last) tl.to(e, { opacity: 0, duration: 0.2 }, Math.max(c.t0 + 0.3, c.t1 - 0.25)); }
  window.__timelines = window.__timelines || {};
  window.__timelines[D.sceneId] = tl;
})();
