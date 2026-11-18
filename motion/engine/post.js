// The final picture: OGL composites every frame on the GPU.
//   - GL Transitions (gl-transitions, MIT shaders only) between shots: the outgoing shot's last picture and the incoming
//     shot run through one transition shader (a wipe that follows the father's run, a page curl into a memory, ...).
//   - a grade for the style and mood (warm/cool/night), a vignette, paper grain (a p5 texture) and soft light (a glow
//     where the place has a light source).
// PixiJS renders the world into its own canvas; OGL takes that canvas (and a snapshot of the previous shot) as textures.
import { Renderer, Program, Mesh, Triangle, Texture } from 'ogl';
import GLT from 'gl-transitions/gl-transitions.json';

const VERT = `attribute vec2 uv; attribute vec2 position; varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position, 0., 1.); }`;
const MIT = Object.fromEntries(GLT.filter(t => /MIT/i.test(t.license || '')).map(t => [t.name, t]));
export const TRANSITIONS = Object.keys(MIT);

function frag(tr) {
  return `precision highp float;
uniform sampler2D uFrom, uTo, uGrain; uniform float progress, ratio, uTime, uVig, uGrainAmt, uLift;
uniform vec3 uTint; uniform vec2 uLight; uniform float uLightAmt;
varying vec2 vUv;
vec4 getFromColor(vec2 uv){ return texture2D(uFrom, uv); }
vec4 getToColor(vec2 uv){ return texture2D(uTo, uv); }
${tr ? tr.glsl : 'vec4 transition(vec2 uv){ return getFromColor(uv); }'}
void main(){
  vec4 c = transition(vUv);
  vec3 col = c.rgb * uTint + uLift;
  float d = distance(vUv, vec2(0.5)); col *= 1.0 - uVig * smoothstep(0.35, 0.85, d);
  float l = uLightAmt * (1.0 - smoothstep(0.0, 0.55, distance(vUv * vec2(ratio, 1.0), uLight * vec2(ratio, 1.0)))); col += vec3(1.0, 0.86, 0.6) * l;
  vec3 gr = texture2D(uGrain, vUv * vec2(ratio, 1.0) * 2.2 + vec2(fract(uTime * 7.31), fract(uTime * 3.17))).rgb;
  col = mix(col, col * (gr * 1.4), uGrainAmt);
  gl_FragColor = vec4(col, 1.0);
}`;
}

const GRADES = {
  day: { tint: [1.02, 1.0, 0.96], lift: 0.0, vig: 0.28 },
  warm: { tint: [1.06, 1.0, 0.9], lift: 0.01, vig: 0.32 },
  dusk: { tint: [1.08, 0.94, 0.86], lift: 0.0, vig: 0.38 },
  cool: { tint: [0.92, 0.97, 1.05], lift: 0.0, vig: 0.34 },
  grey: { tint: [0.9, 0.92, 0.95], lift: 0.02, vig: 0.4 },
  night: { tint: [0.78, 0.84, 1.05], lift: 0.0, vig: 0.5 },
};

export class Post {
  constructor(canvas, w, h, grainCanvas) {
    this.r = new Renderer({ canvas, width: w, height: h, dpr: 1, preserveDrawingBuffer: true });
    this.gl = this.r.gl; this.w = w; this.h = h;
    this.geo = new Triangle(this.gl);
    this.tFrom = new Texture(this.gl, { generateMipmaps: false, flipY: true });
    this.tTo = new Texture(this.gl, { generateMipmaps: false, flipY: true });
    this.tGrain = new Texture(this.gl, { image: grainCanvas, wrapS: this.gl.REPEAT, wrapT: this.gl.REPEAT, generateMipmaps: false });
    this.programs = {};
  }
  program(name) {
    if (this.programs[name]) return this.programs[name];
    const tr = name ? MIT[name] : null;
    const uniforms = {
      uFrom: { value: this.tFrom }, uTo: { value: this.tTo }, uGrain: { value: this.tGrain },
      progress: { value: 0 }, ratio: { value: this.w / this.h }, uTime: { value: 0 }, uVig: { value: 0.3 }, uGrainAmt: { value: 0.08 },
      uTint: { value: [1, 1, 1] }, uLift: { value: 0 }, uLight: { value: [0.5, 0.3] }, uLightAmt: { value: 0 },
    };
    if (tr) for (const [k, v] of Object.entries(tr.defaultParams || {})) uniforms[k] = { value: typeof v === 'boolean' ? (v ? 1 : 0) : v };
    const program = new Program(this.gl, { vertex: VERT, fragment: frag(tr), uniforms });
    return (this.programs[name] = new Mesh(this.gl, { geometry: this.geo, program }));
  }
  // from/to: canvases; transition: {name, progress, params}; look: {grade, grain, light:[x,y,amt]}
  draw(from, to, t, transition, look = {}) {
    const mesh = this.program(transition && to ? transition.name : null), u = mesh.program.uniforms;
    const bind = (src, tex, uni) => { if (src && src.texture === undefined && src.width !== undefined && !src.gl) { tex.image = src; tex.needsUpdate = true; uni.value = tex; } else if (src) uni.value = src; };
    bind(from, this.tFrom, u.uFrom); if (to) bind(to, this.tTo, u.uTo);
    if (transition && to) { u.progress.value = transition.progress; for (const [k, v] of Object.entries(transition.params || {})) if (u[k]) u[k].value = v; }
    const gr = GRADES[look.grade || 'day'] || GRADES.day;
    u.uTint.value = gr.tint; u.uLift.value = gr.lift; u.uVig.value = look.vignette ?? gr.vig; u.uGrainAmt.value = look.grain ?? 0.035; u.uTime.value = Math.floor(t * 8) / 8;   // grain on eighths: moving grain on every frame makes the film incompressible
    const L = look.light; u.uLight.value = L ? [L[0], 1 - L[1]] : [0.5, 0.5]; u.uLightAmt.value = L ? L[2] : 0;
    this.r.render({ scene: mesh });
  }
}
