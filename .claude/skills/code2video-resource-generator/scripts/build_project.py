"""Build the Code2Video project files (docs hyperframes-asset-contract) from spec.json + a timing JSON derived from script.srt.
python build_project.py <spec.json> <out_dir> [--no-audio-tag] [--no-captions]
Writes ONLY: index.html, compositions/scene_N.html, assets/* (script.srt is written by generate.py). No timeline.json / hyperframes.json / package.json: the app adds them.
Re-run it after the app replaces timeline.json with real TTS timings (cue count/order must be unchanged).
"""
import json, html, pathlib, shutil, sys, argparse
HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))
import characters as CH
import lipsync as LS

CAMS = {  # preset -> [scale0, x0, y0, scale1, x1, y1]
    "push": [1.04, 0, 0, 1.14, -30, -10], "push_slow": [1.02, 0, 0, 1.10, 0, -8], "pull": [1.16, 0, -10, 1.04, 0, 0],
    "pan_left": [1.08, 60, 0, 1.08, -60, 0], "pan_right": [1.08, -60, 0, 1.08, 60, 0], "punch": [1.10, 100, 0, 1.28, 220, -30],
    "static_drift": [1.06, 0, 0, 1.08, 10, 0],
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("out")
    ap.add_argument("--no-audio-tag", action="store_true"); ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--bg-dir", help="dir with bg_<setting>.png (default: <out>/assets)"); ap.add_argument("--timeline", required=True, help="timing JSON derived from script.srt")
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8")); out = pathlib.Path(a.out)
    TL = json.load(open(a.timeline, encoding="utf-8"))
    cast = {c["id"]: c for c in spec["cast"]}
    W, H = (1080, 1920) if spec.get("aspect", "16:9") == "9:16" else (1920, 1080)
    assets = out / "assets"; (assets / "fonts").mkdir(parents=True, exist_ok=True); (assets / "vendor").mkdir(exist_ok=True)
    (out / "compositions").mkdir(exist_ok=True)
    shutil.copy(SKILL / "assets/vendor/gsap.min.js", assets / "vendor/gsap.min.js")
    shutil.copy(SKILL / "assets/fonts/BeVietnamPro-Bold.ttf", assets / "fonts/BeVietnamPro-Bold.ttf")
    CH.write_all(spec["cast"], out)
    RIGS = json.load(open(assets / "character-rigs.json", encoding="utf-8"))
    for sc in spec["scenes"]:
        for sh in sc["shots"]:
          for setting in ([pn["setting"] for pn in sh["split"]] if sh.get("split") else [sh["setting"]]):
            bg = pathlib.Path(a.bg_dir or assets) / f"bg_{setting}.png"
            if not bg.exists(): sys.exit(f"missing background {bg} (render settings first)")
            if bg.parent != assets:
                shutil.copy(bg, assets / bg.name)
                for suf in ("_far", "_mid", "_near"):
                    lp = bg.parent / f"bg_{setting}{suf}.png"
                    if lp.exists(): shutil.copy(lp, assets / lp.name)
          if True:
            for p in sh.get("props", []):
                src = SKILL / "assets/props" / f"{p['id']}.svg"
                if src.exists(): (assets / "props").mkdir(exist_ok=True); shutil.copy(src, assets / "props" / src.name)
                elif not (assets / "props" / f"{p['id']}.svg").exists(): sys.exit(f"unknown prop {p['id']}")
    cues = {c["index"]: c for c in TL["cues"]}
    sc_by = {s["sceneIndex"]: s for s in TL["scenes"]}
    n_cues = sum(len(sh.get("cues", [])) for sc in spec["scenes"] for sh in sc["shots"])
    cue_who = {}; _i = 1
    for sc in spec["scenes"]:
        for sh in sc["shots"]:
            for cu in sh.get("cues", []):
                if isinstance(cu, dict) and cu.get("who"): cue_who[_i] = cu["who"]
                _i += 1
    env = LS.load_env(out / "assets" / "audio" / "voiceover.wav")   # real loudness when the app's voiceover.wav is present
    if n_cues != len(TL["cues"]): sys.exit(f"spec has {n_cues} cues but timeline.json has {len(TL['cues'])}")
    engine = (HERE / "engine.js").read_text(encoding="utf-8")
    sec = lambda ms: f"{ms/1000:.3f}"
    GS = "assets/vendor/gsap.min.js"
    next_cue = 1; root_hosts = []

    for sc in spec["scenes"]:
        n = sc["id"]; tsc = sc_by[n]; s0 = tsc["startMs"]; dur = tsc["sceneDurationMs"] / 1000; cid = f"scene-{n}"
        shots_html, shots_data, caps_html, caps_data = [], [], [], []; prev = None; prev_ids = []; prev_full = (0, 1)
        for si, sh in enumerate(sc["shots"]):
            if sh.get("share"):      # reuse the previous shot's cues (cutaway/reaction inside the same line)
                cue_ids, (f0, f1) = prev_ids, prev_full
            else:
                cue_ids = list(range(next_cue, next_cue + len(sh["cues"]))); next_cue += len(sh["cues"])
                f0 = (cues[cue_ids[0]]["startMs"] - s0) / 1000; f1 = (cues[cue_ids[-1]]["endMs"] - s0) / 1000
                prev_ids, prev_full = cue_ids, (f0, f1)
            por = sh.get("portion", [0, 1]); t0 = f0 + (f1 - f0) * por[0]; t1 = f0 + (f1 - f0) * por[1]
            dom = f"s{n}{chr(65+si)}"; chars_html, chars_data = [], []
            if sh.get("focus") and not sh.get("split"):      # close-ups: drop characters that end up outside the frame (fewer DOM nodes = faster render)
                _f = sh["focus"]; _z = min(_f.get("zoom", 2.4), _f.get("to", _f.get("zoom", 2.4) * 1.07)); _hx = next(x["x"] for x in sh["chars"] if x["k"] == _f["k"])
                sh = dict(sh, chars=[x for x in sh["chars"] if x["k"] == _f["k"] or x.get("enter") is not None or abs(_z * (x["x"] - _hx)) < W / 2 + _z * 200 * x.get("s", 0.8) + 60])
            pane_defs = ([dict(pn, idx=i) for i, pn in enumerate(sh["split"])] if sh.get("split") else [dict(idx=None, chars=sh["chars"])])
            pane_chars_html = {}
            for pn in pane_defs:
              pane_chars_html[pn["idx"]] = []
              for ch in pn["chars"]:
                ccid = f"{dom}-{ch['k']}" if pn["idx"] is None else f"{dom}p{pn['idx']}-{ch['k']}"; s = ch.get("s", 0.8)
                w, h = 400 * s, 800 * s; left, top = ch["x"] - w / 2, ch.get("by", 900) - 782 * s
                flip = ("transform:scaleX(-1);" if ch.get("flip") else "") + ("filter:drop-shadow(0 0 7px rgba(255,205,150,.75));" if (ch.get("glow") or cast[ch["k"]].get("glow") or spec.get("rim", True)) else "")
                acts_ = ch.get("acts", [])
                views_ = ["f"] + (["s"] if (ch.get("enter") is not None or any(a_[1] == "walkTo" or (a_[1] == "view" and a_[2] in ("side", "s")) for a_ in acts_)) else []) \
                                 + (["b"] if any(a_[1] == "view" and a_[2] in ("back", "b") for a_ in acts_) else [])
                ext_ = bool(cast[ch["k"]].get("external")) and (assets / f"{ch['k']}.svg").exists()
                svg = (f"<img id='{ccid}-ext' src='assets/{ch['k']}.svg' alt='' style='width:100%;height:100%;display:block'>" if ext_ else
                       CH.build_svg(ccid, cast[ch["k"]], tuple(views_)).replace("<svg xmlns", '<svg preserveAspectRatio="xMidYMax meet" xmlns', 1))
                pane_chars_html[pn["idx"]].append(f"<div id='{ccid}-wrap' class='char' style='left:{left:.1f}px;top:{top:.1f}px;width:{w:.1f}px;height:{h:.1f}px'><div class='flip' style='{flip}'>{svg}</div></div>")
                chars_data.append(dict(k=ch["k"], cid=ccid, acts=ch.get("acts", []), enter=ch.get("enter"), flip=bool(ch.get("flip")), ext=ext_))
            chars_html = pane_chars_html[None] if None in pane_chars_html else []
            props_html, props_data = [], []
            for pi, p in enumerate(sh.get("props", [])):
                pid = f"{dom}-prop{pi}"; w = p.get("w", 170)
                props_html.append(f"<img id='{pid}' class='prop' src='assets/props/{p['id']}.svg' style='left:{p['x']-w/2:.0f}px;top:{p['y']-w*0.7:.0f}px;width:{w}px;opacity:0'>")
                props_data.append(dict(dom=pid, mode=p.get("mode", "drop"), t=p.get("t", 0), lift=p.get("lift")))
            # crowd: seeded silhouettes in perspective rows
            crowd_html, crowd_data = [], []
            cr = sh.get("crowd")
            if cr:
                rs = [cr.get("seed", 7) * 9301 + 49297]
                def rnd():
                    rs[0] = (rs[0] * 9301 + 49297) % 233280; return rs[0] / 233280
                cols = cr.get("colors", ["#c0577a", "#e0b83a", "#3aa6a0", "#6a7ac8", "#d9884a", "#8a5ac8"])
                # `x` and `by` may be fractions of the frame (0-1, portable between 16:9 and 9:16)
                # or pixels in the real frame. Defaults are fractions so a crowd lands on the ground
                # in both aspects instead of floating in the sky of a portrait frame.
                def _span(v, size):
                    a_, b_ = v
                    return (a_ * size if a_ <= 1 else a_), (b_ * size if b_ <= 1 else b_)
                s0_, s1_ = cr.get("s", [0.18, 0.4])
                if H > W: s0_, s1_ = s0_ * 1.25, s1_ * 1.25    # portrait draws characters 1.25x: match them
                y0_, y1_ = _span(cr.get("by", [0.59, 0.83]), H); x0_, x1_ = _span(cr.get("x", [0.10, 0.90]), W)
                figs = sorted(((y0_ + (y1_ - y0_) * rnd(), rnd()) for _ in range(cr.get("n", 60))))
                for fi, (fy, rr) in enumerate(figs):
                    t_ = (fy - y0_) / max(1, (y1_ - y0_)); sc = s0_ + (s1_ - s0_) * t_; fx = x0_ + (x1_ - x0_) * rnd()
                    w_, h_ = 100 * sc * 1.6, 200 * sc * 1.6; fid = f"{dom}-cr{fi}"
                    crowd_html.append(f"<div id='{fid}' class='cfig' style='left:{fx - w_/2:.0f}px;top:{fy - h_:.0f}px;width:{w_:.0f}px;height:{h_:.0f}px;color:{cols[int(rnd()*len(cols))%len(cols)]}'><svg viewBox='0 0 100 200' width='100%' height='100%'><use href='#crowdfig'/></svg></div>")
                    crowd_data.append(dict(id=fid, a=round(rr, 3), d=round(rnd() * 0.5, 3)))
            # overlays (HUD language: chip / counter / burst / bubble / title)
            ov_html, ov_data = [], []
            POS = {"t": 5, "c": 40, "b": 70}; COL = {"l": "flex-start", "c": "center", "r": "flex-end"}
            for oi, o in enumerate(sh.get("overlays", [])):
                oid = f"{dom}-ov{oi}"; ty = o["type"]; pos = o.get("pos", "tc")
                inner = ""; cls = f"ov {ty}"
                if ty == "chip": inner = html.escape(o["text"])
                elif ty == "counter": inner = f"<div class='num' id='{oid}-n'></div><div class='lbl'>{html.escape(o.get('label', ''))}</div>"
                elif ty == "burst": inner = html.escape(o["text"])
                elif ty in ("bubble", "title"): inner = "".join(f"<span class='ch'>{html.escape(ch)}</span>" for ch in o["text"])
                elif ty == "screen":
                    tr = o.get("trend")
                    pts = {"up": "0,90 60,82 120,86 180,70 240,74 300,40 360,8", "down": "0,10 60,22 120,16 180,44 240,40 300,70 360,92",
                           "flat": "0,50 60,48 120,52 180,49 240,51 300,50 360,49"}.get(tr, "")
                    colr = {"up": "#3ccf6e", "down": "#ff5a5a"}.get(tr, "#9aa3ad")
                    inner = (f"<div class='scr-h'><span class='dot'></span>{html.escape(o.get('app', ''))}</div>"
                             f"<div class='scr-l'>{html.escape(o.get('label', ''))}</div>"
                             f"<div class='scr-v' style='color:{colr if tr else '#f6f0e4'}'>{html.escape(str(o.get('value', '')))}</div>"
                             + (f"<svg class='scr-c' viewBox='0 0 360 100'><polyline points='{pts}' fill='none' stroke='{colr}' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/></svg>" if pts else ""))
                top_css = "160px" if (spec.get("letterbox") and pos[0] == "t") else "%s%%" % POS[pos[0]]
                if "x" in o:   # absolute centre placement
                    ov_html.append(f"<div class='ovabs' style='left:{o['x']}px;top:{o['y']}px'><div id='{oid}' class='{cls}' style='opacity:0'>{inner}</div></div>")
                else:
                    ov_html.append(f"<div class='ovw' style='top:{top_css};justify-content:{COL[pos[1]]}'><div id='{oid}' class='{cls}' style='opacity:0'>{inner}</div></div>")
                extra = {"from": o.get("from", 0), "to": o.get("to", 0)} if ty == "counter" else {}
                ov_data.append(dict(id=oid, type=ty, t=o.get("t", 0), dur=o.get("dur", 3), abs=("x" in o), **extra))
            rain = "".join(f"<div class='rain' style='left:{(i*97)%{W+40}-20}px;height:{70+(i*13)%60}px;opacity:0'></div>" for i in range(70)) if sh.get("rain") else ""
            rays = "<div class='rays'></div>" if sh.get("rays") else ""
            cam = sh.get("cam", "push"); cam = CAMS[cam] if isinstance(cam, str) else cam
            foc = sh.get("focus")
            if foc and not sh.get("split"):   # zoom on a character's head (medium close-up 1.8, close-up 2.6, extreme 3.6)
                chf = next(x for x in sh["chars"] if x["k"] == foc["k"]); sf = chf.get("s", 0.8)
                hx = chf["x"] + foc.get("dx", 0); hy = chf.get("by", 900) - 782 * sf + 176 * sf + foc.get("dy", 0)
                Z0 = foc.get("zoom", 2.4); Z1 = foc.get("to", round(Z0 * 1.07, 3))
                tgt = foc.get("target_y", int(H * 0.44))
                kx = lambda Z: round(-Z * (hx - W / 2), 1); ky = lambda Z: round(tgt - 0.62 * H - Z * (hy - 0.62 * H), 1)
                cam = [Z0, kx(Z0), ky(Z0), Z1, kx(Z1), ky(Z1)]
            panes_data = None
            if sh.get("split"):
                parts = []; panes_data = []
                for pn in pane_defs:
                    i = pn["idx"]; pid = f"{dom}-pcam{i}"; panes_data.append(pid)
                    parts.append(f"<div class='pane' style='left:{i*960}px'><div id='{pid}' class='pcam'><img class='bgp' src='assets/bg_{pn['setting']}.png'>{''.join(pane_chars_html[i])}</div>"
                                 f"<div class='tint' style='background:{pn.get('tint', '#ffffff')}'></div></div>")
                sh = dict(sh, setting=sh["split"][0]["setting"], flat=True)
                scene_html = "".join(parts) + "<div class='pdiv'></div>" + "".join(crowd_html) + "".join(props_html)
            _ext = spec.get("external_bg", []); _ext = _ext is True or sh["setting"] in _ext
            layered = all((assets / f"bg_{sh['setting']}{suf}.png").exists() for suf in ("_far", "_mid", "_near")) and not sh.get("flat") and not _ext
            # depth of field only on a real close-up (zoom >= 2.2) or when a shot asks for it, and gently:
            # blurring the setting on every medium shot turned the story's places into colour blocks
            close = bool(foc) and float((foc or {}).get("zoom", 1)) >= 2.2
            dof_far = "filter:blur(2.5px);" if (sh.get("dof") or close) else ""; dof_mid = "filter:blur(1px);" if (sh.get("dof") or close) else ""
            if panes_data:
                layers_data = None
            elif layered:
                lid = lambda n: f"{dom}-{n}"
                scene_html = (f"<img id='{lid('L0')}' class='bg lay' style='{dof_far}' src='assets/bg_{sh['setting']}_far.png'><img id='{lid('L1')}' class='bg lay' style='{dof_mid}' src='assets/bg_{sh['setting']}_mid.png'>"
                              f"<div id='{lid('chars')}' class='lay'>{''.join(crowd_html)}{''.join(props_html)}{''.join(chars_html)}</div>"
                              f"<img id='{lid('L2')}' class='bg lay' style='filter:blur({spec.get('fg_blur', 5)}px);' src='assets/bg_{sh['setting']}_near.png'>")
                layers_data = [dict(dom=lid("L0"), k=0.35 if not foc else 0.6), dict(dom=lid("L1"), k=0.7 if not foc else 0.85), dict(dom=lid("chars"), k=0.85 if not foc else 1.0), dict(dom=lid("L2"), k=1.2)]
            else:
                scene_html = f"<img class='bg' style='{'filter:blur(1.5px);' if (foc and float((foc or {}).get('zoom', 1)) >= 2.2) else ''}' src='assets/bg_{sh['setting']}.png'>{''.join(crowd_html)}{''.join(props_html)}{''.join(chars_html)}"
                layers_data = None
            shots_html.append(f"<div id='{dom}' class='shot' style='z-index:{si+1}'><div id='{dom}-sway' class='cam'><div id='{dom}-cam' class='cam'>{scene_html}</div></div>{rays}{rain}{''.join(ov_html)}</div>")
            d = dict(dom=dom, t0=round(t0, 3), t1=round(t1, 3), cam=cam, chars=chars_data, props=props_data, first=(si == 0), prev=prev,
                     cut=bool(sh.get("cut")), trans=sh.get("trans"), crowd=crowd_data, overlays=ov_data)
            lip = []
            for ci in cue_ids:
                who = cue_who.get(ci)
                if who and any(x["k"] == who for x in chars_data):
                    evs = LS.cue_events(cues[ci].get("words", []), t0, t1, s0 / 1000.0, env)
                    if evs: lip.append(dict(k=who, ev=evs))
            if lip: d["lip"] = lip
            if layers_data: d["layers"] = layers_data
            if panes_data: d["panes"] = panes_data
            for key in ("shake", "rain", "flash", "sway"):
                if key in sh: d[key] = sh[key]
            shots_data.append(d); prev = dom
        for idx in range(tsc["cueRange"][0], tsc["cueRange"][1] + 1):
            c = cues[idx]
            ct0 = (c["startMs"] - s0) / 1000; ct1 = (c["endMs"] - s0) / 1000; islast = idx == tsc["cueRange"][1]
            if islast: ct1 = dur                       # contract rule 17: the last caption of a scene is never faded early
            caps_html.append(f"<div id='cap-{n}-{idx}' class='caption clip' data-start='{ct0:.3f}' data-duration='{ct1 - ct0:.3f}'><span>{html.escape(c['text'])}</span></div>")
            caps_data.append(dict(id=f"cap-{n}-{idx}", t0=round(ct0, 3), t1=round(ct1, 3), last=islast))
        if a.no_captions: caps_html, caps_data = [], []
        data = json.dumps(dict(W=W, H=H, sceneId=cid, dur=dur, shots=shots_data, caps=caps_data, rigs=RIGS), ensure_ascii=False)
        sel = f"[data-composition-id='{cid}']"
        style = f"""
    {sel} {{ position:absolute; inset:0; width:{W}px; height:{H}px; overflow:hidden; background:#07060d; font-family:'Be Vietnam Pro','Nunito',Arial,sans-serif; }}
    {sel} .shot {{ position:absolute; inset:0; opacity:0; overflow:hidden; }}
    {sel} .cam {{ position:absolute; inset:0; }}
    {sel} .bg {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; display:block; }}
    {sel} .char {{ position:absolute; }}
    {sel} .flip, {sel} .flip svg {{ width:100%; height:100%; display:block; }}
    {sel} .prop {{ position:absolute; z-index:5; }}
    {sel} .rain {{ position:absolute; top:0; width:3px; background:linear-gradient(#cfe0ff00,#cfe0ffaa); z-index:8; }}
    {sel} .pane {{ position:absolute; top:0; width:960px; height:1080px; overflow:hidden; }}
    {sel} .pcam {{ position:absolute; inset:0; }}
    {sel} .bgp {{ position:absolute; left:-480px; top:0; width:1920px; height:1080px; display:block; }}
    {sel} .tint {{ position:absolute; inset:0; mix-blend-mode:soft-light; opacity:.6; pointer-events:none; z-index:7; }}
    {sel} .pdiv {{ position:absolute; left:958px; top:0; width:4px; height:1080px; background:#0b0a0c; z-index:9; }}
    {sel} .char, {sel} .flip, {sel} .shot {{ overflow:visible; }}
    {sel} .shot {{ overflow:hidden; }}
    {sel} .lb {{ position:absolute; left:0; width:{W}px; height:{int(H*0.128)}px; background:#000; z-index:25; }}
    {sel} .lay {{ position:absolute; left:0; top:0; width:{W}px; height:{H}px; }}
    {sel} .cfig {{ position:absolute; }}
    {sel} .rays {{ position:absolute; inset:0; z-index:12; pointer-events:none; background:conic-gradient(from 200deg at 78% -10%, rgba(255,214,150,0), rgba(255,214,150,.22) 8%, rgba(255,214,150,0) 16%, rgba(255,214,150,.16) 26%, rgba(255,214,150,0) 36%); }}
    {sel} .ovw {{ position:absolute; left:0; right:0; display:flex; padding:0 72px; z-index:22; pointer-events:none; box-sizing:border-box; }}
    {sel} .ovabs {{ position:absolute; width:0; height:0; z-index:22; pointer-events:none; }}
    {sel} .ov.chip {{ padding:10px 26px; border-radius:999px; background:rgba(8,10,24,.72); border:1.5px solid rgba(255,255,255,.35); color:#f6f0e4; font-size:28px; letter-spacing:.06em; text-transform:uppercase; font-weight:700; white-space:nowrap; }}
    {sel} .ov.screen {{ width:{560 if H > W else 760}px; padding:26px 34px 30px; border-radius:26px; background:#10141d; border:3px solid #2b3240; box-shadow:0 30px 80px rgba(0,0,0,.55); color:#f6f0e4; }}
    {sel} .ov.screen .scr-h {{ display:flex; align-items:center; gap:12px; font-size:24px; letter-spacing:.08em; color:#aeb6c2; text-transform:uppercase; }}
    {sel} .ov.screen .dot {{ width:18px; height:18px; border-radius:50%; background:#3ccf6e; display:inline-block; }}
    {sel} .ov.screen .scr-l {{ margin-top:18px; font-size:28px; color:#cfd6e0; }}
    {sel} .ov.screen .scr-v {{ font-size:{84 if H > W else 96}px; font-weight:700; line-height:1.05; font-variant-numeric:tabular-nums; }}
    {sel} .ov.screen .scr-c {{ width:100%; height:110px; margin-top:14px; }}
    {sel} .ov.counter {{ padding:12px 34px 14px; border-radius:18px; background:rgba(8,10,24,.74); border:1.5px solid rgba(232,184,74,.55); text-align:center; }}
    {sel} .ov.counter .num {{ font-size:78px; font-weight:700; color:#f0c75a; text-shadow:0 0 22px rgba(240,199,90,.55); font-variant-numeric:tabular-nums; line-height:1.05; }}
    {sel} .ov.counter .lbl {{ font-size:22px; letter-spacing:.14em; text-transform:uppercase; color:#d9d2c0; }}
    {sel} .ov.burst {{ width:340px; height:300px; display:grid; place-items:center; text-align:center; background:#ffd23a; clip-path:polygon(100.0% 50.0%,82.3% 60.5%,90.5% 79.4%,70.0% 77.5%,65.5% 97.6%,50.0% 84.0%,34.5% 97.6%,30.0% 77.5%,9.5% 79.4%,17.7% 60.5%,0.0% 50.0%,17.7% 39.5%,9.5% 20.6%,30.0% 22.5%,34.5% 2.4%,50.0% 16.0%,65.5% 2.4%,70.0% 22.5%,90.5% 20.6%,82.3% 39.5%); color:#c2262e; font-size:52px; font-weight:700; line-height:1; padding:40px; box-sizing:border-box; }}
    {sel} .ov.bubble {{ width:560px; padding:20px 28px; border-radius:26px; background:#fff; color:#241726; font-size:34px; line-height:1.25; font-weight:700; box-sizing:border-box; box-shadow:0 6px 0 rgba(0,0,0,.25); }}
    {sel} .ov.title {{ font-size:104px; letter-spacing:.06em; text-transform:uppercase; font-weight:700; color:#ff9ad0; text-shadow:0 0 24px rgba(255,120,190,.7); text-align:center; max-width:1500px; }}
    {sel} .vig {{ position:absolute; inset:0; z-index:20; pointer-events:none; background:radial-gradient(ellipse at 50% 46%, transparent 52%, rgba(3,2,10,.62) 100%); }}
    {sel} .flash {{ position:absolute; inset:0; z-index:30; background:#fff; opacity:0; }}
    {sel} .caption {{ position:absolute; left:{6 if H > W else 8}%; right:{6 if H > W else 8}%; bottom:{16 if H > W else 5.5}%; z-index:40; display:grid; place-items:center; text-align:center; opacity:0; }}
    {sel} .caption span {{ max-width:{980 if H > W else 1500}px; padding:14px 32px; border-radius:14px; background:rgba(8,6,16,.66); color:#f6f0e4; font-size:{62 if H > W else 44}px; line-height:1.25; font-weight:700; text-shadow:0 2px 6px #000; }}
    """
        lb_html = "<div class='lb' data-layout-allow-occlusion='true' style='top:0'></div><div class='lb' data-layout-allow-occlusion='true' style='bottom:0'></div>" if spec.get("letterbox") else ""
        script = engine.replace("__DATA__", data.replace("</", "<\\/"))
        doc = (f"<template id='{cid}-template'>\n  <div data-composition-id='{cid}' data-width='{W}' data-height='{H}' data-duration='{dur:.3f}'>\n"
               f"    <svg width='0' height='0' style='position:absolute'><defs><symbol id='crowdfig' viewBox='0 0 100 200'><circle cx='50' cy='36' r='22' fill='#0b0a0c'/><rect x='24' y='62' width='52' height='80' rx='20' fill='currentColor'/><path d='M38 140 L36 192 M62 140 L64 192' stroke='#241726' stroke-width='12' stroke-linecap='round'/></symbol></defs></svg>\n    {''.join(shots_html)}\n    {lb_html}<div class='vig' data-layout-allow-occlusion='true'></div><div id='flash-{cid}' class='flash'></div>\n    {''.join(caps_html)}\n"
               f"    <style>@font-face{{font-family:'Be Vietnam Pro';src:url('assets/fonts/BeVietnamPro-Bold.ttf');font-weight:700}}{style}</style>\n"
               f"    <script src='{GS}'></script>\n    <script>{script}</script>\n  </div>\n</template>\n")
        (out / "compositions" / f"scene_{n}.html").write_text(doc, encoding="utf-8")
        root_hosts.append(f"<div id='{cid}-host' class='clip scene-host' data-composition-id='{cid}' data-composition-src='compositions/scene_{n}.html' "
                          f"data-start='{sec(tsc['startMs'])}' data-duration='{sec(tsc['sceneDurationMs'])}' data-track-index='1' data-track-kind='graphics'></div>")

    total = sec(TL["durationMs"]); td = TL["durationMs"] / 1000
    fps = spec.get("fps", 60 if td <= 180 else 30)      # long films default to 30 fps: render time is ~7 s per second of video at 30 fps on a laptop
    mb_attr = (' data-motion-blur="on" data-motion-blur-shutter="%s"' % spec.get("motion_blur_shutter", 180)) if spec.get("motion_blur") else ""
    audio = "" if a.no_audio_tag else f"<audio id=\"voice\" src=\"assets/audio/voiceover.wav\" data-start=\"0\" data-duration=\"{total}\" data-track-index=\"0\"></audio>"
    index = f"""<!doctype html>
<html lang="{spec.get('lang', 'vi')}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={W}, height={H}">
  <title>{html.escape(spec.get('title', 'Code2Video'))}</title>
  <script src="{GS}"></script>
  <style>
    html, body {{ margin:0; width:{W}px; height:{H}px; overflow:hidden; background:#07060d; }}
    #root {{ position:relative; width:{W}px; height:{H}px; overflow:hidden; }}
    .scene-host {{ position:absolute; inset:0; z-index:2; }}
    .stage {{ position:absolute; inset:0; z-index:1; background:#07060d; }}
    #voice {{ position:absolute; width:1px; height:1px; opacity:0; }}
    #endfade {{ position:absolute; inset:0; background:#000; opacity:0; z-index:100; pointer-events:none; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="story" data-width="{W}" data-height="{H}" data-start="0" data-duration="{total}" data-fps="{fps}"{mb_attr}>
    <div id="stage" class="clip stage" data-start="0" data-duration="{total}" data-track-index="0"></div>
    {audio}
    {chr(10).join('    ' + h for h in root_hosts)}
    <div id="endfade"></div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      tl.to("#endfade", {{ opacity: 1, duration: 1.2, ease: "power1.in" }}, {max(0, td - 1.2):.3f});
      window.__timelines = window.__timelines || {{}};
      window.__timelines["story"] = tl;
    </script>
  </div>
</body>
</html>
"""
    (out / "index.html").write_text(index, encoding="utf-8")
    print(f"built {len(spec['scenes'])} scenes -> {out}")

if __name__ == "__main__":
    main()
