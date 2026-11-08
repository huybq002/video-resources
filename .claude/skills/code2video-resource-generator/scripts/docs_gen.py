"""Human-readable deliverables written NEXT TO the project (never inside it): scene plan, Gemini character prompts, asset checklist."""
import pathlib
from srt_tools import ts

NAMES = [("#ffffff", "white"), ("#1c1626", "black"), ("#808080", "grey"), ("#c0c0c0", "light grey"), ("#8b0000", "dark red"), ("#d33a3a", "red"), ("#e07a2f", "orange"),
         ("#e8c24a", "mustard yellow"), ("#f2e4a0", "pale yellow"), ("#6b8e3a", "olive green"), ("#2f8f6a", "green"), ("#2f8f8a", "teal"), ("#7fc4c0", "mint"),
         ("#3a6ab0", "blue"), ("#1f2f5a", "navy blue"), ("#8aa8d0", "light blue"), ("#6a4aa0", "purple"), ("#c0577a", "rose pink"), ("#f2a8b8", "light pink"),
         ("#8a5a3a", "brown"), ("#b79a6a", "khaki"), ("#d8c8a8", "beige"), ("#4a3326", "dark brown"), ("#3a3f55", "charcoal"), ("#4a5a70", "slate blue"), ("#e9e4d8", "cream")]
def _rgb(h): h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
def cname(h):
    if not h: return ""
    r = _rgb(h); b = min(NAMES, key=lambda n: sum((x - y) ** 2 for x, y in zip(r, _rgb(n[0]))))
    return f"{b[1]} ({h})"

def auto_look(c):
    import characters_stick as S
    w = S.wardrobe(c); p = []
    top = {"tshirt": "short-sleeved t-shirt", "shirt": "long-sleeved collared shirt", "hoodie": "hoodie with hood and front pocket", "jacket": "jacket with lapels over a shirt",
           "coat": "long knee-length trench-style coat with belt, popped collar, lapels and a double row of buttons (worn alone, NO trousers: bare thin legs below the hem)",
           "dress": "knee-length dress (worn alone, bare thin legs below the hem)", "tank": "sleeveless top"}[w["top"]]
    p.append(f"{cname(w['top_color'])} {top}")
    if w["bottom"] != "none": p.append({"pants": "long trousers", "shorts": "shorts", "skirt": "A-line skirt"}[w["bottom"]] + f" in {cname(w['bottom_color'])}")
    p.append({"sneakers": "sneakers", "boots": "ankle boots", "heels": "high heels", "none": "bare feet"}[w["shoes"]] + f" in {cname(w['shoe_color'])}")
    if c.get("hat", "none") != "none": p.append({"fedora": "fedora hat", "deerstalker": "deerstalker detective cap", "cap": "baseball cap", "beanie": "knitted beanie", "scarf": "headscarf"}[c["hat"]] + f" in {cname(c.get('hat_color', '#3a3f55'))}")
    if c.get("hair_style", "none") != "none": p.append(f"{c['hair_style']} hair in {cname(c.get('hair', '#1c1626'))}")
    for k, t in (("glasses", "round glasses"), ("mustache", "small mustache"), ("badge", "name badge"), ("bag", "shoulder bag"), ("watch", "wristwatch")):
        if c.get(k): p.append(t)
    for k, t in (("tie", "necktie"), ("scarf", "scarf around the neck"), ("apron", "apron"), ("belt", "belt")):
        if c.get(k): p.append(f"{t} in {cname(c[k])}")
    return "; ".join(p)

STYLE = ("Playful minimalist 'stickman explainer' cartoon: a big perfectly round WHITE head with a thick dark outline and a very expressive face "
         "(large oval black eyes with two small white highlights, thin curved eyebrows, pink blush ellipses on the cheeks, simple smiling mouth), a very short thin black neck, "
         "thin black arms and legs drawn as strokes (stroke width 9, round caps), each hand is ONE small solid black dot (no fingers), clothes are simple flat colour shapes with a 4-5 px dark outline "
         "and at most one soft shading gradient. No real person, no sports kit, no brand, no logo, no text.")
