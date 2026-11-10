# Background music library (owner-curated)

`ci/add_music.py` puts one of these tracks under each film, ducked under the voice. With no track here, films have no music.

Add only tracks whose licence allows **monetised** YouTube use: YouTube Audio Library (Studio, Audio Library, filter
"no attribution required" or note the credit), CC0 / public domain, or tracks you bought. Never add a track you only found
on YouTube or a "free" site without a licence page: Content ID claims take the revenue.

Steps:
1. Put the file here (mp3/ogg/m4a; keep each under ~8 MB; instrumental, no vocals).
2. Add an entry to `library.json`:
   `{"file": "night-walk.mp3", "moods": ["tense", "mystery"], "license": "YouTube Audio Library", "source": "<url>", "credit": null}`
   `credit` is the exact line the licence asks for in the description, or `null` when none is needed.
3. Moods are matched against the spec (`mood`, sequence/scene moods, `format`). Useful tags: tense, mystery, warm, sad,
   funny, hopeful, con, money, psychology. Several tracks per mood keep films from sounding the same.

Ideas for AI-made music (not used by the night job, it has no GPU): ACE-Step 1.5 (MIT code and weights, the model card
says output may be used commercially; needs a CUDA GPU with 4 GB+ VRAM, ~10 GB of models). Generate tracks on a GPU
machine, then add them here like any other track with `"license": "ACE-Step 1.5 output (MIT)"`.
