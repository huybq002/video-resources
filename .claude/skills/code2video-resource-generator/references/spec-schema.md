# spec.json schema

**Input keys**: `idea`, `lang` (default vi), `aspect` (`16:9` default | `9:16`), `duration_s`, `script_prompt` (user's own script/outline, text), `style_dna` (≤150 words from a reference), `series` (`{name, episode, open_loops:[...]}`; run `generate.py --series <series-bible.json>`; bible characters/settings are merged in and win over the episode spec). In `9:16`, `sequence` blocks are re-laid out automatically; hand-written shots use a 1080×1920 canvas (character `x` 0–1080, `by` ≈ 1560, `s` ≈ 1.0–1.3).

**Gender tag in script.srt (several speakers, any language)**: give each cast entry `"gender": "male"|"female"` (narrator: top-level `narrator_gender`). With more than one speaker every cue is written `[An][00:00:00,000 --> 00:00:03,500][nữ]: text`; the label is in the script language (vi nam/nữ, en male/female, es hombre/mujer, fr homme/femme, de männlich/weiblich, pt masculino/feminino, it maschio/femmina, id pria/wanita, ja 男性/女性, ko 남성/여성, zh 男/女, th ชาย/หญิง, ru муж/жен, hi पुरुष/महिला; override with `"gender_labels": ["male-label","female-label"]`). A single-speaker video has no tag. The tag drives the voice (`ci/tts.py` picks a male/female voice per language); the parser accepts files with or without it.

**Contract-level keys (new)**: top level `duration_s` (total seconds, exact), `narrator` (cast id used for lines without `who`, default `"narrator"`), `narrator_name`, `external_bg` (`true` or list of setting ids: use user/Gemini `assets/bg_<id>.png` instead of the 3D render), `setting_desc` (`{id: text}` used by the Gemini background prompts). Per scene: `title`, `goal`, **`target_s`** (seconds; all scenes must add up to `duration_s`). Per cast entry: `name` (shown in script.srt as `[Name]`), `role`, `look` (one detailed sentence describing the outfit for the Gemini prompt), `external` (use `assets/<id>.svg` from Gemini as one animated image), `narrator: true` (voice only, no body).

```jsonc
{
 "id": "slug", "title": "…", "lang": "vi", "duration_s": 69.2,       // target length: timeline is calibrated to it
 "idea": "one-paragraph summary (for humans)",
 "cast": [ { "id": "quan", "name": "…", "style": "stick", "top": "coat", "top_color": "#3e5c76", "bottom": "pants", "shoes": "boots", "hat": "fedora" /* full wardrobe list: wardrobe.md */, "shirt": "legacy colour", "pants": "legacy", "shoe": "#1d1620",
             "hair": "#2a1f24", "hair_style": "short|long|tuft|bun|bald", "hat": "none|fedora|cap|scarf", "hat_color": "#…",
             "glasses": false, "mustache": false, "coat": false, "bag": false, "watch": false, "torso_w": 1.0, "eye_gap": 40 } ],
 "settings": { "alley": "settings/alley.json", "park": { /* inline scene DSL */ } },   // see scene-dsl.md
 "scenes": [ { "id": 1, "shots": [ {
     "setting": "alley",                      // key of settings
     "cues": ["Narration sentence 1.", "…"],  // ≤14 words each; numbered 1..N across the WHOLE video in order
     "cam": "push" | [s0,x0,y0,s1,x1,y1],     // presets: push push_slow pull pan_left pan_right punch static_drift
     "cut": false,                            // true = hard cut instead of 0.4 s crossfade
     "rain": false, "flash": 4.57,            // optional FX; flash = seconds after shot start
     "shake": [2.9, 5.0],                     // camera shakes (impacts), seconds after shot start
     "props": [ { "id": "envelope|book|key|photo", "x": 700, "y": 800, "w": 190, "t": 4.7,
                  "mode": "drop|static", "lift": 4.2 } ],
     "chars": [ { "k": "quan", "x": 640, "by": 900, "s": 0.8, "flip": false, "enter": -420,
                  "acts": [ [0.4, "breathe"], [2.0, "think"], [5.0, "worry"] ] } ]
 } ] } ]
}
```

## Film coverage (many shots, close-ups, real lip-sync) — read this for any video longer than 1 minute
```jsonc
{ // cues may be strings or {"t": text, "who": "<cast id>"}: the character named in `who` talks, mouth follows the word timings (and the loudness of voiceover.wav when present)
  "cues": [ {"t": "Cậu đi đâu về?", "who": "lan"}, "Câu dẫn của người kể." ],
  // framing: zoom the camera onto a character's head (1.8 medium close-up, 2.6 close-up, 3.4 extreme close-up); dy shifts the target
  "focus": { "k": "lan", "zoom": 2.6, "to": 2.8, "dy": 0 },
  // several shots inside the SAME line: first shot consumes the cues and uses a slice of their duration, the next shares them
  "portion": [0, 0.6],            // first shot (default [0,1])
  "share": true, "portion": [0.6, 1]   // later shot: no "cues" key; reuses the previous shot's cues for the remaining time (reaction shot)
}
```
**Body views (front / side profile / back)**: every character is drawn three times with its own skeleton. `["t","view","side", dir]` turns the whole body to profile (dir 1 = faces screen-right, -1 = screen-left; mirrored automatically for `flip`ped characters), `["t","view","back"]` shows the back (hair, shirt, bag strap), `["t","view","front"]` returns. Acts listed AFTER a `view` act (sorted by time) drive the new drawing, so a profile walk uses side-view legs and arms. `walkTo` and `enter` automatically walk in profile and turn to the front on arrival. The side/back drawings are only embedded in shots that use them.

Acts for faces: `["t","turn", yaw, secs]` (0 front, ±0.5 three-quarter, ±1 full profile; + = looks to screen-right), `["t","emote","joy|sad|cry|fear|anger|doubt|smirk|surprise|sleepy|neutral"]`, `["t","lidsAct", 0-1]` (half-closed eyes), `["t","look",dx,dy]`, `["t","gesture", secs]`. Mouth shapes: closed, smile, open (wide jaw), e (spread), o (round), smirk, sad. Real speech lip-sync uses Vietnamese vowel/consonant rules per word (`scripts/lipsync.py`).

**Sequences** generate the coverage for you (master → medium → close-up → reaction → two-shot …) so a 10-minute film does not need 150 hand-written shots. Put them inside `scenes[].shots`:
```jsonc
{ "sequence": { "type": "dialogue", "setting": "lib:cafe", "mood": "warm|tense|sad|funny", "seed": 1,
    "a": {"k":"lan","x":620}, "b": {"k":"minh","x":1300},
    "lines": [ {"who":"minh","t":"…"}, {"who":"lan","t":"…"} ] } }
{ "sequence": { "type": "narration", "settings": ["lib:street_day","lib:cafe"], "mood": "warm", "seed": 2,
    "actors": [ {"k":"lan","x":760} ], "cues": ["…", "…"] } }
```
`lib:<name>` = ready-made settings in `assets/settings-library` (street_day, park_dusk, bedroom_night, office, cafe, rooftop_night); you can mix them with your own `settings`. A sequence expands to ~1.2 shots per line (dialogue) / 1–2 per cue (narration). Hand-written shots and sequences can be mixed freely.

## Motion features (from the reference-video analysis, see motion-language.md)
```jsonc
{ // inside a shot:
  "trans": "fade|cut|whip|flash|zoom|dip",   // how this shot ENTERS (default fade; cut:true = cut)
  "rays": true,                               // god-ray overlay (golden light)
  "flat": false,                              // true = ignore depth layers, use the single bg image
  "crowd": { "n": 40, "x": [120, 1800], "by": [600, 720], "s": [0.12, 0.22], "seed": 3, "colors": ["#c0577a", "#e0b83a"] },
  // crowd/props/overlays also work on a `sequence` block: they are copied onto every shot that sequence makes,
  // which is how you show a group (a horde, a queue, a market) behind a narration or a dialogue.
  // `x` and `by` are fractions of the frame (0-1, the portable form: defaults x [0.10,0.90], by [0.59,0.83])
  // or pixels of the real frame (1920x1080, or 1080x1920 in 9:16). `s` is auto-scaled 1.25x in 9:16, like characters.
  "overlays": [
    { "type": "chip",    "text": "Tokyo · 2:14 AM", "t": 0.3, "dur": 3, "pos": "tl" },        // pos = row t|c|b + col l|c|r
    { "type": "counter", "from": 0, "to": 4100000000, "label": "people", "t": 1, "dur": 3.5, "pos": "tr" },
    { "type": "burst",   "text": "CRACK!", "x": 1130, "y": 360, "t": 1.3, "dur": 1.6 },       // x,y = centre in px
    { "type": "bubble",  "text": "Typed letter by letter", "x": 960, "y": 300, "t": 2, "dur": 3 },
    { "type": "title",   "text": "Công lý?", "t": 6, "dur": 3, "pos": "cc" } ] }
// cast entry: "glow": true  (warm rim light on that character).  settings: "layers": [11, 22] (see scene-dsl.md)
```
- **Split screen** (two places/people compared side by side): replace the shot's `setting` + `chars` by
  `"split": [ {"setting":"tea","tint":"#3aa6a0","chars":[…]}, {"setting":"desk","tint":"#e0577a","chars":[…]} ]`.
  Each pane is 960×1080 showing the centre of its setting; character `x` is local to the pane (0–960, centre 480); `tint` is a soft-light colour grade per side. Cues, overlays, trans, shake, props, crowd stay at shot level. Depth layers are not used inside panes. Example: `examples/split-demo/spec.json`.
- **Frame rate / smoothness**: top-level `"fps": 60` (default 60; use 30 for quick drafts — render time is proportional to frames: ≈ 1.5 min per 6 s of video at 60 fps on this machine) and `"motion_blur": true` (+ optional `"motion_blur_shutter": 180`) which turns on HyperFrames' shutter smear on fast movers. The skill writes `data-fps` on the root; the app's `npx hyperframes render` then renders at that rate (or pass `-f 60`). Animation is time-based, so changing fps never changes timing.
- **Film feel**: top-level `"letterbox": true` (2.39:1 bars); per shot `"sway": true` (handheld drift) and `"dof": true` (soft-focus background layers; needs `layers` settings). Acts with arguments: `["t","walkTo", dxPixels, seconds]` (character walks across the frame with a walk cycle), `["t","look", dx, dy]` (eyes + head turn toward -1…1), `["t","reach","r"|"l"]`, `["t","shrug"]`. Limbs are never clipped by the sprite box any more.
- Acts added with rig v2: `["t","talk", seconds]` (mouth flaps per syllable + head beats + alternating gestures), `walk [steps]` (in-place walk cycle), `walkTo`, `look`, `reach`, `shrug` (see animation-principles.md for recipes). Arms are two-segment (elbow follows), legs are three-segment (thigh/shin/foot).
- Extra acts: `happy` (^ ^ eyes + hops) `heart` (heart eyes) `glare` (angry eyes) `normal` (reset eyes/brows/mouth).
- Overlay times are seconds from the shot start; keep chips in the top third, away from captions; ≥ 1 overlay every ~10 s makes it feel produced.

- Canvas 1920x1080. `x` = character centre, `by` = feet y (850–930 keeps feet above the caption), `s` = scale (0.5 child/far … 0.9 close). `flip:true` mirrors to face left. `enter: -420` = walks in from 420 px left over 2.2 s.
- A shot lasts from its first cue's start to its last cue's end (read from timeline.json). Act times are seconds **relative to the shot start**; keep them inside the shot.
- Acts: `breathe` (auto) `blink` (auto) `nod` `shake` `think` `worry` `relief` `lean` `sad` `surprise` `wave` `stir [n]` `receive` `stamp` `offer` `point` `cheer` `laugh` `angry` `cry` `bend` `walk [steps]`. Expressions persist until changed (`worry` then `relief`).
- At most 2–3 characters per shot, ≥ 350 px apart; flip the one on the right so they face each other.
- Scene lengths come from the cues: balance cue counts so each scene is 25–35 s.
