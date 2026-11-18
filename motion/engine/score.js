// The score, composed from the film's own timeline with Tone.js and rendered offline (Tone.Offline) to a WAV.
// One motif per story idea (the "home" theme returns when the son turns home and at the embrace), instruments chosen for
// the world (a plucked lute, a reed-like lead, a warm pad, a frame drum), a real silence before the turn, and swells on
// the story's hit points. tools/score.mjs opens dist/score.html in headless Chromium and saves window.SCORE_WAV.
import * as Tone from 'tone';

const SCALES = { major: [0, 2, 4, 5, 7, 9, 11], minor: [0, 2, 3, 5, 7, 8, 10], dorian: [0, 2, 3, 5, 7, 9, 10], phrygian: [0, 1, 3, 5, 7, 8, 10] };
const midi = (root, scale, deg, oct = 0) => { const s = SCALES[scale] || SCALES.major; const o = Math.floor(deg / s.length); return root + s[((deg % s.length) + s.length) % s.length] + 12 * (o + oct); };
const f = m => Tone.Frequency(m, 'midi').toFrequency();

// a motif is scale degrees + durations in beats
const MOTIFS = {
  home: [[0, 1], [2, 1], [4, 2], [3, 1], [2, 1], [1, 2], [0, 2]],
  wander: [[4, 0.5], [5, 0.5], [7, 1], [5, 0.5], [4, 0.5], [2, 1]],
  feast: [[0, 0.5], [2, 0.5], [4, 0.5], [7, 0.5], [4, 0.5], [2, 0.5], [0, 1]],
  hunger: [[0, 2], [-1, 2], [-2, 4]],
  road: [[0, 1], [1, 1], [2, 2]],
};

function wavFromBuffer(buf) {
  const ch = buf.numberOfChannels, len = buf.length, sr = buf.sampleRate, data = new DataView(new ArrayBuffer(44 + len * ch * 2));
  const w = (o, s) => [...s].forEach((c, i) => data.setUint8(o + i, c.charCodeAt(0)));
  w(0, 'RIFF'); data.setUint32(4, 36 + len * ch * 2, true); w(8, 'WAVE'); w(12, 'fmt '); data.setUint32(16, 16, true); data.setUint16(20, 1, true);
  data.setUint16(22, ch, true); data.setUint32(24, sr, true); data.setUint32(28, sr * ch * 2, true); data.setUint16(32, ch * 2, true); data.setUint16(34, 16, true); w(36, 'data'); data.setUint32(40, len * ch * 2, true);
  const chans = [...Array(ch)].map((_, i) => buf.getChannelData(i)); let o = 44;
  for (let i = 0; i < len; i++) for (let c = 0; c < ch; c++) { const v = Math.max(-1, Math.min(1, chans[c][i])); data.setInt16(o, v * 32767, true); o += 2; }
  return data.buffer;
}