TECH = ("TECHNICAL: output ONLY valid SVG code, no markdown fences, no explanation. Root element: <svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 400 800\" width=\"400\" height=\"800\">. "
        "TRANSPARENT background (no background rectangle). Character centred at x=200, standing, soles of the feet touching y=780, whole body visible, nothing cropped. "
        "Head = circle centred at (200,175) with radius about 100 (top of head at y=75). Allowed elements: path, circle, ellipse, rect, polygon, g, linearGradient, radialGradient. "
        "No <image>, <text>, filters, masks, blur, clip-paths or external references; fewer than 150 elements; outline colour #1c1626.")

VIEWS = {"": ("FRONT view, neutral", "Facing the viewer. Eyes open looking straight ahead, relaxed eyebrows, mouth closed in a gentle small smile. Arms hang slightly away from the body, legs slightly apart."),
         "talk": ("FRONT view, talking", "Same pose, clothes and head as the neutral front image; only the mouth changes: open mid-speech (dark inside, small pink tongue), eyebrows slightly raised."),
         "happy": ("FRONT view, very happy", "Same design. Eyes are closed happy arcs, big open laughing smile, extra rosy cheeks, arms raised a little."),
         "sad": ("FRONT view, sad", "Same design. Eyebrows tilted up toward the middle, mouth a small downward curve, one small blue tear, shoulders lowered."),
         "side": ("SIDE view facing the viewer's RIGHT", "Full-body profile looking to the right edge of the canvas: head in profile with one eye, one eyebrow, mouth closed; both thin legs side by side, feet pointing right, one arm slightly forward."),
         "back": ("BACK view", "Seen from behind: plain round head (hair or hat from behind if the character has one), no face, clothes seen from the back, arms down, legs slightly apart.")}

BG_STYLE = ("Flat-colour 3D-toon illustration (soft cel shading, simple geometric shapes, thin dark ink outlines, gentle depth-of-field), same art style as a minimalist stickman cartoon explainer. "
            "Rich but clean details, warm/cool light contrast, subtle vignette.")

LIB_DESC = {
    "lib_street_day": "sunny city street in daylight: a row of colourful 3-4 storey townhouses (pink, yellow, blue, mint, salmon) with brown roofs, small lit windows and doors, a wide pavement, a few round green trees and slim street lamps, light blue sky with a few soft clouds",
    "lib_park_dusk": "city park at dusk: sandy path leading into the distance, wooden bench on the left, low wooden fence, several round low-poly green trees, two warm street lamps, big peach sun low on the horizon, violet-blue sky fading to orange",
    "lib_bedroom_night": "cosy bedroom at night: bed with purple blanket and white pillow against the back wall, small bedside lamp glowing warm, window with a bright moon and dark blue sky, two small wall posters, soft rug, dark violet walls",
    "lib_office": "modern open office in the evening: three desks in a row with laptop screens glowing cyan, tall windows with a blue city view and warm lamp light, grey-blue walls, potted plant at the right, filing cabinet at the left",
    "lib_cafe": "warm cafe interior: wooden counter with cups at the back left, four small round tables with two white cups each, pendant lamps glowing amber above the tables, big window at the right with a pale blue view, orange-brown walls, wooden floor",
    "lib_rooftop_night": "city rooftop at night: low parapet in the foreground with a string of warm round lights, a dense skyline of dark blue skyscrapers with many lit yellow and blue windows, stars and a bright moon, small rooftop shed with a lit door at the right"}

