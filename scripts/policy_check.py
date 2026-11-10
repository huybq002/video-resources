#!/usr/bin/env python3
"""Guardrail between the idea and the render: refuse anything the platforms would act on.

    python scripts/policy_check.py task  tasks/pending/007-x.md
    python scripts/policy_check.py spec  specs/007-x.json
    python scripts/policy_check.py publish outputs/007-x/publish/publish.json

Nobody reads these videos before they go out, so the rules in data/platform-policy.md have to be
machine-checked. This looks for the four things that actually get a channel struck or sued:

  1. a claim that an invented story is true ("based on a true story", "vụ án có thật")
  2. a real, recognizable person, company, police force or case named in the script
  3. graphic injury or death detail
  4. advice where the channel promised a story (buy this, guaranteed returns, diagnose, cure)

plus the AI disclosure that both YouTube and TikTok expect on synthetic voice-overs, and (spec mode) the
"generic, repetitive or template-based" test of YouTube's inauthentic-content policy (updated 16 July 2026):
a new spec is compared with the last specs in its folder and fails when it is the same film with new nouns.

Exit 1 and one line per problem. It cannot read intent, so it is a floor, not a guarantee:
a passing check still means the story must be invented, as channel.json requires.
"""
import argparse
import json
import pathlib
import re
import sys

TRUTH_CLAIM = re.compile(
    r"\b(based on (a )?(true|real)|true story|real case|really happened|actual case|"
    r"this happened|real[- ]life case|documented case)\b|"
    r"(chuyện|câu chuyện|vụ án|sự việc)\s+(có thật|thật)|dựa trên (sự thật|chuyện có thật)", re.I)

GRAPHIC = re.compile(
    r"\b(dismember\w*|decapitat\w*|mutilat\w*|disembowel\w*|blood[- ]?soaked|gush\w* blood|"
    r"strangl\w+ (her|him|them) (slowly|to death)|torture[ds]?\b|slit (his|her|their) throat|"
    r"bled out|corpse was (found )?(rotting|decomposing))\b|"
    r"(phân xác|chặt xác|moi ruột|cắt cổ|tra tấn)", re.I)

ADVICE = re.compile(
    r"\b(you should (buy|sell|invest)|invest in [A-Z]|guaranteed (returns?|profit)|"
    r"risk[- ]free (return|profit)|will (double|triple) your money|financial advice|"
    r"you (have|need) (a|an) (anxiety|depression|adhd|bipolar)\b|cures? (your )?(anxiety|depression)|"
    r"stop taking (your )?(medication|meds))\b|"
    r"(nên mua|nên đầu tư|lợi nhuận (đảm bảo|cam kết)|chắc chắn (lãi|sinh lời)|tự chữa)", re.I)

# Real-world entities that must never appear in an invented story.
REAL_ENTITY = re.compile(
    r"\b(FBI|CIA|NYPD|Scotland Yard|Interpol|Europol|MI5|MI6|KGB|Mossad|"
    r"Apple|Google|Amazon|Microsoft|Meta|Facebook|Tesla|Netflix|Nvidia|OpenAI|Bitcoin|Ethereum|"
    r"Enron|Theranos|FTX|Lehman Brothers|Wirecard|Madoff|Ponzi scheme of|"
    r"Harvard|Stanford|Oxford|Cambridge University|NASA|WHO|CDC)\b")

PLACEHOLDER = re.compile(r"\b(TODO|TBD|xxx|lorem ipsum|<[a-z_]+>)\b", re.I)

problems, notes = [], []


def scan(text, where):
    for rx, msg in (
        (TRUTH_CLAIM, "claims the story is true. Crime stories here are FICTION: remove the claim "
                      "(channel.json mystery.hard_rules, data/platform-policy.md)"),
        (GRAPHIC, "graphic injury or death detail: cut it. It costs the ads and can cost the channel"),
        (ADVICE, "gives advice (money, medical or legal) where the channel promised a story"),
        (REAL_ENTITY, "names a real organisation, company or case. Invent one instead"),
        (PLACEHOLDER, "left a placeholder in text that ships"),
    ):
        for m in rx.finditer(text):
            frag = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
            problems.append(f"{where}: {msg} -> ...{frag.strip()}...")


def _words(t):
    t = re.sub(r"\d+", "#", str(t or "").lower())
    return [w for w in re.findall(r"[a-z#']+|[^\W\d_]+", t) if len(w) > 2]


def _sim(a, b):
    a, b = set(_words(a)), set(_words(b))
    return len(a & b) / max(1, len(a | b))


