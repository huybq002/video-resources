"""Stick-figure characters with a story-driven wardrobe (default character style).
Big round head with a fully expressive face, thin black arms and legs, clothes drawn as flat shapes. Front, side (profile) and back drawings
share one rig (same part ids as the old bean style, so every act in engine.js works unchanged).

Cast fields (all optional):
  skin           head colour (default "#ffffff"; stick heads are usually white, any tone works)
  top            tshirt | shirt | hoodie | jacket | coat | dress | tank        (choose from the script: detective = coat, student = shirt/uniform, ...)
  top_color, top2 (collar/lapel/inner colour), bottom (pants | shorts | skirt | none), bottom_color, shoes (sneakers | boots | heels | none), shoe_color, sock
  tie (hex), scarf (hex), badge (bool), bag (bool), watch (bool), apron (hex), belt (hex), buttons (bool), pattern (none | stripes | hoops | checks)
  hat (none | fedora | cap | beanie | scarf), hat_color, hair_style (none | short | long | bun | tuft | spiky), hair, glasses, mustache, torso_w (0.85-1.2), eye_gap, blush
Legacy fields shirt / pants / coat / bag are still understood.
"""
import math

INK = "#1c1626"

def _h():
    import characters as C
    return C

def _rgb(h): h = h.lstrip("#"); return [int(h[i:i+2], 16) for i in (0, 2, 4)]
def _hex(c): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)
def light(h, f): return _hex([v + (255 - v) * f for v in _rgb(h)])
def dark(h, f): return _hex([v * (1 - f) for v in _rgb(h)])