def setting_desc(spec, sid, data):
    """text description of a setting: spec.setting_desc[sid] (preferred, hand-written) else derived from the 3D setting"""
    if spec.get("setting_desc", {}).get(sid): return spec["setting_desc"][sid]
    if sid in LIB_DESC: return LIB_DESC[sid]
    sky = data.get("sky"); bg = data.get("bg")
    mood = "night" if (sky and sum(_rgb(sky[0])) < 250) or (bg and sum(_rgb(bg)) < 200) else "daytime / dusk"
    kinds = {}
    for o in data.get("objects", []):
        k = o.get("n") or o["t"]; kinds[k] = kinds.get(k, 0) + 1
    names = ", ".join(f"{k} x{v}" if v > 1 else k for k, v in list(kinds.items())[:10])
    return f"{'exterior' if sky else 'interior'} scene, {mood}; main elements: {names}"

def bg_prompt(spec, sid, data):
    ratio, size = ("9:16 vertical", "1080x1920") if spec.get("aspect") == "9:16" else ("16:9", "1920x1080")
    return (f"You are an expert background artist. Draw ONE {ratio} background image ({size} px, PNG) for an animated video.\n"
            f"SCENE ({sid}): {setting_desc(spec, sid, data)}.\n"
            f"STYLE: {BG_STYLE}\n"
            "COMPOSITION: wide establishing view with the camera at about eye height; horizon / floor line at about 62% of the height; the lower-middle area (x 15-85%, y 55-90%) is open ground or floor where characters will stand; "
            "keep the bottom 22% calm (no important detail, captions go there); important props near the left and right thirds, nothing tall in the exact centre. "
            "NO people, NO characters, NO animals, NO text, NO logos, NO watermarks, no frame or border. Seamless edges, no transparency (full-bleed picture).")

def file_for(cid, view): return f"assets/{cid}.svg" if not view else f"assets/{cid}_{view}.svg"

def prompt(c, view):
    look = c.get("look") or auto_look(c); t, pose = VIEWS[view]
    return (f"You are an expert vector illustrator. Draw ONE SVG character sprite.\nCHARACTER: {c.get('name', c['id'])} - {c.get('role', 'character')}. {look}.\n"
            f"STYLE: {STYLE}\nVIEW / EXPRESSION: {t}. {pose}\n"
            f"CONSISTENCY: this is part of a set of images of the same character; keep the same proportions, head size, colours, clothes and line weight in all of them (if you already drew this character's neutral front image in this chat, reuse its design exactly).\n{TECH}")

def character_prompts(spec, path, settings=None):
    L = ["# Prompt Gemini: nhân vật SVG + background", "",
         "Mỗi nhân vật: mở một cuộc trò chuyện Gemini mới, dán prompt `front` trước (bắt buộc), rồi các prompt tùy chọn trong cùng cuộc trò chuyện để nhân vật đồng nhất.",
         "Lưu **chỉ phần `<svg>...</svg>`** vào đúng đường dẫn ở tiêu đề mỗi prompt (thư mục `assets/` của project), rồi trong spec đặt `\"external\": true` cho nhân vật đó và chạy lại `generate.py --keep-srt --skip-bg`.",
         "Nhân vật dùng file ngoài được di chuyển/nghiêng/nhún/đi ngang như một khối (không có khớp riêng); các file `talk`, `happy`, `sad`, `side`, `back` là bộ biến thể tùy chọn để thay khi cần (chưa tự động đổi trong render hiện tại).", "",
         "Kiểm tra file: nền trong suốt, nhân vật ở giữa canvas 400×800, chân chạm đáy (y≈780), đầu tròn tâm (200,175).", ""]
    for c in [c_ for c_ in spec.get("cast", []) if not c_.get("extra")]:
        if c.get("narrator") or c.get("id") == spec.get("narrator", "narrator"): continue
        L += [f"## {c.get('name', c['id'])} (id `{c['id']}`)", "", f"- Vai trò: {c.get('role', '')}", f"- Trang phục: {c.get('look') or auto_look(c)}", ""]
        for v in VIEWS:
            L += [f"### {file_for(c['id'], v)}  ·  {VIEWS[v][0]}" + ("" if v == "" else "  (tùy chọn)"), "", "```text", prompt(c, v), "```", ""]
    L += ["# Background (bối cảnh) — lưu PNG 1920×1080 vào assets/", "",
          "Mỗi bối cảnh một ảnh. Dán prompt vào Gemini (tạo ảnh), tải về PNG và lưu đúng tên. Muốn dùng ảnh Gemini thay ảnh 3D của skill: thêm vào spec `\"external_bg\": true` (hoặc danh sách id bối cảnh) rồi chạy lại `generate.py --keep-srt --skip-bg`.", ""]
    for sid, data in (settings or {}).items():
        L += [f"## assets/bg_{sid}.png  (bối cảnh `{sid}`)", "", "```text", bg_prompt(spec, sid, data), "```", ""]
    pathlib.Path(path).write_text("\n".join(L), encoding="utf-8")

