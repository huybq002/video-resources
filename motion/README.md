# hezb-motion: the film engine

Since 2026-11-17 (owner decision) every Hezb Stories video is drawn by this engine, replacing the stickman-video-director
runtime. A film is a web page with `render(t)`. Headless Chromium renders it frame by frame. Everything is code: no
image or video model, no paid API.

```
story.json ──narrate.py──► voice/ (narration.wav, timing.json) ──align.py (faster-whisper)──► voice/words.json
      │
      └─ direct.py (you, the director, with director.py + worlds.py) ──► film/film.json
                                                            │
             tools/score.mjs (Tone.js) ──► film/out/score.wav
             tools/render.mjs (Chromium + the engine) ──► film/out/video.mp4
             mix.py (voice + score + room tone + foley, −14 LUFS) ──► the film
```

## What each library does

| library | job in the engine | file |
|---|---|---|
| PixiJS | the stage: parallax layers, actors, props and the camera, rendered on WebGL | `engine/index.js` |
| paper.js | hand-inked vector drawings: houses, hills, fences, tables, doors, props | `engine/places.js` |
| p5.js | generative painting: skies, paper grain, wheat and grass strokes, mud, planks, stones, stars | `engine/places.js` |
| OGL | the final GPU composite: grade, vignette, grain and light; 3D insert shots (`three3d.js`) | `engine/post.js`, `engine/three3d.js` |
| GL Transitions | the transition shaders between shots (MIT ones only) | `engine/post.js` |
| glTF-Transform | builds the 3D story props (ring, coin, cup, lantern) as `.glb` | `tools/props3d.mjs` |
| tsParticles | weather and air: rain, drizzle, dust, leaves, fireflies, smoke, confetti, snow, flies | `engine/particles.js` |
| Rapier | rigid props that fall, bounce and settle: coins on a table, a thrown hoe, spilled food | `engine/physics.js` |
| Matter.js | hanging things on ropes: lanterns that swing when a story moment hits them | `engine/physics.js` |
| react-spring | its spring presets, solved in closed form: pose blends with anticipation and settle; captions that spring in | `engine/springs.js`, `engine/overlay.js` |
| React | the caption layer, rendered on every frame | `engine/overlay.js` |
| anime.js | scene title cards and story text: timelines that are only seeked, never played | `engine/overlay.js` |
| Tone.js | the original score, composed from the film's sections and hit points, rendered offline | `engine/score.js`, `tools/score.mjs` |
| faster-whisper | word timings: mouths move on the speaker's words, captions light up word by word, actions land on their word | `align.py` |

Each frame is a pure function of `t`. Nothing reads the clock or `Math.random`.
- Physics is simulated once at load.
- Particles are stepped from a seeded start.
- Springs are closed-form.
- Anime timelines are seeked.

So any frame renders the same on every run, and the workers can split the film.

## The direction rules (owner, 2026-11-17)

1. **No motion without a purpose.** A character at rest only breathes and blinks. Every other movement is a verb in the
   action list that the story asks for (walk out, hand over the bag, kneel, run with open arms). There are no gesture
   loops.
2. **The world lives around the story and reacts to it.** Birds cross; smoke rises; wheat bends in gusts; rain falls on
   the pig farm; the tavern crowd toasts. Story moments trigger the world: birds scatter when the father runs, the
   lanterns swing when the coins slam down, wind sweeps the wheat when the hoe is thrown.
3. **A new picture often.** A shot lasts at most about 6 s. Shot kinds vary (wide, medium, close, two, over, detail,
   track, reveal, 3D insert). Never use the same kind three times in a row. `director.py` checks this on save.
4. **Objects the words name are on screen when they are named**, big enough to read: the bag, the coins, the bread, the
   ring, the robe.
5. Sound follows the picture:
   - every visible action has a sound;
   - the score has real silences before turns;
   - the score swells on hit points.

## Commands

```bash
bash motion/install.sh                                            # node modules + bundle (runner: links the image's modules)
python motion/align.py outputs/<id>/voice                         # words.json (faster-whisper)
python outputs/<id>/direct.py                                     # film/film.json
node motion/tools/props3d.mjs outputs/<id>/film/models ring coin  # 3D props used by insert3d shots
node motion/tools/render.mjs outputs/<id>/film --still 5,20,40    # review stills (out/still-*.png)
node motion/tools/score.mjs outputs/<id>/film                     # out/score.wav
node motion/tools/render.mjs outputs/<id>/film --workers 3        # out/video.mp4 (RENDER_GL=gpu where a GPU exists)
python motion/mix.py outputs/<id>/film outputs/<id>/voice outputs/<id>/<id>.mp4
```

