# Event relay: the picture changes its premise, not just its angle

Adapted 2026-11-14 from the "successive visual events" structure of kaomei/stickman-video-director (MIT licence). The
reference films hand the stage from one main visual to the next (an anvil, a flattened figure, a hand, a graph); the
words choose each visual, the viewer never watches the same picture re-framed. Our video 007 did the opposite: 14 shots
of the same woman, same room, same pose, varied only by zoom.

## The rule

Every scene is a sequence of **main visuals**. Between two consecutive main visuals something must change the stage's
premise: the place, the people, the object that leads, the scale, the silhouette or the meaning. Zooming, a new subtitle,
a different angle of the same still pose, or small objects appearing around an idle figure do not count.

What counts as a handoff:
- a new place (`at` another setting);
- a new lead object: an insert of the card, the statement, the phone, a counter, a map, a chart;
- a new person takes the frame, or two people instead of one;
- the character does something that changes the picture (walks away, hands the card over, tears the page);
- a graphic that turns the idea into an image (`hud` counter, graph, chain, a drawn metaphor).

Per scene: entrance -> decisive change -> a readable result -> handoff to the next visual. Hold a result long enough to
read it (about 1 s) and then move: fast does not mean constant motion. Offset related events: starts and tails should
not all share one pulse.

## Fit the picture to the words, not the words to a template

Start from the meaning of each clause and choose a specific visual verb: slide the card across, count the coins, the
balance ticks up, the page gets circled, the door shuts. Do not copy an earlier film's gags; invent the ones this script
needs. A figure need not be in every shot: a lead object can carry a line.

## Draw the needed states before you animate

For an object or pose the story needs (a card held out, a statement page, a monitor line), build the before, the
contact/peak and the changed result as actual states, then animate between them. If an articulated pose would break the
silhouette (an arm that cannot reach), use a complete pose variant, never a stretched arm. Parts may move separately
only while their connections and lengths stay coherent. Each added asset must do a job in the current meaning.

## The ending follows the current words

The last event is entrance -> change -> readable result -> finish. Never add a recap row, a side-by-side comparison or an
icon list only because seconds remain.

## How the lint checks it

`relay_lint.py` (inside `spec_lint.py`) warns, per scene:
- 4+ consecutive lines on the same place, the same people and the same shot kind with no new lead object, `hud`, action or
  prop (the picture is a re-framing, not a handoff);
- a scene whose lines all share one setting and one actor while the film has 3+ scenes in total (the same stage for the
  whole scene), unless its target is under 15 s;
- an opening 10 s with no visual premise change (hook).

Treat each warning as a script problem first: change what the lines show, then the shots.

## Review on the real film

After the render, watch the actual mp4 at normal speed with sound (frames at every scene change + 3 per scene): list
for each scene its main visuals in order and the handoff between them. A populated template or passing lint is not
proof that the film feels different; failed intervals go in the report with times.
