# Making SVG puppets move like an animated film

## Character design (rig v3)
Tapered limbs (shoulder 30 → wrist 20 px), round joint caps on the parent segment so elbows/knees/shoulders/hips never show a seam while rotating, skin-coloured hands with a thumb, shaped shoes with a white sole line, pelvis/belt that hides the leg tops, torso with collar and fold lines, gradient shading on skin/shirt/pants (light from top-left), ears, blush, nose, eyes with two highlights, upper-lid line, tapered brows, mouth shapes closed/smile/open (with tongue)/sad. Outlines are drawn as a thick ink pass under a colour pass, so line weight stays even at any pose. Recolour via cast fields (`skin shirt pants shoe hair hat glasses mustache coat bag watch torso_w eye_gap blush glow`).

## Three drawings per character (front, side, back)
Front (full face + 3/4 head turn via `turn`), side profile (profile head with nose, one eye, two-segment arms and legs, shoes pointing forward) and back (hair/hat covers the head). Switch with `view`; walk across the frame in profile; show the back when a character leaves, watches something, or the camera follows them; use profile two-shots (A facing right, B facing left) for tense confrontations or farewells. Mouth, blink and eyes work in front and side drawings.

## What the rig can do (rig v2 hierarchy, unchanged in v3)
Hierarchy: `root > life > [leg > shin > foot] ×2, body > torso, [arm > forearm(+hand)] ×2, neck, headsway > head > face`.
- `root`: jumps, squash & stretch. `life`: idle weight shift/breathing (never used by acts, so idle never fights a gesture). `headsway`: idle head drift + talk beats. `head`: acting (nod, shake, tilt). `body`: lean/sway. `torso`: breathing scale. Arms and legs are two-segment, so elbows and knees bend; hands have a thumb.
- Eyes: normal (blink every 2–5 s with a tiny head dip), happy ^ ^, heart, angry; brows rotate; mouth closed/open/sad; pupils can `look`.

## The twelve principles → how the engine does them
| Principle | In this skill |
|---|---|
| Squash & stretch | `jump()` squashes 8 % before take-off, stretches in the air, squashes on landing and settles with `back.out` (acts `surprise`, `cheer`) |
| Anticipation | arm raised before `stamp`; crouch before every jump; `bend`/`lean` before reaching |
| Staging | one clear action per shot, ≤ 3 characters, camera moves toward the point of interest |
| Straight-ahead / pose-to-pose | acts are keyed poses with eased in-betweens; use 2–3 acts per 6–10 s shot, not one per second |
| Follow-through & overlap | every `arm()` sends the elbow 0.07 s later and 25 % longer; head lags body; blink dips the head |
| Slow in / slow out | `power3.out` for gestures, `sine.inOut` for sways, `back.out` for pops, never `none` on a character |
| Arcs | shoulder→elbow→hand swing gives curved paths; walk bob is two dips per cycle |
| Secondary action | breathing, weight shift, head drift, eye blinks, talk head-beats while the hands gesture |
| Timing | gesture 0.3–0.5 s, beat holds 0.4–1.0 s, walk step 0.46 s, blink 0.14 s |
| Exaggeration | surprise jump 46 px, cheer 56 px, brow ±14°, shrug lifts the whole body 8 px |
| Solid drawing | limbs never clip (overflow visible), joints overlap with round caps, feet stay on the ground shadow |
| Appeal | big readable head, simple eyes, consistent palette and proportions per character |

## Acting recipes (copy these into `acts`)
- Greeting: `walkTo` toward the other (or `enter`), at arrival `wave`, other replies `nod`.
- Dialogue exchange (6–10 s): A `talk` (3 s) while B `look` at A, then B `nod` and `talk`; use `shrug`, `point`, `think` between lines.
- Reaction: `surprise` (jump + open mouth) → hold 0.6 s → `worry` or `relief`; never react and cut in the same frame.
- Decision/thinking: `think` → `look` away → `normal`.
- Emotional beat: `sad`/`cry` or `happy`/`heart`, camera `push_slow`, remove overlays, let the held pose breathe.
- Handing over an object: `reach` (giver) while the receiver `receive`; drop a prop with `mode:"drop"`.

## Film grammar (what turns animated slides into a film)
1. **Master shot → coverage.** Open each sequence wide (establish place and positions), then medium on the speaker, close-up on the reaction, then back to wide. 2–3 shots per sequence, not 8.
2. **Long takes with a story inside.** Let a shot run 6–12 s with 2–3 acts and a camera move instead of cutting every 2 s. Fast cutting is for montage, jokes and reveals.
3. **180° rule / eyeline.** Characters facing each other keep their sides across cuts (left stays left); use `flip` so they look toward each other; `look` before they speak.
4. **Motivated camera.** Push-in when something becomes important, pull-out for isolation, pan/track to follow a walk, whip pan only as a time/place jump, shake only on impacts, `sway` for handheld tension.
5. **Depth.** Exteriors use depth `layers` (+ `dof` on close-ups) so every camera move shows parallax; interiors use 2–3 foreground props.
6. **Continuity.** Same cast colours and positions; time of day follows story (dusk → night); recurring motifs (clock, envelope) return in later shots.
7. **Rhythm.** Alternate calm (long take, music-like pause) and busy (cuts, overlays). Put the biggest visual beat on the key word of a cue; start the action 0.1–0.3 s before the word.
8. **Cinematic frame.** `letterbox:true` for dramatic/story films; leave it off for explainers with many overlays.
9. **Silence is acting.** After a revelation hold the close-up 1–2 s with only breathing and a blink.
10. **Light tells the mood.** One warm practical light (lamp/window) against cool ambient; backlit rim (`glow`) on the hero for emphasis.

## Checklist before delivering
- No character sits motionless > 3 s (idle runs automatically) and no gesture repeats identically twice in a row.
- Every sequence has at least one wide, one medium/close, and one reaction.
- Feet end on the same ground line within a shot; characters do not cross captions.
- Check 10 fps contact sheets of the busiest 3 s (walk, wave, talk) for gaps at shoulders/elbows/knees.
