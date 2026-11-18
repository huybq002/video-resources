// Physics, precomputed once at load so every frame is a lookup (deterministic, any worker can render any frame).
//   Rapier (rapier2d, deterministic) : rigid props that fall, bounce, roll and settle: coins on a table, a dropped bag,
//                                       bread thrown to the floor, a cup knocked over.
//   Matter.js                        : hanging things on ropes: lanterns, signs, a bell; they swing from a wind gust or
//                                       a door slam (an impulse at a story moment), then settle.
import RAPIER from '@dimforge/rapier2d-compat';
import Matter from 'matter-js';
import { mulberry, hash, noise1 } from './util.js';

const DT = 1 / 60;
let rapierReady = null;
export const initPhysics = () => (rapierReady ??= RAPIER.init());

// spills: [{id, t, prop, n, from:[x,y], vel:[vx,vy], spread, floor:y, table:[x0,x1,y], size}]
// returns { sample(id, t) -> [{x, y, a}] }
export function simulateSpills(spills) {
  const tracks = {};
  for (const sp of spills) {
    const world = new RAPIER.World({ x: 0, y: 1800 });   // y down, px/s^2
    const r = mulberry(hash(sp.id));
    const ground = world.createCollider(RAPIER.ColliderDesc.cuboid(4000, 20).setTranslation(960, (sp.floor ?? 900) + 20).setFriction(0.9).setRestitution(0.3));
    if (sp.table) { const [x0, x1, y] = sp.table; world.createCollider(RAPIER.ColliderDesc.cuboid((x1 - x0) / 2, 10).setTranslation((x0 + x1) / 2, y + 10).setFriction(0.8).setRestitution(0.35)); }
    for (const wx of sp.walls || []) world.createCollider(RAPIER.ColliderDesc.cuboid(10, 2000).setTranslation(wx, 0));
    const bodies = [], size = sp.size ?? 34;
    for (let i = 0; i < (sp.n ?? 1); i++) {
      const b = world.createRigidBody(RAPIER.RigidBodyDesc.dynamic()
        .setTranslation(sp.from[0] + (r() - 0.5) * (sp.spread ?? 40), sp.from[1] - i * 6)
        .setLinvel((sp.vel?.[0] ?? 0) + (r() - 0.5) * 260, (sp.vel?.[1] ?? 0) - r() * 200)
        .setAngvel((r() - 0.5) * 18).setCcdEnabled(true));
      const shape = sp.shape === 'box' ? RAPIER.ColliderDesc.cuboid(size / 2, size / 2) : sp.shape === 'disc' ? RAPIER.ColliderDesc.cuboid(size / 2, size / 7) : RAPIER.ColliderDesc.ball(size / 2);
      world.createCollider(shape.setRestitution(sp.bounce ?? 0.45).setFriction(0.7).setDensity(1), b);
      bodies.push({ b, delay: i * (sp.stagger ?? 0.06) });
    }
    const frames = [], steps = Math.ceil((sp.dur ?? 5) / DT);
    for (let s = 0; s <= steps; s++) {
      frames.push(bodies.map(({ b }) => { const p = b.translation(); return { x: p.x, y: p.y, a: b.rotation() }; }));
      world.step();
    }
    world.free();
    tracks[sp.id] = { t0: sp.t, frames, prop: sp.prop, size, until: sp.until ?? Infinity };
  }
  return {
    tracks,
    sample(id, t) { const tr = tracks[id]; if (!tr || t < tr.t0 || t > tr.until) return null; const k = Math.min(tr.frames.length - 1, Math.floor((t - tr.t0) / DT)); return tr.frames[k]; },
  };
}

// hangers: [{id, x, y (anchor), len, gusts:[{t, force}], wind}] -> sample(id, t) -> {x, y, a} of the hanging bob
export function simulateHangers(hangers, duration) {
  const tracks = {};
  for (const h of hangers) {
    const engine = Matter.Engine.create({ gravity: { x: 0, y: 1, scale: 0.001 } });
    const bob = Matter.Bodies.rectangle(h.x, h.y + h.len, 40, 60, { frictionAir: h.damping ?? 0.02, density: 0.002 });
    const rope = Matter.Constraint.create({ pointA: { x: h.x, y: h.y }, bodyB: bob, length: h.len, stiffness: 1 });
    Matter.Composite.add(engine.world, [bob, rope]);
    const frames = [], steps = Math.ceil(duration / DT), gusts = (h.gusts || []).slice().sort((a, b) => a.t - b.t);
    let gi = 0;
    for (let s = 0; s <= steps; s++) {
      const t = s * DT;
      frames.push({ x: bob.position.x, y: bob.position.y, a: Math.atan2(bob.position.x - h.x, bob.position.y - h.y) });
      while (gi < gusts.length && gusts[gi].t <= t) { Matter.Body.applyForce(bob, bob.position, { x: gusts[gi].force * 0.002, y: 0 }); gi++; }
      if (h.wind) Matter.Body.applyForce(bob, bob.position, { x: noise1(t * 0.6, hash(h.id)) * h.wind * 0.00004, y: 0 });
      Matter.Engine.update(engine, DT * 1000);
    }
    tracks[h.id] = { frames, anchor: [h.x, h.y], prop: h.prop || 'lantern' };
  }
  return { tracks, sample(id, t) { const tr = tracks[id]; if (!tr) return null; return tr.frames[Math.min(tr.frames.length - 1, Math.max(0, Math.floor(t / DT)))]; } };
}
