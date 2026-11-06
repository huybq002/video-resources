"""Parametric 2D "bean-head" cartoon characters as rigged SVG (rig v3: tapered limbs, joint caps, shaded face).
CLI:  python characters.py <spec.json> <out_dir>      -> out_dir/assets/char_<id>.svg + character-rigs.json
API:  build_svg(cid, cast_entry) -> svg string ; rig_for(cast_entry) -> dict
Cast entry keys (all optional except id): skin, shirt, pants, shoe, hair (color), hair_style (short|long|tuft|bun|bald),
hat (none|fedora|cap|scarf), glasses, mustache, coat, bag, watch, torso_w (0.8-1.2), eye_gap, brow, glow, blush (default true)

Rig v3 hierarchy (every id is prefixed with the character id):
 root > life (idle sway / breathing) > pelvis, [leg-l > shin-l > foot-l] [leg-r > shin-r > foot-r], body > torso,
   arm-l > forearm-l (hand), arm-r > forearm-r, neck, headsway (idle head drift) > head > ears, face
   (brow-l/r, eye-l/r (lid, pupil with highlights), eyes-happy/heart/angry, cheeks, nose, mouth-closed/smile/open/sad) + hair/hat.
Drawing method: every limb piece is drawn twice (ink pass, then colour pass) so outlines are even and joints are covered by round caps
on the parent segment; the child segment starts flat so the rotating joint never shows a seam.
"""
import json, math, sys, pathlib
INK = "#241726"

def _rgb(h): h = h.lstrip("#"); return [int(h[i:i+2], 16) for i in (0, 2, 4)]
def _hex(c): return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in c)
def light(h, f): return _hex([v + (255 - v) * f for v in _rgb(h)])
def dark(h, f): return _hex([v * (1 - f) for v in _rgb(h)])

