"""Series memory: every episode is its own independent run (new session, new out folder) yet keeps the same characters and continues the story.
The memory is ONE json file, the series bible (kept outside any episode project):
{ "name", "style": {"lang","aspect","tone","narrator"}, "world": ["rules/places that must stay true"],
  "characters": [cast entries: look, wardrobe, name, role, external ...],      <- design is frozen: the bible wins over an episode spec
  "character_state": {"lan": "what she knows / feels / wears now"},
  "settings": {...}, "setting_desc": {...}, "assets_dir": "<dir with <id>.svg and bg_*.png made once with Gemini>",
  "story_so_far": "rolling summary, <= 200 words",
  "open_loops": ["unresolved questions / promises still pending"],
  "episodes": [{"n","title","duration_s","summary","key_events":[],"clues":[],"last_line","next_hook"}] }

Commands
  python series.py brief <bible.json>      compact brief (~300-500 words) the writer reads BEFORE writing the next episode
  python series.py init  <bible.json> --name "..." --lang vi --aspect 16:9
generate.py --series <bible.json> merges the bible into the episode, copies the shared art into the project and, afterwards, writes the episode back.
Episode spec `series` block:  {"name","episode":N, "summary", "key_events":[...], "clues":[...], "last_line", "next_hook",
                               "resolved":[loops paid off in this episode], "open_loops":[new loops], "story_so_far":"updated rolling summary",
                               "character_state":{"id":"state at the end of this episode"}}
"""
import json, pathlib, shutil, sys

DESIGN_KEYS = ("name", "role", "look", "look_extra", "style", "skin", "top", "top_color", "top2", "bottom", "bottom_color", "shoes", "shoe_color", "sock", "hat", "hat_color",
               "hair", "hair_style", "glasses", "mustache", "tie", "scarf", "apron", "belt", "badge", "bag", "bag_color", "watch", "pattern", "torso_w", "eye_gap", "external")

def load(path):
    p = pathlib.Path(path)
    if p.exists(): return json.loads(p.read_text(encoding="utf-8"))
    return {"name": p.stem, "style": {}, "world": [], "characters": [], "character_state": {}, "settings": {}, "setting_desc": {}, "episodes": [],
            "open_loops": [], "story_so_far": "", "assets_dir": str(p.parent / "assets")}

def save(bible, path):
    p = pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(bible, ensure_ascii=False, indent=1), encoding="utf-8")

def merge(spec, bible):
    """returns (merged spec, warnings). Bible design wins so a character never changes look between episodes."""
    warns = []; spec = dict(spec); cast = {c["id"]: dict(c) for c in spec.get("cast", [])}
    for c in bible.get("characters", []):
        old = cast.get(c["id"], {})
        diff = [k for k in DESIGN_KEYS if k in old and old[k] != c.get(k)]
        if diff: warns.append(f"character '{c['id']}': episode spec differs from the bible on {diff}; bible design kept (edit the bible if the change is intended, e.g. a new outfit).")
        cast[c["id"]] = {**old, **c}
    spec["cast"] = list(cast.values())
    for k in ("settings", "setting_desc"):
        d = dict(bible.get(k, {})); d.update(spec.get(k, {})); spec[k] = d
    st = bible.get("style", {})
    for k in ("lang", "aspect"):
        if k in st and k not in spec: spec[k] = st[k]
    if bible.get("narrator") and "narrator" not in spec: spec["narrator"] = bible["narrator"]
    ser = dict(spec.get("series", {})); n = ser.get("episode") or (len(bible.get("episodes", [])) + 1); ser["episode"] = n
    spec["series"] = ser
    pend = [l for l in bible.get("open_loops", []) if l not in ser.get("resolved", [])]
    if n > 1 and bible.get("open_loops") and not ser.get("resolved") and not spec.get("script_prompt"):
        warns.append(f"episode {n}: {len(bible['open_loops'])} open loop(s) from earlier episodes and none listed in series.resolved; pay at least one off in the first 15 s and list it.")
    spec["series_context"] = {"story_so_far": bible.get("story_so_far", ""), "pending_loops": pend}
    return spec, warns

def copy_assets(bible, out_dir, bible_path):
    src = pathlib.Path(bible.get("assets_dir") or pathlib.Path(bible_path).parent / "assets"); out = pathlib.Path(out_dir) / "assets"; out.mkdir(parents=True, exist_ok=True); n = []
    if src.exists():
        for f in list(src.glob("*.svg")) + list(src.glob("bg_*.png")):
            shutil.copy(f, out / f.name); n.append(f.name)
    return n

