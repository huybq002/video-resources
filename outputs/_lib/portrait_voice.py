"""python portrait_voice.py <voice dir> <limit chars>: writes <voice dir>-portrait (same wav, captions re-split to fit one portrait line)"""
import json, shutil, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts" / "stickman"))
from narrate import split_caption
src = pathlib.Path(sys.argv[1]); lim = int(sys.argv[2]); dst = pathlib.Path(str(src) + "-portrait"); dst.mkdir(exist_ok=True)
shutil.copy(src / "narration.wav", dst / "narration.wav")
T = json.load(open(src / "timing.json")); caps = []
for c in T["captions"]:
    parts = split_caption(c["text"], lim); tot = sum(len(p) for p in parts) or 1; t = c["start"]
    for p in parts:
        d = (c["end"] - c["start"]) * len(p) / tot; caps.append({"start": round(t, 3), "end": round(t + d - 0.02 if p is not parts[-1] else c["end"], 3), "text": p}); t += d
T["captions"] = caps; json.dump(T, open(dst / "timing.json", "w"), indent=1, ensure_ascii=False)
print(len(T["captions"]), "captions, longest", max(len(c["text"]) for c in caps))