def _first_line(spec):
    for sc in spec.get("scenes", []):
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(item.get("cues") or []):
                t = c if isinstance(c, str) else str(c.get("t", ""))
                if t.strip():
                    return t
    return ""


def sameness(spec, path, keep=8):
    """YouTube 2026-07-16: 'generic, repetitive or template-based' videos lose monetization, AI or not. One automated
    film a night is only safe while each is a different film: different opening, different want, different shape."""
    folder = path.parent
    prev = sorted((q for q in folder.glob("*.json") if q.resolve() != path.resolve()), key=lambda q: q.stat().st_mtime)[-keep:]
    olds = []
    for q in prev:
        try:
            olds.append((q.name, json.load(open(q, encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    if not olds:
        return
    first, want = _first_line(spec), (spec.get("spine") or {}).get("want", "")
    shape = (spec.get("format"), len(spec.get("scenes", [])), tuple(sc.get("target_s") for sc in spec.get("scenes", [])))
    for name, o in olds:
        if first and _sim(first, _first_line(o)) >= 0.5:
            problems.append(f"{path.name}: opening line is almost the one of {name} ({_first_line(o)[:60]!r}): "
                            f"a repeated template is 'inauthentic content'. Open on a different image")
        ow = (o.get("spine") or {}).get("want", "")
        if want and ow and _sim(want, ow) >= 0.6:
            problems.append(f"{path.name}: spine.want repeats {name} ({ow[:60]!r}): tell a different story")
        if _sim(spec.get("title", ""), o.get("title", "")) >= 0.6:
            problems.append(f"{path.name}: title is a copy of {name}'s title pattern ({o.get('title', '')[:60]!r})")
    same_shape = [n for n, o in olds[-5:] if (o.get("format"), len(o.get("scenes", [])),
                                               tuple(sc.get("target_s") for sc in o.get("scenes", []))) == shape]
    if len(same_shape) >= 2:
        problems.append(f"{path.name}: same format, scene count and scene lengths as {', '.join(same_shape)}: "
                        f"change the shape (format, number of scenes, where the turn lands)")
    fmts = [o.get("format") for _, o in olds[-3:]]
    if spec.get("format") and len(fmts) == 3 and all(f == spec.get("format") for f in fmts):
        problems.append(f"{path.name}: fourth '{spec.get('format')}' film in a row: rotate formats "
                        f"(story-formats.md) so the channel is not one template")


def spec_text(spec):
    out = [str(spec.get("idea", "")), str(spec.get("title", ""))]
    for sc in spec.get("scenes", []):
        out += [str(sc.get("title", "")), str(sc.get("goal", ""))]
        for item in sc.get("shots", []):
            seq = item.get("sequence") or {}
            for c in list(seq.get("cues", [])) + list(seq.get("lines", [])) + list(item.get("cues") or []):
                out.append(c if isinstance(c, str) else str(c.get("t", "")))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["task", "spec", "publish"])
    ap.add_argument("path")
    ap.add_argument("--channel", default="channel.json")
    a = ap.parse_args()
    p = pathlib.Path(a.path)
    if not p.is_file():
        print(f"not found: {p}", file=sys.stderr)
        return 1
    cfg = json.load(open(a.channel, encoding="utf-8")) if pathlib.Path(a.channel).is_file() else {}

    if a.kind == "task":
        scan(p.read_text(encoding="utf-8"), p.name)
    elif a.kind == "spec":
        spec = json.load(open(p, encoding="utf-8"))
        scan(spec_text(spec), p.name)
        sameness(spec, p)
        for c in spec.get("cast", []):
            if c.get("real") or c.get("real_person"):
                problems.append(f"{p.name}: cast '{c.get('id')}' is marked as a real person")
    else:
        pub = json.load(open(p, encoding="utf-8"))
        flat = json.dumps(pub, ensure_ascii=False)
        scan(flat, p.name)
        disc = str(cfg.get("publish", {}).get("ai_disclosure", "")).strip()
        if cfg.get("publish", {}).get("require_ai_label", True):
            low = flat.lower()
            said = ("ai-generated" in low or "ai generated" in low or
                    (disc and disc.lower()[:28] in low))
            if not said:
                problems.append(f"{p.name}: no AI disclosure in any description or caption. Both YouTube and "
                                f"TikTok expect synthetic voice-overs to be labelled; add channel.json "
                                f"publish.ai_disclosure to each description, and switch the label on at upload")
            notes.append("remember the platform toggles too: YouTube Studio 'altered or synthetic content', "
                         "TikTok 'AI-generated' label")

    for n in notes:
        print("note:", n)
    if problems:
        print("POLICY PROBLEMS:")
        for x in problems:
            print(" -", x)
        return 1
    print("policy OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
