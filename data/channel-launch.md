# Channel launch kit (owner does the account steps; the job does the rest)

Written 2026-11-14. The channel does not exist yet (checked: `youtube.com/@HezbStories` is a 404, and searching "Hezb
Stories" finds only other people's channels). Account creation, branding upload and legal acceptances are the owner's:
the job never creates accounts. Everything below is ready to paste.

## 1. Create the channel

- **Name**: Hezb Stories. **Handle**: `@HezbStories` looked free on 2026-11-14 (404). A handle can still be reserved or taken
  by the time you try; fallbacks: `@HezbStoriesTV`, `@HezbShorts`, `@WhyWeDoItStories`.
- **Language / country**: English, United States (target market US/UK/AU, high CPM).
- **Category** (upload default): People & Blogs, id 27 in `channel.json`.
- **Turn on** in YouTube Studio -> Settings -> Upload defaults: "Altered or synthetic content: yes" on every upload (the
  voice is AI). It is a disclosure toggle, separate from monetisation.

## 2. Paste-ready channel text

**About** (the first 125 characters show in search, so the promise comes first):

> Short animated stories about the decisions we make and what they cost: money, the mind, and invented mysteries.
> One story, one idea you can use the same day. Calm narrator, dry wit, no lecturing.
>
> New stories every week. Every character and event is fictional. Voice and visuals are AI-generated.
> Stories show mechanisms; they are not financial, medical or legal advice.

**Channel keywords** (Studio -> Settings -> Channel -> Basic info): `animated story, story explained, psychology explained,
money psychology, why we procrastinate, sunk cost fallacy, lifestyle creep, debt trap, mystery story animated, how the scam worked`.

**Banner text** (one line, centred, 2560x1440 safe area 1546x423): `Short animated stories about decisions and their cost`.
**Avatar**: the stick-figure head on a flat colour, no text.
**Links**: none until there is a second platform.

## 3. What the market says (2026-11-14, from the nightly research digest and a web check)

- **Policy first.** YouTube's July 2026 guidance targets mass-produced, templated content with little creative input and AI
  personas posing as human experts on health, finance, legal or political topics. AI itself is allowed. Our rules already
  fit: every video is its own invented story; the narrator is not a persona and never gives advice; money stories say
  "a story, not advice". Keep it that way. A channel is judged as a whole, so never publish two near-identical videos.
  (Sources: [AIR Media-Tech](https://air.io/en/monetization/youtube-monetization-policy-changes-2026-a-complete-dated-timeline),
  [Tubefilter](https://www.tubefilter.com/2026/07/13/youtube-inauthentic-content-monetization-policy-update/),
  [vidIQ](https://vidiq.com/blog/post/youtube-ai-monetization/). Secondary coverage: check YouTube's own Partner Program pages
  before relying on it.)
- **Cadence.** Vendor blogs agree on: long videos are the base, about 2 per week; Shorts are the cheap way to test ideas
  and get discovered, 3-5 per week at a quality you can sustain. Consistency beats volume.
  ([Syllaby](https://syllaby.io/blog/posting-cadence-scheduling-faceless-channels/),
  [Subscribr](https://subscribr.ai/youtube-strategy/upload-frequency-faceless-ai-channel).) These are opinions of vendors,
  not YouTube rules.
- **Our topic.** The animated, invented-case story has no direct competitor in the top results (learnings 2026-11-11/12);
  titles and packaging decide it (growth-playbook.md).

## 4. Posting plan for the first month (owner posts by hand from the Release pack)

| week | long videos | Shorts / TikTok | note |
|---|---|---|---|
| 1 | 2: the two best finished films (one psychology, one money or mystery) | 3 teasers of 45-58 s from those films | the portrait cut is over 3 min, so it is NOT a Short: cut a teaser |
| 2-4 | 2 per week, different topics | 3-5 teasers per week | alternate topics; never two of the same topic in a row |

- **Order of the first uploads**: pick the finished films whose first line is the strongest hook (the job's report names
  them); post the best one first, because the first uploads set the channel's audience.
- **Do not upload the old test films** (001 test thumbnail, 002 zombie world): they predate the quality rules.
- **Before each upload**: Release pack -> youtube.md (title, description, tags, pinned comment); switch on
  "Altered or synthetic content"; set the thumbnail from the pack; schedule rather than publish at once.

## 5. After the first upload

Put the channel URL in `channel.json` `own_channel` (e.g. `https://www.youtube.com/@HezbStories`). The next night
`scripts/channel_stats.py` reads the public view counts into `data/performance.md` and the job learns which topic and
title pattern work (growth-playbook.md R5). Until then it runs without numbers.
