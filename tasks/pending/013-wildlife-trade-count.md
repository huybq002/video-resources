---
id: 013-wildlife-trade-count
type: video
priority: 013
status: pending
lane: news
topic: news
sources:
  - "https://sheffield.ac.uk/news/global-wildlife-trade-involves-more-double-number-species-previously-estimated (University of Sheffield release dated 29 Oct 2026, read 2026-11-15)"
  - "https://www.downtoearth.org.in/wildlife-biodiversity/global-wildlife-trade-involves-more-than-107000-species-twice-previous-estimates-study (Down To Earth, 3 Nov 2026, read 2026-11-15)"
  - "https://www.qmul.ac.uk/news/latest-news/2026/science-and-engineering/se/global-wildlife-trade-involves-more-than-100000-species-new-study-reveals.html (Queen Mary University of London release, found by search 2026-11-15)"
news_date: "2026-10-29"
keyword: "how many species are traded"
format: explainer
idea: "News explainer: a new study in Science Advances counts at least 107,356 wild species used or traded worldwide, more than double the ~50,000 of the earlier intergovernmental estimate; and why only a few percent of them are tracked (Title: The Count of Traded Wildlife Just Doubled / Thumb: 107,356 SPECIES)"
lang: en
only_aspect: ""
duration_min: 2.5
script_prompt: "News lane (data/news-lane.md): 2.5 min explainer, no real person shown or quoted, no advice, no opinion, no prediction. Say aloud what is not known. Species counts only (no money figures: the currency is not stated by the sources). Date chip + source chip in the first 10 s."
style: "B1"
series: ""
episode: ""
upload: false
privacy: private
---

# The Count of Traded Wildlife Just Doubled

## Goal
2.5-minute news explainer in B1, both cuts. Sources above; facts only as they state them.

## Done when
- [ ] story lints clean, policy_check spec OK
- [ ] voice, both cuts rendered and verified
- [ ] Release published, publish pack with Sources block

## Progress notes
- 2026-11-16 night: story 013 lint+policy OK, voice 161.5 s, shots-16x9/9x16 authored with outputs/013-wildlife-trade-count/author.py (+ outputs/_lib/alib.py), both validate OK. 60-s previews rendered (render ~1 min per 60 s) and looked at.
- BLOCKER: the runtime's `preview` is capped at 60 s and its full `render` command refuses without the runtime's approve artifacts (human-approved preview; `approve` is owner-only). assemble.py therefore cannot produce the 161 s film. Not bypassed. Owner: approve this project's preview with the runtime's own approve flow, then run `render`; or decide another route (see report).