def taper(p0, p1, w0, w1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
    pts = [(p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2), (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2), (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2), (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)]
    return "M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" % tuple(v for p in pts for v in p)

def lerp(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

def wardrobe(c):
    top = c.get("top") or ("coat" if c.get("coat") else "shirt")
    bottom = c.get("bottom") or ("none" if top in ("dress", "coat") else "pants")   # long garments cover the hips: only the garment + thin bare legs
    return dict(
        top=top, bottom=bottom, shoes=c.get("shoes", "sneakers"),
        top_color=c.get("top_color") or c.get("shirt") or "#5b6f9a", top2=c.get("top2") or "#f2efe6",
        bottom_color=c.get("bottom_color") or c.get("pants") or "#2f3646", shoe_color=c.get("shoe_color") or c.get("shoe") or "#2a2230",
        sock=c.get("sock"), tie=c.get("tie"), scarf=c.get("scarf"), apron=c.get("apron"), belt=c.get("belt"),
        pattern=c.get("pattern", "none"), buttons=c.get("buttons", top in ("shirt", "jacket", "coat")))

HEM = {"tshirt": (470, 4), "shirt": (480, 4), "hoodie": (494, 8), "jacket": (500, 6), "coat": (600, 24), "dress": (604, 54), "tank": (470, 3)}
SLEEVE = {"tshirt": "short", "shirt": "long", "hoodie": "long", "jacket": "long", "coat": "long", "dress": "short", "tank": "none"}

def _hair(style, color, pid):
    hl = light(color, .3)
    if style == "short":
        return f'<path d="M108 140 Q112 78 200 74 Q288 78 292 140 Q272 104 200 100 Q128 104 108 140 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
    if style == "spiky":
        return f'<path d="M108 140 L120 92 L146 112 L166 74 L190 104 L214 70 L232 106 L262 80 L272 116 L292 140 Q272 108 200 104 Q128 108 108 140 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
    if style == "tuft":
        return (f'<path d="M110 146 Q130 80 200 76 Q270 80 290 146 Q250 112 200 110 Q150 112 110 146 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M198 80 Q206 50 236 62 Q216 66 214 82" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    if style == "long":
        return (f'<path d="M102 190 C92 100 146 64 200 64 C254 64 308 100 298 190 L302 300 Q280 292 266 268 L256 130 Q200 98 144 130 L134 268 Q120 292 98 300 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    if style == "bun":
        return (f'<circle cx="200" cy="60" r="30" fill="{color}" stroke="{INK}" stroke-width="5"/>'
                f'<path d="M110 144 Q116 84 200 80 Q284 84 290 144 Q272 106 200 102 Q128 106 110 144 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    return ""

def _hat(kind, color):
    if kind == "fedora":
        return (f'<path d="M100 128 Q200 98 300 128 L294 108 Q200 34 106 108 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M106 114 Q200 132 294 114 L294 124 Q200 144 106 124 Z" fill="{dark(color, .4)}"/>'
                f'<path d="M78 128 Q200 154 322 128 Q200 110 78 128 Z" fill="{dark(color, .12)}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    if kind == "deerstalker":
        return (f'<path d="M236 134 Q304 130 322 148 Q272 160 230 148 Z" fill="{dark(color, .2)}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M164 134 Q96 130 78 148 Q128 160 170 148 Z" fill="{dark(color, .2)}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M102 142 Q104 58 200 54 Q296 58 298 142 Q200 120 102 142 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M150 66 L148 130 M200 56 L200 124 M250 66 L252 130" stroke="{dark(color, .35)}" stroke-width="4" opacity=".55"/>'
                f'<path d="M176 56 Q200 36 224 56 Q200 70 176 56 Z" fill="{dark(color, .15)}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    if kind == "cap":
        return (f'<path d="M106 142 Q200 48 294 142 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<path d="M276 138 Q330 140 340 160 Q296 152 268 148 Z" fill="{dark(color, .15)}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    if kind == "beanie":
        return (f'<path d="M104 136 Q104 60 200 58 Q296 60 296 136 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                f'<rect x="98" y="120" width="204" height="26" rx="10" fill="{dark(color, .18)}" stroke="{INK}" stroke-width="5"/><circle cx="200" cy="52" r="14" fill="{color}" stroke="{INK}" stroke-width="5"/>')
    if kind == "scarf":
        return (f'<path d="M100 190 C92 106 140 60 200 60 C260 60 308 106 300 190 C294 140 252 106 200 106 C148 106 106 140 100 190 Z" fill="{color}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>')
    return ""

def _defs(cid, c, w):
    skin = c.get("skin", "#ffffff")
    pat = ""
    clip = ""
    return (f'<defs><radialGradient id="{cid}-skinG" cx=".36" cy=".3" r=".9"><stop offset="0" stop-color="{light(skin, .15) if skin != "#ffffff" else "#ffffff"}"/><stop offset=".65" stop-color="{skin}"/><stop offset="1" stop-color="{dark(skin, .1)}"/></radialGradient>'
            f'<linearGradient id="{cid}-topG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light(w["top_color"], .16)}"/><stop offset=".6" stop-color="{w["top_color"]}"/><stop offset="1" stop-color="{dark(w["top_color"], .18)}"/></linearGradient>'
            f'<linearGradient id="{cid}-botG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{light(w["bottom_color"], .1)}"/><stop offset="1" stop-color="{dark(w["bottom_color"], .2)}"/></linearGradient></defs>')

def _face(pid, c, skin, eg=44):
    """front face; ids identical to the old rig"""
    brow = c.get("brow", INK)
    def eye(side, x):
        return (f'<g id="{pid}-eye-{side}"><g id="{pid}-pupil-{side}"><ellipse cx="{x}" cy="179" rx="11.5" ry="16" fill="{INK}"/><circle cx="{x-3.5}" cy="173" r="4" fill="#fff"/><circle cx="{x+4}" cy="186" r="1.8" fill="#fff"/></g>'
                f'<g id="{pid}-lid-{side}"><rect x="{x-20}" y="154" width="40" height="46" fill="{skin}"/><path d="M{x-15} 199 Q{x} 207 {x+15} 199" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/></g>'
                f'<g id="{pid}-lidp-{side}"><rect x="{x-20}" y="154" width="40" height="46" fill="{skin}"/><path d="M{x-15} 199 Q{x} 207 {x+15} 199" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/></g></g>')
    def brw(side, x, sg):
        return f'<g id="{pid}-brow-{side}"><path d="M{x-21*sg} 152 Q{x} 138 {x+19*sg} 148" stroke="{brow}" stroke-width="6" fill="none" stroke-linecap="round"/></g>'
    ex = 200 - eg, 200 + eg
    blush = '' if c.get("blush") is False else f'<ellipse cx="{200-eg-22}" cy="214" rx="20" ry="12" fill="#ff7f8c" opacity=".45"/><ellipse cx="{200+eg+22}" cy="214" rx="20" ry="12" fill="#ff7f8c" opacity=".45"/>'
    return f'''<g id="{pid}-face">
    {blush}{brw("l", ex[0], 1)}{brw("r", ex[1], -1)}{eye("l", ex[0])}{eye("r", ex[1])}
    <g id="{pid}-eyes-happy" style="opacity:0"><path d="M{ex[0]-18} 188 Q{ex[0]} 156 {ex[0]+18} 188" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/><path d="M{ex[1]-18} 188 Q{ex[1]} 156 {ex[1]+18} 188" stroke="{INK}" stroke-width="7" fill="none" stroke-linecap="round"/></g>
    <g id="{pid}-eyes-heart" style="opacity:0"><path d="M{ex[0]} 196 C{ex[0]-32} 174 {ex[0]-17} 150 {ex[0]} 168 C{ex[0]+17} 150 {ex[0]+32} 174 {ex[0]} 196 Z" fill="#ff4f6e" stroke="{INK}" stroke-width="4"/><path d="M{ex[1]} 196 C{ex[1]-32} 174 {ex[1]-17} 150 {ex[1]} 168 C{ex[1]+17} 150 {ex[1]+32} 174 {ex[1]} 196 Z" fill="#ff4f6e" stroke="{INK}" stroke-width="4"/></g>
    <g id="{pid}-eyes-angry" style="opacity:0"><ellipse cx="{ex[0]}" cy="182" rx="12" ry="12" fill="{INK}"/><ellipse cx="{ex[1]}" cy="182" rx="12" ry="12" fill="{INK}"/><path d="M{ex[0]-22} 156 L{ex[0]+20} 176" stroke="{INK}" stroke-width="12" stroke-linecap="round"/><path d="M{ex[1]+22} 156 L{ex[1]-20} 176" stroke="{INK}" stroke-width="12" stroke-linecap="round"/></g>
    <g id="{pid}-tears" style="opacity:0"><path id="{pid}-tear-l" d="M{ex[0]-8} 202 Q{ex[0]-16} 222 {ex[0]-8} 230 Q{ex[0]} 222 {ex[0]-8} 202 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="2.5"/><path id="{pid}-tear-r" d="M{ex[1]+8} 202 Q{ex[1]+16} 222 {ex[1]+8} 230 Q{ex[1]} 222 {ex[1]+8} 202 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="2.5"/></g>
    <path id="{pid}-sweat" d="M268 108 Q280 132 268 146 Q256 132 268 108 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="3" style="opacity:0"/>
    <path id="{pid}-nose" d="M200 196 Q206 208 198 212" stroke="{INK}" stroke-width="3" fill="none" opacity=".35"/>
    <g id="{pid}-mouth">
     <path id="{pid}-mouth-closed" d="M176 238 Q200 252 224 238" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>
     <path id="{pid}-mouth-smile" d="M162 230 Q200 296 238 230 Q200 244 162 230 Z" fill="#7a1f2e" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
     <g id="{pid}-mouth-open" style="opacity:0"><path d="M170 232 Q200 224 230 232 Q234 284 200 288 Q166 284 170 232 Z" fill="#6a1626" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/><ellipse cx="200" cy="268" rx="17" ry="10" fill="#e8687a"/></g>
     <path id="{pid}-mouth-e" d="M166 236 Q200 228 234 236 Q232 258 200 260 Q168 258 166 236 Z" fill="#6a1626" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
     <ellipse id="{pid}-mouth-o" cx="200" cy="250" rx="14" ry="18" fill="#5a1220" stroke="{INK}" stroke-width="5" style="opacity:0"/>
     <path id="{pid}-mouth-smirk" d="M176 248 Q206 252 232 230" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round" style="opacity:0"/>
     <path id="{pid}-mouth-sad" d="M176 254 Q200 232 224 254" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round" style="opacity:0"/>
    </g></g>'''

def _extras_head(c, pid):
    hair = c.get("hair", INK); style = c.get("hair_style", "none")
    out = _hair(style, hair, pid) + _hat(c.get("hat", "none"), c.get("hat_color", "#3a3f55"))
    return out

def _glasses(c, front=True):
    if not c.get("glasses"): return ""
    eg = c.get("eye_gap", 44)
    return (f'<circle cx="{200-eg}" cy="178" r="28" fill="#cfe9ff" fill-opacity=".2" stroke="{INK}" stroke-width="5"/><circle cx="{200+eg}" cy="178" r="28" fill="#cfe9ff" fill-opacity=".2" stroke="{INK}" stroke-width="5"/>'
            f'<path d="M{200-eg+28} 176 Q200 168 {200+eg-28} 176" stroke="{INK}" stroke-width="5" fill="none"/>')

def _mustache(c):
    return '' if not c.get("mustache") else f'<path d="M172 226 Q186 219 200 226 Q214 219 228 226 Q214 234 200 231 Q186 234 172 226 Z" fill="{c.get("mustache_color", INK)}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'

def figure(pid, gid, c, view="front"):
    """view: front | back | side. pid = id prefix, gid = gradient prefix"""
    w = wardrobe(c); skin = c.get("skin", "#ffffff"); tf = c.get("torso_w", 1.0); eg = c.get("eye_gap", 44)
    TOP, BOT = w["top"], w["bottom"]; hem, flare = HEM.get(TOP, (480, 4)); sleeve = SLEEVE.get(TOP, "long")
    TG, BG = f"url(#{gid}-topG)", f"url(#{gid}-botG)"; tc, bc = w["top_color"], w["bottom_color"]
    side = view == "side"; back = view == "back"
    sw = (30 if side else 44) * tf
    cx = 204 if side else 200
    sh_l = (cx - sw - 2, 318) if not side else (204, 318)
    ink = f'stroke="{INK}" stroke-linejoin="round" stroke-linecap="round"'
    # ---------------------------------------------------------------- arms
    def arm(sd, near=True):
        sg = -1 if sd == "l" else 1
        if side: S, E, Wr = (204, 318), (208, 414), (218, 498)
        else: S, E, Wr = (200 + sg * (sw + 4), 318), (200 + sg * (sw + 10), 414), (200 + sg * (sw + 15), 498)
        col = tc if near else dark(tc, .22)
        line = lambda a, b: f'<path d="M{a[0]} {a[1]} L{b[0]} {b[1]}" stroke="{INK}" stroke-width="9" fill="none" stroke-linecap="round"/>'
        up = line(S, E)
        if sleeve == "short": mid = lerp(S, E, .6); up += f'<path d="{taper(S, mid, 34, 30)}" fill="{col}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><circle cx="{S[0]}" cy="{S[1]}" r="17" fill="{col}"/>'
        elif sleeve == "long": up += f'<path d="{taper(S, E, 30, 26)}" fill="{col}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><circle cx="{S[0]}" cy="{S[1]}" r="15" fill="{col}"/><circle cx="{E[0]}" cy="{E[1]}" r="13" fill="{col}" stroke="{INK}" stroke-width="4"/>'
        up += f'<circle cx="{E[0]}" cy="{E[1]}" r="{6 if sleeve != "long" else 0.1}" fill="{INK}"/>'
        fo = line(E, Wr)
        if sleeve == "long": fo += f'<path d="{taper(E, lerp(E, Wr, .9), 26, 22)}" fill="{col}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><path d="{taper(lerp(E, Wr, .78), lerp(E, Wr, .92), 25, 24)}" fill="{dark(col, .25)}"/>'
        watch = ''
        if c.get("watch") and sd == "l" and not side and not back:
            watch = f'<g id="{pid}-watch"><circle cx="{Wr[0]}" cy="{Wr[1]-12}" r="12" fill="#f4efe0" stroke="{INK}" stroke-width="4"/><path d="M{Wr[0]} {Wr[1]-12} L{Wr[0]} {Wr[1]-21} M{Wr[0]} {Wr[1]-12} L{Wr[0]-5} {Wr[1]-7}" stroke="{INK}" stroke-width="3" stroke-linecap="round"/></g>'
        hand = f'<circle cx="{Wr[0]}" cy="{Wr[1]+9}" r="9" fill="{INK}"/>'
        return f'<g id="{pid}-arm-{sd}">{up}<g id="{pid}-forearm-{sd}">{fo}{hand}{watch}</g></g>'
    # ---------------------------------------------------------------- legs
    def leg(sd, near=True):
        sg = -1 if sd == "l" else 1
        if side: dx = 7 if near else -7; Hh, K, A = (200 + dx, 540), (204 + dx, 650), (208 + dx, 760)
        else: Hh, K, A = (200 + sg * 24, 540), (200 + sg * 28, 650), (200 + sg * 32, 760)
        pant = BOT in ("pants",)
        pcol = bc if near else dark(bc, .22)
        thigh = f'<path d="M{Hh[0]} {Hh[1]} L{K[0]} {K[1]}" stroke="{INK}" stroke-width="9" fill="none" stroke-linecap="round"/>'
        shin = f'<path d="M{K[0]} {K[1]} L{A[0]} {A[1]}" stroke="{INK}" stroke-width="9" fill="none" stroke-linecap="round"/>'
        if pant:
            thigh += f'<path d="{taper(Hh, K, 38, 30)}" fill="{pcol}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><circle cx="{K[0]}" cy="{K[1]}" r="15" fill="{pcol}"/>'
            shin += f'<path d="{taper(K, lerp(K, A, .92), 30, 26)}" fill="{pcol}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
        elif w["sock"]:
            shin += f'<path d="{taper(lerp(K, A, .5), A, 17, 15)}" fill="{w["sock"]}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
        shoe_c = w["shoe_color"] if near else dark(w["shoe_color"], .2)
        dirn = 1 if side else (-1 if sd == "l" else 1)          # toes point right in profile; left foot points left, right foot right in front view
        if w["shoes"] == "none": foot = f'<circle cx="{A[0] + dirn*6}" cy="768" r="8" fill="{INK}"/>'
        else:
            if w["shoes"] == "boots": shin += f'<path d="{taper(lerp(K, A, .62), A, 26, 24)}" fill="{shoe_c}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            x0, x1 = A[0] - dirn * 12, A[0] + dirn * (44 if side else 34)
            if w["shoes"] == "heels": d = f'M{x0} 756 L{A[0]+dirn*8} 756 L{x1} 772 Q{x1+dirn*3} 780 {x1-dirn*8} 782 L{A[0]-dirn*4} 782 L{x0} 772 Z'
            else: d = f'M{x0} 756 L{A[0]+dirn*10} 756 Q{x1} 758 {x1+dirn*4} 774 Q{x1} 784 {x0-dirn*2} 782 Z'
            foot = f'<path d="{d}" fill="{shoe_c}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><path d="M{x0-dirn*2} 780 L{x1} 780" stroke="#f1ece4" stroke-width="3" stroke-linecap="round"/>'
        return f'<g id="{pid}-leg-{sd}">{thigh}<g id="{pid}-shin-{sd}">{shin}<g id="{pid}-foot-{sd}">{foot}</g></g></g>'
    # ---------------------------------------------------------------- garment
    mid = (318 + hem) / 2; fm = flare * .5
    if TOP == "dress":
        torso_d = (f"M{cx-sw} 308 Q{cx} 292 {cx+sw} 308 L{cx+sw-4} 392 Q{cx+sw+8} 430 {cx+sw+flare} {hem} Q{cx} {hem+10} {cx-sw-flare} {hem} Q{cx-sw-8} 430 {cx-sw+4} 392 Z")
    else:
        torso_d = (f"M{cx-sw} 308 Q{cx} 292 {cx+sw} 308 L{cx+sw+fm} {mid} L{cx+sw+flare} {hem} Q{cx} {hem+8} {cx-sw-flare} {hem} L{cx-sw-fm} {mid} Z")
    cid_clip = f"{gid}-clip{pid[len(gid):]}"
    pattern = ""
    if w["pattern"] != "none":
        acc = w["top2"]
        if w["pattern"] == "stripes": pattern = "".join(f'<rect x="{cx-sw-40+i*22}" y="290" width="9" height="340" fill="{acc}" opacity=".55"/>' for i in range(8))
        elif w["pattern"] == "hoops": pattern = "".join(f'<rect x="{cx-sw-60}" y="{318+i*26}" width="{2*sw+120}" height="9" fill="{acc}" opacity=".55"/>' for i in range(12))
        elif w["pattern"] == "checks": pattern = "".join(f'<rect x="{cx-sw-40+i*28}" y="290" width="12" height="340" fill="{acc}" opacity=".3"/>' for i in range(7)) + "".join(f'<rect x="{cx-sw-60}" y="{318+i*28}" width="{2*sw+120}" height="12" fill="{acc}" opacity=".3"/>' for i in range(11))
        pattern = f'<clipPath id="{cid_clip}"><path d="{torso_d}"/></clipPath><g clip-path="url(#{cid_clip})">{pattern}</g>'
    extra = ""
    if not back and not side:
        if TOP in ("shirt", "jacket", "coat"):
            extra += f'<path d="M200 304 L170 {330 if TOP!="coat" else 360} L200 {380 if TOP!="coat" else 430} L230 {330 if TOP!="coat" else 360} Z" fill="{w["top2"] if TOP!="coat" else dark(tc, .25)}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
        if TOP == "shirt": extra += f'<path d="M200 304 L178 322 L192 336 Z M200 304 L222 322 L208 336 Z" fill="{w["top2"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
        if TOP in ("jacket", "coat"):
            extra += f'<path d="M200 304 L168 350 L200 {390 if TOP=="jacket" else 450} Z M200 304 L232 350 L200 {390 if TOP=="jacket" else 450} Z" fill="{dark(tc, .15)}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
        if TOP == "tshirt": extra += f'<path d="M{200-26} 304 Q200 338 {200+26} 304" stroke="{dark(tc, .35)}" stroke-width="6" fill="none"/>'
        if TOP == "tank": extra += f'<path d="M{200-24} 304 Q200 342 {200+24} 304" stroke="{dark(tc, .35)}" stroke-width="6" fill="none"/>'
        if TOP == "dress": extra += f'<path d="M{200-26} 304 Q200 340 {200+26} 304" stroke="{dark(tc, .3)}" stroke-width="6" fill="none"/><path d="M{cx-sw+2} 392 Q{cx} 402 {cx+sw-2} 392" stroke="{w["belt"] or dark(tc, .35)}" stroke-width="9" fill="none" stroke-linecap="round"/>'
        if TOP == "hoodie": extra += f'<path d="M{200-50} 440 L{200+50} 440 L{200+58} 484 L{200-58} 484 Z" fill="{dark(tc, .12)}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><path d="M190 304 L188 350 M210 304 L212 350" stroke="{w["top2"]}" stroke-width="4" stroke-linecap="round"/>'
        if TOP == "coat": extra += f'<path d="M{cx-sw-4} 440 L{cx+sw+4} 440" stroke="{w["belt"] or dark(tc, .4)}" stroke-width="12" stroke-linecap="round"/><path d="M200 450 L200 {hem}" stroke="{INK}" stroke-width="3" opacity=".6"/>'
        if w["buttons"] and TOP in ("shirt", "jacket", "coat"): extra += "".join(f'<circle cx="204" cy="{y}" r="3.6" fill="{INK}"/>' for y in ((350, 390, 430) if TOP == "shirt" else (400, 450, 500)) if y < hem - 12)
        if w["tie"]: extra += f'<path d="M200 322 L192 344 L200 440 L208 344 Z" fill="{w["tie"]}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/><path d="M193 324 L207 324 L204 336 L196 336 Z" fill="{dark(w["tie"], .2)}"/>'
        if w["apron"]: extra += f'<path d="M{200-36} 346 L{200+36} 346 L{200+44} 520 L{200-44} 520 Z" fill="{w["apron"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/><path d="M{200-36} 346 L{200-34} 306 M{200+36} 346 L{200+34} 306" stroke="{INK}" stroke-width="4"/>'
        if c.get("badge"): extra += f'<rect x="{cx+14}" y="350" width="26" height="18" rx="3" fill="#f4efe0" stroke="{INK}" stroke-width="3"/><path d="M{cx+18} 356 L{cx+36} 356 M{cx+18} 362 L{cx+30} 362" stroke="{INK}" stroke-width="2"/>'
    if back:
        extra += f'<path d="M200 306 L200 {hem-8}" stroke="{INK}" stroke-width="3" opacity=".35"/>'
        if TOP == "hoodie": extra += f'<path d="M{200-48} 310 Q200 360 {200+48} 310" fill="{dark(tc, .15)}" stroke="{INK}" stroke-width="4"/>'
    if side:
        if TOP in ("jacket", "coat"): extra += f'<path d="M{cx} 306 L{cx+16} 350 L{cx} 410" fill="{dark(tc, .15)}" stroke="{INK}" stroke-width="3"/>'
        if w["tie"]: extra += f'<path d="M{cx+10} 322 L{cx+16} 346 L{cx+12} 430 L{cx+6} 346 Z" fill="{w["tie"]}" stroke="{INK}" stroke-width="3"/>'
        if w["apron"]: extra += f'<path d="M{cx+20} 346 L{cx+34} 520 L{cx-6} 520 L{cx+4} 346 Z" fill="{w["apron"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    if TOP == "coat":
        bl = w["belt"] or dark(tc, .4); lap = dark(tc, .14); by = 446
        tie = (f'<path d="M200 330 L193 346 L200 420 L207 346 Z" fill="{w["tie"]}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>' if w["tie"] else "")
        if view == "front":
            extra = (f'<path d="M200 306 L182 330 L200 392 L218 330 Z" fill="{w["top2"]}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>{tie}'
                     f'<path d="M200 306 L164 322 L158 410 L200 392 Z M200 306 L236 322 L242 410 L200 392 Z" fill="{lap}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                     f'<path d="M176 302 L156 284 L150 320 L170 318 Z M224 302 L244 284 L250 320 L230 318 Z" fill="{lap}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                     f'<path d="M{cx-sw-6} {by} L{cx+sw+6} {by}" stroke="{bl}" stroke-width="13" stroke-linecap="round"/><rect x="{cx-10}" y="{by-9}" width="20" height="18" rx="3" fill="#d9c27a" stroke="{INK}" stroke-width="3"/>'
                     f'<path d="M{cx+10} {by+6} Q{cx+22} {by+34} {cx+14} {by+46}" stroke="{bl}" stroke-width="9" fill="none" stroke-linecap="round"/>'
                     + "".join(f'<circle cx="{cx+dx}" cy="{y}" r="4" fill="{INK}"/>' for dx in (-13, 13) for y in (480, 520, 560))
                     + f'<path d="M{cx-sw+4} 500 L{cx-sw+30} 506 M{cx+sw-4} 500 L{cx+sw-30} 506" stroke="{INK}" stroke-width="3" opacity=".6"/>'
                     f'<path d="M200 {by+14} L200 {hem}" stroke="{INK}" stroke-width="3" opacity=".5"/>')
        elif view == "side":
            extra = (f'<path d="M{cx} 306 L{cx+16} 352 L{cx} 410" fill="{lap}" stroke="{INK}" stroke-width="3"/><path d="M{cx-10} 302 L{cx-24} 286 L{cx-26} 318 Z" fill="{lap}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                     f'<path d="M{cx-sw-6} {by} L{cx+sw+10} {by}" stroke="{bl}" stroke-width="13" stroke-linecap="round"/>{tie}')
        else:
            extra = (f'<path d="M176 302 L156 284 L150 320 L170 318 Z M224 302 L244 284 L250 320 L230 318 Z" fill="{lap}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
                     f'<path d="M{cx-sw+4} 346 Q200 362 {cx+sw-4} 346" stroke="{INK}" stroke-width="3" fill="none" opacity=".5"/>'
                     f'<path d="M{cx-sw-6} {by} L{cx+sw+6} {by}" stroke="{bl}" stroke-width="13" stroke-linecap="round"/><path d="M200 {by+8} L200 {hem}" stroke="{INK}" stroke-width="3" opacity=".6"/>')
    if w["scarf"]:
        extra += f'<path d="M{cx-34} 300 Q{cx} 326 {cx+34} 300 L{cx+30} 322 Q{cx} 346 {cx-30} 322 Z" fill="{w["scarf"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
        if not side: extra += f'<path d="M{cx+14} 326 L{cx+26} 392 L{cx+6} 388 Z" fill="{w["scarf"]}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    if c.get("bag"):
        if side or back: extra += f'<path d="M{cx-26} 310 L{cx+22} 470" stroke="{INK}" stroke-width="7" opacity=".8"/>'
        else: extra += f'<path d="M{cx-sw} 312 L{cx+sw} 460" stroke="{INK}" stroke-width="7" opacity=".8"/><rect x="{cx+sw-8}" y="446" width="46" height="40" rx="7" fill="{c.get("bag_color", "#b08850")}" stroke="{INK}" stroke-width="4"/>'
    # bottoms (hips)
    if BOT == "pants": pelvis = f'<path id="{pid}-pelvis" d="M{cx-sw*.9} 462 L{cx+sw*.9} 462 L{cx+sw*.8} 552 Q{cx} 564 {cx-sw*.8} 552 Z" fill="{BG}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    elif BOT == "shorts": pelvis = f'<path id="{pid}-pelvis" d="M{cx-sw*.9} 462 L{cx+sw*.9} 462 L{cx+sw*1.0} 580 L{cx+4} 580 L{cx} 560 L{cx-4} 580 L{cx-sw*1.0} 580 Z" fill="{BG}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    elif BOT == "skirt": pelvis = f'<path id="{pid}-pelvis" d="M{cx-sw*.9} 462 L{cx+sw*.9} 462 L{cx+sw*1.7} 600 Q{cx} 614 {cx-sw*1.7} 600 Z" fill="{BG}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    else: pelvis = f'<g id="{pid}-pelvis"></g>'
    # head
    sk = c.get("skin", "#ffffff")
    if side:
        head = f'''<path id="{pid}-head-shape" d="M200 76 C262 70 304 112 302 176 C300 240 258 282 200 280 C142 278 102 236 102 176 C102 114 142 78 200 76 Z" fill="url(#{gid}-skinG)" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>
   <ellipse cx="272" cy="214" rx="18" ry="11" fill="#ff7f8c" opacity=".45"/>
   <path d="M252 198 Q262 210 254 216" stroke="{INK}" stroke-width="3" fill="none" opacity=".4"/>
   <g id="{pid}-brow-l"><path d="M234 150 Q256 136 282 148" stroke="{c.get('brow', INK)}" stroke-width="6" fill="none" stroke-linecap="round"/></g>
   <g id="{pid}-eye-l"><g id="{pid}-pupil-l"><ellipse cx="262" cy="180" rx="11.5" ry="16" fill="{INK}"/><circle cx="258" cy="174" r="4" fill="#fff"/></g>
    <g id="{pid}-lid-l"><rect x="242" y="154" width="40" height="46" fill="{sk}"/><path d="M247 199 Q262 207 277 199" stroke="{INK}" stroke-width="5" fill="none"/></g>
    <g id="{pid}-lidp-l"><rect x="242" y="154" width="40" height="46" fill="{sk}"/><path d="M247 199 Q262 207 277 199" stroke="{INK}" stroke-width="5" fill="none"/></g></g>
   <g id="{pid}-mouth">
    <path id="{pid}-mouth-closed" d="M268 242 Q282 250 296 240" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>
    <path id="{pid}-mouth-smile" d="M262 232 Q284 282 304 230 Q284 244 262 232 Z" fill="#7a1f2e" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
    <path id="{pid}-mouth-open" d="M266 234 Q284 226 300 234 Q304 280 282 284 Q262 278 266 234 Z" fill="#6a1626" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
    <path id="{pid}-mouth-e" d="M264 238 Q284 230 302 238 Q300 256 282 258 Q266 256 264 238 Z" fill="#6a1626" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
    <ellipse id="{pid}-mouth-o" cx="284" cy="250" rx="10" ry="15" fill="#5a1220" stroke="{INK}" stroke-width="5" style="opacity:0"/>
    <path id="{pid}-mouth-smirk" d="M266 248 Q286 252 302 232" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round" style="opacity:0"/>
    <path id="{pid}-mouth-sad" d="M266 254 Q284 236 302 252" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round" style="opacity:0"/></g>
   {('<ellipse cx="262" cy="180" rx="30" ry="30" fill="#cfe9ff" fill-opacity=".2" stroke="'+INK+'" stroke-width="5"/><path d="M232 178 L170 186" stroke="'+INK+'" stroke-width="5" fill="none" stroke-linecap="round"/>') if c.get("glasses") else ""}
   {_extras_head(c, pid)}'''
        head_wrap_id = ("headsway", "head")
    elif back:
        style = c.get("hair_style", "none"); hc = c.get("hair", INK) if style != "none" else sk
        head = (f'<path id="{pid}-head-shape" d="M200 76 C264 72 300 114 298 178 C296 240 256 282 200 280 C144 282 104 240 102 178 C100 114 136 72 200 76 Z" fill="{hc if style != "none" else "url(#" + gid + "-skinG)"}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                f'<ellipse id="{pid}-ear-l" cx="102" cy="190" rx="9" ry="16" fill="{sk}" stroke="{INK}" stroke-width="4"/><ellipse id="{pid}-ear-r" cx="298" cy="190" rx="9" ry="16" fill="{sk}" stroke="{INK}" stroke-width="4"/>'
                + (_hair(style, hc, pid) if style != "none" else "") + _hat(c.get("hat", "none"), c.get("hat_color", "#3a3f55")))
    else:
        head = (f'<g id="{pid}-ears"><path id="{pid}-ear-l" d="M100 190 Q96 190 100 190" fill="none"/><path id="{pid}-ear-r" d="M300 190 Q304 190 300 190" fill="none"/></g>'
                f'<path id="{pid}-head-shape" d="M200 74 C268 70 304 114 302 178 C300 242 258 284 200 282 C142 284 100 242 98 178 C96 114 132 70 200 74 Z" fill="url(#{gid}-skinG)" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                + _face(pid, c, sk, eg) + _glasses(c) + _mustache(c) +
                f'<g id="{pid}-profile" style="opacity:0"><path d="M200 76 C262 70 304 112 302 176 C300 240 258 282 200 280 C142 278 102 236 102 176 C102 114 142 78 200 76 Z" fill="url(#{gid}-skinG)" stroke="{INK}" stroke-width="6"/>'
                f'<ellipse cx="272" cy="214" rx="18" ry="11" fill="#ff7f8c" opacity=".45"/><path d="M234 150 Q256 136 282 148" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>'
                f'<ellipse cx="262" cy="180" rx="11.5" ry="16" fill="{INK}"/><circle cx="258" cy="174" r="4" fill="#fff"/><path d="M268 242 Q282 250 296 240" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/></g>'
                + _extras_head(c, pid))
    hood = ""
    if TOP == "hoodie" and not side: hood = f'<path d="M{cx-64} 296 Q{cx-70} 250 {cx} 262 Q{cx+70} 250 {cx+64} 296 Q{cx} 336 {cx-64} 296 Z" fill="{dark(tc, .12)}" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
    body_inner = (("" if side else "") +
                  (arm("r", False) if side else "") +
                  f'<path id="{pid}-torso" d="{torso_d}" fill="{TG}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>{pattern}{extra}' +
                  (arm("l", True) if side else arm("l", True) + arm("r", True)) +
                  f'<path d="M{cx} 262 L{cx} 304" stroke="{INK}" stroke-width="9" stroke-linecap="round"/>' + hood +
                  f'<g id="{pid}-headsway"><g id="{pid}-head">{head}</g></g>')
    shadow = f'<ellipse id="{pid}-shadow" cx="{214 if side else 200}" cy="786" rx="{96 if side else 100}" ry="11" fill="#000" opacity="0.28"/>'
    legs = (leg("r", False) + leg("l", True)) if side else (leg("r") + leg("l"))
    return f'''<g id="{pid}-root" stroke-linecap="round" stroke-linejoin="round">
 {shadow}
 <g id="{pid}-turn"><g id="{pid}-life">
 {legs}{pelvis}
 <g id="{pid}-body">{body_inner}</g>
 </g></g>
</g>'''

def build_svg(cid, c, views=("f", "s", "b")):
    w = wardrobe(c)
    parts = [f'<g id="{cid}-vf">{figure(cid, cid, c, "front")}</g>']
    if "s" in views: parts.append(f'<g id="{cid}-vs" style="opacity:0">{figure(cid + "-s", cid, c, "side")}</g>')
    if "b" in views: parts.append(f'<g id="{cid}-vb" style="opacity:0">{figure(cid + "-b", cid, c, "back")}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" id="{cid}" viewBox="0 0 400 800" width="400" height="800" overflow="visible" style="overflow:visible">{_defs(cid, c, w)}'
            + "".join(parts) + '</svg>')

def rig(c, view="front"):
    tf = c.get("torso_w", 1.0); eg = c.get("eye_gap", 44)
    if view == "side":
        P = {"root": {"pivot": [200, 780]}, "turn": {"pivot": [200, 780]}, "life": {"pivot": [200, 780]}, "body": {"pivot": [200, 540]}, "torso": {"pivot": [204, 540]},
             "headsway": {"pivot": [204, 270]}, "head": {"pivot": [204, 270]},
             "arm-l": {"pivot": [204, 318]}, "forearm-l": {"pivot": [208, 414]}, "arm-r": {"pivot": [204, 318]}, "forearm-r": {"pivot": [208, 414]},
             "leg-l": {"pivot": [207, 540]}, "shin-l": {"pivot": [211, 650]}, "foot-l": {"pivot": [215, 760]},
             "leg-r": {"pivot": [193, 540]}, "shin-r": {"pivot": [197, 650]}, "foot-r": {"pivot": [201, 760]},
             "lid-l": {"pivot": [262, 154]}, "lidp-l": {"pivot": [262, 154]}, "pupil-l": {"pivot": [262, 180]}, "brow-l": {"pivot": [262, 150]},
             "mouth-open": {"pivot": [284, 240]}, "mouth-e": {"pivot": [284, 240]}, "mouth-o": {"pivot": [284, 250]}}
        return {"viewBox": [0, 0, 400, 800], "restPose": "profile facing right", "parts": P}
    sw = 44 * tf
    P = {"root": {"pivot": [200, 780]}, "turn": {"pivot": [200, 780]}, "life": {"pivot": [200, 780]}, "body": {"pivot": [200, 540]}, "torso": {"pivot": [200, 540]},
         "headsway": {"pivot": [200, 270]}, "head": {"pivot": [200, 270]}, "face": {"pivot": [200, 178]}, "profile": {"pivot": [200, 178]}, "nose": {"pivot": [200, 200]},
         "tears": {"pivot": [200, 200]}, "mouth-open": {"pivot": [200, 240]}, "mouth-e": {"pivot": [200, 240]}, "mouth-o": {"pivot": [200, 250]}}
    for side, sg in (("l", -1), ("r", 1)):
        P[f"arm-{side}"] = {"pivot": [200 + sg * (sw + 4), 318]}; P[f"forearm-{side}"] = {"pivot": [200 + sg * (sw + 10), 414]}
        P[f"leg-{side}"] = {"pivot": [200 + sg * 24, 540]}; P[f"shin-{side}"] = {"pivot": [200 + sg * 28, 650]}; P[f"foot-{side}"] = {"pivot": [200 + sg * 32, 760]}
        P[f"lid-{side}"] = {"pivot": [200 + sg * eg, 154]}; P[f"lidp-{side}"] = {"pivot": [200 + sg * eg, 154]}
        P[f"pupil-{side}"] = {"pivot": [200 + sg * eg, 180]}; P[f"brow-{side}"] = {"pivot": [200 + sg * eg, 150]}
    return {"viewBox": [0, 0, 400, 800], "restPose": "standing, arms hanging", "parts": P, "mouthShapes": ["closed", "smile", "open", "e", "o", "smirk", "sad"]}