def scene_plan(spec, plan, path):
    L = [f"# Kế hoạch scene — {spec.get('title', spec.get('id', ''))}", "", f"Tổng thời lượng: **{plan['totalMs']/1000:.1f}s** ({plan['totalMs']/60000:.2f} phút) · {len(plan['scenes'])} scene · {len(plan['cues'])} câu thoại", "",
         "| Scene | Từ | Đến | Dài (s) | Mục tiêu (s) | Câu | Từ | Mục đích / nội dung |", "|---|---|---|---|---|---|---|---|"]
    for s in plan["scenes"]:
        sc = next(x for x in spec["scenes"] if x["id"] == s["id"]); cs = [c for c in plan["cues"] if c["scene"] == s["id"]]
        L.append(f"| {s['id']} | {ts(s['startMs'])[:8]} | {ts(s['endMs'])[:8]} | {(s['endMs']-s['startMs'])/1000:.1f} | {sc.get('target_s', '-')} | {len(cs)} | {sum(len(c['text'].split()) for c in cs)} | {sc.get('title', '')} — {sc.get('goal', '')} |")
    L += ["", "## Chi tiết từng scene", ""]
    for s in plan["scenes"]:
        sc = next(x for x in spec["scenes"] if x["id"] == s["id"]); cs = [c for c in plan["cues"] if c["scene"] == s["id"]]
        L += [f"### Scene {s['id']} · {ts(s['startMs'])[:8]} → {ts(s['endMs'])[:8]} · {title(sc)}", ""]
        L += [f"- {c['speaker']}: {c['text']}  _({(c['endMs']-c['startMs'])/1000:.1f}s)_" for c in cs] + [""]
    for n in plan["notes"]: L.append(f"> {n}")
    pathlib.Path(path).write_text("\n".join(L), encoding="utf-8")

def title(sc): return sc.get("title", "")

def checklist(spec, out_dir, path):
    out = pathlib.Path(out_dir); L = ["# Danh sách file trong project", "", "| File | Tạo bởi | Trạng thái |", "|---|---|---|"]
    for rel, who in [("index.html", "skill"), ("script.srt", "skill"), ("assets/audio/voiceover.wav", "app (TTS)")]:
        L.append(f"| `{rel}` | {who} | {'có' if (out / rel).exists() else 'chưa (app sinh khi render)' if 'wav' in rel else 'THIẾU'} |")
    for f in sorted((out / "compositions").glob("*.html")): L.append(f"| `compositions/{f.name}` | skill | có |")
    for f in sorted((out / "assets").glob("bg_*.png")): L.append(f"| `assets/{f.name}` | skill (3D) | có |")
    for c in [c_ for c_ in spec.get("cast", []) if not c_.get("extra")]:
        if c.get("narrator"): continue
        ext = c.get("external")
        L.append(f"| `assets/{c['id']}.svg` | {'Gemini (bạn)' if ext else 'skill (nhân vật dựng sẵn)'} | {'có' if (out/'assets'/(c['id']+'.svg')).exists() else ('CẦN ĐẶT' if ext else 'có')} |")
    pathlib.Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
