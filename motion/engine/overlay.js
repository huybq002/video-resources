// Words on screen, as DOM over the picture (the screenshot captures both):
//   - captions with React; each caption springs in (react-spring presets, solved in closed form by springs.js) and the
//     spoken word lights up on its faster-whisper time, so the reader's eye follows the voice;
//   - scene title cards and story text (a sign, a letter, "three months later") with anime.js timelines that are never
//     played, only seeked to the frame time (letter staggers, elastic pops), so they are exact on every frame.
import React from 'react';
import { createRoot } from 'react-dom/client';
import { flushSync } from 'react-dom';
import { createTimeline, stagger } from 'animejs';
import { springStep, SPRING } from './springs.js';

const h = React.createElement;

function Caption({ cap, t, theme }) {
  if (!cap) return null;
  const k = springStep(t - cap.t0, SPRING.stiff), out = cap.t1 - t < 0.18 ? Math.max(0, (cap.t1 - t) / 0.18) : 1;
  const words = cap.words?.length ? cap.words : [{ w: cap.text, t0: cap.t0, t1: cap.t1 }];
  return h('div', { style: { position: 'absolute', left: 0, right: 0, bottom: theme.bottom ?? 70, display: 'flex', justifyContent: 'center', opacity: Math.min(1, k) * out, transform: `translateY(${(1 - Math.min(1, k)) * 24}px) scale(${0.94 + 0.06 * k})` } },
    h('div', { style: { background: theme.box ?? 'rgba(250,244,230,.92)', color: theme.ink ?? '#2b2622', padding: '10px 26px', borderRadius: 14, border: '3px solid #2b2622', font: `600 ${theme.size ?? 46}px ${theme.font ?? 'Patrick Hand, Comic Neue, sans-serif'}`, maxWidth: 1500, textAlign: 'center', boxShadow: '0 6px 0 rgba(0,0,0,.15)' } },
      words.map((w, i) => h('span', { key: i, style: { color: t >= w.t0 ? (theme.ink ?? '#2b2622') : (theme.dim ?? 'rgba(43,38,34,.45)'), transition: 'none' } }, (i ? ' ' : '') + w.w))));
}

export class Overlay {
  constructor(el, theme = {}) {
    this.el = el; this.theme = theme;
    this.capEl = document.createElement('div'); this.capEl.style.cssText = 'position:absolute;inset:0;pointer-events:none';
    this.cardEl = document.createElement('div'); this.cardEl.style.cssText = 'position:absolute;inset:0;pointer-events:none';
    el.appendChild(this.cardEl); el.appendChild(this.capEl);
    this.root = createRoot(this.capEl); this.cards = [];
  }
  // cards: [{t0, t1, text, sub, pos:'top-left'|'center', size}]
  addCards(cards) {
    for (const c of cards) {
      const box = document.createElement('div');
      box.style.cssText = `position:absolute;${c.pos === 'center' ? 'left:0;right:0;top:40%;text-align:center' : 'left:70px;top:56px'};font:700 ${c.size ?? 64}px ${this.theme.titleFont ?? 'Patrick Hand, sans-serif'};color:${c.color ?? '#2b2622'};text-shadow:0 3px 0 rgba(255,255,255,.5);opacity:0`;
      box.innerHTML = [...c.text].map(ch => `<span style="display:inline-block;white-space:pre">${ch}</span>`).join('') + (c.sub ? `<div class="sub" style="font-size:.45em;opacity:0;margin-top:6px">${c.sub}</div>` : '');
      this.cardEl.appendChild(box);
      const tl = createTimeline({ autoplay: false })
        .add(box, { opacity: [0, 1], duration: 1 }, 0)
        .add(box.querySelectorAll('span'), { y: [40, 0], opacity: [0, 1], rotate: [-12, 0], ease: 'outElastic(1, .6)', duration: 700, delay: stagger(35) }, 0)
        .add(box.querySelectorAll('.sub'), { opacity: [0, 1], duration: 400 }, 500);
      this.cards.push({ ...c, box, tl, len: Math.round((c.t1 - c.t0) * 1000) });
    }
  }
  render(t, cap) {
    for (const c of this.cards) {
      if (t < c.t0 || t > c.t1) { c.box.style.display = 'none'; continue; }
      c.box.style.display = 'block'; c.tl.seek(Math.min(1400, (t - c.t0) * 1000));
      const fade = Math.min(1, (c.t1 - t) / 0.35); c.box.style.opacity = String(fade);
    }
    flushSync(() => this.root.render(h(Caption, { cap, t, theme: this.theme })));
  }
}
