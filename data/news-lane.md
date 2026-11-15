# News lane (the third video of the night)

Owner decision 2026-11-15: every night makes three videos, one per lane (channel.json `night.lanes`): **trending** keyword, **mystery**
(fair-play whodunit, data/mystery-craft.md) and **news**. This page is the rulebook of the news lane. News is the one lane that talks about
the real world, so it has its own guard-rails; the other lanes stay fiction.

## What the lane is
"The story behind the headline": a 2-3 minute explainer of ONE current story, told with the channel's stick figures and drawings
(never a real person's face or likeness). It explains what happened, the mechanism behind it, and what is still unknown.

## Which stories are allowed
Allowed: science and discoveries, technology and products as a development, economy and consumer data explained, health research as
a finding (never advice), space, nature, culture and sport results, everyday-life trends.
Never: crime and crime victims, deaths, accidents and disasters, war and terrorism, elections and partisan politics, ongoing legal
cases, named private people, minors, anything that needs a medical, legal or investment recommendation, rumours.
If tonight has no safe story, say so in the report and make a second trending video instead. A skipped news video is better than a risky one.

## How the job researches (WebSearch)
1. Search today's top stories in the allowed areas; list 5 candidates with their dates.
2. Pick the one a viewer would search about tomorrow (a keyword people type, also in the digest) and that is **reported by at least two
   independent reputable outlets** (wire services, major newspapers, the scientific journal or the official statistics office itself).
3. Open the sources and write the facts down in the task's `sources:` list with the date each was read. Numbers exactly as published, with
   the unit and the date. No fact enters the script that the sources do not state.
4. Say what is not known yet ("early results", "not yet peer reviewed", "the figure may be revised").

## What the video must do
- On screen in the first 10 s: the date and the outlet/source ("Reported 15 Nov by ..."), as a `hud` chip.
- Real organisations, countries and products may be named only as the source states them, as facts, never as jokes, villains or advice.
  Real people are referred to by role ("the lead researcher", "the minister"), never shown, never quoted at length, never given invented lines.
- No opinion, no prediction, no advice. The narrator explains; the viewer decides.
- The description has a Sources block (links) and the date; the pinned comment repeats them; the labels (AI voice, drawings are illustrations) go last.
- A correction line in the description: "If a figure here is out of date, the sources above are the reference."

## Task fields
`lane: news`, `topic: news`, `sources:` (2+ URLs with dates), `news_date:` (the story's date). `scripts/policy_check.py` fails a news task
or story without them; for a news story it does NOT block real organisation names (REAL_ENTITY), but it still blocks truth-claims about
fiction, advice and franchise names.

## Timing
News goes stale: the news video is researched, voiced, rendered and published FIRST (it is the shortest), then mystery, then trending.
