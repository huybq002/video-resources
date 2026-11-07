#!/usr/bin/env python3
"""Market + keyword research for the night job, with no API key.

    python scripts/research_youtube.py [--config channel.json] [--out data/research] [--quick]

For every seed keyword in channel.json it asks YouTube itself (yt-dlp `ytsearchN:`) what is
actually ranking, and for every reference channel what that channel's recent videos are. From the
titles, view counts and durations it works out, per keyword: how much demand there is, how strong
the competition is, whether the format is Shorts or long, which words keep coming back in titles,
and which keywords look under-served (decent views, few big channels).

It writes:
  <out>/<date>.json   full data (kept for later comparison)
  <out>/latest.md     a short digest, which is the only thing Claude needs to read

Claude then turns the digest into ideas and a task. The script makes no judgement calls and
never writes a task itself: it only brings the numbers.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import subprocess
import sys
from collections import Counter

STOP = set("""
the a an and or of to in on for with your you how what why when which that this is are be do does
did not no it its от và của cho với các một những là và được khi nào tại sao thế bạn mình tôi em
anh chị người cách học nên không có như để từ trong ra vào ở về rất thì mà nếu hay cũng đã sẽ
video full hd new 2024 2025 2026 part tap tập shorts short
""".split())
WORD = re.compile(r"[0-9\w'À-ỹ]+", re.UNICODE)
# words that say nothing about the subject, so they are useless as extra search terms
GENERIC = set("""
more most best worst every always never thing things stuff about really actually simple easy
explained explain complete ultimate guide tips tricks facts secret secrets truth story stories
minutes minute hours hour today tonight everything nothing someone people person
introduction intro video channel watch series episode part full short shorts documentary
""".split())
# a discovered word must never steer the writing into a policy problem: crime stories here are
# fiction (data/platform-policy.md), so "true", "real" and named-victim language stay out
RISKY_KEYWORD = re.compile(
    r"^(true|real|actual|genuine|documented|confession|victim|victims|murderer|killer|rape|"
    r"suicide|corpse|autopsy|evidence of|arrested|convicted)$", re.I)


def ytdlp(target, limit, timeout=240):
    """flat-playlist JSON lines -> list of dicts; never raises, returns [] on failure."""
    cmd = [sys.executable, "-m", "yt_dlp", "--flat-playlist", "--dump-json",
           "--playlist-end", str(limit), "--no-warnings", "--ignore-errors", target]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"  timeout: {target}", file=sys.stderr)
        return []
    out = []
    for line in (r.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.append({"title": d.get("title") or "", "views": d.get("view_count") or 0,
                    "duration": d.get("duration") or 0, "channel": d.get("channel") or d.get("uploader") or "",
                    "id": d.get("id") or ""})
    if not out:
        print(f"  nothing from {target}: {(r.stderr or '')[-160:]}", file=sys.stderr)
    return out


def words(titles):
    c = Counter()
    for t in titles:
        for w in WORD.findall(t.lower()):
            if len(w) > 2 and w not in STOP and not w.isdigit():
                c[w] += 1
    return c


def summarise(rows):
    if not rows:
        return {}
    views = [r["views"] for r in rows if r["views"]]
    durs = [r["duration"] for r in rows if r["duration"]]
    shorts = sum(1 for d in durs if 0 < d <= 60)
    chans = Counter(r["channel"] for r in rows if r["channel"])
    top = sorted(rows, key=lambda r: r["views"], reverse=True)[:5]
    return {
        "n": len(rows),
        "median_views": int(statistics.median(views)) if views else 0,
        "max_views": max(views) if views else 0,
        "median_duration_s": int(statistics.median(durs)) if durs else 0,
        "shorts_share": round(shorts / len(durs), 2) if durs else 0.0,
        "distinct_channels": len(chans),
        "top_channels": [c for c, _ in chans.most_common(3)],
        "top_titles": [{"t": r["title"][:90], "v": r["views"], "d": r["duration"], "ch": r["channel"]} for r in top],
        "title_words": [w for w, _ in words([r["title"] for r in rows]).most_common(12)],
    }


def opportunity(s):
    """Rough 0-100: demand (median views) up, crowding by few big channels down."""
    if not s or not s.get("n"):
        return 0
    import math
    # log scale: 10k views ~ 20, 100k ~ 36, 1M ~ 52, so niches do not all saturate at the top
    demand = min(60, max(0.0, math.log10(max(1, s["median_views"]) / 1000) * 18))
    spread = min(25, (s["distinct_channels"] / max(1, s["n"])) * 25)   # many different channels = easier to enter
    headroom = min(15, (s["max_views"] / 2000000) * 15)
    return round(demand + spread + headroom)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="channel.json")
    ap.add_argument("--out", default="data/research")
    ap.add_argument("--quick", action="store_true", help="fewer results per keyword (smoke test)")
    ap.add_argument("--update-channel", action="store_true",
                    help="write the keywords discovered this run back into channel.json discovered_keywords")
    a = ap.parse_args()

    cfg = json.load(open(a.config, encoding="utf-8"))
    rcfg = cfg.get("research", {})
    per_kw = 6 if a.quick else int(rcfg.get("results_per_keyword", 20))
    per_ch = 6 if a.quick else int(rcfg.get("videos_per_channel", 20))
    today = dt.date.today().isoformat()
    out_dir = pathlib.Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # keywords come from topics[].seed_keywords plus whatever earlier runs discovered;
    # the old flat seed_keywords list still works
    topics = cfg.get("topics") or [{"id": "all", "name": cfg.get("niche", "all"),
                                    "seed_keywords": cfg.get("seed_keywords", [])}]
    disc_all = cfg.get("discovered_keywords", {})
    plan = []
    for t in topics:
        kws = list(dict.fromkeys(list(t.get("seed_keywords", [])) + list(disc_all.get(t.get("id", ""), []))))
        plan += [(t.get("id", "all"), kw) for kw in kws]

    data = {"date": today, "lang": cfg.get("lang"), "niche": cfg.get("niche"),
            "topics": {t.get("id", "all"): t.get("name", "") for t in topics},
            "keywords": {}, "channels": {}}
    for tid, kw in plan:
        print(f"[{tid}] keyword: {kw}", file=sys.stderr, flush=True)
        st = summarise(ytdlp(f"ytsearch{per_kw}:{kw}", per_kw))
        st["opportunity"] = opportunity(st)
        st["topic"] = tid
        data["keywords"][kw] = st
    for url in cfg.get("reference_channels", []):
        print(f"channel: {url}", file=sys.stderr, flush=True)
        target = url.rstrip("/")
        if not target.endswith(("/videos", "/shorts")):
            target += "/videos"
        data["channels"][url] = summarise(ytdlp(target, per_ch))

    (out_dir / f"{today}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- digest: the only file Claude reads --------------------------------------------------
    ranked = sorted(data["keywords"].items(), key=lambda kv: kv[1].get("opportunity", 0), reverse=True)
    L = [f"# YouTube research {today}", "",
         f"niche: {cfg.get('niche', '')}", f"language: {cfg.get('lang', '')}", "",
         "## Keywords, best opportunity first",
         "",
         "| topic | keyword | opp | median views | max views | median len | shorts | channels |",
         "|---|---|---|---|---|---|---|---|"]
    for kw, s in ranked:
        if not s.get("n"):
            L.append(f"| {s.get('topic','')} | {kw} | - | no data | | | | |")
            continue
        L.append(f"| {s.get('topic','')} | {kw} | {s['opportunity']} | {s['median_views']:,} | {s['max_views']:,} | "
                 f"{s['median_duration_s']}s | {int(s['shorts_share'] * 100)}% | {s['distinct_channels']}/{s['n']} |")
    L += ["", "## What is winning right now (top titles per keyword)", ""]
    for kw, s in ranked:
        if not s.get("top_titles"):
            continue
        L.append(f"**{kw}** — recurring words: {', '.join(s['title_words'][:10])}")
        for t in s["top_titles"]:
            L.append(f"- {t['v']:,} views · {t['d']}s · {t['ch']} — {t['t']}")
        L.append("")
    if data["channels"]:
        L += ["## Reference channels", ""]
        for url, s in data["channels"].items():
            if not s.get("n"):
                continue
            L.append(f"**{url}** — median {s['median_views']:,} views, median {s['median_duration_s']}s, "
                     f"words: {', '.join(s['title_words'][:10])}")
            for t in s["top_titles"]:
                L.append(f"- {t['v']:,} views · {t['d']}s — {t['t']}")
            L.append("")
    L += ["## How to read this",
          "- `opp` mixes demand (median views) with how many different channels share the results; high views held by",
          "  two or three big channels is a worse bet than slightly lower views spread over many channels.",
          "- `shorts` is the share of results under 60 s: high means the audience for that keyword watches vertical.",
          "- Recurring title words are what the audience searches for; reuse them in the title, not in the story.",
          "- Numbers come from YouTube search results on the day, not from an ads API: treat them as a direction, not a forecast."]
    # ---- candidate keywords discovered this run, per topic ---------------------------------
    cap = int(rcfg.get("max_discovered_keywords_per_topic", 14))
    seeds_by_topic = {t.get("id", "all"): {k.lower() for k in t.get("seed_keywords", [])} for t in topics}
    found = {}
    for tid, seeds in seeds_by_topic.items():
        c = Counter()
        for kw, st in data["keywords"].items():
            if st.get("topic") == tid:
                for w in st.get("title_words", []):
                    c[w] += 1
        # a candidate has to be a real topic word: in several titles, long enough to search for,
        # not already a seed, and never one that would steer the writing into a policy problem
        found[tid] = [w for w, n in c.most_common(60)
                      if n >= 2 and len(w) >= 5 and w not in GENERIC
                      and not RISKY_KEYWORD.search(w)
                      and not any(w in sk for sk in seeds)][:cap]
    data["discovered"] = found
    (out_dir / f"{today}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if any(found.values()):
        L += ["## Words the winning titles keep using (candidate keywords per topic)", ""]
        L += [f"- **{tid}**: {', '.join(ws)}" for tid, ws in found.items() if ws]
        L.append("")

    (out_dir / "latest.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    if a.update_channel and any(found.values()):
        merged = dict(cfg.get("discovered_keywords", {}))
        for tid, ws in found.items():
            merged[tid] = list(dict.fromkeys(list(merged.get(tid, [])) + ws))[:cap]
        cfg["discovered_keywords"] = merged
        json.dump(cfg, open(a.config, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("channel.json discovered_keywords updated:", {k: len(v) for k, v in merged.items()})
    print(f"wrote {out_dir / (today + '.json')} and {out_dir / 'latest.md'}")
    got = sum(1 for s in data["keywords"].values() if s.get("n"))
    print(f"keywords with data: {got}/{len(data['keywords'])}")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
