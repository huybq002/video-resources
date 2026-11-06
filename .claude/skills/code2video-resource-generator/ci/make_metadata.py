"""Build YouTube metadata.json (title, description with chapters, tags) from the episode spec + the generated project.
python make_metadata.py <spec.json> <project_dir> [--privacy private] > metadata.json
spec["youtube"] may override: title, description, tags, categoryId, privacy, madeForKids, language.
"""
import argparse, json, pathlib, re, sys

def mmss(s): s = int(s); return f"{s//3600:d}:{s%3600//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60:02d}:{s%60:02d}"

ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("project"); ap.add_argument("--privacy", default=None); a = ap.parse_args()
spec = json.load(open(a.spec, encoding="utf-8")); yt = spec.get("youtube", {}); proj = pathlib.Path(a.project)
idx = (proj / "index.html").read_text(encoding="utf-8")
starts = [float(x) for x in re.findall(r"data-composition-src='compositions/scene_\d+\.html'\s+data-start='([\d.]+)'", idx)]
chapters = []
for sc, st in zip(spec["scenes"], starts):
    if sc.get("title"): chapters.append((st, sc["title"]))
if chapters and chapters[0][0] != 0: chapters.insert(0, (0.0, "Mở đầu"))
chap_txt = "\n".join(f"{mmss(t)} {n}" for t, n in chapters) if len(chapters) >= 3 else ""      # YouTube needs >= 3 chapters, first at 00:00
ep = spec.get("series", {}); title = yt.get("title") or spec.get("title") or spec.get("idea", "")[:90]
desc = yt.get("description") or "\n\n".join(x for x in [spec.get("idea", ""), chap_txt, "Video do AI tạo (giọng đọc và hình ảnh tổng hợp).", " ".join(yt.get("hashtags", ["#hoathinh", "#cauchuyen"]))] if x)
meta = {"title": title[:100], "description": desc[:5000], "tags": yt.get("tags", spec.get("tags", [])), "categoryId": yt.get("categoryId", "24"),
        "privacy": a.privacy or yt.get("privacy", "private"), "language": spec.get("lang", "vi"), "madeForKids": yt.get("madeForKids", False)}
sys.stdout.reconfigure(encoding="utf-8"); print(json.dumps(meta, ensure_ascii=False, indent=1))
