# Character design: stick figure + story wardrobe

Default style (`"style": "stick"`): round head (white by default, any tone via `skin`), fully expressive face (eyes with highlights, brows, blush, 7 mouth shapes, tears, sweat), thin black arms and legs, clothes drawn as flat shapes. Three drawings per character (front, side profile, back) share one skeleton. The old shaded "bean" characters remain available with `"style": "bean"`.

**Rule: dress every character from the script, never from a template.** Before writing the cast, ask for each character: who are they, where do they live, what do they do this day, what is the weather/season, what should the viewer feel? Then pick the wardrobe below. Keep the outfit identical in every scene unless the story changes it (a time jump, a disguise).

## Fields (cast entry)
| Field | Values |
|---|---|
| `top` | `tshirt` `shirt` `hoodie` `jacket` `coat` `dress` `tank` |
| `top_color`, `top2` | main colour; `top2` = collar / inner shirt / lapel colour |
| `bottom` | `pants` `shorts` `skirt` `none` (dress / long coat) |
| `bottom_color`, `sock` | trouser/skirt colour; sock colour for bare lower legs |
| `shoes`, `shoe_color` | `sneakers` `boots` `heels` `none` |
| `hat`, `hat_color` | `none` `fedora` `cap` `beanie` `scarf` (headscarf) |
| `hair_style`, `hair` | `none` `short` `spiky` `tuft` `long` `bun` + colour |
| accessories | `tie` (colour) `scarf` (colour) `apron` (colour) `belt` (colour) `badge` `bag` `bag_color` `watch` `glasses` `mustache` `buttons` |
| `pattern` | `none` `stripes` `hoops` `checks` (uses `top2`) |
| body | `torso_w` 0.85–1.2 (stocky vs slim), `eye_gap`, `skin`, `blush:false` |

**Long garments (`coat`, `dress`) are drawn as the garment only**: no trousers or skirt under them, the bare thin black legs come out below the hem (knee-length trench coat: belt with buckle, popped collar, lapels, double row of buttons, pocket flaps; the hem is at the knee). Add `bottom` explicitly only if you really want trousers visible. Hands are always a single small black dot; do not ask for gloves or fingers.

**How the lower body is drawn.** The hip garment starts behind the torso and ends just below the hem; the thin black leg hangs from that hem, so there is never a gap between body and legs and never a pelvis block sticking out like a nappy. That gives the three shapes of the reference style:
- `bottom:"none"` → the garment hem (shirt, jacket, coat, dress) and thin black legs straight out of it, down to the shoes. This is the house look.
- `bottom:"shorts"` → a visible short with a crotch notch, then thin black legs, then `sock` if set, then shoes. This is the football-kit / school-boy shape.
`sock` draws a real sock from under the knee to the ankle (football socks, school socks); it shows wherever the leg is bare, so it needs `bottom` `none` or `shorts`.

**No long trousers for anyone (owner's rule).** Every character is a full stick figure: `"bottom": "none"` (thin black legs, the house look) is the default, `"shorts"` or a `"skirt"` at most. `"pants"` is not drawn any more — it is rendered as bare legs, and `generate.py` warns so the spec and the Gemini prompt stay honest. Put the character into the top, shoes and accessories instead: `top` + `top_color` + `top2`, `shoes` (or a `sock` colour), and two or three of `hat`, `bag`, `tie`, `scarf`, `belt`, `badge`, `glasses`, `watch`, `mustache`, `buttons`, `pattern`.

## Script role → outfit (examples; invent, don't copy)
- Detective / inspector: `coat` khaki or slate-blue (trench), `deerstalker` or `fedora`, `tie` dark red, `boots`, `mustache` optional, `buttons`.
- Office worker (man): `shirt` white/pale blue + `tie`, `bottom:"none"`, `belt`, `badge`, `watch`, dark `shoes`; woman: `shirt` + `skirt` or `dress`, `heels`/`sneakers`, `bun`.
- Student / school: `shirt` white + `tie` or `scarf`, `bag`, `sneakers` (boy: `shorts` navy or `bottom:"none"`; girl: `skirt`/`pants` navy); younger kid: scale `s` 0.55–0.6, `tshirt`, `shorts`, `cap`/`tuft`.
- Street / teen (boy): `hoodie` bold colour, `shorts` dark or `bottom:"none"` + dark `sock`, `beanie` or `cap`, `bag`, `sneakers`, `spiky` hair.
- Elder (man): `jacket` or `coat` muted, `bottom:"none"`, `glasses`, `scarf`, `belt`, grey hair (`hair:"#9a9aa2"`), `torso_w` 0.9; woman: add `skirt` or `dress`.
- Cook / shop owner: `shirt` + `apron`, `cap`/`bun`, `sneakers`.
- Homeless / traveller: `coat` worn grey-brown, `beanie`, `scarf`, `boots`, `bag` (man: leave `bottom:"none"` so the legs show under the hem).
- Doctor / lab: `coat` white + `top2` mint, `badge`, `glasses`, `sneakers`; nurse: `shirt` teal + `shorts`/`skirt` or `bottom:"none"`.
- Romance / date: `dress` or `shirt`+`jacket`, `scarf`, accent colour echoing the partner's (colour story).
- Villain / mystery: dark `coat`, `hat`, high contrast with the hero's colour; give the hero one signature colour that stays in every scene.

## Design tips
1. Each character gets a distinct **silhouette** (hat, hair, coat length, skirt) and a distinct **main colour**; at 1/4 size they must still be recognisable.
2. Use 2–3 colours per outfit (main + `top2` + bottom or `sock`), a warm accent only on the hero.
2b. **Crowd and background characters are cast entries too** (zombies, soldiers, neighbours, a queue of commuters): give them one shared silhouette and a single drab colour so the hero stands out, and vary `torso_w`, `hair_style`, `hat` and `s` between them. For a large group use a `crowd` block in the shot (spec-schema.md) instead of many cast entries, and keep 2–3 named ones in the foreground.
3. Match period/place through shape (coat, scarf, apron), not logos or real brand marks; no real team kits, names or numbers.
4. Close-ups show only the head + collar: put identity there (glasses, hat, hair, collar colour, tie).
5. The head is the star: keep `skin` white or one flat tone so the expressions (blush, tears, ^ ^ eyes) read at any distance.


## Smooth figures (2026-11-08, after the reference frame study)
We keep our own design (big white head, full face). What we took from the reference films is only what makes a figure read
as smooth and finished: thicker one-piece limbs with round ends and round hands (no joints), clothes edged in a darker shade
of their own colour instead of a black ink line, a thinner head outline with a softer blush and no nose line, and a crisp
warm rim light on one side. `"style": "ink"` on a cast entry is an optional all-dark silhouette variant with a warm-white face
(night or mystery stories); do not make it the channel's main look.