// spec: {duration, root (midi), sections:[{t0, t1, mood, motif, bpm, scale, energy 0..1, instruments:[lute,reed,pad,drum,bell], silence}], hits:[{t, kind}]}
async function compose(spec) {
  const buf = await Tone.Offline(({ transport }) => {
    const master = new Tone.Compressor(-18, 3).toDestination(), verb = new Tone.Reverb({ decay: 3.2, wet: 0.28 }).connect(master);
    const lute0 = new Tone.PluckSynth({ attackNoise: 1.2, dampening: 3600, resonance: 0.93 }).connect(verb); lute0.volume.value = -6;
    const reed0 = new Tone.MonoSynth({ oscillator: { type: 'fmsawtooth', modulationType: 'sine', harmonicity: 1.01 }, filter: { Q: 2, type: 'lowpass', rolloff: -24 }, envelope: { attack: 0.08, decay: 0.2, sustain: 0.7, release: 0.6 }, filterEnvelope: { attack: 0.06, decay: 0.3, sustain: 0.4, baseFrequency: 600, octaves: 2.2 } }).connect(new Tone.Vibrato(5, 0.08).connect(verb)); reed0.volume.value = -17;
    const pad0 = new Tone.PolySynth(Tone.AMSynth, { harmonicity: 1.5, envelope: { attack: 1.4, decay: 0.5, sustain: 0.8, release: 2.5 } }).connect(verb); pad0.volume.value = -22;
    const drum0 = new Tone.MembraneSynth({ pitchDecay: 0.04, octaves: 3, envelope: { attack: 0.001, decay: 0.35, sustain: 0 } }).connect(master); drum0.volume.value = -14;
    const tick0 = new Tone.NoiseSynth({ noise: { type: 'pink' }, envelope: { attack: 0.001, decay: 0.06, sustain: 0 } }).connect(master); tick0.volume.value = -30;
    const bell0 = new Tone.FMSynth({ harmonicity: 3.01, modulationIndex: 12, envelope: { attack: 0.001, decay: 1.6, sustain: 0, release: 1.6 } }).connect(verb); bell0.volume.value = -20;
    // monophonic synths need strictly increasing start times: collect every note, sort, nudge ties, then schedule
    const Q = [];
    const at = (syn) => new Proxy(syn, { get: (o, k) => (k === 'triggerAttack' || k === 'triggerAttackRelease') ? (...a) => Q.push({ o, k, a }) : o[k] });
    const lute = at(lute0), reed = at(reed0), pad = at(pad0), drum = at(drum0), tick = at(tick0), bell = at(bell0);
    const root = spec.root ?? 50;
    for (const s of spec.sections) {
      if (s.silence) continue;
      const bpm = s.bpm ?? 72, beat = 60 / bpm, sc = s.scale || 'major', ins = new Set(s.instruments || ['lute', 'pad']), e = s.energy ?? 0.5;
      const chordDegs = s.chords || [0, 3, 4, 0];
      // pad chords every bar
      if (ins.has('pad')) for (let t = s.t0, i = 0; t < s.t1 - 0.5; t += beat * 4, i++) { const d = chordDegs[i % chordDegs.length]; pad.triggerAttackRelease([f(midi(root, sc, d, -1)), f(midi(root, sc, d + 2, -1)), f(midi(root, sc, d + 4, -1))], Math.min(beat * 4, s.t1 - t), t, 0.35 + e * 0.3); }
      // lute arpeggio
      if (ins.has('lute')) for (let t = s.t0, i = 0; t < s.t1 - 0.2; t += beat / (e > 0.6 ? 2 : 1), i++) { const d = chordDegs[Math.floor((t - s.t0) / (beat * 4)) % chordDegs.length]; const deg = d + [0, 2, 4, 2, 7, 4][i % 6]; lute.triggerAttack(f(midi(root, sc, deg)), t); }
      // motif on the lead, phrased with rests
      if (ins.has('reed') && s.motif && MOTIFS[s.motif]) { let t = s.t0 + beat * (s.motifAt ?? 2); while (t < s.t1 - beat * 4) { for (const [d, b] of MOTIFS[s.motif]) { if (t > s.t1 - 0.3) break; reed.triggerAttackRelease(f(midi(root, sc, d, 1)), b * beat * 0.92, t, 0.6 + e * 0.3); t += b * beat; } t += beat * 4; } }
      if (ins.has('drum')) for (let t = s.t0; t < s.t1 - 0.1; t += beat) { drum.triggerAttackRelease(f(midi(root, sc, 0, -2)), beat * 0.5, t, ((t - s.t0) / beat) % 2 < 1 ? 0.8 : 0.45); if (e > 0.5) tick.triggerAttackRelease(beat * 0.1, t + beat / 2, 0.4); }
      if (ins.has('bell')) for (let t = s.t0 + beat * 2; t < s.t1 - 1; t += beat * 8) bell.triggerAttackRelease(f(midi(root, sc, 4, 1)), beat * 2, t, 0.5);
    }
    for (const h of spec.hits || []) {
      if (h.kind === 'swell') pad.triggerAttackRelease([f(midi(root, 'major', 0, 0)), f(midi(root, 'major', 4, 0)), f(midi(root, 'major', 7, 0))], 3, h.t, 0.9);
      if (h.kind === 'sting') bell.triggerAttackRelease(f(midi(root, 'minor', 5, 1)), 1.5, h.t, 0.8);
      if (h.kind === 'boom') drum.triggerAttackRelease(f(midi(root, 'minor', 0, -2)), 1, h.t, 1);
    }
    const timeIdx = q => (q.k === 'triggerAttack' || q.o === tick0) ? 1 : 2;
    Q.sort((p, q) => p.a[timeIdx(p)] - q.a[timeIdx(q)]);
    const last = new Map();
    for (const q of Q) { const i = timeIdx(q); let t = q.a[i]; const l = last.get(q.o); if (q.o !== pad0 && l != null && t <= l) t = l + 0.002; last.set(q.o, t); q.a[i] = t; q.o[q.k](...q.a); }
  }, spec.duration, 2, 44100);
  return buf.get ? buf.get() : buf;
}

window.composeScore = async spec => {
  const b = await compose(spec), wav = new Uint8Array(wavFromBuffer(b));
  let s = ''; for (let i = 0; i < wav.length; i += 0x8000) s += String.fromCharCode.apply(null, wav.subarray(i, i + 0x8000));
  return btoa(s);
};
window.SCORE_READY = true;
