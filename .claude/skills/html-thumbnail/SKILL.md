---
name: html-thumbnail
description: Use when the user or a task asks for a YouTube thumbnail or Shorts cover made from HTML/CSS and existing assets (characters, backgrounds, headshots), rendered to PNG with headless Chromium. Makes several variants per video and logs them for CTR comparison. Needs no image-generation API.
---

# HTML Thumbnail

Make thumbnails as HTML, render to PNG. Vietnamese text renders with correct diacritics.

## Steps

1. **Learn from past results.** Read `data/thumbnail-results.csv`. Rows with a `ctr_percent` show what worked. Reuse winning styles. Avoid repeating losers. If the file has no results yet, say so in the notes and explore different styles.
2. **Pick format.** Long-form 1280x720 (default) or Shorts 720x1280 (`--size 720x1280`, change html/body size in CSS to match). If the task does not say, use long-form and note the assumption.
3. **Gather assets.** Use files already in the repo (`outputs/`, scene assets, `.claude/skills/video-thumbnail/assets/headshots/`). Reference with relative paths. Never invent files that do not exist.
4. **Write 3 variants** in `outputs/<task id>/thumbnails/`, named `a.html`, `b.html`, `c.html`. Start from `templates/base.html`. Make them genuinely different (layout, color scheme, headline angle), not small tweaks. Each variant must have:
   - a headline of at most 4 words, readable when shrunk to phone size
   - strong contrast between text and background
   - one focal point (a face, character, or object), not several
   - safe margins: keep key content away from the bottom-right corner (YouTube puts the duration badge there)
5. **Render.**
   ```bash
   python .claude/skills/html-thumbnail/scripts/render_thumbnail.py outputs/<task id>/thumbnails
   ```
   Each `x.html` becomes `x.png`. If a render fails, fix the HTML and retry. Read each PNG to check text is not cut off and nothing overlaps.
6. **Log the variants.** Append one row per variant to `data/thumbnail-results.csv`: date, video, variant letter, a short style label (e.g. `yellow-on-navy-face-right`), headline, empty `ctr_percent`, notes.

## After posting (human step)

The owner uploads the variants (YouTube Studio "Test & Compare" if available), then fills in `ctr_percent` in the CSV. The next run reads it in step 1.

## Rules

- Do not claim a thumbnail "will perform well". Say which design principles it follows and that CTR must be measured.
- Do not copy another channel's thumbnail or use a real person's face other than the owner's provided headshots.
