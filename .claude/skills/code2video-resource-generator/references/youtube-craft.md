# YouTube craft (distilled; read only for scripts, hooks, series, Shorts)

Sources, used selectively and NOT loaded at run time: AgriciDaniel/claude-youtube (retention-scripting, shorts-playbook, hook, script) and yashaiguy-dev/faceless-youtube-agents (viral-dna-extractor). Do not install or read those repos while generating; this page is the distilled part. Read the repos only if the user asks for something beyond this page (SEO audit, analytics, upload).

## Hook (first 30 s of a long video; first 1-3 s of a Short)
| Time | Job |
|---|---|
| 0-5 s | Attention grab: strongest image or line, bold claim, unexpected moment. Never "xin chào các bạn / welcome back". |
| 5-15 s | The promise: what the viewer gets or what question will be answered. |
| 15-30 s | Stakes: why it matters, what they lose by leaving; plant an open loop ("cuối video bạn sẽ hiểu vì sao..."). |
55 % of viewers leave in the first minute, 20 % in the first 10 s: the hook is the highest-leverage part. Deliver on the title/thumbnail promise immediately.

## Retention
- Open loops (the "suspension bridge"): open a question early, answer it late, open the next before closing the first. Highest completion gain.
- Pattern interrupt about every 30 s (long form) / every 2-3 s (Shorts): camera change, new place, sound/music shift, text pop-up, surprising fact, format change. In this skill: shot cut, `trans`, chip/counter overlay, burst, close-up.
- Energy: strong open, calm-burst rhythm (15-25 s calm, burst every 2-3 min), anchor back to the core question every 2-3 min, strategic pauses before the key reveal, strong payoff at the end. Do not pad: length follows the story.
- Sentence rhythm for narration: short-short-long-short; one idea per line; vary pace before reveals.

## CTA
Dual CTA: first at ~1 min (after first value), second ~4 min or just before the payoff; never only at the end (only 16 % reach the last 10 %). Embedded (spoken + on-screen chip) beats spoken only. Give a specific comment question tied to the story.

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
