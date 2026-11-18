// react-spring's spring model, made seekable.
// react-spring runs springs on a real-time frame loop, which a frame-by-frame renderer cannot use. We take its physical
// presets (tension, friction, mass from `config`) and solve the same damped spring in closed form, so a pose blend or a
// caption pop at time t is the same on every render and on every worker. Use it for anticipation, overshoot and settle.
import { config as SPRING } from '@react-spring/web';
import { clamp } from './util.js';

export { SPRING };

// value of a spring that starts at 0 (at rest) and is released toward 1 at time 0; dt = seconds since release
export function springStep(dt, cfg = SPRING.default) {
  if (dt <= 0) return 0;
  const k = cfg.tension ?? 170, c = cfg.friction ?? 26, m = cfg.mass ?? 1;
  const w0 = Math.sqrt(k / m), zeta = c / (2 * Math.sqrt(k * m));
  if (zeta < 1) {
    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * w0 * dt) * (Math.cos(wd * dt) + (zeta * w0 / wd) * Math.sin(wd * dt));
  }
  return 1 - Math.exp(-w0 * dt) * (1 + w0 * dt);       // critically/over damped: no overshoot
}

// a weight that springs in at t0 and springs out at t1 (0..1, may overshoot a little for bouncy presets)
export function springWindow(t, t0, t1, cfgIn = SPRING.default, cfgOut = SPRING.default) {
  if (t < t0) return 0;
  const up = springStep(t - t0, cfgIn);
  if (t1 == null || t < t1) return up;
  const at1 = springStep(t1 - t0, cfgIn);
  return at1 * (1 - springStep(t - t1, cfgOut));
}

export const settle = (t, t0, cfg = SPRING.gentle) => clamp(springStep(t - t0, cfg), -0.2, 1.3);
