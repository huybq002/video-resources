# Growth playbook (ideas, scripts, titles, descriptions)

Read by the night job at research (step 2c), when writing the spec (step 4) and when writing the
publishing pack (step 7b). Written 2026-11-13 after the first four videos got almost no views.
It lives outside the generator skill on purpose: changing it never forces a new demo approval.

## What went wrong in videos 003-005 (evidence)

| fault | evidence | rule below |
|---|---|---|
| Ideas were picked from keywords nobody new can rank for | `data/research/latest.md` 2026-11-11: the top "opportunity" rows were `music`, `season`, `cannot`, `lyrics`, `official` (single words discovered from music-video titles); real rows were held by 10-60 min videos of million-subscriber channels (Bailey Sarian, Morgan Housel interviews) | R1, R2 |
| The score rewarded all-time hits, not what a small channel can win this month | `opportunity()` used the median views of the top 20 results by relevance, which are mostly years old | R2 |
| Titles described the plot instead of making a stranger curious, and spent characters on a genre label | "The Till Was Over by the Same Sum Every Friday (Mystery Story)" (63 chars, label in brackets), "Why You Clean Everything Except The Work (Procrastination)" | T1-T4 |
| The first line of every description said "invented" / "fiction", which is what feeds and search snippets show | 003: "An invented story about a woman..."; 005: "An invented mystery about..." in the first 125 characters | D1, D2 |
| Descriptions were ~400 characters with one weak keyword mention: too little text for search to know what the video is about | 003/004/005 youtube.md | D3 |
| The vertical cut was the full 4-5 min film, so it never ran as a Short (limit 3 min) and got no Shorts-feed reach | 004/005 progress notes: "portrait is 4 min, not a Short" | S1 |
| No numbers came back from the channel, so no night could learn which video worked | no performance file existed | P1 |

## Research and ideas

- **R1. Keywords are phrases people type.** A keyword is 2-6 words a viewer would type into YouTube search
  ("sunk cost fallacy example", "why do i procrastinate"), taken from YouTube autocomplete (the digest's
  "What people type" section). Never a single word, never a word lifted from someone's title.
- **R2. Choose where a small channel can win now**, in this order of evidence from the digest:
  1. `breakouts`: a video from the last months by a channel under 100 K subscribers with more views than
     subscribers. That is proof the topic travels without a big audience. Strongest signal.
  2. `recent median`: median views of this year's uploads for the keyword (not the all-time top 20).
  3. `spread`: many different channels in the results.
  A keyword whose results are all > 2 years old, or all from channels > 1 M subscribers, is a poor bet
  however big its views look.
- **R3. Title first.** Every idea in data/ideas.md carries a working title (T rules) and a 3-word
  thumbnail text in the `idea` cell: "Title: ... / Thumb: ...". If no title that a stranger would click
  can be written, the idea is dropped (reason: "no clickable title"). The story serves the title, not the
  other way round.
- **R4. One searchable mechanism per video.** Viewers search for the effect ("sunk cost fallacy",
  "lifestyle creep", "how a ponzi scheme works"); the story is how we show it. Each idea names that
  effect and its search phrase.
- **R5. Learn from our own numbers first** (data/performance.md, P1): a topic or title pattern whose
  videos beat the channel median gets the next idea; one that sits at the bottom twice is paused.

## Script (the first 60 seconds decide everything)

- **H1. Line 1 = the title's promise, in a picture, in 5 seconds.** The opening line states the stakes
  or the strange fact the title promised ("Every Friday the till was forty-seven dollars over" is good;
  "Nora heard the news on a Monday morning" as line 2 is filler).
- **H2. Open a loop by 15 s and say when it closes**: a question the viewer wants answered and a hint
  of when ("by Friday she would know who"). Close it in the last scene, not before.
- **H3. Name the mechanism by 60 s** for psychology and money videos (the search phrase from R4,
  spoken and on a `hud` chip): the searcher must hear that they are in the right video.
- **H4. Re-hook every 45-60 s**: a new number, a new person, a reversal, or a question. Three narration
  montages in a row with no new fact is a drop-off point (learnings 2026-11-12).
- **H5. No meta talk in the story**: no "this is an invented story", "fiction" or disclaimers in the
  narration. The fiction label lives in the description's last block and the AI label at upload.
- **H6. End with a payoff, then one question** the viewer can answer in a comment from their own life.

## Titles (YouTube, landscape)

- **T1. 40-60 characters.** Feeds cut long titles; > 60 is a PROBLEM in `make_publish_pack.py`.
- **T2. No genre label in brackets** ("(Mystery Story)", "(Procrastination)"): it uses space and
  promises nothing. A label is a PROBLEM.
- **T3. Curiosity gap or concrete outcome, with the search phrase early** when there is one:
  "Why Smart People Keep Paying for Things They Hate (Sunk Cost)" is still a label; better
  "He Spent $9,000 Fixing a Car He Hated" + the phrase in the description and tags.
  Patterns that work for story-explainers: "Why X Happens to Y", "The X That Y", "He Did X. Then Y.",
  a number + a strange fact. Never a lie about the video, never "true story" (policy).
- **T4. Write 3 titles, pick one**: put all three in `publish.json` `title_options`; the owner can A/B
  them in YouTube Studio ("Test & compare").

## Descriptions

- **D1. The first 125 characters are the hook plus the search phrase**: they show in search and in
  the feed. No "invented", "fiction", "AI" there (PROBLEM if found).
- **D2. Required labels go last**, in one block after the chapters: the AI disclosure from
  channel.json (it says "fictional") and the music credit. They stay mandatory.
- **D3. 600-1500 characters**: hook (2 lines), what the viewer will understand by the end (2-3 lines
  with the search phrase and one or two related phrases from the digest said naturally), chapters,
  the comment question, labels, 3 hashtags.
- **D4. Tags**: the search phrase, 3-5 autocomplete phrases from the digest, then broad ones.

## Shorts

- **S1. The vertical cut over 3 minutes is not a Short.** For a long film, the publishing pack's
  posting notes say so and propose a 45-58 s teaser: the hook scene (line 1 to the open loop) as a
  separate Short that ends on the loop and says "full story on the channel". When the night has time
  left, build it as its own spec (`only_aspect: portrait`, duration_s <= 58) from the same cast.

## Performance loop

- **P1. data/performance.md** is written by `python scripts/channel_stats.py` from the channel's
  public video list (channel.json `own_channel`): views per video and per day since upload, against the
  channel median. The owner may add CTR / average-view-duration from YouTube Studio in the same table.
  The improvement phase reads it before changing any rule above; every change cites it.
