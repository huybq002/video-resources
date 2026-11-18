// 3D insert shots with OGL: a prop that matters to the story (the ring, the last coin, the father's lantern) turns slowly
// in light, as a close-up insert. Models are .glb files made by tools/props3d.mjs with glTF-Transform (procedural
// geometry, materials, deduplicated and welded), loaded here with OGL's GLTFLoader and drawn with a soft toon shader.
import { Camera, Transform, Program, GLTFLoader, RenderTarget, Mesh, Plane, Vec3 } from 'ogl';
import { springStep, SPRING } from './springs.js';

const VERT = `attribute vec3 position; attribute vec3 normal; uniform mat4 modelViewMatrix, projectionMatrix; uniform mat3 normalMatrix;
varying vec3 vN; varying vec3 vV; void main(){ vN = normalize(normalMatrix * normal); vec4 mv = modelViewMatrix * vec4(position, 1.); vV = -mv.xyz; gl_Position = projectionMatrix * mv; }`;
const FRAG = `precision highp float; uniform vec4 uColor; uniform float uMetal; varying vec3 vN; varying vec3 vV;
void main(){ vec3 n = normalize(vN), v = normalize(vV), l = normalize(vec3(0.5, 0.8, 0.6));
  float d = max(dot(n, l), 0.); float band = d > 0.6 ? 1.0 : d > 0.25 ? 0.72 : 0.45;
  vec3 h = normalize(l + v); float s = pow(max(dot(n, h), 0.), 40.) * uMetal; float rim = pow(1. - max(dot(n, v), 0.), 3.) * 0.35;
  float edge = smoothstep(0.18, 0.28, max(dot(n, v), 0.));
  vec3 col = uColor.rgb * band + vec3(1.0, 0.95, 0.8) * step(0.5, s) * 0.8 + rim;
  gl_FragColor = vec4(mix(vec3(0.17, 0.15, 0.13), col, edge), 1.); }`;
const BG_FRAG = `precision highp float; uniform vec3 uTop, uBot; varying vec2 vUv; void main(){ gl_FragColor = vec4(mix(uBot, uTop, vUv.y), 1.); }`;
const BG_VERT = `attribute vec3 position; attribute vec2 uv; varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy * 2.0, 0.999, 1.); }`;

export class Insert3D {
  constructor(gl, w, h) {
    this.gl = gl; this.target = new RenderTarget(gl, { width: w, height: h });
    this.camera = new Camera(gl, { fov: 30, aspect: w / h }); this.camera.position.set(0, 0, 6);
    this.scene = new Transform(); this.models = {};
    this.bg = new Mesh(gl, { geometry: new Plane(gl), program: new Program(gl, { vertex: BG_VERT, fragment: BG_FRAG, depthTest: false, uniforms: { uTop: { value: [0.98, 0.93, 0.82] }, uBot: { value: [0.85, 0.72, 0.55] } } }) });
  }
  async load(name, url) {
    const g = await GLTFLoader.load(this.gl, url), root = new Transform();
    (g.scene || g.scenes[0]).forEach(n => n.setParent(root));
    root.traverse(n => {
      if (!n.program) return;
      const m = n.program.gltfMaterial, pbr = m?.baseColorFactor || [0.85, 0.65, 0.3, 1];
      n.program = new Program(this.gl, { vertex: VERT, fragment: FRAG, uniforms: { uColor: { value: pbr }, uMetal: { value: m?.metallicFactor ?? 0.6 } } });
    });
    this.models[name] = root;
  }
  // shot: {model, t0, t1, spin, tilt, bg:[top,bot], drop}
  render(shot, t) {
    const m = this.models[shot.model]; if (!m) return null;
    this.scene.children.slice().forEach(c => c.setParent(null)); m.setParent(this.scene);
    const lt = t - shot.t0, arrive = springStep(lt, SPRING.wobbly);
    m.rotation.y = (shot.spin ?? 0.6) * lt + 0.4; m.rotation.x = shot.tilt ?? 0.35;
    m.position.y = (1 - arrive) * (shot.drop ?? 2.5); const sc = shot.scale ?? 1; m.scale.set(sc, sc, sc);
    this.camera.position.z = 6 - Math.min(1.2, lt * (shot.push ?? 0.15)); this.camera.lookAt(new Vec3(0, 0, 0));
    if (shot.bg) { this.bg.program.uniforms.uTop.value = shot.bg[0]; this.bg.program.uniforms.uBot.value = shot.bg[1]; }
    const r = this.gl.renderer;
    r.render({ scene: this.bg, target: this.target, clear: true });
    r.render({ scene: this.scene, camera: this.camera, target: this.target, clear: false });
    return this.target.texture;
  }
}
