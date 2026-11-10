# YouTube craft (distilled; read only for scripts, hooks, series, Shorts)

Sources, used selectively and NOT loaded at run time: AgriciDaniel/claude-youtube (retention-scripting, shorts-playbook, hook, script) and yashaiguy-dev/faceless-youtube-agents (viral-dna-extractor). Do not install or read those repos while generating; this page is the distilled part. Read the repos only if the user asks for something beyond this page (SEO audit, analytics, upload).

## Hook (first 30 s of a long video; first 1-3 s of a Short)
| Time | Job |
|---|---|
| 0-5 s | Attention grab: strongest image or line, bold claim, unexpected moment. Never "xin chào các bạn / welcome back". |
| 5-15 s | The promise: what the viewer gets or what question will be answered. |
| 15-30 s | Stakes: why it matters, what they lose by leaving; plant an open loop ("cuối video bạn sẽ hiểu vì sao..."). |
55 % of viewers leave in the first minute, 20 % in the first 10 s: the hook is the highest-leverage part. Deliver on the title/thumbnail promise immediately.

**Write the hook as a scene plan, not as a wish.** `generate.py` checks these and warns:
- Scene 1 is 15-30 s and nothing else. Scene 2 carries the stakes and the open loop.
- The first line is ≤ 14 words (≤ 10 in 9:16) and is the single strongest line in the film. No greeting, no "in this video", no title card, no logo: the first frame is already the story.
- Something is left open inside the first 30 s: a question mark, or a promise ("by the end you will know why she never opened the door").
- At least 4 shots in the first 30 s (8+ in 9:16) and at least two different places: a static opening reads as a slideshow and loses the 10-second cliff.
- The last scene ends on a question the viewer can answer in the comments.

**Cold open shape that works for a story film**
| s | Beat | Example |
|---|---|---|
| 0-5 | The image or line that is hardest to look away from. Often the middle of the story, out of order. | "Six in the morning. Nobody in the city is awake." |
| 5-15 | What this is and what the viewer gets: the promise, concrete. | "By tonight she will knock on the only door still lit." |
| 15-30 | Stakes + the loop that stays open to the end. | "She has one rule, and breaking it is how the story ends." |

## Retention
- Open loops (the "suspension bridge"): open a question early, answer it late, open the next before closing the first. Highest completion gain.
- Pattern interrupt about every 30 s (long form) / every 2-3 s (Shorts): camera change, new place, sound/music shift, text pop-up, surprising fact, format change. In this skill: shot cut, `trans`, chip/counter overlay, burst, close-up.
- Energy: strong open, calm-burst rhythm (15-25 s calm, burst every 2-3 min), anchor back to the core question every 2-3 min, strategic pauses before the key reveal, strong payoff at the end. Do not pad: length follows the story.
- Sentence rhythm for narration: short-short-long-short; one idea per line; vary pace before reveals.

## Payoff ladder (research 2026-11-10)
Creator retention guides agree on one more rule beyond the hook: **pay something off early, and let each payoff open a
deeper question.**
- The first 10 s prove the title/thumbnail is true with one concrete picture (the con already working, the four boxes on
  the doorstep). Promise, then proof, then the one-line map of the film.
