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

2026-11-13 (videos 003-005 got almost no views): the old score ranked keywords by the all-time top 20
results, which belong to million-subscriber channels, and "discovered" single words from music-video
titles ("lyrics", "season", "cannot") that then topped the table. Now, per keyword, it also reads:
  - YouTube autocomplete: the phrases people actually type (these become the discovered keywords);
  - the newest uploads (ytsearchdate): is anyone still getting views on this now;
  - breakouts: for the top results, the channel's subscriber count and the upload date; a recent video
    from a channel under 100 K subscribers with more views than subscribers proves a small channel can win.
The opportunity score is built from those. See data/growth-playbook.md (R1, R2).
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request
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
introduction intro video channel watch series episode part full short shorts documentary summary
""".split())
# a discovered word must never steer the writing into a policy problem: crime stories here are
# fiction (data/platform-policy.md), so "true", "real" and named-victim language stay out
RISKY_KEYWORD = re.compile(
    r"^(true|real|actual|genuine|documented|confession|victim|victims|murder|murders|murdered|murderer|killer|rape|"
    r"suicide|corpse|autopsy|evidence of|arrested|convicted)$", re.I)
# autocomplete phrases that are about something else (songs, games, other languages, a named show) or that would
# steer a story into a policy problem
JUNK_PHRASE = re.compile(
    r"\b(lyrics|song|songs|music|official|remix|karaoke|cover|trailer|reaction|minecraft|roblox|fortnite|genshin|"
    r"gaming|game|anime|tiktok|meme|memes|edit|asmr|ted ed|ted-ed|law and order|netflix|season|episode|"
    r"adalah|artinya|hindi|urdu|tamil|telugu|bangla|espanol|deutsch|true story|real story|real case|"
    r"based on true|murder|killer|victim|album|svu|ted talk|ted|podcast|audiobook|interview|reddit|by|ft|feat|fox stevenson)\b", re.I)


def autocomplete(query, timeout=15):
    """YouTube search suggestions for a query (what people type). [] on any failure."""
    url = ("https://suggestqueries.google.com/complete/search?client=firefox&ds=yt&hl=en&gl=US&q="
           + urllib.parse.quote(query))
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        return [str(x) for x in (data[1] if len(data) > 1 else [])]
    except Exception as e:  # noqa: BLE001 - research must never crash on one query
        print(f"  autocomplete failed for {query!r}: {e}", file=sys.stderr)
        return []


def typed_phrases(seed, max_out=12):
    """autocomplete for the seed and a few continuations: 2-6 word phrases about the subject"""
    out = []
    for q in [seed] + [f"{seed} {c}" for c in "aehiwsy"] + [f"why {seed}", f"how {seed}"]:
        for ph in autocomplete(q):
            ph = ph.strip().lower()
            if 2 <= len(ph.split()) <= 6 and ph.isascii() and not JUNK_PHRASE.search(ph) and ph not in out:
                out.append(ph)
        if len(out) >= max_out * 2:
            break
        time.sleep(0.2)
    return out[:max_out]


def video_details(vid, timeout=45):
    """subscriber count and upload date of one video (full extraction, slow). {} on failure."""
    cmd = [sys.executable, "-m", "yt_dlp", "--skip-download", "--dump-json", "--no-warnings",
           "--no-playlist", f"https://www.youtube.com/watch?v={vid}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        d = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {}
    return {"subs": d.get("channel_follower_count") or 0, "upload_date": d.get("upload_date") or "",
            "views": d.get("view_count") or 0, "channel": d.get("channel") or "", "title": d.get("title") or ""}


def age_days(upload_date, today):
    try:
        return (today - dt.datetime.strptime(upload_date, "%Y%m%d").date()).days
    except (TypeError, ValueError):
        return None


def is_breakout(d, today):
    """a recent video from a small channel that travelled beyond its own audience"""
    a = age_days(d.get("upload_date"), today)
    return (a is not None and a <= 365 and 0 < d.get("subs", 0) < 100_000
            and d.get("views", 0) >= max(20_000, d.get("subs", 0)))


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
    """Rough 0-100 for a NEW channel: is there demand now, and do small channels win it?

    recent demand (median views of the newest uploads)  up to 35
    breakouts (small recent channels with views > subs)  up to 30
    spread (many different channels in the results)      up to 15
    all-time demand (median views of the top results)    up to 20, damped: big old hits are not our market
    minus up to 10 when most top results are over two years old (a settled market).
    Without the recent/breakout data (YouTube refused) it falls back to the old shape, capped at 70, so a
    keyword never looks better for missing evidence.
    """
    if not s or not s.get("n"):
        return 0
    import math
    lg = lambda v: max(0.0, math.log10(max(1, v) / 1000))   # 10k = 1, 100k = 2, 1M = 3
    spread = min(15, (s["distinct_channels"] / max(1, s["n"])) * 15)
    alltime = min(20, lg(s["median_views"]) * 6)
    rec = s.get("recent") or {}
    if not rec.get("n") and not s.get("enriched"):
        return round(min(70, alltime * 2 + spread + min(10, (s["max_views"] / 2000000) * 10)))
    recent = min(35, lg(rec.get("median_views", 0)) * 14)
    brk = min(30, 12 * len(s.get("breakouts") or []))
    old = s.get("old_share")
    penalty = 10 * old if isinstance(old, (int, float)) else 0
    return max(0, round(recent + brk + spread + alltime - penalty))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="channel.json")
    ap.add_argument("--out", default="data/research")
    ap.add_argument("--quick", action="store_true", help="fewer results per keyword (smoke test)")
    ap.add_argument("--update-channel", action="store_true",
                    help="write the keywords discovered this run into data/discovered_keywords.json")
    ap.add_argument("--discovered", default="data/discovered_keywords.json")
    ap.add_argument("--enrich", type=int, default=None,
                    help="top results per keyword whose channel size and age are looked up (slow; default research.enrich_per_keyword or 4)")
    ap.add_argument("--enrich-budget-s", type=int, default=None,
                    help="stop looking up details after this many seconds in total (default research.enrich_budget_s or 420)")
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
    disc_path = pathlib.Path(a.discovered)
    disc_all = json.load(open(disc_path, encoding="utf-8")) if disc_path.is_file() else cfg.get("discovered_keywords", {})
    plan = []
    for t in topics:
        # discovered entries must be phrases: single words from older runs ("lyrics", "season") are skipped
        disc = [w for w in disc_all.get(t.get("id", ""), []) if len(w.split()) >= 2 and not JUNK_PHRASE.search(w)]
        kws = list(dict.fromkeys(list(t.get("seed_keywords", [])) + disc))
        plan += [(t.get("id", "all"), kw) for kw in kws]

    data = {"date": today, "lang": cfg.get("lang"), "niche": cfg.get("niche"),
            "topics": {t.get("id", "all"): t.get("name", "") for t in topics},
            "keywords": {}, "channels": {}, "typed": {}}
    enrich_n = a.enrich if a.enrich is not None else int(rcfg.get("enrich_per_keyword", 4))
    budget_s = a.enrich_budget_s if a.enrich_budget_s is not None else int(rcfg.get("enrich_budget_s", 420))
    budget_end = time.time() + budget_s
    if a.quick:
        enrich_n = min(enrich_n, 1)
    tday = dt.date.today()
    seed_set = {(t.get("id", "all"), k) for t in topics for k in t.get("seed_keywords", [])}
    seen_vid = {}
    for tid, kw in plan:
        print(f"[{tid}] keyword: {kw}", file=sys.stderr, flush=True)
        rows = ytdlp(f"ytsearch{per_kw}:{kw}", per_kw)
        st = summarise(rows)
        # yt-dlp 2026.10 no longer accepts "ytsearchdateN:"; a results URL with the "uploaded this month, videos" filter
        # (sp=EgQIBBAB) does: checked 2026-11-13, it returns this month's uploads (0-6 000 views for "sunk cost fallacy example").
        # sp=CAI%3D (sort by date) was tried first and still returned the relevance order.
        newest_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(kw) + "&sp=EgQIBBAB"
        newest = [r for r in ytdlp(newest_url, per_kw) if r.get("views")]
        if newest:
            nv = [r["views"] for r in newest]
            st["recent"] = {"n": len(newest), "median_views": int(statistics.median(nv)),
                            "with_1k": sum(1 for v in nv if v >= 1000),
                            "top": [{"t": r["title"][:90], "v": r["views"], "ch": r["channel"]}
                                    for r in sorted(newest, key=lambda r: r["views"], reverse=True)[:3]]}
        # channel size + age of the top results (relevance and newest), within the time budget
        cand = sorted({r["id"]: r for r in rows + newest if r.get("id")}.values(),
                      key=lambda r: r["views"], reverse=True)[:enrich_n]
        det = []
        for r in cand:
            if time.time() > budget_end:
                break
            d = seen_vid[r["id"]] if r["id"] in seen_vid else video_details(r["id"])
            seen_vid[r["id"]] = d
            if d:
                det.append(dict(d, id=r["id"]))
        if det:
            ages = [x for x in (age_days(d["upload_date"], tday) for d in det) if x is not None]
            st["enriched"] = len(det)
            st["old_share"] = round(sum(1 for x in ages if x > 730) / len(ages), 2) if ages else None
            st["median_subs"] = int(statistics.median([d["subs"] for d in det if d["subs"]] or [0]))
            st["breakouts"] = [{"t": d["title"][:90], "v": d["views"], "subs": d["subs"], "ch": d["channel"],
                                "age_d": age_days(d["upload_date"], tday)} for d in det if is_breakout(d, tday)]
        if (tid, kw) in seed_set:
            data["typed"][kw] = typed_phrases(kw)
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
         "| topic | keyword | opp | recent median | breakouts | median subs (top) | old >2y | all-time median | median len | channels |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for kw, s in ranked:
        if not s.get("n"):
            L.append(f"| {s.get('topic','')} | {kw} | - | no data | | | | | | |")
            continue
        rec = s.get("recent") or {}
        old = s.get("old_share")
        rmed = format(rec["median_views"], ",") if rec.get("n") else "?"
        nbrk = len(s.get("breakouts") or []) if s.get("enriched") else "?"
        msub = format(s["median_subs"], ",") if s.get("enriched") else "?"
        olds = f"{int(old * 100)}%" if isinstance(old, (int, float)) else "?"
        L.append(f"| {s.get('topic','')} | {kw} | {s['opportunity']} | {rmed} | {nbrk} | {msub} | {olds} | "
                 f"{s['median_views']:,} | {s['median_duration_s']}s | {s['distinct_channels']}/{s['n']} |")
    brk = [(kw, b) for kw, s in ranked for b in (s.get("breakouts") or [])]
    L += ["", "## Breakouts: small channels winning now (strongest signal, growth-playbook R2)", ""]
    if brk:
        for kw, b in sorted(brk, key=lambda x: x[1]["v"] / max(1, x[1]["subs"]), reverse=True)[:15]:
            L.append(f"- **{kw}**: {b['v']:,} views on a {b['subs']:,}-subscriber channel, {b['age_d']} days old - {b['ch']} - {b['t']}")
    else:
        L.append("- none found (or channel details were not available tonight): rely on recent median and spread")
    if data.get("typed"):
        L += ["", "## What people type (YouTube autocomplete, per seed keyword)", "",
              "Use these phrases as an idea's search phrase, in its title, first description line and tags (playbook R1, D1, D4).", ""]
        for kw, phs in data["typed"].items():
            if phs:
                L.append(f"- **{kw}**: " + "; ".join(phs))
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
          "- `opp` is built for a NEW channel: recent demand (median views of the newest uploads) and breakouts (recent",
          "  videos of channels under 100 K subscribers with more views than subscribers) weigh most; all-time views of the",
          "  top results weigh little, and a market whose top results are mostly over two years old loses points.",
          "  `?` means YouTube gave no details tonight; such rows are capped at 70.",
          "- `shorts` is the share of results under 60 s: high means the audience for that keyword watches vertical.",
          "- Recurring title words are what the audience searches for; reuse them in the title, not in the story.",
          "- Numbers come from YouTube search results on the day, not from an ads API: treat them as a direction, not a forecast."]
    # ---- candidate keywords discovered this run, per topic ---------------------------------
    cap = int(rcfg.get("max_discovered_keywords_per_topic", 14))
    seeds_by_topic = {t.get("id", "all"): {k.lower() for k in t.get("seed_keywords", [])} for t in topics}
    found = {}
    for tid, seeds in seeds_by_topic.items():
        # a discovered keyword is a PHRASE people type (autocomplete of one of this topic's seeds), 2-6 words, not a
        # seed itself, and never one that steers the writing into a policy problem. (Single words taken from titles
        # gave "lyrics", "season", "official", which then topped the table on 2026-11-11.)
        by_seed = []
        for kw, phs in data.get("typed", {}).items():
            if data["keywords"].get(kw, {}).get("topic") != tid:
                continue
            by_seed.append([ph for ph in phs if ph not in seeds and not any(RISKY_KEYWORD.search(w) for w in ph.split())])
        order = []
        for i in range(3):          # round robin, so every seed is represented
            order += [lst[i] for lst in by_seed if len(lst) > i and lst[i] not in order]
        found[tid] = order[:cap]
    data["discovered"] = found
    (out_dir / f"{today}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if any(found.values()):
        L += ["## Discovered search phrases per topic (added to data/discovered_keywords.json)", ""]
        L += [f"- **{tid}**: {', '.join(ws)}" for tid, ws in found.items() if ws]
        L.append("")

    (out_dir / "latest.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    if a.update_channel and any(found.values()):
        merged = dict(disc_all)
        for tid, ws in found.items():
            # old single-word entries are dropped; tonight's phrases go first, so the list follows what people type now
            old = [w for w in merged.get(tid, []) if len(w.split()) >= 2 and not JUNK_PHRASE.search(w)]
            merged[tid] = list(dict.fromkeys(ws + old))[:cap]
        disc_path.parent.mkdir(parents=True, exist_ok=True)
        json.dump(merged, open(disc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"{disc_path} updated:", {k: len(v) for k, v in merged.items()})
    print(f"wrote {out_dir / (today + '.json')} and {out_dir / 'latest.md'}")
    got = sum(1 for s in data["keywords"].values() if s.get("n"))
    print(f"keywords with data: {got}/{len(data['keywords'])}")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