The worked example is `examples/prodigal-son/direct.py`: a 5-minute film with 120+ shots, 11 scenes and 125+ actions.

## Credits and licences

- Libraries: PixiJS (MIT), paper.js (MIT), p5.js (LGPL-2.1, loaded unmodified as a library), OGL (Unlicense),
  gl-transitions (MIT; only MIT shaders are used), glTF-Transform (MIT), tsParticles (MIT), Rapier (Apache-2.0),
  Matter.js (MIT), react-spring (MIT), React (MIT), anime.js (MIT), Tone.js (MIT), faster-whisper (MIT), Playwright
  (Apache-2.0), esbuild (MIT).
- Font: Patrick Hand (SIL OFL 1.1, `fonts/OFL.txt`).
- Techniques were learned from these projects. Their code was not copied, and none of their characters, films or style
  texts are used:
  - lemo-opuscar (code MIT; docs CC BY-NC 4.0): frame-by-frame capture with workers, one timeline driving picture and
    sound, the review loop;
  - mg-styles-15 and mg-video (MIT);
  - huashu-art-motion (MIT; its demo characters are excluded from that licence).

## Reference for the director

**Place elements** (`far`, `mid`, `front`, `near` lists in a place spec; coordinates in the 1920x1080 world):
- paper.js: `hills`, `dune`, `ground`, `road`, `house`, `shack`, `tree`, `palm`, `fence`, `wall`, `floor`, `window`, `door`, `table`, `shelf`, `pen`, `trough`, `well`, `gate`, `stall`, `sign`, `boulder`.
- p5.js: `field`, `grass`, `mud`, `planks`, `bricks`, `stones`.
- Sky: `{top, bottom, sun:[x,y,r], moon:[x,y,r], stars:true}`.

**Ambient life** (`ambient` list, drawn with the camera): `clouds`, `birds` (`scatter` = story time they burst up), `smoke`, `wheat` (`gusts`), `pigs`, `glow`, `cloth`, `ripples`, `fire`, `passers`.

**Particles** (`particles` list; `near: true` = in front; `t0`/`t1` limit them to part of a scene): `rain`, `drizzle`, `dust`, `leaves`, `fireflies`, `smoke`, `confetti`, `snow`, `flies`.

**Props** (`f.prop(scene, id, prop, x, y, s=...)`, with `held=[{who, t0, t1}]` to put it in a hand, `follow={who, dx, dy}` to carry it along with someone, `pop=t` to spring it in, `keys` to move it, `from`/`until` to show it for part of the scene):
`bag coin cup bread ring robe sandals lantern pod stick donkey bed jar bandage`. New props are small paper.js functions in `engine/places.js` (`PROPS`).

**Actor looks** (`f.look`): `shirt vest apron belt shoes skin hair hairStyle(short|long|bald) beard moustache headscarf skirt rags`.

**Verbs** (`f.act(scene, who, verb, t0, t1, emotion=...)`): `walk run` (`to=[x,y]`, `open`, `carry`), `give take beg point wave cheer toast drink eat count sigh shout armsOpen carry look nod shake turnAway crossArms dig kneel sit lie despair hug face(dir=+-1)`.
Emotions: `neutral happy sad angry worried surprised ashamed`.

**Shot kinds** (`f.shot`): `wide medium close two over detail track reveal`, plus `f.insert3d` (a 3D prop turning in light: models built by `tools/props3d.mjs`: ring, coin, cup, lantern).
Transitions (`transition=` on a shot): any MIT shader of gl-transitions, for example `fade`, `wipeLeft`, `Dreamy`, `directionalwipe`, `CrossZoom`, `swap`.
Looks (`look=` on a shot or a place): `{grade: day|warm|dusk|cool|grey|night, vignette, grain, light:[x,y,amount]}`.

`Film.default_cy` sets the camera height of wide and reveal shots: raise it when the actors stand low in the frame.