def update(bible, spec0, plan, bible_path):
    """write this episode back into the bible. spec0 = the episode spec as the writer wrote it (before merging)."""
    ser = spec0.get("series", {}); have = {c["id"] for c in bible.get("characters", [])}
    for c in spec0.get("cast", []):
        if c["id"] not in have: bible.setdefault("characters", []).append(c)
    for k, v in spec0.get("settings", {}).items():
        if isinstance(v, dict): bible.setdefault("settings", {})[k] = v
    for k, v in spec0.get("setting_desc", {}).items(): bible.setdefault("setting_desc", {})[k] = v
    st = bible.setdefault("style", {})
    for k in ("lang", "aspect"):
        if spec0.get(k): st[k] = spec0[k]
    n = ser.get("episode") or (len(bible.get("episodes", [])) + 1)
    ep = {"n": n, "title": spec0.get("title", ""), "duration_s": round(plan["totalMs"] / 1000, 1), "summary": ser.get("summary") or spec0.get("idea", ""),
          "key_events": ser.get("key_events", []), "clues": ser.get("clues", []), "last_line": ser.get("last_line") or (plan["cues"][-1]["text"] if plan["cues"] else ""),
          "next_hook": ser.get("next_hook", "")}
    bible["episodes"] = sorted([e for e in bible.get("episodes", []) if e.get("n") != n] + [ep], key=lambda e: e["n"])
    loops = [l for l in bible.get("open_loops", []) if l not in ser.get("resolved", [])]
    bible["open_loops"] = loops + [l for l in ser.get("open_loops", []) if l not in loops]
    if ser.get("character_state"): bible.setdefault("character_state", {}).update(ser["character_state"])
    if ser.get("story_so_far"): bible["story_so_far"] = ser["story_so_far"]
    elif ep["summary"]: bible["story_so_far"] = (bible.get("story_so_far", "") + f" [Tập {n}] {ep['summary']}")[-1500:]    # fallback: rolling tail
    save(bible, bible_path)

def brief(bible):
    """compact text the writer of the NEXT episode reads instead of re-reading everything"""
    L = [f"SERIES: {bible.get('name')}  | next episode: {len(bible.get('episodes', [])) + 1}  | style: {json.dumps(bible.get('style', {}), ensure_ascii=False)}"]
    if bible.get("world"): L.append("WORLD RULES: " + "; ".join(bible["world"]))
    L.append("CAST (design frozen; do not change):")
    for c in bible.get("characters", []):
        if c.get("narrator"): L.append(f"- {c['id']} ({c.get('name')}): narrator voice, no body"); continue
        L.append(f"- {c['id']} = {c.get('name', c['id'])}, {c.get('role', '')}; top={c.get('top', 'shirt')}/{c.get('top_color', '')}, hat={c.get('hat', 'none')}, hair={c.get('hair_style', 'none')}; now: {bible.get('character_state', {}).get(c['id'], '-')}")
    L.append("STORY SO FAR: " + (bible.get("story_so_far") or "(nothing yet)"))
    for e in bible.get("episodes", [])[-3:]:
        L.append(f"EP{e['n']} '{e.get('title')}' {e.get('duration_s')}s: {e.get('summary', '')} | events: {'; '.join(e.get('key_events', []))} | clues: {'; '.join(e.get('clues', []))} | last line: \"{e.get('last_line', '')}\" | hook: {e.get('next_hook', '')}")
    L.append("OPEN LOOPS TO PAY OFF / CARRY: " + ("; ".join(bible.get("open_loops", [])) or "-"))
    L.append("RULES FOR THE NEW EPISODE: start by paying off or reacting to the last open loop within 15 s (list it in series.resolved), keep names, relationships, places and outfits identical, "
             "end on a new open loop (series.open_loops) + next_hook, and fill series.summary / key_events / clues / last_line / character_state / story_so_far (<=200 words) so the next run can continue.")
    return "\n".join(L)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["brief", "init"]); ap.add_argument("bible"); ap.add_argument("--name"); ap.add_argument("--lang", default="vi"); ap.add_argument("--aspect", default="16:9")
    a = ap.parse_args(); b = load(a.bible)
    if a.cmd == "init":
        b["name"] = a.name or b["name"]; b["style"] = {"lang": a.lang, "aspect": a.aspect}; save(b, a.bible); print("series bible created:", a.bible)
    else:
        sys.stdout.reconfigure(encoding="utf-8"); print(brief(b))
