# Short-film craft: story, scene and shot

Sources: Pixar's story spine (Kenn Adams, via Emma Coats's 22 rules), short-film screenwriting handouts (AFTRS, LTX: one protagonist, few locations, one turning point, show don't tell, a page per minute), and the continuity-editing system (establishing shot, shot/reverse shot, 180-degree rule, 30-degree rule, eyeline match, match on action). `craft_lint.py` checks what can be checked in the spec.

A short film is not a long film made short. It is **one person, one want, one turn, one choice**, told with pictures first.

## The spine (write it BEFORE any line; put it in `spec.spine`)
Pixar's spine: *Once upon a time... Every day... One day... Because of that... Because of that... Until finally...*

| key | meaning | test |
|---|---|---|
| `want` | what the hero is trying to get, filmable | "get the 6:15 train", never "be happy" |
| `obstacle` | what stops them (a person, a rule, their own habit) | something that can be shown on screen |
| `turn` | the one moment that changes what they believe | the middle of the film, not the end |
| `choice` | what they do about it, and what it costs | a choice between two things they want |
| `opening_image` | the first picture | a place + an object + a state |
| `ending_image` | the same picture, changed | same place/object, new meaning |
| `motif` | one object planted in scene 1, changed in the middle, returned in the last scene | the phone, the key, the chair |

Rules: one protagonist; at most 3 places that matter (more only if each is a different emotional step); the theme is never said aloud.

## The scene (`goal`, `turn`, `value` on every scene)
A scene is a small story: the hero **wants** something in this place, **meets resistance**, and the situation **ends different**.
- `goal`: what they want here. `turn`: one sentence of what is different at the end. No turn = cut or merge the scene.
- `value`: `"+"` the hero ends better off, `"-"` worse, `"0"` unchanged. **Alternate them**; never four the same in a row; the lowest `"-"` sits at 70-85 % of the film, before the choice.
- Enter late, leave early: start the scene at the moment something is about to happen, cut out the walking-in and the goodbyes.
- Every scene needs one thing the viewer can **see** change (an object moved, a light off, a seat empty), not just a line that says so.

## Show, don't tell
- A character's feeling is an action on a prop: *she turns the phone face down*, *he straightens the tie twice*.
- The narrator gives what the camera cannot (time, numbers, a thought). The camera gives the rest. If the narration names what is on screen, cut the narration.
- **Subtext**: the line is about the small thing, the scene is about the big one ("Did you eat?" = *I'm worried about you*).
- Plant early, pay off late. The ending is the opening image changed.

## Shot grammar (what the generator does, and what you must not undo)
1. **Establish, then come in.** Every new place opens on a wide or establishing shot, people small, then medium, then close-up. `craft_lint` warns when a scene changes place without one.
2. **Shot size follows emotion.** Wide = context, medium = action, close-up = the thought, insert = the object that matters. Go tighter as the pressure rises; release on a wide.
3. **30-degree rule / no jump cuts.** Two cuts in a row on the same person must differ clearly in size or angle. `coverage._cinematic_pass` pushes the second one to a different zoom automatically.
4. **180-degree line.** Two people talking keep their sides (A left, B right) for the whole conversation; the camera stays on one side. Do not swap `a`/`b` x-positions between dialogue blocks in a scene.
5. **Eyeline match.** Before a cut to an object (insert) the person looks at it; the generator adds that look to the shot before an insert. Looking left cuts to something screen-left of them.
6. **Over the shoulder** for two-person talk, close-up for the one who matters most in the line, reaction shot (the listener) on the line's last words.
7. **Motivated movement.** The camera pushes in when attention narrows, pulls out when someone is alone, pans to follow a look or a walk. Never move for decoration. The last shot of a scene holds with a slow push.
8. **Cut on the action**, not after it: the hand starts to reach, cut; the hand arrives in the insert.
9. **Hold a beat.** After the turn, give the picture a moment without a new idea (a held close-up, a wide of the empty room).
10. **Light tells the time and the mood.** Night scenes cool, memories warm and hazy (`look: flashback`), a confession in one cone of light (`spot`). Change the light between scenes so the film has a colour arc, not one palette.

## Set and cast, so it looks like a place and not a stage
- Every place has **one thing that only belongs to this story** (the sticky note that says *ask for a raise*, the second toothbrush) beside the stock furniture.
- Hero in one signature colour no extra wears; supporting cast each a distinct silhouette. People in a place *do* things (a barista wipes, a colleague types), see `extras.py`.
- Hero is the largest and nearest figure in the shot; the camera never loses their face in a scene's key beat.

## Workflow addition
1. Write the `spine` (7 keys) and `scenes[].goal / turn / value` first, in one pass, then lines.
2. Run `python scripts/spec_lint.py spec.json | grep "craft:\|voice:"`: a spec with `craft:` WARNINGs is not finished.
