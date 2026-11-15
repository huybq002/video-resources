# stories/<id>.json

```jsonc
{
  "id": "008-night-shift-balance",
  "title": "She Paid Every Month. The Balance Never Moved",   // working title (the publish pack writes the final one)
  "lang": "en",                         // en -> edge-tts voices; vi -> VieNeu
  "style": "B2",                        // B1 | B2 | B3 (stickman/lock.json enabled_styles)
  "idea": "...", "topic": "money", "keyword": "debt trap explained", "format": "character",
  "duration_min": 4,                    // a target; the real length is the voice's length
  "mood": "tense",                      // the film's overall mood (score); scenes can override
  "narrator": {"name": "Narrator", "gender": "female"},          // optional "voice": an edge-tts voice id
  "cast": [
    {"id": "nina", "name": "Nina", "gender": "female", "look": "night nurse, mint scrubs, hair in a bun, a lanyard badge"},
    {"id": "lena", "name": "Lena", "gender": "female", "look": "her friend, pink hoodie, always holding a coffee"}
  ],
  "scenes": [
    {
      "id": 1,
      "title": "Every month",           // chapter title in the description
      "place": "Nina's tiny kitchen at 6 a.m., the card statement on the table, a kettle on",   // where THIS beat happens
      "mood": "tense",                  // tense | mystery | sad | warm | hopeful | upbeat (score + room tone feel)
      "value": "-",                     // + or -: the scene ends better or worse for the hero (score darkens/brightens)
      "lines": [
        {"who": "narrator", "t": "Nina paid her card every month.", "emote": "doubt"},
        {"who": "narrator", "t": "And the balance never moved.", "emote": "worry"},
        {"who": "nina", "t": "Ninety again. Like it says.", "emote": "tired"}
      ]
    }
  ]
}
```

Rules (`scripts/lint_story.py` checks them):
- `who` is `narrator` or a cast `id`. Each speaker keeps one voice for the film.
- `place`: concrete, story-specific, at least 4 words, never a bare category word ("kitchen"). A new scene in the same
  place repeats the same place text.
- Lines: spoken English, at most 22 words. Captions are split automatically into one-line phrases.
- `emote` on most character lines: joy, happy, excited, surprise, shock, angry, frustrated, worry, fear, doubt, think,
  confused, sad, tired, relief, calm, proud, laugh. Questions rise and short lines land slower by themselves.
- Line 1 is the hook: at most 14 words, no greeting. The last scene ends with a question to the viewer.
- No "invented", "fiction" or "true story" in the lines. The fiction and AI labels live in the description and the
  upload setting.
- Length: about 2.6 words per second of the target, within 20 %.
