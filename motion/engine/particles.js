// Weather and air with tsParticles: rain, drizzle, dust in the sun, falling leaves, fireflies, chimney smoke, confetti,
// snow, flies over a pig pen. tsParticles normally runs on the browser's frame clock; we replace its animation loop
// (setAnimationFunctions) and its random source (setRandom, seeded), and step it ourselves at the film's frame rate, so
// the same frame always shows the same particles. Each worker renders a contiguous range of frames; on the first frame of
// its range it fast-forwards the system from t = 0 (cheap), then steps one frame at a time.
import { tsParticles, setRandom, setAnimationFunctions } from '@tsparticles/engine';
import { loadSlim } from '@tsparticles/slim';
import { mulberry, hash } from './util.js';

let queue = [], slimLoaded = null;
setAnimationFunctions(cb => { queue.push(cb); return queue.length; }, () => {});

const PRESETS = {
  rain: { number: 260, color: '#9fb6d6', shape: 'line', size: [1, 2], speed: 38, direction: 'bottom', straight: true, opacity: 0.55, tilt: 12 },
  drizzle: { number: 120, color: '#b9c8de', shape: 'line', size: [1, 1.5], speed: 22, direction: 'bottom', straight: true, opacity: 0.45 },
  dust: { number: 70, color: '#fff2c4', shape: 'circle', size: [1, 3], speed: 0.4, direction: 'none', opacity: [0.2, 0.7] },
  leaves: { number: 26, color: ['#d98a3a', '#c4544a', '#e0b04a'], shape: 'square', size: [5, 9], speed: 2.2, direction: 'bottom-right', opacity: 0.9, rotate: true },
  fireflies: { number: 50, color: '#fff3a0', shape: 'circle', size: [2, 4], speed: 0.6, direction: 'none', opacity: [0.1, 1], twinkle: true },
  smoke: { number: 30, color: '#d9d4cc', shape: 'circle', size: [16, 40], speed: 1.2, direction: 'top', opacity: [0.05, 0.35] },
  confetti: { number: 120, color: ['#c4544a', '#e0b04a', '#4f86c6', '#5f9a4e', '#ffffff'], shape: 'square', size: [4, 8], speed: 5, direction: 'bottom', opacity: 1, rotate: true },
  snow: { number: 160, color: '#ffffff', shape: 'circle', size: [2, 5], speed: 1.6, direction: 'bottom', opacity: 0.85 },
  flies: { number: 14, color: '#1f1f1f', shape: 'circle', size: [1.5, 2.5], speed: 3, direction: 'none', opacity: 0.9 },
};

function options(p, area) {
  const pr = PRESETS[p.preset] || PRESETS.dust;
  return {
    fullScreen: { enable: false }, fpsLimit: 240, detectRetina: false, background: { color: 'transparent' },
    particles: {
      number: { value: p.number ?? pr.number, density: { enable: false } },
      color: { value: pr.color }, shape: { type: pr.shape },
      opacity: { value: Array.isArray(pr.opacity) ? { min: pr.opacity[0], max: pr.opacity[1] } : pr.opacity, animation: pr.twinkle ? { enable: true, speed: 1.2, sync: false } : { enable: false } },
      size: { value: { min: pr.size[0], max: pr.size[1] } },
      move: { enable: true, speed: (p.speed ?? 1) * pr.speed, direction: pr.direction, straight: !!pr.straight, outModes: { default: 'out' }, random: !pr.straight, angle: pr.tilt ? { offset: pr.tilt, value: 10 } : undefined },
      rotate: pr.rotate ? { value: { min: 0, max: 360 }, animation: { enable: true, speed: 20 } } : undefined,
      stroke: pr.shape === 'line' ? { width: 1.6, color: { value: pr.color } } : undefined,
    },
    emitters: undefined,
  };
}

export class ParticleLayer {
  // spec: {id, preset, number, speed, area:[x,y,w,h], t0, t1}
  constructor(spec, fps) { this.spec = spec; this.fps = fps; this.lastFrame = -1; }
  async init() {
    slimLoaded ??= loadSlim(tsParticles);
    await slimLoaded;
    const [x, y, w, h] = this.spec.area || [0, 0, 1920, 1080];
    this.el = document.createElement('div'); this.el.style.cssText = `position:absolute;left:-99999px;top:0;width:${w}px;height:${h}px`;
    document.body.appendChild(this.el);
    setRandom(mulberry(hash(this.spec.id)));
    this.container = await tsParticles.load({ id: 'p-' + this.spec.id, element: this.el, options: options(this.spec, this.spec.area) });
    this.canvas = this.el.querySelector('canvas');
    this.canvas.width = w; this.canvas.height = h;
    this.area = [x, y, w, h];
    queue = [];                                   // tsParticles queued its first frame: we drive it from now on
    this.ts = 1000;
  }
  _step(n) {
    setRandom(mulberry(hash(this.spec.id) + this.lastFrame));
    for (let i = 0; i < n; i++) {
      this.ts += 1000 / this.fps;
      this.container.draw(false);
      const q = queue; queue = [];
      for (const cb of q) cb(this.ts);
    }
  }
  // advance to frame index f (frames are rendered in order inside a worker; a jump back restarts the system)
  async seekFrame(f) {
    if (f === this.lastFrame) return;
    if (f < this.lastFrame || this.lastFrame < 0) { await this.container.refresh(); queue = []; this.ts = 1000; this.lastFrame = 0; this._step(Math.max(0, f)); this.lastFrame = f; return; }
    this._step(f - this.lastFrame); this.lastFrame = f;
  }
}