- First real payoff (a reveal, a number, a small answer) before 60 s. Viewers who get nothing for 30-60 s are the ones who leave.
- Re-hook around 30 s with a smaller loop or a number that previews the next section.
- Every payoff hands over the next, deeper question ("so how did nobody check the bridge?" → "who checked, and why did
  they stay quiet?"). The big question stays open to the turn.
- Long-form pattern interrupt every 60-90 s at story level (new place, new person, time jump, a counter on screen) on
  top of the shot cuts every ~3 s.

## Market notes (research 2026-11-10, `scripts/research_youtube.py`, YouTube search, all-time ranking)
- Demand in this niche is **long-form**: medians 8-40 min, Shorts share ~0 % for every seed keyword. Shorts are for
  discovery (a 45-60 s teaser), search and suggested traffic come from 8-15 min films.
- Strongest bets (high median views spread over many channels): money psychology (1.5 M), behavioural psychology (2.9 M),
  unsolved mystery story (2.2 M), con artist story (1.7 M), why we procrastinate (1.2 M), how the scam worked (0.7 M).
- What wins: **a story that explains a mechanism** (how a scam worked, why the same income ends rich or broke, the
  procrastinator's monkey). Animated detective/mystery stories for older kids and teens (English Fairy Tales,
  Story Time Animated) reach 2-6 M; story-documentaries (fern) 6-13 M.
- Under-served: sunk cost (explainer 15.8 M, long versions ~44 K median), buy-now-pay-later trap (story version missing),
  lifestyle inflation. Ideas are in `data/ideas.md`.
- Title words the audience searches: psychology, why, broke, scam, actually worked, explained, mystery, same income.
  Use them in the title, never in the story.
- Policy shapes the format (data/platform-policy.md): since 16 July 2026, template-based, manipulative, and
  "AI persona on finance/health/legal" videos are not monetizable. Each film is its own story, the narrator tells what
  happened to invented people and never advises the viewer.

## CTA
Dual CTA: first at ~1 min (after first value), second ~4 min or just before the payoff; never only at the end (only 16 % reach the last 10 %). Embedded (spoken + on-screen chip) beats spoken only. Give a specific comment question tied to the story.

## Two cuts from one spec (16:9 + 9:16)
`scripts/build_both.py <spec> <out>` builds `landscape/` and `portrait/` from the same story. They are **not the same pixels cropped**: each is generated for its frame, so the three.js backgrounds are re-rendered at 1920x1080 / 1080x1920 with the camera pulled back in portrait, characters are rescaled and re-placed, the focus zooms are eased, and the captions move up out of the Shorts UI. `script.srt` is identical in both, so make `voiceover.wav` once and copy it (with `timeline.json`) into the second project.

What differs editorially, and what to write for it:
- **Subject size.** Portrait has half the width: 1-2 characters per shot, never 3; put the important thing in the middle third, vertically between 25 % and 75 %.
- **Safe zones.** In 9:16 the top ~10 % and bottom ~20 % are covered by the app UI. Captions are already moved up; keep faces and any `overlays` out of those bands.
- **Pace.** The vertical cut wants a picture change every 2-3 s, the horizontal one every 5-8 s.
- **Length.** Over 3 minutes a vertical video is no longer a Short, it is a vertical long-form video and gets far weaker distribution. For a film over 3 min, the honest options are: publish the vertical cut as a normal video, or write a separate 45-60 s vertical teaser spec that ends on the question (best reach). Say which one you chose in the hand-off.

## Shorts / 9:16 (spec `aspect: "9:16"`)
- Length 15-60 s (sweet spot), up to 3 min allowed; 1-2 scenes of 20-30 s.
- Hook in 1-3 s; visual change every ~3 s; captions essential (already on); loopable ending (last line echoes the first) is favoured; completion rate is the main signal (70 %+ is strong).
- Title 4-6 words (≤ 40 chars), 3-5 hashtags; first 125 chars of description show in feeds.

## Series (spec `series`, `--series series-bible.json`)
Keep characters, wardrobe, voice names and places identical across episodes; end each episode with an open loop recorded in `series.open_loops`; open the next episode by paying off the previous loop within 15 s, then start a new one. The bible stores the cast, custom settings, Gemini art and an episode ledger (`series_context.previous` shows the last 3 episodes when writing the next).

## Viral DNA (only when the user gives a reference channel/video/transcripts → spec `style_dna`)
From the transcripts extract five things and write them to `style_dna` (≤ 150 words total): (1) hook pattern + 3 exact opening-line templates, (2) retention phrases and interrupt frequency, (3) sentence rhythm, (4) section structure and where the payoff lands, (5) CTA pattern. Then write the script in that structure with new content; never copy their wording.

## Metadata (when asked)
Title: curiosity or concrete promise, ≤ 60 chars, keyword early. Thumbnail concept: one expressive face + 3-4 words max. Description: 2-line hook, summary, timestamps from `script.srt`, 3 hashtags.