def _hair(style, color, cid):
    hl = light(color, 0.35)
    if style == "short":
        return (f'<path d="M116 134 Q118 86 200 80 Q282 86 284 134 Q268 104 200 100 Q132 104 116 134 Z" fill="{color}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                f'<path d="M150 98 Q176 88 206 92" stroke="{hl}" stroke-width="5" fill="none" opacity=".55"/>')
    if style == "tuft":
        return (f'<path d="M114 150 Q130 80 200 76 Q270 80 286 150 Q250 112 200 110 Q150 112 114 150 Z" fill="{color}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                f'<path d="M198 80 Q206 52 234 62 Q216 66 214 82" fill="{color}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>')
    if style == "long":
        return (f'<path d="M108 196 C96 100 150 62 200 62 C250 62 304 100 292 196 L296 300 Q276 292 262 268 L254 132 Q200 98 146 132 L138 268 Q124 292 104 300 Z" fill="{color}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
                f'<path d="M148 90 Q184 72 224 82" stroke="{hl}" stroke-width="6" fill="none" opacity=".5"/>')
    if style == "bun":
        return (f'<circle cx="200" cy="62" r="30" fill="{color}" stroke="{INK}" stroke-width="6"/>'
                f'<path d="M116 144 Q120 90 200 86 Q280 90 284 144 Q268 106 200 102 Q132 106 116 144 Z" fill="{color}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                f'<path d="M184 52 Q196 44 212 50" stroke="{hl}" stroke-width="5" fill="none" opacity=".55"/>')
    return ""

def _hat(kind, color):
    if kind == "fedora":
        return (f'<path d="M104 130 Q200 100 296 130 L290 112 Q200 38 110 112 Z" fill="{color}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
                f'<path d="M110 118 Q200 134 290 118 L290 128 Q200 146 110 128 Z" fill="{dark(color, .35)}"/>'
                f'<path d="M84 130 Q200 154 316 130 Q200 112 84 130 Z" fill="{dark(color, .15)}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>')
    if kind == "cap":
        return (f'<path d="M112 142 Q200 54 288 142 Z" fill="{color}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
                f'<path d="M270 138 Q322 140 332 158 Q290 152 262 148 Z" fill="{dark(color, .15)}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>')
    if kind == "scarf":
        return (f'<path d="M104 192 C96 108 140 62 200 62 C260 62 304 108 296 192 C290 140 250 108 200 108 C150 108 110 140 104 192 Z" fill="{color}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>'
                f'<path d="M104 192 Q96 252 130 292 L152 262 Q120 230 120 192 Z M296 192 Q304 252 270 292 L248 262 Q280 230 280 192 Z" fill="{color}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>')
    return ""

def _taper(p0, p1, w0, w1):
    """polygon (path d) of a tapered limb from p0 (width w0) to p1 (width w1)"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L, dx / L
    a = (p0[0] + nx * w0 / 2, p0[1] + ny * w0 / 2); b = (p1[0] + nx * w1 / 2, p1[1] + ny * w1 / 2)
    c = (p1[0] - nx * w1 / 2, p1[1] - ny * w1 / 2); d = (p0[0] - nx * w0 / 2, p0[1] - ny * w0 / 2)
    return "M%.1f %.1f L%.1f %.1f L%.1f %.1f L%.1f %.1f Z" % (a + b + c + d)

def _two_pass(shapes, fill, ink_w=7):
    """shapes: list of svg elements WITHOUT fill/stroke attrs. Draw ink (thick stroke) then colour."""
    return f'<g fill="{INK}" stroke="{INK}" stroke-width="{ink_w}" stroke-linejoin="round">{shapes}</g><g fill="{fill}" stroke="none">{shapes}</g>'

def _front(cid, c, gid=None, back=False):
    gid = gid or cid
    skin = c.get("skin", "#d9b38c"); shirt = c.get("shirt", "#556"); pants = c.get("pants", "#333"); shoe = c.get("shoe", "#1d1620")
    hair = c.get("hair", "#2a1f24"); brow = c.get("brow", INK); eg = c.get("eye_gap", 40)
    tw = int(70 * c.get("torso_w", 1.0))
    G = lambda n: f"url(#{gid}-{n})"
    defs = (f'<defs>'
            f'<radialGradient id="{cid}-skinG" cx=".38" cy=".3" r=".85"><stop offset="0" stop-color="{light(skin, .22)}"/><stop offset=".6" stop-color="{skin}"/><stop offset="1" stop-color="{dark(skin, .16)}"/></radialGradient>'
            f'<linearGradient id="{cid}-skinL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{light(skin, .12)}"/><stop offset="1" stop-color="{dark(skin, .14)}"/></linearGradient>'
            f'<linearGradient id="{cid}-shirtG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{light(shirt, .2)}"/><stop offset=".55" stop-color="{shirt}"/><stop offset="1" stop-color="{dark(shirt, .2)}"/></linearGradient>'
            f'<linearGradient id="{cid}-shirtL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{light(shirt, .12)}"/><stop offset="1" stop-color="{dark(shirt, .18)}"/></linearGradient>'
            f'<linearGradient id="{cid}-pantsL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{light(pants, .12)}"/><stop offset="1" stop-color="{dark(pants, .22)}"/></linearGradient>'
            f'</defs>')
    hand_fill = G("skinL")

    def arm(side):
        sg = -1 if side == "l" else 1
        S, E, W = (200 + sg * (tw + 6), 322), (200 + sg * (tw + 14), 420), (200 + sg * (tw + 22), 505)
        upper = _two_pass(f'<path d="{_taper(S, E, 30, 25)}"/><circle cx="{S[0]}" cy="{S[1]}" r="15"/><circle cx="{E[0]}" cy="{E[1]}" r="12.5"/>', G("shirtL"))
        fore_sh = f'<path d="{_taper(E, W, 25, 20)}"/>'
        cuff = f'<path d="{_taper((E[0] + (W[0]-E[0])*.78, E[1] + (W[1]-E[1])*.78), W, 23, 22)}" fill="{dark(shirt, .3)}" stroke="none"/>'
        fore = _two_pass(fore_sh, G("shirtL")) + cuff
        hx, hy = W[0] + sg * 1, W[1] + 18
        hand = (_two_pass(f'<ellipse cx="{hx}" cy="{hy}" rx="13" ry="16"/><ellipse cx="{hx - sg*11}" cy="{hy - 4}" rx="5.5" ry="9" transform="rotate({sg*28} {hx - sg*11} {hy - 4})"/>', hand_fill, 6))
        watch = ""
        if c.get("watch") and side == "l":
            watch = (f'<g id="{cid}-watch"><circle cx="{W[0]+2}" cy="{W[1]-14}" r="14" fill="#f4efe0" stroke="{INK}" stroke-width="4"/>'
                     f'<path d="M{W[0]+2} {W[1]-14} L{W[0]+2} {W[1]-25} M{W[0]+2} {W[1]-14} L{W[0]-4} {W[1]-8}" stroke="{INK}" stroke-width="3" stroke-linecap="round"/></g>')
        return f'<g id="{cid}-arm-{side}">{upper}<g id="{cid}-forearm-{side}">{fore}{hand}{watch}</g></g>'

    def leg(side):
        sg = -1 if side == "l" else 1
        H, K, A = (200 + sg * 28, 528), (200 + sg * 33, 648), (200 + sg * 38, 764)
        thigh = _two_pass(f'<path d="{_taper(H, K, 40, 30)}"/><circle cx="{H[0]}" cy="{H[1]}" r="20"/><circle cx="{K[0]}" cy="{K[1]}" r="15"/>', G("pantsL"))
        shin = _two_pass(f'<path d="{_taper(K, A, 30, 22)}"/>', G("pantsL"))
        tx = A[0] + sg * 36
        shoe_d = f'M{A[0]-sg*14} 758 L{A[0]+sg*12} 758 Q{tx} 760 {tx+sg*4} 776 Q{tx} 786 {A[0]-sg*16} 782 Z'
        foot = _two_pass(f'<path d="{shoe_d}"/>', shoe, 6) + f'<path d="M{A[0]-sg*16} 780 L{tx+sg*2} 780" stroke="#f1ece4" stroke-width="4" stroke-linecap="round"/>'
        return f'<g id="{cid}-leg-{side}">{thigh}<g id="{cid}-shin-{side}">{shin}<g id="{cid}-foot-{side}">{foot}</g></g></g>'

    extra_head = _hair(c.get("hair_style", "short" if c.get("hat", "none") == "none" else "bald"), hair, cid)
    extra_head += _hat(c.get("hat", "none"), c.get("hat_color", "#2a2f3a"))
    glasses_profile = ""
    if c.get("glasses"):
        glasses_profile = (f'<ellipse cx="254" cy="178" rx="25" ry="26" fill="#bfe3ff" fill-opacity=".18" stroke="{INK}" stroke-width="5"/>'
                           f'<path d="M229 176 L176 184" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>')
        extra_head += (f'<g id="{cid}-glasses">' + (f'<circle cx="{200-eg}" cy="177" r="27" fill="#bfe3ff" fill-opacity=".18" stroke="{INK}" stroke-width="5"/><circle cx="{200+eg}" cy="177" r="27" fill="#bfe3ff" fill-opacity=".18" stroke="{INK}" stroke-width="5"/>'
                       f'<path d="M{200-eg+27} 175 Q200 168 {200+eg-27} 175" stroke="{INK}" stroke-width="5" fill="none"/>'
                       f'<path d="M{200-eg-14} 162 L{200-eg-4} 156" stroke="#fff" stroke-width="3" opacity=".7"/>') + '</g>')
    if c.get("mustache"):
        extra_head += f'<path d="M162 224 Q182 214 200 224 Q218 214 238 224 Q220 240 200 232 Q180 240 162 224 Z" fill="{c.get("mustache_color", "#8a8690")}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
    extra_body = ""
    if c.get("coat"):
        extra_body += (f'<path d="M198 304 L198 548" stroke="{INK}" stroke-width="4"/>'
                       f'<path d="M200 300 L164 366 L200 346 Z M200 300 L236 366 L200 346 Z" fill="{c.get("coat_color", "#2c4358")}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
                       f'<circle cx="206" cy="420" r="4" fill="{INK}"/><circle cx="206" cy="470" r="4" fill="{INK}"/>')
    else:
        extra_body += (f'<path d="M{200-24} 298 Q200 328 {200+24} 298" stroke="{dark(shirt, .35)}" stroke-width="6" fill="none" stroke-linecap="round"/>'
                       f'<path d="M{200-tw+22} 430 Q{200-tw+34} 470 {200-tw+30} 520" stroke="{dark(shirt, .3)}" stroke-width="4" fill="none" opacity=".35" stroke-linecap="round"/>')
    if c.get("bag"):
        extra_body += (f'<path d="M262 336 L294 476 L238 476 Z" fill="{c.get("bag_color", "#cdb98f")}" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                       f'<path d="M276 346 Q292 306 262 322" stroke="{INK}" stroke-width="6" fill="none" stroke-linecap="round"/>')
    if back:
        head_d = "M200 68 C264 68 294 118 290 178 C286 240 248 280 200 280 C152 280 114 240 110 178 C106 118 136 68 200 68 Z"
        style_ = c.get("hair_style", "short" if c.get("hat", "none") == "none" else "bald")
        hcol = hair if style_ != "bald" else skin
        extra_head = (f'<path d="{head_d}" fill="{hcol}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>'
                      f'<path d="M150 96 Q190 78 236 92" stroke="{light(hcol, .35)}" stroke-width="6" fill="none" opacity=".5"/>'
                      + _hair(style_, hair, cid) + _hat(c.get("hat", "none"), c.get("hat_color", "#2a2f3a")))
        extra_body = (f'<path d="M200 306 L200 540" stroke="{dark(shirt, .3)}" stroke-width="4" opacity=".5"/>'
                      f'<path d="M{200-tw+10} 330 Q200 350 {200+tw-10} 330" stroke="{dark(shirt, .3)}" stroke-width="4" fill="none" opacity=".4"/>')
        if c.get("bag"):
            extra_body += (f'<path d="M{200-tw} 330 L{200+tw} 470" stroke="{INK}" stroke-width="7" opacity=".8"/>')
    cheeks = '' if c.get("blush") is False else (f'<ellipse cx="{200-eg-14}" cy="214" rx="17" ry="10" fill="#ff7f8c" opacity=".3"/><ellipse cx="{200+eg+14}" cy="214" rx="17" ry="10" fill="#ff7f8c" opacity=".3"/>')
    torso_d = (f"M{200-tw} 302 Q200 278 {200+tw} 302 Q{200+tw+12} 336 {200+tw-2} 410 L{200+tw-9} 538 Q200 556 {200-tw+9} 538 L{200-tw+2} 410 Q{200-tw-12} 336 {200-tw} 302 Z")
    def eye(side, x):
        return (f'<g id="{cid}-eye-{side}"><ellipse cx="{x}" cy="176" rx="17" ry="21" fill="#fff" stroke="{INK}" stroke-width="4"/>'
                f'<g id="{cid}-pupil-{side}"><circle cx="{x}" cy="179" r="10" fill="{INK}"/><circle cx="{x-3.5}" cy="174" r="3.4" fill="#fff"/><circle cx="{x+4}" cy="184" r="1.7" fill="#fff"/></g>'
                f'<g id="{cid}-lid-{side}"><rect x="{x-20}" y="152" width="40" height="48" fill="{skin}"/><path d="M{x-17} 199 Q{x} 207 {x+17} 199" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/></g>'
                f'<g id="{cid}-lidp-{side}" style="transform-box:fill-box"><rect x="{x-20}" y="152" width="40" height="48" fill="{skin}"/><path d="M{x-17} 199 Q{x} 207 {x+17} 199" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/></g>'
                f'<path d="M{x-18} 160 Q{x} 151 {x+18} 160" stroke="{INK}" stroke-width="4.5" fill="none" stroke-linecap="round"/></g>')
    def brow_path(x, sg):
        return (f'<path d="M{x-24*sg} 152 Q{x} 138 {x+22*sg} 147 Q{x} 144 {x-24*sg} 158 Z" fill="{brow}" stroke="{brow}" stroke-width="2.5" stroke-linejoin="round"/>')
    return defs, f'''<g id="{cid}-root" stroke-linecap="round" stroke-linejoin="round">
 <ellipse id="{cid}-shadow" cx="200" cy="784" rx="108" ry="12" fill="#000" opacity="0.32"/>
 <g id="{cid}-turn"><g id="{cid}-life">
 {leg("r")}{leg("l")}
 <ellipse id="{cid}-pelvis" cx="200" cy="540" rx="{tw+4}" ry="26" fill="{pants}" stroke="{INK}" stroke-width="6"/>
 <g id="{cid}-body">
  <path id="{cid}-torso" d="{torso_d}" fill="{G('shirtG')}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>
  {extra_body}
  {arm("l")}
  {arm("r")}
  <rect id="{cid}-neck" x="186" y="258" width="28" height="46" rx="10" fill="{G('skinL')}" stroke="{INK}" stroke-width="5"/>
  <ellipse cx="200" cy="288" rx="30" ry="9" fill="#000" opacity=".16"/>
  <g id="{cid}-headsway"><g id="{cid}-head">
   <g id="{cid}-ears"><ellipse id="{cid}-ear-l" cx="112" cy="184" rx="11" ry="19" fill="{skin}" stroke="{INK}" stroke-width="5"/><ellipse id="{cid}-ear-r" cx="288" cy="184" rx="11" ry="19" fill="{skin}" stroke="{INK}" stroke-width="5"/></g>
   <path id="{cid}-head-shape" d="M200 68 C264 68 294 118 290 178 C286 240 248 280 200 280 C152 280 114 240 110 178 C106 118 136 68 200 68 Z" fill="{G('skinG')}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>
   <ellipse cx="164" cy="116" rx="36" ry="17" fill="#fff" opacity=".16" transform="rotate(-24 164 116)"/>
   <g id="{cid}-face">
    {cheeks}
    <g id="{cid}-brow-l">{brow_path(200-eg, 1)}</g>
    <g id="{cid}-brow-r">{brow_path(200+eg, -1)}</g>
    {eye("l", 200-eg)}{eye("r", 200+eg)}
    <g id="{cid}-eyes-happy" style="opacity:0"><path d="M{200-eg-17} 186 Q{200-eg} 156 {200-eg+17} 186" stroke="{INK}" stroke-width="7" fill="none"/><path d="M{200+eg-17} 186 Q{200+eg} 156 {200+eg+17} 186" stroke="{INK}" stroke-width="7" fill="none"/></g>
    <g id="{cid}-eyes-heart" style="opacity:0"><path d="M{200-eg} 194 C{200-eg-32} 172 {200-eg-17} 148 {200-eg} 166 C{200-eg+17} 148 {200-eg+32} 172 {200-eg} 194 Z" fill="#ff4f6e" stroke="{INK}" stroke-width="4"/><path d="M{200+eg} 194 C{200+eg-32} 172 {200+eg-17} 148 {200+eg} 166 C{200+eg+17} 148 {200+eg+32} 172 {200+eg} 194 Z" fill="#ff4f6e" stroke="{INK}" stroke-width="4"/></g>
    <g id="{cid}-eyes-angry" style="opacity:0"><ellipse cx="{200-eg}" cy="182" rx="17" ry="15" fill="#fff" stroke="{INK}" stroke-width="4"/><ellipse cx="{200+eg}" cy="182" rx="17" ry="15" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="{200-eg+3}" cy="184" r="8" fill="{INK}"/><circle cx="{200+eg-3}" cy="184" r="8" fill="{INK}"/><path d="M{200-eg-22} 156 L{200-eg+20} 178" stroke="{INK}" stroke-width="13" stroke-linecap="round"/><path d="M{200+eg+22} 156 L{200+eg-20} 178" stroke="{INK}" stroke-width="13" stroke-linecap="round"/></g>
    <g id="{cid}-tears" style="opacity:0"><path id="{cid}-tear-l" d="M{200-eg-8} 200 Q{200-eg-16} 220 {200-eg-8} 228 Q{200-eg} 220 {200-eg-8} 200 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="2.5"/><path id="{cid}-tear-r" d="M{200+eg+8} 200 Q{200+eg+16} 220 {200+eg+8} 228 Q{200+eg} 220 {200+eg+8} 200 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="2.5"/></g>
    <path id="{cid}-sweat" d="M262 112 Q274 134 262 146 Q250 134 262 112 Z" fill="#8fd3ff" stroke="{INK}" stroke-width="3" style="opacity:0"/>
    <path id="{cid}-nose" d="M200 192 Q212 214 197 220" stroke="{dark(skin, .45)}" stroke-width="5" fill="none"/>
    <g id="{cid}-mouth">
     <path id="{cid}-mouth-closed" d="M174 242 Q200 252 226 242" stroke="{INK}" stroke-width="6" fill="none"/>
     <path id="{cid}-mouth-smile" d="M170 238 Q200 268 230 238 Q200 250 170 238 Z" fill="#7a2434" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
     <g id="{cid}-mouth-open" style="opacity:0"><path d="M176 238 Q200 230 224 238 Q224 274 200 276 Q176 274 176 238 Z" fill="#6a1d2c" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/><ellipse cx="200" cy="265" rx="13" ry="7" fill="#e0687a"/></g>
     <path id="{cid}-mouth-e" d="M172 240 Q200 234 228 240 Q226 256 200 258 Q174 256 172 240 Z" fill="#6a1d2c" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>
     <ellipse id="{cid}-mouth-o" cx="200" cy="248" rx="13" ry="15" fill="#5a1626" stroke="{INK}" stroke-width="5" style="opacity:0"/>
     <path id="{cid}-mouth-smirk" d="M176 248 Q204 250 228 232" stroke="{INK}" stroke-width="6" fill="none" style="opacity:0"/>
     <path id="{cid}-mouth-sad" d="M176 252 Q200 234 224 252" stroke="{INK}" stroke-width="6" fill="none" style="opacity:0"/>
    </g>
   </g>
   <g id="{cid}-profile" style="opacity:0">
    <path d="M196 68 C252 66 290 102 292 152 L306 194 Q311 204 298 207 L294 222 Q298 232 289 238 L287 256 Q270 284 222 284 C168 284 122 248 116 190 C110 118 140 70 196 68 Z" fill="{G('skinG')}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>
    <ellipse cx="170" cy="196" rx="14" ry="22" fill="{skin}" stroke="{INK}" stroke-width="5"/><path d="M164 188 Q172 200 166 210" stroke="{INK}" stroke-width="3" fill="none"/>
    <ellipse cx="262" cy="216" rx="14" ry="9" fill="#ff7f8c" opacity=".3"/>
    <path d="M232 152 Q252 142 276 150 Q254 150 232 160 Z" fill="{brow}" stroke="{brow}" stroke-width="2.5"/>
    <g id="{cid}-pprofile-eye"><ellipse cx="254" cy="176" rx="14" ry="19" fill="#fff" stroke="{INK}" stroke-width="4"/><circle cx="260" cy="179" r="9" fill="{INK}"/><circle cx="256" cy="174" r="3" fill="#fff"/></g>
    <path d="M262 242 Q276 246 288 240" stroke="{INK}" stroke-width="6" fill="none"/>
    {glasses_profile}
   </g>
   {extra_head}
  </g></g>
 </g>
 </g></g>
</g>'''

PROFILE_D = "M196 68 C252 66 290 102 292 152 L306 194 Q311 204 298 207 L294 222 Q298 232 289 238 L287 256 Q270 284 222 284 C168 284 122 248 116 190 C110 118 140 70 196 68 Z"

def _side(pid, gid, c):
    """full-body profile facing screen-right (the engine mirrors it for left). near arm/leg = 'l', far arm/leg = 'r'."""
    skin = c.get("skin", "#d9b38c"); shirt = c.get("shirt", "#556"); pants = c.get("pants", "#333"); shoe = c.get("shoe", "#1d1620")
    hair = c.get("hair", "#2a1f24"); brow = c.get("brow", INK); tw = int(70 * c.get("torso_w", 1.0)); G = lambda n: f"url(#{gid}-{n})"
    fs, fp = dark(shirt, .28), dark(pants, .3)
    def arm(side, near):
        S, E, W = (204, 322), (210, 420), (222, 505); fill = G("shirtL") if near else fs
        up = _two_pass(f'<path d="{_taper(S, E, 30, 25)}"/><circle cx="{S[0]}" cy="{S[1]}" r="15"/><circle cx="{E[0]}" cy="{E[1]}" r="12.5"/>', fill)
        fo = _two_pass(f'<path d="{_taper(E, W, 25, 20)}"/>', fill)
        hand = _two_pass(f'<ellipse cx="{W[0]+2}" cy="{W[1]+18}" rx="13" ry="16"/><ellipse cx="{W[0]+13}" cy="{W[1]+12}" rx="5" ry="9" transform="rotate(-30 {W[0]+13} {W[1]+12})"/>', G("skinL") if near else dark(skin, .18), 6)
        return f'<g id="{pid}-arm-{side}">{up}<g id="{pid}-forearm-{side}">{fo}{hand}</g></g>'
    def leg(side, near):
        dx = 6 if near else -6; H, K, A = (200 + dx, 528), (204 + dx, 648), (208 + dx, 764); fill = G("pantsL") if near else fp
        thigh = _two_pass(f'<path d="{_taper(H, K, 40, 30)}"/><circle cx="{H[0]}" cy="{H[1]}" r="20"/><circle cx="{K[0]}" cy="{K[1]}" r="15"/>', fill)
        shin = _two_pass(f'<path d="{_taper(K, A, 30, 22)}"/>', fill)
        shoe_d = f'M{A[0]-16} 758 L{A[0]+10} 758 Q{A[0]+46} 760 {A[0]+50} 777 Q{A[0]+44} 787 {A[0]-18} 783 Z'
        foot = _two_pass(f'<path d="{shoe_d}"/>', shoe if near else dark(shoe, .2), 6) + f'<path d="M{A[0]-18} 781 L{A[0]+46} 781" stroke="#f1ece4" stroke-width="4" stroke-linecap="round"/>'
        return f'<g id="{pid}-leg-{side}">{thigh}<g id="{pid}-shin-{side}">{shin}<g id="{pid}-foot-{side}">{foot}</g></g></g>'
    style_ = c.get("hair_style", "short" if c.get("hat", "none") == "none" else "bald")
    top = _hair(style_, hair, pid) + _hat(c.get("hat", "none"), c.get("hat_color", "#2a2f3a"))
    gl = ""
    if c.get("glasses"):
        gl = (f'<ellipse cx="254" cy="178" rx="25" ry="26" fill="#bfe3ff" fill-opacity=".18" stroke="{INK}" stroke-width="5"/>'
              f'<path d="M229 176 L176 184" stroke="{INK}" stroke-width="5" fill="none" stroke-linecap="round"/>')
    torso_d = f"M{200-34} 302 Q200 280 {200+30} 302 Q{200+44} 350 {200+34} 420 L{200+28} 538 Q200 554 {200-28} 538 L{200-34} 420 Q{200-44} 350 {200-34} 302 Z"
    mouths = (f'<path id="{pid}-mouth-closed" d="M262 242 Q276 246 288 240" stroke="{INK}" stroke-width="6" fill="none"/>'
              f'<path id="{pid}-mouth-smile" d="M260 238 Q278 258 290 237" stroke="{INK}" stroke-width="6" fill="none" style="opacity:0"/>'
              f'<path id="{pid}-mouth-open" d="M262 240 Q276 237 288 238 L286 258 Q272 264 262 252 Z" fill="#6a1d2c" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>'
              f'<path id="{pid}-mouth-e" d="M262 241 Q276 238 288 239 L286 252 Q272 255 262 249 Z" fill="#6a1d2c" stroke="{INK}" stroke-width="5" stroke-linejoin="round" style="opacity:0"/>'
              f'<ellipse id="{pid}-mouth-o" cx="278" cy="248" rx="8" ry="10" fill="#5a1626" stroke="{INK}" stroke-width="5" style="opacity:0"/>'
              f'<path id="{pid}-mouth-smirk" d="M262 248 Q278 250 289 236" stroke="{INK}" stroke-width="6" fill="none" style="opacity:0"/>'
              f'<path id="{pid}-mouth-sad" d="M262 252 Q276 240 288 250" stroke="{INK}" stroke-width="6" fill="none" style="opacity:0"/>')
    return f"""<g id="{pid}-root" stroke-linecap="round" stroke-linejoin="round">
 <ellipse cx="214" cy="784" rx="100" ry="12" fill="#000" opacity="0.32"/>
 <g id="{pid}-turn"><g id="{pid}-life">
 {leg("r", False)}{leg("l", True)}
 <ellipse id="{pid}-pelvis" cx="206" cy="540" rx="{int(tw*.5)+6}" ry="26" fill="{pants}" stroke="{INK}" stroke-width="6"/>
 <g id="{pid}-body">
  {arm("r", False)}
  <path id="{pid}-torso" d="{torso_d}" fill="{G('shirtG')}" stroke="{INK}" stroke-width="7" stroke-linejoin="round"/>
  <path d="M{200-26} 298 Q206 322 {200+24} 300" stroke="{dark(shirt, .35)}" stroke-width="6" fill="none"/>
  {arm("l", True)}
  <rect id="{pid}-neck" x="190" y="258" width="26" height="46" rx="10" fill="{G('skinL')}" stroke="{INK}" stroke-width="5"/>
  <g id="{pid}-headsway"><g id="{pid}-head">
   <path id="{pid}-head-shape" d="{PROFILE_D}" fill="{G('skinG')}" stroke="{INK}" stroke-width="8" stroke-linejoin="round"/>
   <ellipse cx="170" cy="196" rx="14" ry="22" fill="{skin}" stroke="{INK}" stroke-width="5"/><path d="M164 188 Q172 200 166 210" stroke="{INK}" stroke-width="3" fill="none"/>
   <ellipse cx="262" cy="216" rx="14" ry="9" fill="#ff7f8c" opacity=".3"/>
   <g id="{pid}-brow-l"><path d="M232 152 Q254 140 278 150 Q254 150 232 160 Z" fill="{brow}" stroke="{brow}" stroke-width="2.5"/></g>
   <g id="{pid}-eye-l"><ellipse cx="254" cy="176" rx="15" ry="20" fill="#fff" stroke="{INK}" stroke-width="4"/>
    <g id="{pid}-pupil-l"><circle cx="260" cy="179" r="9.5" fill="{INK}"/><circle cx="256" cy="174" r="3.2" fill="#fff"/></g>
    <g id="{pid}-lid-l"><rect x="236" y="154" width="38" height="46" fill="{skin}"/><path d="M238 199 Q254 207 270 199" stroke="{INK}" stroke-width="5" fill="none"/></g>
    <g id="{pid}-lidp-l"><rect x="236" y="154" width="38" height="46" fill="{skin}"/><path d="M238 199 Q254 207 270 199" stroke="{INK}" stroke-width="5" fill="none"/></g>
    <path d="M238 160 Q254 150 272 160" stroke="{INK}" stroke-width="4.5" fill="none"/></g>
   <g id="{pid}-mouth">{mouths}</g>
   {gl}{top}
  </g></g>
 </g>
 </g></g>
</g>"""

def build_svg_bean(cid, c, views=("f", "s", "b")):
    """one <svg> holding the front, side (profile, faces right) and back drawings; the engine toggles the visible one."""
    defs, front = _front(cid, c)
    parts = [f'<g id="{cid}-vf">{front}</g>']
    if "s" in views: parts.append(f'<g id="{cid}-vs" style="opacity:0">{_side(cid + "-s", cid, c)}</g>')
    if "b" in views: parts.append(f'<g id="{cid}-vb" style="opacity:0">{_front(cid + "-b", c, cid, back=True)[1]}</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" id="{cid}" viewBox="0 0 400 800" width="400" height="800" overflow="visible" style="overflow:visible">'
            f'{defs}' + "".join(parts) + '</svg>')

def rig_side_bean(c):
    g = c.get("eye_gap", 40)
    P = {"root": {"pivot": [200, 780]}, "turn": {"pivot": [200, 780], "parent": "root"}, "life": {"pivot": [200, 780], "parent": "turn"},
         "body": {"pivot": [200, 540], "parent": "life"}, "torso": {"pivot": [206, 540], "parent": "body"},
         "headsway": {"pivot": [206, 270], "parent": "body"}, "head": {"pivot": [206, 270], "parent": "headsway"},
         "arm-l": {"pivot": [204, 322], "parent": "body"}, "forearm-l": {"pivot": [210, 420], "parent": "arm-l"},
         "arm-r": {"pivot": [204, 322], "parent": "body"}, "forearm-r": {"pivot": [210, 420], "parent": "arm-r"},
         "leg-l": {"pivot": [206, 528], "parent": "life"}, "shin-l": {"pivot": [210, 648], "parent": "leg-l"}, "foot-l": {"pivot": [214, 764], "parent": "shin-l"},
         "leg-r": {"pivot": [194, 528], "parent": "life"}, "shin-r": {"pivot": [198, 648], "parent": "leg-r"}, "foot-r": {"pivot": [202, 764], "parent": "shin-r"},
         "lid-l": {"pivot": [254, 154]}, "lidp-l": {"pivot": [254, 154]}, "pupil-l": {"pivot": [254, 178]}, "brow-l": {"pivot": [254, 150]},
         "mouth-open": {"pivot": [276, 244]}, "mouth-e": {"pivot": [276, 244]}, "mouth-o": {"pivot": [278, 248]}}
    return {"viewBox": [0, 0, 400, 800], "restPose": "profile facing right", "parts": P}

def rig_for_bean(c):
    tw = int(70 * c.get("torso_w", 1.0)); g = c.get("eye_gap", 40)
    P = {"root": {"pivot": [200, 780]}, "turn": {"pivot": [200, 780], "parent": "root"},
         "face": {"pivot": [200, 176], "parent": "head"}, "profile": {"pivot": [200, 176], "parent": "head"}, "nose": {"pivot": [200, 200], "parent": "face"},
         "tears": {"pivot": [200, 200], "parent": "face"}, "mouth-open": {"pivot": [200, 240], "parent": "face"}, "mouth-e": {"pivot": [200, 240], "parent": "face"}, "mouth-o": {"pivot": [200, 240], "parent": "face"}, "life": {"pivot": [200, 780], "parent": "turn"},
         "body": {"pivot": [200, 540], "parent": "life", "rotate": [-8, 8]}, "torso": {"pivot": [200, 540], "parent": "body", "scaleY": [0.97, 1.04]},
         "headsway": {"pivot": [200, 270], "parent": "body", "rotate": [-4, 4]}, "head": {"pivot": [200, 270], "parent": "headsway", "rotate": [-14, 14]}}
    for side, sg in (("l", -1), ("r", 1)):
        P[f"arm-{side}"] = {"pivot": [200 + sg * (tw + 6), 322], "parent": "body", "rotate": [-40, 170] if side == "l" else [-170, 40]}
        P[f"forearm-{side}"] = {"pivot": [200 + sg * (tw + 14), 420], "parent": f"arm-{side}", "rotate": [-20, 130] if side == "l" else [-130, 20]}
        P[f"leg-{side}"] = {"pivot": [200 + sg * 28, 528], "parent": "life", "rotate": [-35, 35]}
        P[f"shin-{side}"] = {"pivot": [200 + sg * 33, 648], "parent": f"leg-{side}", "rotate": [-10, 70]}
        P[f"foot-{side}"] = {"pivot": [200 + sg * 38, 764], "parent": f"shin-{side}", "rotate": [-25, 25]}
        P[f"lid-{side}"] = {"pivot": [200 + sg * g, 152], "scaleY": [0, 1]}
        P[f"lidp-{side}"] = {"pivot": [200 + sg * g, 152], "scaleY": [0, 1]}
        P[f"pupil-{side}"] = {"pivot": [200 + sg * g, 178], "range": [6, 5]}
        P[f"brow-{side}"] = {"pivot": [200 + sg * g, 148], "rotate": [-15, 15]}
    return {"viewBox": [0, 0, 400, 800], "restPose": "standing, arms hanging, eyes open, mouth closed", "parts": P, "mouthShapes": ["closed", "smile", "open", "e", "o", "smirk", "sad"]}

def _stick(c): return c.get("style", "stick") != "bean"

def build_svg(cid, c, views=("f", "s", "b")):
    """default style = stick figure with a story wardrobe (characters_stick.py); style 'bean' keeps the old shaded bean-head characters"""
    if _stick(c):
        import characters_stick as S
        return S.build_svg(cid, c, views)
    return build_svg_bean(cid, c, views)

def rig_for(c):
    if _stick(c):
        import characters_stick as S
        return S.rig(c, "front")
    return rig_for_bean(c)

def rig_side(c):
    if _stick(c):
        import characters_stick as S
        return S.rig(c, "side")
    return rig_side_bean(c)

def write_all(cast, out_dir):
    out = pathlib.Path(out_dir) / "assets"; out.mkdir(parents=True, exist_ok=True)
    rigs = {}
    for c in cast:
        if c.get("narrator"): continue                                   # the narrator has no body on screen
        target = out / f"{c['id']}.svg"                                   # contract name: assets/<id>.svg
        if not (c.get("external") and target.exists()):                    # never overwrite a Gemini SVG the user placed
            target.write_text(build_svg(c["id"], c), encoding="utf-8")
        rigs[c["id"]] = rig_for(c); rigs[c["id"] + ":s"] = rig_side(c); rigs[c["id"] + ":b"] = rig_for(c)
    (out / "character-rigs.json").write_text(json.dumps(rigs, indent=1), encoding="utf-8")
    return rigs

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8")); write_all(spec["cast"], sys.argv[2]); print("ok")
