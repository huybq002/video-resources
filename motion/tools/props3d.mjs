// Build the 3D story props as .glb with glTF-Transform: node motion/tools/props3d.mjs <out-dir> [ring coin lantern cup]
// Geometry is generated here (torus, cylinder, sphere, box), given a PBR material, then welded and deduplicated with
// @gltf-transform/functions so the files stay small. three3d.js loads them with OGL for insert shots.
import { Document, NodeIO } from '@gltf-transform/core';
import { weld, dedup, prune } from '@gltf-transform/functions';
import fs from 'fs'; import path from 'path';

function torus(R, r, seg = 64, side = 24) {
  const P = [], N = [], I = [];
  for (let i = 0; i <= seg; i++) for (let j = 0; j <= side; j++) {
    const u = i / seg * Math.PI * 2, v = j / side * Math.PI * 2, cx = Math.cos(u) * R, cy = Math.sin(u) * R;
    const x = (R + r * Math.cos(v)) * Math.cos(u), y = (R + r * Math.cos(v)) * Math.sin(u), z = r * Math.sin(v);
    P.push(x, y, z); const n = [x - cx, y - cy, z], l = Math.hypot(...n); N.push(n[0] / l, n[1] / l, n[2] / l);
  }
  for (let i = 0; i < seg; i++) for (let j = 0; j < side; j++) { const a = i * (side + 1) + j, b = a + side + 1; I.push(a, b, a + 1, b, b + 1, a + 1); }
  return { P, N, I };
}
function sphere(r, cx = 0, cy = 0, cz = 0, seg = 32) {
  const P = [], N = [], I = [];
  for (let i = 0; i <= seg; i++) for (let j = 0; j <= seg; j++) {
    const th = i / seg * Math.PI, ph = j / seg * Math.PI * 2, n = [Math.sin(th) * Math.cos(ph), Math.cos(th), Math.sin(th) * Math.sin(ph)];
    P.push(cx + n[0] * r, cy + n[1] * r, cz + n[2] * r); N.push(...n);
  }
  for (let i = 0; i < seg; i++) for (let j = 0; j < seg; j++) { const a = i * (seg + 1) + j, b = a + seg + 1; I.push(a, b, a + 1, b, b + 1, a + 1); }
  return { P, N, I };
}
function cylinder(r, h, seg = 64) {
  const P = [], N = [], I = [];
  for (let i = 0; i <= seg; i++) { const a = i / seg * Math.PI * 2, c = Math.cos(a), s = Math.sin(a); P.push(c * r, -h / 2, s * r, c * r, h / 2, s * r); N.push(c, 0, s, c, 0, s); }
  for (let i = 0; i < seg; i++) { const a = i * 2; I.push(a, a + 2, a + 1, a + 1, a + 2, a + 3); }
  for (const [y, ny] of [[h / 2, 1], [-h / 2, -1]]) { const c0 = P.length / 3; P.push(0, y, 0); N.push(0, ny, 0); for (let i = 0; i <= seg; i++) { const a = i / seg * Math.PI * 2; P.push(Math.cos(a) * r, y, Math.sin(a) * r); N.push(0, ny, 0); } for (let i = 0; i < seg; i++) ny > 0 ? I.push(c0, c0 + i + 2, c0 + i + 1) : I.push(c0, c0 + i + 1, c0 + i + 2); }
  return { P, N, I };
}

const MODELS = {
  ring: [[torus(0.9, 0.16), [0.88, 0.66, 0.22, 1], 0.9], [sphere(0.28, 0, 1.08, 0), [0.55, 0.8, 0.95, 1], 0.4]],
  coin: [[cylinder(1.0, 0.16), [0.93, 0.74, 0.28, 1], 0.95]],
  cup: [[cylinder(0.6, 1.3), [0.82, 0.73, 0.45, 1], 0.5]],
  lantern: [[cylinder(0.55, 1.2, 6), [0.95, 0.76, 0.3, 1], 0.3], [sphere(0.35, 0, 0, 0), [1, 0.95, 0.7, 1], 0]],
};

const outDir = path.resolve(process.argv[2] || '.'); fs.mkdirSync(outDir, { recursive: true });
const names = process.argv.slice(3).length ? process.argv.slice(3) : Object.keys(MODELS);
const io = new NodeIO();
for (const name of names) {
  const doc = new Document(), buf = doc.createBuffer(), scene = doc.createScene(name), node = doc.createNode(name);
  const mesh = doc.createMesh(name);
  for (const [g, color, metal] of MODELS[name]) {
    const pos = doc.createAccessor().setType('VEC3').setArray(new Float32Array(g.P)).setBuffer(buf);
    const nor = doc.createAccessor().setType('VEC3').setArray(new Float32Array(g.N)).setBuffer(buf);
    const idx = doc.createAccessor().setType('SCALAR').setArray(new Uint32Array(g.I)).setBuffer(buf);
    const mat = doc.createMaterial(name + '-mat').setBaseColorFactor(color).setMetallicFactor(metal).setRoughnessFactor(0.35);
    mesh.addPrimitive(doc.createPrimitive().setAttribute('POSITION', pos).setAttribute('NORMAL', nor).setIndices(idx).setMaterial(mat));
  }
  node.setMesh(mesh); scene.addChild(node);
  await doc.transform(weld(), dedup(), prune());
  const file = path.join(outDir, name + '.glb'); fs.writeFileSync(file, await io.writeBinary(doc)); console.log('model', file, fs.statSync(file).size, 'bytes');
}
