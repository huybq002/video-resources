# Platform policy the pipeline must obey

Refreshed by the night job before it writes any idea (step 1), and enforced by
`scripts/policy_check.py` before anything is rendered or published. Sources below are mostly
creator-education blogs and news rewrites, not the platforms' own pages: treat the wording as a
direction, re-check the official pages when something looks decisive, and prefer the safer reading.

Last refreshed: 2026-11-10

## The rule that shapes this channel

YouTube's harassment policy covers **realistic recreations of real victims of violent events**.
The January 2024 update was aimed exactly at AI true-crime content: videos that simulate deceased
or missing minors, or victims of deadly or well-documented violent events, describing their death.
A video that breaks it earns a strike, not just demonetization.

Separately, a recognizable real case with invented details is the **worst** legal position
available: it is identifiable enough to point at real people and false enough to be defamatory.
Pure fiction and accurate reporting are both safer than "mostly true".

**So crime stories in this channel are fiction.** Take the *pattern* from reality — the kind of
deception, the kind of motive, the way such a case unravels — and invent everything else: names,
places, dates, jobs, outcome. The video never claims to be a real case, and no title, description
or caption says "true story", "real case" or anything equivalent. `policy_check.py` fails the build
when it finds such a claim or a recognizable real entity.

## YouTube

- **Inauthentic content** (renamed from "repetitious content" on 15 July 2025): mass-produced and
  repetitive content is not monetizable. AI is not the trigger; low value and sameness are. One
  automated video a night is fine only while each one is a genuinely different story.
- **Inauthentic content, update of 16 July 2026** (TechCrunch 2026-07-20, Nieman Lab): three kinds of content
  cannot earn ad revenue, AI-made or not, and a channel with "too much" of any one loses monetization:
  1. *generic, repetitive or template-based* videos (interchangeable from one to the next);
  2. *distressing or emotionally manipulative* videos (built to provoke, shock or upset);
  3. *AI personas discussing sensitive topics* (health, finance, legal).
  For this channel: (1) every film needs its own opening, want, shape and format; `policy_check.py spec`
  now compares a new spec with the last 8 in `specs/` and fails a copy (same opening line, same
  `spine.want`, same title pattern, same format+scene shape twice in the last 5, a fourth same format in a
  row). (2) No rage-bait, no fake urgency, no shock thumbnails; sad endings are fine, cruelty for clicks is not.
  (3) The AI narrator is a storyteller, never a money/health/legal expert: money videos are stories about
  invented people, the narrator describes what happened to them and never addresses the viewer's own
  money ("you should", "your savings"). The existing ADVICE check is the floor.
- **Synthetic content disclosure**: required for *realistic* AI-generated or AI-altered media a
  viewer could mistake for real footage, set in YouTube Studio; automated detection has been
  applied since around May 2025, and YouTube can add the label itself. Stick-figure animation is
  not realistic, but the voice-over is synthetic, so **disclose anyway** — the label is reported
  not to affect distribution.
- **Advertiser-friendly is a separate bar** from Community Guidelines: content can stay up and
  still lose ads. Graphic violence, shocking detail and sensitive events are the usual causes.
- Severe harassment, child safety and some violent content can end a channel outright, not just a
  video.

## TikTok

- **AI-generated content must be labelled** when it shows realistic people or scenes, including
  synthetic voices. TikTok's Help Centre is reported to say the label does not reduce reach as long
  as the content follows the Community Guidelines. TikTok may also auto-label using Content
  Credentials. Unlabelled AI content can be removed.
- Community Guidelines apply the same whether or not AI was used.
- TikTok's own rules on crime, violent content and financial advice were not covered by the
  research above: check them before the first crime or money video goes out.

## What this means for each topic here

| Topic | Hard rules |
|---|---|
| Money stories | A story with a lesson, never advice. No "buy X", no returns promised, no real tickers or products. No real companies. |
| Behavioural psychology | Describe a mechanism and name the effect. No diagnosis, no treatment, no claim about a named person. |
| Crime / mystery | Fiction only. Invented names and places. No real case named or recognizable. No graphic injury detail. No claim of truth anywhere, including the thumbnail. |

## Every video, every platform

- Disclose that the voice and the images are AI-generated: the Studio setting on YouTube, the
  AI-generated label on TikTok, and one line in the description.
- No real people, real brands, real team kits, or real logos (the skill already forbids these).
- No shocking or graphic description, however "true" it would be.
- Each video is its own story. Repeating a template with new nouns is what "inauthentic" means.
